#!/usr/bin/env python3
"""Validate content-design briefs, writer results, and optional recommendations."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


TOKEN_PATTERNS = [
    re.compile(r"\$\{[^{}]+\}"),
    re.compile(r"\{\{[^{}]+\}\}"),
    re.compile(r"(?<!\{)\{[A-Za-z_][^{}]*\}(?!\})"),
    re.compile(r"%\([A-Za-z_][^)]+\)[#0 +\-]?[0-9.*]*[a-zA-Z]"),
    re.compile(r"%(?!%)[#0 +\-]?[0-9.*]*[a-zA-Z]"),
    re.compile(r"\]\((?:https?://|/|#)[^)]+\)"),
    re.compile(r"</?[A-Za-z][^>]*>"),
]

SURFACE_PROTOCOL = "userese-surface-map/v1"
CANDIDATE_PROTOCOL = "userese-candidates/v1"
INVENTORY_PROTOCOL = "userese-inventory/v2"
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


class ValidationError(Exception):
    pass


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON object from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must contain a JSON object")
    return value


def missing_keys(value: dict[str, Any], keys: list[str]) -> list[str]:
    return [key for key in keys if key not in value]


def collect_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    for pattern in TOKEN_PATTERNS:
        tokens.extend(pattern.findall(value))
    return sorted(tokens)


def find_secret_fields(value: Any, path: str) -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in SECRET_KEYS:
                errors.append(f"secret-bearing field is not allowed: {path}.{key}")
            errors.extend(find_secret_fields(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(find_secret_fields(child, f"{path}[{index}]"))
    return errors


def validate_surface_map(mapping: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if mapping.get("protocol") != SURFACE_PROTOCOL:
        errors.append(f"surface map protocol must be {SURFACE_PROTOCOL}")
    surface = mapping.get("surface")
    if not isinstance(surface, dict):
        return errors + ["surface map surface must be an object"], warnings
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
                continue
            if state.get("access") not in {"accessed", "unavailable", "not-requested"}:
                errors.append(f"surface.states[{index}] has invalid access")
            if state.get("access") == "unavailable" and not state.get("reason"):
                errors.append(f"surface.states[{index}] needs an unavailable reason")
    sources = mapping.get("sources")
    if not isinstance(sources, list):
        errors.append("surface map sources must be an array")
    else:
        source_ids: set[str] = set()
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                errors.append(f"surface map sources[{index}] must be an object")
                continue
            source_id = source.get("id")
            if not isinstance(source_id, str) or not source_id:
                errors.append(f"surface map sources[{index}] needs an id")
            elif source_id in source_ids:
                errors.append(f"duplicate surface source id {source_id}")
            else:
                source_ids.add(source_id)
            if source.get("origin_type") not in {"source", "ssr", "api", "cms", "i18n", "runtime-template", "unknown"}:
                errors.append(f"surface map source {source_id or index} has invalid origin_type")
            if source.get("status") not in {"accessed", "unavailable", "candidate", "not-requested"}:
                errors.append(f"surface map source {source_id or index} has invalid status")
            if not isinstance(source.get("locator"), dict):
                errors.append(f"surface map source {source_id or index} needs locator")
    if not isinstance(mapping.get("limitations"), list):
        errors.append("surface map limitations must be an array")
    scan = mapping.get("scan")
    if scan is not None:
        if not isinstance(scan, dict):
            errors.append("surface map scan must be an object")
        else:
            for key in ["files_scanned", "readable_files_sampled", "total_bytes", "file_types", "route_candidates", "signals", "limits"]:
                if key not in scan:
                    errors.append(f"surface map scan is missing {key}")
    errors.extend(find_secret_fields(mapping, "surface-map"))
    return errors, warnings


def validate_candidates(artifact: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if artifact.get("protocol") != CANDIDATE_PROTOCOL:
        errors.append(f"candidate protocol must be {CANDIDATE_PROTOCOL}")
    candidates = artifact.get("candidates")
    observations = artifact.get("observations")
    if not isinstance(candidates, list):
        return errors + ["candidates.candidates must be an array"], warnings
    if not isinstance(observations, dict):
        errors.append("candidates.observations must be an object")
    else:
        if observations.get("candidate_count") != len(candidates):
            errors.append("candidate observation count does not match candidates")
        expected_characters = sum(
            len(item.get("text", ""))
            for item in candidates
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        )
        if observations.get("candidate_characters") != expected_characters:
            errors.append("candidate character observation does not match candidates")
    required = [
        "id",
        "text",
        "kind",
        "content_nature",
        "detail_class",
        "rendered_at",
        "origin_type",
        "source_locator",
        "editability",
        "trace_confidence",
        "location",
    ]
    ids: set[str] = set()
    for index, item in enumerate(candidates):
        if not isinstance(item, dict):
            errors.append(f"candidates[{index}] must be an object")
            continue
        for key in missing_keys(item, required):
            errors.append(f"candidates[{index}] is missing {key}")
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id.startswith("candidate-"):
            errors.append(f"candidates[{index}].id must start with candidate-")
        elif item_id in ids:
            errors.append(f"duplicate candidate id {item_id}")
        else:
            ids.add(item_id)
        if item.get("origin_type") not in {"source", "ssr", "api", "cms", "i18n", "runtime-template", "unknown"}:
            errors.append(f"candidate {item_id or index} has invalid origin_type")
        if item.get("content_nature") not in {"authored-copy", "system-template", "business-data", "user-generated", "decorative", "unknown"}:
            errors.append(f"candidate {item_id or index} has invalid content_nature")
        if item.get("trace_confidence") not in {"high", "medium", "low"}:
            errors.append(f"candidate {item_id or index} has invalid trace_confidence")
    errors.extend(find_secret_fields(artifact, "candidates"))
    return errors, warnings


def validate_inventory(inventory: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    surface = inventory.get("surface")
    coverage = inventory.get("coverage")
    selection = inventory.get("selection")
    items = inventory.get("items")

    if not isinstance(surface, dict):
        errors.append("inventory.surface must be an object")
    else:
        if not isinstance(surface.get("name"), str) or not surface.get("name"):
            errors.append("inventory.surface.name must be a non-empty string")
        for key in ["routes", "paths"]:
            if not isinstance(surface.get(key), list):
                errors.append(f"inventory.surface.{key} must be an array")

    if not isinstance(coverage, dict):
        errors.append("inventory.coverage must be an object")
    else:
        for key in [
            "source_files",
            "rendered_routes",
            "states_checked",
            "excluded_source_patterns",
            "limitations",
        ]:
            if not isinstance(coverage.get(key), list):
                errors.append(f"inventory.coverage.{key} must be an array")

    selection_status: Any = None
    if not isinstance(selection, dict):
        errors.append("inventory.selection must be an object")
    else:
        selection_status = selection.get("status")
        if selection_status not in {"pending", "confirmed"}:
            errors.append(
                f"invalid inventory.selection.status: {selection_status!r}"
            )
        if selection_status == "confirmed":
            if not isinstance(selection.get("confirmed_at"), str) or not selection.get(
                "confirmed_at"
            ):
                errors.append(
                    "confirmed inventory.selection.confirmed_at must be a non-empty string"
                )
            if not isinstance(selection.get("note"), str) or not selection.get("note"):
                errors.append(
                    "confirmed inventory.selection.note must record the user's choice"
                )

    if not isinstance(items, list):
        errors.append("inventory.items must be an array")
        return errors, warnings
    is_v2 = inventory.get("protocol") == INVENTORY_PROTOCOL
    if not items and not is_v2:
        errors.append("inventory.items must be a non-empty array")
        return errors, warnings

    if is_v2:
        if inventory.get("audit_mode") not in {"core", "surface", "project"}:
            errors.append("v2 inventory audit_mode must be core, surface, or project")
        if isinstance(coverage, dict):
            for key in ["complete", "discovered_count", "analyzed_count", "grouped_count", "groups"]:
                if key not in coverage:
                    errors.append(f"v2 inventory.coverage is missing {key}")
            groups = coverage.get("groups")
            if not isinstance(groups, list):
                errors.append("v2 inventory.coverage.groups must be an array")
                groups = []
            grouped_count = 0
            grouped_ids: list[str] = []
            for index, group in enumerate(groups):
                if not isinstance(group, dict):
                    errors.append(f"coverage.groups[{index}] must be an object")
                    continue
                for key in ["category", "count", "examples", "rendered_at", "origins", "reason", "how_to_expand", "candidate_ids"]:
                    if key not in group:
                        errors.append(f"coverage.groups[{index}] is missing {key}")
                if isinstance(group.get("count"), int):
                    grouped_count += group["count"]
                if isinstance(group.get("candidate_ids"), list):
                    grouped_ids.extend(group["candidate_ids"])
            if coverage.get("analyzed_count") != len(items):
                errors.append("v2 inventory analyzed_count does not match items")
            if coverage.get("grouped_count") != grouped_count:
                errors.append("v2 inventory grouped_count does not match groups")
            if coverage.get("discovered_count") != len(items) + grouped_count:
                errors.append("v2 inventory discovered_count must equal analyzed plus grouped")
            if len(grouped_ids) != len(set(grouped_ids)):
                errors.append("a candidate appears in more than one coverage group")
        observations = inventory.get("observations")
        if not isinstance(observations, dict):
            errors.append("v2 inventory.observations must be an object")
        else:
            for key in ["files_scanned", "dom_states_scanned", "responses_scanned", "candidate_count", "candidate_characters", "semantic_candidate_count", "semantic_characters", "knowledge_reads", "duplicate_full_reads"]:
                if key not in observations:
                    errors.append(f"v2 inventory.observations is missing {key}")

    valid_visibility = {
        "default",
        "conditional",
        "dynamic",
        "metadata",
        "accessibility",
        "unknown",
    }
    valid_treatments = {"review", "keep", "needs-context"}
    valid_decisions = {"pending", "include", "exclude"}
    required = [
        "id",
        "location",
        "route",
        "section",
        "kind",
        "original",
        "purpose",
        "visibility",
        "proposed_treatment",
        "proposal_reason",
        "scope_decision",
    ]
    if is_v2:
        required.extend(
            [
                "candidate_id",
                "rendered_at",
                "origin_type",
                "source_locator",
                "editability",
                "trace_confidence",
                "content_nature",
                "writer_eligibility",
            ]
        )
    ids: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"inventory.items[{index}] must be an object")
            continue
        for key in missing_keys(item, required):
            errors.append(f"inventory.items[{index}] is missing {key}")
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id.startswith("copy-"):
            errors.append(f"inventory.items[{index}].id must start with copy-")
        elif item_id in ids:
            errors.append(f"duplicate inventory item id {item_id}")
        else:
            ids.add(item_id)
        location = item.get("location")
        if not isinstance(location, dict) or not location.get("path"):
            errors.append(f"inventory item {item_id or index} needs location.path")
        if not isinstance(item.get("original"), str):
            errors.append(f"inventory item {item_id or index}.original must be a string")
        if item.get("visibility") not in valid_visibility:
            errors.append(
                f"invalid visibility for inventory item {item_id or index}: "
                f"{item.get('visibility')!r}"
            )
        if item.get("proposed_treatment") not in valid_treatments:
            errors.append(
                f"invalid proposed_treatment for inventory item {item_id or index}: "
                f"{item.get('proposed_treatment')!r}"
            )
        decision = item.get("scope_decision")
        if decision not in valid_decisions:
            errors.append(
                f"invalid scope_decision for inventory item {item_id or index}: "
                f"{decision!r}"
            )
        elif selection_status == "pending" and decision != "pending":
            errors.append(
                f"inventory item {item_id or index} is preselected before user confirmation"
            )
        elif selection_status == "confirmed" and decision == "pending":
            errors.append(
                f"inventory item {item_id or index} remains pending after confirmation"
            )
        if is_v2:
            if item.get("origin_type") not in {"source", "ssr", "api", "cms", "i18n", "runtime-template", "unknown"}:
                errors.append(f"inventory item {item_id or index} has invalid origin_type")
            if item.get("content_nature") not in {"authored-copy", "system-template", "business-data", "user-generated", "decorative", "unknown"}:
                errors.append(f"inventory item {item_id or index} has invalid content_nature")
            if item.get("trace_confidence") not in {"high", "medium", "low"}:
                errors.append(f"inventory item {item_id or index} has invalid trace_confidence")
            if item.get("writer_eligibility") not in {"eligible", "conditional", "ineligible"}:
                errors.append(f"inventory item {item_id or index} has invalid writer_eligibility")
    if is_v2 and isinstance(coverage, dict) and isinstance(coverage.get("groups"), list):
        detailed_ids = {item.get("candidate_id") for item in items if isinstance(item, dict)}
        grouped_ids = {
            candidate_id
            for group in coverage["groups"]
            if isinstance(group, dict) and isinstance(group.get("candidate_ids"), list)
            for candidate_id in group["candidate_ids"]
        }
        overlap = sorted(value for value in detailed_ids & grouped_ids if isinstance(value, str))
        if overlap:
            errors.append(f"candidates are both detailed and grouped: {', '.join(overlap)}")
        errors.extend(find_secret_fields(inventory, "inventory"))
    return errors, warnings


def validate_brief(brief: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    run = brief.get("run")
    items = brief.get("items")
    blocked_items = brief.get("blocked_items")
    pipeline = brief.get("writing_pipeline")
    if not isinstance(run, dict):
        return ["brief.run must be an object"], warnings
    if not isinstance(pipeline, dict):
        errors.append("brief.writing_pipeline must be an object")
    else:
        writer = pipeline.get("writer")
        if not isinstance(writer, dict):
            errors.append("brief.writing_pipeline.writer must be an object")
        else:
            if writer.get("type") not in {"host", "skill", "adapter"}:
                errors.append(
                    f"invalid brief.writing_pipeline.writer.type: {writer.get('type')!r}"
                )
            if not isinstance(writer.get("name"), str) or not writer.get("name"):
                errors.append(
                    "brief.writing_pipeline.writer.name must be a non-empty string"
                )
        postprocessors = pipeline.get("postprocessors")
        if not isinstance(postprocessors, list):
            errors.append("brief.writing_pipeline.postprocessors must be an array")
        else:
            for index, postprocessor in enumerate(postprocessors):
                if not isinstance(postprocessor, dict):
                    errors.append(f"postprocessors[{index}] must be an object")
                    continue
                if postprocessor.get("type") not in {"skill", "adapter"}:
                    errors.append(
                        f"invalid postprocessors[{index}].type: {postprocessor.get('type')!r}"
                    )
                if not isinstance(postprocessor.get("name"), str) or not postprocessor.get(
                    "name"
                ):
                    errors.append(f"postprocessors[{index}].name must be a non-empty string")
        if not isinstance(pipeline.get("selection_note"), str) or not pipeline.get(
            "selection_note"
        ):
            errors.append("brief.writing_pipeline.selection_note must be a non-empty string")

    required_run = [
        "project",
        "goal",
        "target_language",
        "profile_source",
        "surface",
        "page_job",
        "audience",
        "audience_detail",
        "communication_goal",
        "brand_voice",
        "avoid",
        "terms",
        "message_strategy",
        "knowledge",
        "global_constraints",
    ]
    for key in missing_keys(run, required_run):
        errors.append(f"brief.run is missing {key}")

    surface = run.get("surface")
    if not isinstance(surface, dict):
        errors.append("brief.run.surface must be an object")
    elif surface.get("kind") not in {
        "core-narrative",
        "task-interface",
        "professional-explanation",
        "global-audit",
    }:
        errors.append(f"invalid surface.kind: {surface.get('kind')!r}")

    strategy = run.get("message_strategy")
    if not isinstance(strategy, dict):
        errors.append("brief.run.message_strategy must be an object")
    else:
        for key in [
            "desired_understanding",
            "desired_perception",
            "next_action",
            "message_hierarchy",
        ]:
            if key not in strategy:
                errors.append(f"brief.run.message_strategy is missing {key}")

    knowledge = run.get("knowledge")
    claim_ids: set[str] = set()
    if not isinstance(knowledge, dict):
        errors.append("brief.run.knowledge must be an object")
    else:
        for key in ["verified_claims", "assumptions", "conflicts", "unresolved"]:
            if not isinstance(knowledge.get(key), list):
                errors.append(f"brief.run.knowledge.{key} must be an array")
        claims = knowledge.get("verified_claims")
        if not isinstance(claims, list):
            claims = []
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                errors.append(f"verified_claims[{index}] must be an object")
                continue
            claim_id = claim.get("id")
            if not isinstance(claim_id, str) or not claim_id:
                errors.append(f"verified_claims[{index}].id must be a non-empty string")
            elif claim_id in claim_ids:
                errors.append(f"duplicate verified claim id {claim_id}")
            else:
                claim_ids.add(claim_id)
            if not isinstance(claim.get("evidence"), list) or not claim.get("evidence"):
                warnings.append(f"verified claim {claim_id or index} has no evidence")

    if not isinstance(items, list):
        errors.append("brief.items must be an array")
        return errors, warnings
    if isinstance(blocked_items, list) and not items and not blocked_items:
        errors.append("brief must contain at least one ready or blocked item")

    item_ids: set[str] = set()
    required_item = [
        "id",
        "location",
        "purpose",
        "original",
        "context",
        "intended_meaning",
        "evidence_refs",
        "constraints",
    ]
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{index}] must be an object")
            continue
        for key in missing_keys(item, required_item):
            errors.append(f"items[{index}] is missing {key}")
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            errors.append(f"items[{index}].id must be a non-empty string")
        elif item_id in item_ids:
            errors.append(f"duplicate item id {item_id}")
        else:
            item_ids.add(item_id)
        location = item.get("location")
        if not isinstance(location, dict) or not location.get("path"):
            errors.append(f"items[{index}].location.path is required")
        if not isinstance(item.get("original"), str):
            errors.append(f"items[{index}].original must be a string")
        if not isinstance(item.get("constraints"), list):
            errors.append(f"items[{index}].constraints must be an array")
        refs = item.get("evidence_refs")
        if not isinstance(refs, list):
            errors.append(f"items[{index}].evidence_refs must be an array")
        else:
            for ref in refs:
                if ref not in claim_ids:
                    errors.append(f"item {item_id or index} references unknown claim {ref!r}")
        if not item.get("intended_meaning"):
            warnings.append(f"item {item_id or index} has an empty intended_meaning")

    if not isinstance(blocked_items, list):
        errors.append("brief.blocked_items must be an array")
    else:
        required_blocked = ["id", "location", "original", "reason", "question"]
        for index, item in enumerate(blocked_items):
            if not isinstance(item, dict):
                errors.append(f"blocked_items[{index}] must be an object")
                continue
            for key in missing_keys(item, required_blocked):
                errors.append(f"blocked_items[{index}] is missing {key}")
            item_id = item.get("id")
            if not isinstance(item_id, str) or not item_id.startswith("copy-"):
                errors.append(f"blocked_items[{index}].id must start with copy-")
            elif item_id in item_ids:
                errors.append(f"duplicate ready/blocked item id {item_id}")
            else:
                item_ids.add(item_id)
            location = item.get("location")
            if not isinstance(location, dict) or not location.get("path"):
                errors.append(f"blocked item {item_id or index} needs location.path")
            if not isinstance(item.get("original"), str):
                errors.append(f"blocked item {item_id or index}.original must be a string")
            for key in ["reason", "question"]:
                if not isinstance(item.get(key), str) or not item.get(key):
                    errors.append(
                        f"blocked item {item_id or index}.{key} must be a non-empty string"
                    )

    return errors, warnings


def validate_inventory_against_brief(
    inventory: dict[str, Any], brief: dict[str, Any]
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    selection = inventory.get("selection", {})
    if not isinstance(selection, dict) or selection.get("status") != "confirmed":
        return ["inventory selection must be confirmed before creating a brief"], warnings

    inventory_items = {
        item.get("id"): item
        for item in inventory.get("items", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    included = {
        item_id
        for item_id, item in inventory_items.items()
        if item.get("scope_decision") == "include"
    }
    ready_items = [item for item in brief.get("items", []) if isinstance(item, dict)]
    blocked_items = [
        item for item in brief.get("blocked_items", []) if isinstance(item, dict)
    ]
    accounted_items = ready_items + blocked_items
    accounted_ids = [item.get("id") for item in accounted_items]
    accounted = {item_id for item_id in accounted_ids if isinstance(item_id, str)}

    for item_id in sorted(included - accounted):
        errors.append(f"selected inventory item {item_id} is missing from the brief")
    for item_id in sorted(accounted - included):
        errors.append(f"brief item {item_id} was not selected by the user")
    for item_id in sorted(accounted):
        if accounted_ids.count(item_id) > 1:
            errors.append(f"brief accounts for inventory item {item_id} more than once")
            continue
        source = inventory_items.get(item_id)
        target = next(
            (item for item in accounted_items if item.get("id") == item_id), None
        )
        if not source or not target:
            continue
        if source.get("original") != target.get("original"):
            errors.append(f"{item_id}: inventory and brief originals differ")
        source_location = source.get("location")
        target_location = target.get("location")
        source_path = source_location.get("path") if isinstance(source_location, dict) else None
        target_path = target_location.get("path") if isinstance(target_location, dict) else None
        if source_path != target_path:
            errors.append(f"{item_id}: inventory and brief location paths differ")
    return errors, warnings


def validate_result(
    brief: dict[str, Any], result: dict[str, Any]
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    source_items = brief.get("items", [])
    result_items = result.get("items")
    if not isinstance(result_items, list):
        return ["result.items must be an array"], warnings

    expected = [item.get("id") for item in source_items if isinstance(item, dict)]
    actual = [item.get("id") for item in result_items if isinstance(item, dict)]
    for item_id in expected:
        count = actual.count(item_id)
        if count == 0:
            errors.append(f"missing result for {item_id}")
        elif count > 1:
            errors.append(f"duplicate result for {item_id}")
    for item_id in actual:
        if item_id not in expected:
            errors.append(f"unexpected result id {item_id!r}")

    source_by_id = {
        item["id"]: item
        for item in source_items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for index, item in enumerate(result_items):
        if not isinstance(item, dict):
            errors.append(f"result.items[{index}] must be an object")
            continue
        item_id = item.get("id")
        if item_id not in source_by_id:
            continue
        decision = item.get("decision")
        rewrite = item.get("rewrite")
        if decision not in {"rewrite", "keep", "needs-context"}:
            errors.append(f"invalid decision for {item_id}: {decision!r}")
        if not isinstance(rewrite, str):
            errors.append(f"rewrite for {item_id} must be a string")
            continue
        if not isinstance(item.get("rationale"), str):
            errors.append(f"rationale for {item_id} must be a string")
        original = source_by_id[item_id].get("original", "")
        if collect_tokens(original) != collect_tokens(rewrite):
            warnings.append(f"{item_id}: protected variables, markup or links differ")
        if decision in {"keep", "needs-context"} and rewrite != original:
            warnings.append(f"{item_id}: {decision} normally preserves the original")
    return errors, warnings


def validate_recommendations(
    recommendations: dict[str, Any],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    items = recommendations.get("items")
    if not isinstance(items, list):
        return ["recommendations.items must be an array"], warnings

    valid_types = {"structure", "product", "visual", "evidence", "other"}
    required = ["id", "type", "title", "reason", "evidence", "impact", "proposal", "locations"]
    ids: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"recommendations.items[{index}] must be an object")
            continue
        for key in missing_keys(item, required):
            errors.append(f"recommendations.items[{index}] is missing {key}")
        item_id = item.get("id")
        item_type = item.get("type")
        if not isinstance(item_id, str) or not item_id:
            errors.append(f"recommendations.items[{index}].id must be a non-empty string")
        elif item_id in ids:
            errors.append(f"duplicate recommendation id {item_id}")
        else:
            ids.add(item_id)
        if item_type not in valid_types:
            errors.append(f"invalid recommendation type for {item_id or index}: {item_type!r}")
        elif isinstance(item_id, str) and not item_id.startswith(f"{item_type}-"):
            errors.append(f"recommendation id {item_id} must start with {item_type}-")
        for key in ["evidence", "locations"]:
            if not isinstance(item.get(key), list):
                errors.append(f"recommendation {item_id or index}.{key} must be an array")
        if not item.get("proposal"):
            warnings.append(f"recommendation {item_id or index} has an empty proposal")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", type=Path, nargs="?")
    parser.add_argument("result", type=Path, nargs="?")
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--surface-map", type=Path)
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--recommendations", type=Path)
    args = parser.parse_args()

    try:
        if not args.brief and not args.inventory and not args.surface_map and not args.candidates:
            parser.error("provide a brief, --inventory, --surface-map, or --candidates")
        if args.result and not args.brief:
            parser.error("a result requires a brief")
        if args.recommendations and not args.brief:
            parser.error("recommendations require a brief")

        errors: list[str] = []
        warnings: list[str] = []
        inventory: dict[str, Any] | None = None
        brief: dict[str, Any] | None = None
        if args.surface_map:
            mapping = read_object(args.surface_map)
            surface_errors, surface_warnings = validate_surface_map(mapping)
            errors.extend(surface_errors)
            warnings.extend(surface_warnings)
        if args.candidates:
            candidate_artifact = read_object(args.candidates)
            candidate_errors, candidate_warnings = validate_candidates(candidate_artifact)
            errors.extend(candidate_errors)
            warnings.extend(candidate_warnings)
        if args.inventory:
            inventory = read_object(args.inventory)
            inventory_errors, inventory_warnings = validate_inventory(inventory)
            errors.extend(inventory_errors)
            warnings.extend(inventory_warnings)
        if args.brief:
            brief = read_object(args.brief)
            brief_errors, brief_warnings = validate_brief(brief)
            errors.extend(brief_errors)
            warnings.extend(brief_warnings)
        if inventory is not None and brief is not None:
            coverage_errors, coverage_warnings = validate_inventory_against_brief(
                inventory, brief
            )
            errors.extend(coverage_errors)
            warnings.extend(coverage_warnings)
        if args.result:
            assert brief is not None
            result = read_object(args.result)
            result_errors, result_warnings = validate_result(brief, result)
            errors.extend(result_errors)
            warnings.extend(result_warnings)
        recommendation_count = 0
        if args.recommendations:
            assert brief is not None
            recommendations = read_object(args.recommendations)
            recommendation_errors, recommendation_warnings = validate_recommendations(
                recommendations
            )
            errors.extend(recommendation_errors)
            warnings.extend(recommendation_warnings)
            recommendation_count = len(recommendations.get("items", []))
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
        if errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 1
        item_count = len(brief.get("items", [])) if brief is not None else 0
        blocked_count = len(brief.get("blocked_items", [])) if brief is not None else 0
        inventory_count = len(inventory.get("items", [])) if inventory is not None else 0
        labels = []
        if args.surface_map:
            labels.append("surface map")
        if args.candidates:
            labels.append("candidates")
        if inventory is not None:
            labels.append(f"inventory: {inventory_count} item(s)")
        if brief is not None:
            labels.append(f"brief: {item_count} ready, {blocked_count} blocked")
        if args.result:
            labels.append("result")
        recommendation_suffix = (
            f", {recommendation_count} recommendation(s)" if args.recommendations else ""
        )
        print(
            f"Valid {'; '.join(labels)}{recommendation_suffix}, "
            f"{len(warnings)} warning(s)"
        )
        return 0
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
