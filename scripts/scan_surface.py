#!/usr/bin/env python3
"""Add bounded, deterministic repository reconnaissance to a Surface map."""

from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any


DISCOVERY_PATH = Path(__file__).with_name("discover_content.py")
SPEC = importlib.util.spec_from_file_location("userese_discovery", DISCOVERY_PATH)
assert SPEC and SPEC.loader
DISCOVERY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DISCOVERY)


SKIP_DIRS = {
    ".git",
    ".userese",
    ".working",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "private",
    "vendor",
}
SENSITIVE_NAMES = {".env", "credentials", "secrets", "id_rsa", "id_ed25519"}
TEXT_SUFFIXES = {
    ".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte",
    ".astro", ".py", ".rb", ".php", ".json", ".yaml", ".yml", ".toml",
    ".md", ".mdx", ".po", ".properties",
}
SIGNATURES = {
    "static-render": re.compile(r"<html|<!doctype\s+html", re.I),
    "ssr": re.compile(r"getServerSideProps|renderToString|Astro\.request|server[-_ ]side", re.I),
    "client-render": re.compile(r"['\"]use client['\"]|createRoot\(|ReactDOM\.|createApp\(", re.I),
    "api": re.compile(r"\bfetch\s*\(|\baxios\b|['\"]/api/", re.I),
    "i18n": re.compile(r"\bi18n\b|\blocales?\b|\btranslations?\b|\bt\(['\"]", re.I),
    "cms": re.compile(r"\b(contentful|sanity|strapi|wordpress|prismic|directus|cms)\b", re.I),
    "runtime-template": re.compile(r"<canvas|<svg|innerHTML|textContent", re.I),
}


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def is_sensitive(path: Path) -> bool:
    lowered = path.name.lower()
    return (
        lowered in SENSITIVE_NAMES
        or lowered.startswith(".env.")
        or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
        or any(part in SKIP_DIRS for part in path.parts)
    )


def scan(root: Path, mapping: dict[str, Any], max_files: int = 10000, max_read_bytes: int = 65536) -> dict[str, Any]:
    errors = DISCOVERY.validate_surface_map(mapping)
    if errors:
        raise ValueError("; ".join(errors))
    root = root.resolve()
    files: list[Path] = []
    skipped_sensitive = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        if not path.is_file():
            continue
        if is_sensitive(relative):
            skipped_sensitive += 1
            continue
        files.append(path)
        if len(files) >= max_files:
            break

    types: Counter[str] = Counter()
    signals: dict[str, list[str]] = {name: [] for name in SIGNATURES}
    route_candidates: list[str] = []
    total_bytes = 0
    readable_files = 0
    routes = [str(route) for route in mapping["surface"]["routes"]]
    for path in files:
        relative = path.relative_to(root).as_posix()
        suffix = path.suffix.lower() or "[no-extension]"
        types[suffix] += 1
        try:
            size = path.stat().st_size
        except OSError:
            continue
        total_bytes += size
        if suffix not in TEXT_SUFFIXES or size > max_read_bytes:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        readable_files += 1
        route_words = [route.strip("/") for route in routes if route != "/"]
        if relative.endswith(("page.tsx", "page.jsx", "index.html", "index.htm")) or any(
            word and (word in relative or repr(route) in content or f'"{route}"' in content)
            for word, route in zip(route_words, [route for route in routes if route != "/"])
        ):
            route_candidates.append(relative)
        for name, pattern in SIGNATURES.items():
            if pattern.search(content) and len(signals[name]) < 20:
                signals[name].append(relative)

    limitations = list(mapping.get("limitations", []))
    if len(files) >= max_files:
        limitations.append(f"Repository scan stopped at the configured {max_files}-file limit.")
    if skipped_sensitive:
        limitations.append(f"Skipped {skipped_sensitive} credential-like or private file(s) by policy.")
    result = dict(mapping)
    result["limitations"] = list(dict.fromkeys(limitations))
    result["scan"] = {
        "root": str(root),
        "files_scanned": len(files),
        "readable_files_sampled": readable_files,
        "total_bytes": total_bytes,
        "file_types": dict(sorted(types.items())),
        "route_candidates": sorted(set(route_candidates)),
        "signals": {name: paths for name, paths in signals.items() if paths},
        "limits": {"max_files": max_files, "max_read_bytes_per_file": max_read_bytes},
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("surface_map", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--max-files", type=int, default=10000)
    parser.add_argument("--max-read-bytes", type=int, default=65536)
    args = parser.parse_args()
    try:
        mapping = read_object(args.surface_map)
        result = scan(args.root, mapping, args.max_files, args.max_read_bytes)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Scanned {result['scan']['files_scanned']} file(s) -> {args.output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
