#!/usr/bin/env python3
"""Render a compact Userese scan card before detailed semantic review."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


DISCOVERY_PATH = Path(__file__).with_name("discover_content.py")
SPEC = importlib.util.spec_from_file_location("userese_discovery", DISCOVERY_PATH)
assert SPEC and SPEC.loader
DISCOVERY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DISCOVERY)


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def effort(count: int) -> str:
    if count <= 20:
        return "小"
    if count <= 80:
        return "中"
    return "大"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("surface_map", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--mode", choices=sorted(DISCOVERY.MODES))
    args = parser.parse_args()
    try:
        mapping = read_object(args.surface_map)
        errors = DISCOVERY.validate_surface_map(mapping)
        if errors:
            raise ValueError("; ".join(errors))
        candidates: list[dict[str, Any]] = []
        if args.candidates:
            artifact = read_object(args.candidates)
            if artifact.get("protocol") != DISCOVERY.CANDIDATE_PROTOCOL:
                raise ValueError("candidate artifact has an unsupported protocol")
            candidates = [item for item in artifact.get("candidates", []) if isinstance(item, dict)]
        surface = mapping["surface"]
        accessed = [state["name"] for state in surface["states"] if state.get("access") == "accessed"]
        unavailable = [state for state in surface["states"] if state.get("access") == "unavailable"]
        core_count = sum(
            item.get("detail_class") == "core"
            and item.get("content_nature") not in {"business-data", "user-generated"}
            for item in candidates
        )
        surface_count = sum(item.get("content_nature") not in {"business-data", "user-generated"} for item in candidates)
        origins = sorted({str(item.get("origin_type")) for item in candidates})
        origins.extend(
            str(source.get("origin_type"))
            for source in mapping.get("sources", [])
            if isinstance(source, dict) and source.get("origin_type") not in origins
        )
        lines = [
            f"# 内容勘察卡：{surface['name']}",
            "",
            "> 这是深入语义分析前的覆盖与工作量说明；尚未生成 Writer brief，也未修改产品文件。",
            "",
            "## 目标 Surface",
            "",
            f"- 路由/入口：{'、'.join(surface['routes'])}",
            f"- 用户角色：{surface['role']}",
            f"- 语言：{surface['locale']}",
            f"- 设备/viewport：{surface['viewport']}",
            f"- 已访问状态：{'、'.join(accessed) or '无'}",
            f"- 未访问状态：{'、'.join(state['name'] for state in unavailable) or '无'}",
            "",
            "## 已发现内容面",
            "",
            f"- 候选：{len(candidates)} 条",
            f"- 来源：{'、'.join(origins) or '尚未识别'}",
        ]
        scan = mapping.get("scan", {})
        if isinstance(scan, dict) and scan:
            lines.extend(
                [
                    f"- 机械扫描：{scan.get('files_scanned', 0)} 个文件，约 {scan.get('total_bytes', 0)} bytes",
                    f"- 路由/入口候选：{'、'.join(str(value) for value in scan.get('route_candidates', [])) or '未定位'}",
                    f"- 技术迹象：{'、'.join(str(value) for value in scan.get('signals', {}).keys()) or '未识别'}",
                ]
            )
        for source in mapping.get("sources", []):
            if isinstance(source, dict):
                locator = json.dumps(source.get("locator", {}), ensure_ascii=False, sort_keys=True)
                lines.append(f"- `{source.get('origin_type', 'unknown')}` · `{source.get('status', 'unknown')}` · {locator}")
        lines.extend(
            [
                "",
                "## 审计模式",
                "",
                f"- 核心表达 `core`（默认建议，工作量：{effort(core_count)}）：详细展开主要标题、正文、案例、关键说明和 CTA；其余保留分组证据。",
                f"- 完整界面 `surface`（工作量：{effort(surface_count)}）：详细展开目标 Surface 内全部可发现的产品表达；业务数据和用户内容仍只记录边界。",
                f"- 全项目审计 `project`（工作量：{'大' if len(surface['routes']) > 1 or surface_count > 40 else '中'}）：跨已声明 Surface/渠道检查一致性，知识仍按主张渐进读取。",
                "",
                "## 已知限制",
                "",
            ]
        )
        limitations = list(mapping.get("limitations", []))
        limitations.extend(
            f"{state['name']}：{state.get('reason', '不可访问')}" for state in unavailable
        )
        lines.extend(f"- {value}" for value in limitations or ["未记录限制"])
        lines.extend(
            [
                "",
                "## 模式决定",
                "",
                f"- 当前决定：`{args.mode}`" if args.mode else "- 当前决定：未确认",
                "- 未确认前不进入高成本语义分析；确认模式不等于确认具体改写范围。" if not args.mode else "- 已保留用户指定模式；详细条目生成后仍需单独确认改写范围。",
                "",
            ]
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote scan plan -> {args.output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
