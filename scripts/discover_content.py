#!/usr/bin/env python3
"""Deterministically extract Userese content candidates and build an inventory."""

from __future__ import annotations

import argparse
from collections import OrderedDict
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


SURFACE_PROTOCOL = "userese-surface-map/v1"
CAPTURE_PROTOCOL = "userese-capture/v1"
CANDIDATE_PROTOCOL = "userese-candidates/v1"
INVENTORY_PROTOCOL = "userese-inventory/v2"
MODES = {"core", "surface", "project"}
ORIGIN_TYPES = {"source", "ssr", "api", "cms", "i18n", "runtime-template", "unknown"}
CONTENT_NATURES = {
    "authored-copy",
    "system-template",
    "business-data",
    "user-generated",
    "decorative",
    "unknown",
}
SECRET_KEYS = {
    "authorization",
    "cookie",
    "cookies",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "password",
    "secret",
}
TEXT_TAGS = {
    "title",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "a",
    "button",
    "label",
    "li",
    "dt",
    "dd",
    "figcaption",
    "option",
    "legend",
    "summary",
    "small",
    "footer",
    "text",
    "span",
    "div",
}
SKIP_TAGS = {"script", "style", "noscript"}


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _json_hash(value: Any, length: int = 16) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()[:length]


def _check_no_secrets(value: Any, path: str = "capture") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalised = str(key).lower().replace("-", "_")
            if normalised in SECRET_KEYS:
                raise ValueError(f"secret-bearing field is not allowed: {path}.{key}")
            _check_no_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_no_secrets(child, f"{path}[{index}]")


