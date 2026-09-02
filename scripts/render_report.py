#!/usr/bin/env python3
"""Render a review-only before/after report from a content brief and writer result."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import sys
from pathlib import Path
from typing import Any


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def fenced(value: str) -> str:
    longest = 0
    current = 0
    for char in value:
        if char == "`":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    marker = "`" * max(3, longest + 1)
    return f"{marker}text\n{value}\n{marker}"


def location_label(location: dict[str, Any]) -> str:
    label = str(location.get("path", "unknown"))
    if location.get("line") is not None:
        label += f":{location['line']}"
    if location.get("symbol"):
        label += f" · {location['symbol']}"
    return label


def writer_label(brief: dict[str, Any], result: dict[str, Any]) -> str:
    result_pipeline = result.get("pipeline")
    brief_pipeline = brief.get("writing_pipeline")
    writer = result.get("writer")
    if not isinstance(writer, dict) and isinstance(result_pipeline, dict):
        writer = result_pipeline.get("writer")
    if not isinstance(writer, dict) and isinstance(brief_pipeline, dict):
        writer = brief_pipeline.get("writer")
    if not isinstance(writer, dict):
        writer = {}
    name = result.get("model") or writer.get("model") or writer.get("name") or "host"
    return str(name)


def postprocessor_label(brief: dict[str, Any], result: dict[str, Any]) -> str:
    result_pipeline = result.get("pipeline")
    brief_pipeline = brief.get("writing_pipeline")
    postprocessors: Any = None
    if isinstance(result_pipeline, dict):
        postprocessors = result_pipeline.get("postprocessors")
    if not isinstance(postprocessors, list) and isinstance(brief_pipeline, dict):
        postprocessors = brief_pipeline.get("postprocessors")
    if not isinstance(postprocessors, list) or not postprocessors:
        return "未使用"
    names = [
        str(item.get("name", "unknown"))
        for item in postprocessors
        if isinstance(item, dict)
    ]
    return "、".join(names) or "未使用"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", type=Path)
    parser.add_argument("result", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--recommendations", type=Path)
    args = parser.parse_args()

    try:
        brief = read_object(args.brief)
        result = read_object(args.result)
        run = brief["run"]
        items = brief["items"]
        result_by_id = {
            item.get("id"): item
            for item in result.get("items", [])
            if isinstance(item, dict) and item.get("id")
        }
        validation = result.get("validation", {})
        if not isinstance(validation, dict):
            validation = {}
        recommendation_counts: Counter[str] = Counter()
        inventory_items: list[dict[str, Any]] = []
        coverage: dict[str, Any] = {}
        if args.inventory:
            inventory = read_object(args.inventory)
            raw_coverage = inventory.get("coverage", {})
            if isinstance(raw_coverage, dict):
                coverage = raw_coverage
            inventory_items = [
                item for item in inventory.get("items", []) if isinstance(item, dict)
            ]
        inventory_decisions = Counter(
            item.get("scope_decision", "unknown") for item in inventory_items
        )
        result_decisions = Counter(
            item.get("decision", "unknown")
            for item in result.get("items", [])
            if isinstance(item, dict)
        )
        blocked_items = [
            item for item in brief.get("blocked_items", []) if isinstance(item, dict)
        ]
        if args.recommendations:
            recommendations = read_object(args.recommendations)
            recommendation_counts.update(
                item.get("type", "other")
                for item in recommendations.get("items", [])
                if isinstance(item, dict)
            )

        lines = [
            f"# Userese 内容提案：{run.get('project', 'Untitled project')}",
            "",
            "> 本文档仅供核实。产品源文件未修改，代码未提交，生产环境未发布。",
            "",
            "## 内容策略",
            "",
            f"- 页面：{run.get('surface', {}).get('name', '')}",
            f"- 页面任务：{run.get('page_job', '')}",
            f"- 主要受众：{run.get('audience', '')}",
            f"- 沟通目标：{run.get('communication_goal', '')}",
            f"- Writer：{writer_label(brief, result)}",
            f"- 去 AI 味步骤：{postprocessor_label(brief, result)}",
            f"- 策略来源：{run.get('profile_source', '')}",
            "",
            "## 提案范围",
            "",
            f"- 程序已发现：{coverage.get('discovered_count', len(inventory_items)) if args.inventory else '未提供 inventory'}",
            f"- 模型已详细分析：{coverage.get('analyzed_count', len(inventory_items)) if args.inventory else '未提供 inventory'}",
            f"- 已发现但分组展示：{coverage.get('grouped_count', 0) if args.inventory else '未提供 inventory'}",
            f"- 用户已选择：{inventory_decisions['include'] if args.inventory else '未提供 inventory'}",
            f"- 用户排除：{inventory_decisions['exclude'] if args.inventory else '未提供 inventory'}",
            f"- 进入 Writer：{len(items)} 条",
            f"- Writer 已处理：{len(result_by_id)} 条",
            "- 用户已批准应用：0 条（本报告仍是待核实提案）",
            f"- 因知识缺口阻塞：{len(blocked_items)} 条",
            f"- Writer 建议改写：{result_decisions['rewrite']} 条",
            f"- Writer 建议保留：{result_decisions['keep']} 条",
            f"- Writer 需要更多上下文：{result_decisions['needs-context']} 条",
            f"- 结构建议：{recommendation_counts['structure']} 条（独立审批）",
            f"- 产品建议：{recommendation_counts['product']} 条（独立审批）",
            f"- 视觉建议：{recommendation_counts['visual']} 条（独立审批）",
            f"- 证据建议：{recommendation_counts['evidence']} 条（独立审批）",
            f"- 其他建议：{recommendation_counts['other']} 条（独立审批）",
            "",
            "非文案建议不属于本报告的文案批准范围；详细内容保存在独立建议文档。",
            "",
            "## 审批与实施状态",
            "",
            "- 内容策略：已用于本次提案",
            "- 文案提案：等待用户核实",
            "- 产品源文件：未修改",
            "- 提交、推送与合并：未执行",
            "- 生产部署与发布：未执行",
            "",
        ]

        knowledge = run.get("knowledge", {})
        if not isinstance(knowledge, dict):
            knowledge = {}
        conflicts = knowledge.get("conflicts", [])
        unresolved = knowledge.get("unresolved", [])
        blockers = list(conflicts if isinstance(conflicts, list) else []) + list(
            unresolved if isinstance(unresolved, list) else []
        )
        if blockers:
            lines.extend(["## 未解决的知识缺口", ""])
            for blocker in blockers:
                if isinstance(blocker, dict):
                    value = (
                        blocker.get("statement")
                        or blocker.get("question")
                        or json.dumps(blocker, ensure_ascii=False)
                    )
                else:
                    value = str(blocker)
                lines.append(f"- {value}")
            lines.append("")

        if blocked_items:
            lines.extend(["## 已选择但暂未进入写作", ""])
            for item in blocked_items:
                lines.extend(
                    [
                        f"### {item.get('id', 'unknown')} · {location_label(item.get('location', {}))}",
                        "",
                        f"- 阻塞原因：{item.get('reason', '')}",
                        f"- 待确认：{item.get('question', '')}",
                        "",
                        fenced(str(item.get("original", ""))),
                        "",
                    ]
                )

        errors = validation.get("errors", [])
        warnings = validation.get("warnings", [])
        lines.extend(["## Writer 校验", ""])
        if not errors and not warnings:
            lines.append("未报告数据格式或受保护标记异常。")
        else:
            lines.extend(f"- 错误：{value}" for value in errors)
            lines.extend(f"- 警告：{value}" for value in warnings)
        lines.extend(["", "## Before / Proposed After", ""])

        for source in items:
            item_id = source["id"]
            proposed = result_by_id.get(item_id)
            lines.extend(
                [
                    f"### {item_id} · {location_label(source['location'])}",
                    "",
                    f"用途：{source.get('purpose', '')}",
                    "",
                    f"确认含义：{source.get('intended_meaning', '')}",
                    "",
                    "Before",
                    "",
                    fenced(str(source.get("original", ""))),
                    "",
                    "Proposed After",
                    "",
                ]
            )
            if proposed:
                lines.extend(
                    [
                        fenced(str(proposed.get("rewrite", ""))),
                        "",
                        f"- 决策：`{proposed.get('decision', 'unknown')}`",
                        f"- 说明：{proposed.get('rationale', '')}",
                    ]
                )
            else:
                lines.extend(["_缺少 writer 结果_", "", "- 决策：`missing`"])
            lines.append("")

        lines.extend(
            [
                "## 核实后的选择",
                "",
                "请仅针对文案明确选择：批准全部文案、批准指定 copy ID、要求修改指定 copy ID，或放弃文案提案。",
                "结构、产品、视觉、证据和其他建议必须在独立建议文档中按建议 ID 另行批准。",
                "批准修改工作区不包含提交、推送、合并、部署或发布；生产动作需要查看实际差异后另行授权。",
                "",
            ]
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote report -> {args.output}")
        return 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
