#!/usr/bin/env python3
"""Render a reviewable Markdown view of a Userese content inventory."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    try:
        inventory = read_object(args.inventory)
        surface = inventory.get("surface", {})
        coverage = inventory.get("coverage", {})
        selection = inventory.get("selection", {})
        items = inventory.get("items", [])
        if not isinstance(items, list):
            raise ValueError("inventory.items must be an array")

        decisions = Counter(
            item.get("scope_decision", "unknown")
            for item in items
            if isinstance(item, dict)
        )
        sections = Counter(
            f"{item.get('route', '')} · {item.get('section', '')}"
            for item in items
            if isinstance(item, dict)
        )

        lines = [
            f"# 展示文案清单：{surface.get('name', 'Untitled surface')}",
            "",
            "> 这份清单用于确认覆盖和改写范围；它不是修改提案，产品源文件尚未改变。",
            "",
            "## 覆盖摘要",
            "",
            f"- 程序已发现：{coverage.get('discovered_count', len(items))} 条",
            f"- 当前模式详细分析：{coverage.get('analyzed_count', len(items))} 条",
            f"- 已发现但分组展示：{coverage.get('grouped_count', 0)} 条",
            f"- 范围状态：`{selection.get('status', 'unknown')}`",
            f"- 已选择：{decisions['include']} 条",
            f"- 已排除：{decisions['exclude']} 条",
            f"- 待选择：{decisions['pending']} 条",
            f"- 路由：{'、'.join(str(x) for x in surface.get('routes', [])) or '未记录'}",
            "",
            "### 页面与区块",
            "",
        ]
        lines.extend(f"- {name}：{count} 条" for name, count in sections.items())
        lines.extend(["", "### 扫描限制", ""])
        limitations = coverage.get("limitations", [])
        if limitations:
            lines.extend(f"- {value}" for value in limitations)
        else:
            lines.append("- 未记录限制")
        groups = coverage.get("groups", [])
        if isinstance(groups, list) and groups:
            lines.extend(["", "### 已发现但未逐项展开", ""])
            for group in groups:
                if not isinstance(group, dict):
                    continue
                examples = "；".join(str(value) for value in group.get("examples", []))
                origins = "、".join(str(value) for value in group.get("origins", []))
                lines.extend(
                    [
                        f"#### {group.get('category', 'unknown')} · {group.get('count', 0)} 条",
                        "",
                        f"- 示例：{examples or '无'}",
                        f"- 来源：{origins or 'unknown'}",
                        f"- 未展开原因：{group.get('reason', '')}",
                        f"- 如何展开：{group.get('how_to_expand', '')}",
                        "",
                    ]
                )
        lines.extend(["", "## 当前模式详细条目", ""])

        for item in items:
            if not isinstance(item, dict):
                continue
            location = item.get("location", {})
            if not isinstance(location, dict):
                location = {}
            lines.extend(
                [
                    f"### {item.get('id', 'unknown')} · {item.get('route', '')} · {item.get('section', '')}",
                    "",
                    f"- 位置：{location_label(location)}",
                    f"- 类型：`{item.get('kind', '')}`",
                    f"- 可见条件：`{item.get('visibility', '')}`",
                    f"- 内容性质：`{item.get('content_nature', '未记录（v0.2）')}`",
                    f"- 展示状态：`{json.dumps(item.get('rendered_at', {}), ensure_ascii=False, sort_keys=True)}`",
                    f"- 技术来源：`{item.get('origin_type', '未记录（v0.2）')}` · `{json.dumps(item.get('source_locator', {}), ensure_ascii=False, sort_keys=True)}`",
                    f"- 可修改性 / 追踪置信度：`{item.get('editability', '未记录')}` / `{item.get('trace_confidence', '未记录')}`",
                    f"- 用途：{item.get('purpose', '')}",
                    f"- 系统建议：`{item.get('proposed_treatment', '')}` — {item.get('proposal_reason', '')}",
                    f"- 用户范围决定：`{item.get('scope_decision', 'pending')}`",
                    "",
                    fenced(str(item.get("original", ""))),
                    "",
                ]
            )

        if selection.get("status") == "pending":
            lines.extend(
                [
                    "## 请确认本次范围",
                    "",
                    "可以选择全部文案、指定页面或区块，或指定 `copy-*` ID。系统建议仅供参考；未得到你的选择前不会生成 Writer brief。",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "## 已确认范围",
                    "",
                    f"{selection.get('note', '')}",
                    "",
                ]
            )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote inventory report -> {args.output}")
        return 0
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