def validate_surface_map(mapping: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if mapping.get("protocol") != SURFACE_PROTOCOL:
        errors.append(f"surface map protocol must be {SURFACE_PROTOCOL}")
    surface = mapping.get("surface")
    if not isinstance(surface, dict):
        return errors + ["surface map surface must be an object"]
    for key in ["name", "role", "locale", "viewport"]:
        if not isinstance(surface.get(key), str) or not surface.get(key):
            errors.append(f"surface map surface.{key} must be a non-empty string")
    if not isinstance(surface.get("routes"), list) or not surface.get("routes"):
        errors.append("surface map surface.routes must be a non-empty array")
    states = surface.get("states")
    if not isinstance(states, list) or not states:
        errors.append("surface map surface.states must be a non-empty array")
    else:
        for index, state in enumerate(states):
            if not isinstance(state, dict) or not state.get("name"):
                errors.append(f"surface.states[{index}] needs a name")
            elif state.get("access") not in {"accessed", "unavailable", "not-requested"}:
                errors.append(f"surface.states[{index}] has invalid access")
            elif state.get("access") == "unavailable" and not state.get("reason"):
                errors.append(f"surface.states[{index}] needs an unavailable reason")
    sources = mapping.get("sources")
    if not isinstance(sources, list):
        errors.append("surface map sources must be an array")
    else:
        for index, source in enumerate(sources):
            if not isinstance(source, dict) or not source.get("id"):
                errors.append(f"surface map sources[{index}] needs an id")
            elif source.get("origin_type") not in ORIGIN_TYPES:
                errors.append(f"surface map source {source.get('id')} has invalid origin_type")
            elif source.get("status") not in {"accessed", "unavailable", "candidate", "not-requested"}:
                errors.append(f"surface map source {source.get('id')} has invalid status")
            elif not isinstance(source.get("locator"), dict):
                errors.append(f"surface map source {source.get('id')} needs locator")
    if not isinstance(mapping.get("limitations"), list):
        errors.append("surface map limitations must be an array")
    try:
        _check_no_secrets(mapping, "surface-map")
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def _surface_defaults(mapping: dict[str, Any]) -> dict[str, str]:
    surface = mapping["surface"]
    accessed = next(
        (state.get("name") for state in surface["states"] if state.get("access") == "accessed"),
        surface["states"][0].get("name", "default"),
    )
    return {
        "route": str(surface["routes"][0]),
        "state": str(accessed),
        "locale": str(surface["locale"]),
        "viewport": str(surface["viewport"]),
    }


def _kind_for(tag: str, attribute: str | None = None) -> str:
    if attribute in {"alt", "aria-label", "aria-description"}:
        return "accessibility"
    if attribute in {"placeholder"}:
        return "form-help"
    if tag in {"title", "meta"}:
        return "metadata"
    if tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
        return "heading"
    if tag in {"a", "button"}:
        return "action"
    if tag in {"label", "legend", "option"}:
        return "label"
    if tag in {"footer", "small"}:
        return "decorative"
    if tag in {"text"}:
        return "runtime-text"
    return "body"


def _classification(tag: str, text: str, attribute: str | None, attrs: dict[str, str]) -> tuple[str, str]:
    explicit_nature = attrs.get("data-userese-nature")
    explicit_detail = attrs.get("data-userese-detail")
    kind = _kind_for(tag, attribute)
    if explicit_nature in CONTENT_NATURES:
        nature = explicit_nature
    elif kind == "decorative" or re.fullmatch(r"[\W\d_]+", text, re.UNICODE):
        nature = "decorative"
    else:
        nature = "authored-copy"
    if explicit_detail in {"core", "supplemental", "noncopy"}:
        detail = explicit_detail
    elif nature in {"business-data", "user-generated", "decorative"}:
        detail = "noncopy" if nature in {"business-data", "user-generated"} else "supplemental"
    elif kind in {"metadata", "accessibility", "decorative", "runtime-text"}:
        detail = "supplemental"
    else:
        detail = "core"
    return nature, detail


def _candidate(
    *,
    mapping: dict[str, Any],
    text: str,
    kind: str,
    content_nature: str,
    detail_class: str,
    rendered_at: dict[str, Any],
    origin_type: str,
    source_locator: dict[str, Any],
    editability: str,
    trace_confidence: str,
    location: dict[str, Any],
    visibility: str = "default",
    section: str = "Unsectioned",
) -> dict[str, Any]:
    defaults = _surface_defaults(mapping)
    rendered = {**defaults, **rendered_at}
    identity = {
        "surface": mapping["surface"].get("name"),
        "text": text,
        "kind": kind,
        "rendered_at": rendered,
        "origin_type": origin_type,
        "source_locator": source_locator,
        "location": location,
    }
    return {
        "id": f"candidate-{_json_hash(identity)}",
        "text": text,
        "kind": kind,
        "content_nature": content_nature,
        "detail_class": detail_class,
        "rendered_at": rendered,
        "origin_type": origin_type,
        "source_locator": source_locator,
        "editability": editability,
        "trace_confidence": trace_confidence,
        "location": location,
        "visibility": visibility,
        "section": section,
        "consumers": [location],
    }


class _HTMLCandidateParser(HTMLParser):
    def __init__(self, mapping: dict[str, Any], path: str, rendered_at: dict[str, Any]):
        super().__init__(convert_charrefs=True)
        self.mapping = mapping
        self.path = path
        self.rendered_at = rendered_at
        self.stack: list[dict[str, Any]] = []
        self.candidates: list[dict[str, Any]] = []
        self.counts: dict[str, int] = {}

    def _selector(self, tag: str) -> str:
        self.counts[tag] = self.counts.get(tag, 0) + 1
        return f"{tag}:nth-of-source({self.counts[tag]})"

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        line = self.getpos()[0]
        selector = self._selector(tag)
        frame = {"tag": tag, "attrs": attrs, "line": line, "selector": selector, "text": []}
        self.stack.append(frame)
        if tag == "meta" and attrs.get("content") and (
            attrs.get("name") in {"description"} or attrs.get("property", "").startswith("og:")
        ):
            self._emit(attrs["content"], tag, "content", frame)
        for attribute in ("alt", "aria-label", "aria-description", "placeholder"):
            if attrs.get(attribute):
                self._emit(attrs[attribute], tag, attribute, frame)

    def handle_startendtag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs_list)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self.stack and not any(frame["tag"] in SKIP_TAGS for frame in self.stack):
            self.stack[-1]["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            return
        index = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i]["tag"] == tag), None)
        if index is None:
            return
        frames = self.stack[index:]
        del self.stack[index:]
        for frame in reversed(frames):
            if frame["tag"] in TEXT_TAGS:
                text = _normalise_text("".join(frame["text"]))
                if text:
                    self._emit(text, frame["tag"], None, frame)

    def _emit(self, raw: str, tag: str, attribute: str | None, frame: dict[str, Any]) -> None:
        text = _normalise_text(raw)
        if not text:
            return
        nature, detail = _classification(tag, text, attribute, frame["attrs"])
        kind = _kind_for(tag, attribute)
        location = {"path": self.path, "line": frame["line"], "selector": frame["selector"]}
        if attribute:
            location["attribute"] = attribute
        self.candidates.append(
            _candidate(
                mapping=self.mapping,
                text=text,
                kind=kind,
                content_nature=nature,
                detail_class=detail,
                rendered_at=self.rendered_at,
                origin_type="source",
                source_locator={"path": self.path, "line": frame["line"], "selector": frame["selector"]},
                editability="repository",
                trace_confidence="high",
                location=location,
                visibility="metadata" if kind == "metadata" else "accessibility" if kind == "accessibility" else "default",
            )
        )


