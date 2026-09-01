#!/usr/bin/env python3
"""Render optional non-copy recommendations for separate user approval."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


TYPE_LABELS = {
    "structure": "结构",
    "product": "产品与交互",
    "visual": "视觉层级",
    "evidence": "证据与内容缺口",
    "other": "其他",
}


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def values(items: Any) -> str:
    if not isinstance(items, list) or not items:
        return "无"
    return "；".join(str(item) for item in items)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recommendations", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    try:
        data = read_object(args.recommendations)
        items = data.get("items")
        if not isinstance(items, list):
            raise ValueError("recommendations.items must be an array")
        counts = Counter(
            item.get("type", "other") for item in items if isinstance(item, dict)
        )
        lines = [
            "# 非文案建议",
            "",
            "> 以下内容不属于文案改写，也不会随文案批准自动实施。每条建议都需要按 ID 单独决定。",
            "",
            "## 分类摘要",
            "",
        ]
        for item_type, label in TYPE_LABELS.items():
            lines.append(f"- {label}：{counts[item_type]} 条")
        lines.append("")

        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type", "other"))
            label = TYPE_LABELS.get(item_type, "其他")
            lines.extend(
                [
                    f"## {item.get('id', 'unknown')} · {label} · {item.get('title', '')}",
                    "",
                    f"- 原因：{item.get('reason', '')}",
                    f"- 证据：{values(item.get('evidence'))}",
                    f"- 影响：{item.get('impact', '')}",
                    f"- 可选动作：{item.get('proposal', '')}",
                    f"- 涉及位置：{values(item.get('locations'))}",
                    "",
                ]
            )

        lines.extend(
            [
                "## 你的选择",
                "",
                "可以批准指定建议 ID、要求调整指定 ID，或全部不采用。批准文案不会批准这里的任何建议。",
                "",
            ]
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote recommendations -> {args.output}")
        return 0
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