def _deduplicate(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for candidate in candidates:
        candidate_id = candidate["id"]
        if candidate_id not in by_id:
            by_id[candidate_id] = candidate
        else:
            for consumer in candidate.get("consumers", []):
                if consumer not in by_id[candidate_id]["consumers"]:
                    by_id[candidate_id]["consumers"].append(consumer)
    return list(by_id.values())


def extract_html(
    html: str,
    mapping: dict[str, Any],
    *,
    path: str,
    rendered_at: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    errors = validate_surface_map(mapping)
    if errors:
        raise ValueError("; ".join(errors))
    parser = _HTMLCandidateParser(mapping, path, rendered_at or {})
    parser.feed(html)
    parser.close()
    return _deduplicate(parser.candidates)


def _capture_location(locator: dict[str, Any]) -> dict[str, Any]:
    if locator.get("path"):
        return {key: value for key, value in locator.items() if key in {"path", "line", "symbol", "selector", "field"}}
    if locator.get("endpoint"):
        return {"path": f"{locator['endpoint']}#{locator.get('field', 'unknown-field')}", "field": locator.get("field")}
    if locator.get("collection"):
        return {"path": f"cms:{locator['collection']}#{locator.get('field', 'unknown-field')}", "field": locator.get("field")}
    return {"path": f"unknown:{locator.get('reason', 'untraced')}"}


def extract_capture(capture: dict[str, Any], mapping: dict[str, Any]) -> list[dict[str, Any]]:
    _check_no_secrets(capture)
    if capture.get("protocol") != CAPTURE_PROTOCOL:
        raise ValueError(f"capture protocol must be {CAPTURE_PROTOCOL}")
    entries = capture.get("entries")
    if not isinstance(entries, list):
        raise ValueError("capture.entries must be an array")
    candidates: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"capture.entries[{index}] must be an object")
        text = _normalise_text(str(entry.get("text", "")))
        if not text:
            raise ValueError(f"capture.entries[{index}].text must be non-empty")
        origin = entry.get("origin_type", "unknown")
        nature = entry.get("content_nature", "unknown")
        if origin not in ORIGIN_TYPES:
            raise ValueError(f"capture.entries[{index}] has invalid origin_type")
        if nature not in CONTENT_NATURES:
            raise ValueError(f"capture.entries[{index}] has invalid content_nature")
        locator = entry.get("source_locator")
        if not isinstance(locator, dict) or not locator:
            locator = {"reason": "capture did not identify the source"}
            origin = "unknown"
        location = entry.get("location")
        if not isinstance(location, dict) or not location.get("path"):
            location = _capture_location(locator)
        candidates.append(
            _candidate(
                mapping=mapping,
                text=text,
                kind=str(entry.get("kind", "body")),
                content_nature=nature,
                detail_class=str(entry.get("detail_class", "supplemental")),
                rendered_at=entry.get("rendered_at", {}),
                origin_type=origin,
                source_locator=locator,
                editability=str(entry.get("editability", "unknown")),
                trace_confidence=str(entry.get("trace_confidence", "low")),
                location=location,
                visibility=str(entry.get("visibility", "dynamic")),
                section=str(entry.get("section", "Unsectioned")),
            )
        )
    return _deduplicate(candidates)


def build_observations(
    candidates: Iterable[dict[str, Any]],
    *,
    files_scanned: int = 0,
    dom_states_scanned: int = 0,
    responses_scanned: int = 0,
    knowledge_reads: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    values = list(candidates)
    reads = knowledge_reads or []
    signatures: set[tuple[str, str]] = set()
    duplicate_reads = 0
    for read in reads:
        signature = (str(read.get("source", "")), str(read.get("content_hash", "")))
        if signature in signatures and any(signature):
            duplicate_reads += 1
        signatures.add(signature)
    return {
        "files_scanned": files_scanned,
        "dom_states_scanned": dom_states_scanned,
        "responses_scanned": responses_scanned,
        "candidate_count": len(values),
        "candidate_characters": sum(len(str(value.get("text", ""))) for value in values),
        "semantic_candidate_count": 0,
        "semantic_characters": 0,
        "knowledge_reads": reads,
        "duplicate_full_reads": duplicate_reads,
    }


def _group_candidates(candidates: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for candidate in candidates:
        nature = candidate["content_nature"]
        if nature in {"business-data", "user-generated", "decorative"}:
            category = nature
        elif candidate["kind"] in {"accessibility", "metadata"}:
            category = candidate["kind"]
        elif candidate["origin_type"] == "runtime-template":
            category = "runtime-template"
        else:
            category = candidate["kind"]
        groups.setdefault(category, []).append(candidate)
    result = []
    for category, members in groups.items():
        reasons = "not Writer-controlled content" if category in {"business-data", "user-generated"} else f"not expanded in {mode} mode"
        result.append(
            {
                "category": category,
                "count": len(members),
                "examples": [member["text"] for member in members[:3]],
                "rendered_at": [member["rendered_at"] for member in members[:3]],
                "origins": sorted({member["origin_type"] for member in members}),
                "reason": reasons,
                "how_to_expand": "Choose surface mode or explicitly request this category." if mode == "core" else "Review the data-bearing template rather than rewriting its values.",
                "candidate_ids": [member["id"] for member in members],
            }
        )
    return result


def build_inventory(
    mapping: dict[str, Any],
    candidates: Iterable[dict[str, Any]],
    *,
    mode: str,
    observations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {sorted(MODES)}")
    values = _deduplicate(candidates)
    detailed: list[dict[str, Any]] = []
    grouped: list[dict[str, Any]] = []
    for candidate in values:
        non_writer_data = candidate["content_nature"] in {"business-data", "user-generated"}
        expand = not non_writer_data and (mode != "core" or candidate["detail_class"] == "core")
        (detailed if expand else grouped).append(candidate)

    items = []
    for candidate in detailed:
        nature = candidate["content_nature"]
        eligibility = "eligible" if nature == "authored-copy" else "conditional"
        treatment = "needs-context" if nature == "unknown" or candidate["trace_confidence"] == "low" else "review"
        items.append(
            {
                "id": f"copy-{candidate['id'].removeprefix('candidate-')}",
                "candidate_id": candidate["id"],
                "location": candidate["location"],
                "route": candidate["rendered_at"]["route"],
                "section": candidate["section"],
                "kind": candidate["kind"],
                "original": candidate["text"],
                "purpose": "Confirm this text's user-facing job during semantic review.",
                "visibility": candidate["visibility"],
                "proposed_treatment": treatment,
                "proposal_reason": "Mechanical discovery found this item; the host must verify meaning and evidence.",
                "scope_decision": "pending",
                "rendered_at": candidate["rendered_at"],
                "origin_type": candidate["origin_type"],
                "source_locator": candidate["source_locator"],
                "editability": candidate["editability"],
                "trace_confidence": candidate["trace_confidence"],
                "content_nature": nature,
                "writer_eligibility": eligibility,
            }
        )

    surface = mapping["surface"]
    unavailable = [state for state in surface["states"] if state.get("access") == "unavailable"]
    limitations = list(mapping.get("limitations", []))
    limitations.extend(
        f"State {state.get('name')} was unavailable: {state.get('reason')}"
        for state in unavailable
        if state.get("reason") and not any(state.get("reason") in value for value in limitations)
    )
    source_paths = sorted(
        {
            str(candidate["source_locator"]["path"])
            for candidate in values
            if isinstance(candidate.get("source_locator"), dict) and candidate["source_locator"].get("path")
        }
    )
    obs = observations or build_observations(values)
    obs = {**obs, "semantic_candidate_count": len(detailed), "semantic_characters": sum(len(item["original"]) for item in items)}
    return {
        "protocol": INVENTORY_PROTOCOL,
        "audit_mode": mode,
        "surface": {
            "name": surface["name"],
            "routes": surface["routes"],
            "paths": source_paths,
            "role": surface["role"],
            "locale": surface["locale"],
            "viewport": surface["viewport"],
        },
        "coverage": {
            "source_files": source_paths,
            "rendered_routes": sorted({candidate["rendered_at"]["route"] for candidate in values}),
            "states_checked": [state["name"] for state in surface["states"] if state.get("access") == "accessed"],
            "excluded_source_patterns": [],
            "limitations": limitations,
            "complete": not limitations and not unavailable,
            "discovered_count": len(values),
            "analyzed_count": len(detailed),
            "grouped_count": len(grouped),
            "groups": _group_candidates(grouped, mode),
        },
        "observations": obs,
        "selection": {"status": "pending", "confirmed_at": None, "note": ""},
        "items": items,
    }


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_object(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("surface_map", type=Path)
    parser.add_argument("--html", action="append", default=[], type=Path)
    parser.add_argument("--capture", action="append", default=[], type=Path)
    parser.add_argument("--mode", choices=sorted(MODES))
    parser.add_argument("--candidates-out", required=True, type=Path)
    parser.add_argument("--inventory-out", type=Path)
    args = parser.parse_args()
    try:
        mapping = _read_object(args.surface_map)
        errors = validate_surface_map(mapping)
        if errors:
            raise ValueError("; ".join(errors))
        candidates: list[dict[str, Any]] = []
        for path in args.html:
            candidates.extend(extract_html(path.read_text(encoding="utf-8"), mapping, path=str(path)))
        for path in args.capture:
            candidates.extend(extract_capture(_read_object(path), mapping))
        candidates = _deduplicate(candidates)
        observations = build_observations(
            candidates,
            files_scanned=len(args.html),
            dom_states_scanned=sum(1 for path in args.capture if path.name.endswith(("dom.json", "capture.json"))),
            responses_scanned=sum(1 for candidate in candidates if candidate["origin_type"] in {"api", "cms"}),
        )
        candidate_artifact = {
            "protocol": CANDIDATE_PROTOCOL,
            "surface": mapping["surface"],
            "observations": observations,
            "candidates": candidates,
        }
        _write_object(args.candidates_out, candidate_artifact)
        if args.inventory_out:
            if not args.mode:
                raise ValueError("--mode is required with --inventory-out")
            _write_object(args.inventory_out, build_inventory(mapping, candidates, mode=args.mode, observations=observations))
        print(f"Discovered {len(candidates)} candidate(s) -> {args.candidates_out}")
        if args.inventory_out:
            print(f"Built {args.mode} inventory -> {args.inventory_out}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
