from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).parents[1]


def load(name: str, script: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DISCOVERY = load("discovery_v03", "discover_content.py")
VALIDATOR = load("validator_v03", "validate_artifacts.py")
SCANNER = load("scanner_v03", "scan_surface.py")


def mapping() -> dict:
    return {
        "protocol": "userese-surface-map/v1",
        "surface": {
            "name": "Settings",
            "routes": ["/settings"],
            "role": "account owner",
            "locale": "en-US",
            "viewport": "desktop",
            "states": [{"name": "default", "access": "accessed"}],
        },
        "sources": [],
        "limitations": [],
    }


class V03ArtifactTest(unittest.TestCase):
    def test_low_cost_scan_reports_signals_without_secret_contents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app").mkdir()
            (root / "app" / "page.tsx").write_text(
                "'use client'; fetch('/api/home'); const t = i18n.t('hero.title')",
                encoding="utf-8",
            )
            (root / ".env").write_text("API_KEY=must-not-leak", encoding="utf-8")
            result = SCANNER.scan(root, mapping())
            self.assertEqual(result["scan"]["files_scanned"], 1)
            self.assertIn("client-render", result["scan"]["signals"])
            self.assertIn("api", result["scan"]["signals"])
            self.assertIn("i18n", result["scan"]["signals"])
            serialized = json.dumps(result)
            self.assertNotIn("must-not-leak", serialized)
            self.assertTrue(any("credential-like" in value for value in result["limitations"]))

    def test_surface_map_requires_user_and_state_boundary(self) -> None:
        value = mapping()
        del value["surface"]["role"]
        errors, _ = VALIDATOR.validate_surface_map(value)
        self.assertIn("surface map surface.role must be a non-empty string", errors)

    def test_candidate_metrics_must_match_payload(self) -> None:
        candidates = DISCOVERY.extract_html("<h1>Hello</h1>", mapping(), path="settings.html")
        artifact = {
            "protocol": "userese-candidates/v1",
            "surface": mapping()["surface"],
            "observations": {**DISCOVERY.build_observations(candidates), "candidate_count": 99},
            "candidates": candidates,
        }
        errors, _ = VALIDATOR.validate_candidates(artifact)
        self.assertIn("candidate observation count does not match candidates", errors)

    def test_v2_inventory_keeps_grouped_only_discovery(self) -> None:
        capture = {
            "protocol": "userese-capture/v1",
            "entries": [
                {
                    "text": "$42.00",
                    "kind": "price",
                    "content_nature": "business-data",
                    "detail_class": "noncopy",
                    "rendered_at": {"route": "/settings", "state": "default"},
                    "origin_type": "api",
                    "source_locator": {"endpoint": "/api/billing", "field": "amount"},
                    "editability": "read-only",
                    "trace_confidence": "high",
                }
            ],
        }
        candidates = DISCOVERY.extract_capture(capture, mapping())
        inventory = DISCOVERY.build_inventory(mapping(), candidates, mode="surface")
        self.assertEqual(inventory["items"], [])
        errors, _ = VALIDATOR.validate_inventory(inventory)
        self.assertEqual(errors, [])

    def test_v2_inventory_requires_source_trace(self) -> None:
        candidates = DISCOVERY.extract_html("<h1>Hello</h1>", mapping(), path="settings.html")
        inventory = DISCOVERY.build_inventory(mapping(), candidates, mode="core")
        del inventory["items"][0]["trace_confidence"]
        errors, _ = VALIDATOR.validate_inventory(inventory)
        self.assertTrue(any("trace_confidence" in error for error in errors))

    def test_a08_v2_selected_item_hands_off_to_v1_brief(self) -> None:
        candidates = DISCOVERY.extract_html("<h1>Hello</h1>", mapping(), path="settings.html")
        inventory = DISCOVERY.build_inventory(mapping(), candidates, mode="core")
        inventory["selection"] = {
            "status": "confirmed",
            "confirmed_at": "2026-09-02T08:00:00Z",
            "note": "User selected the heading.",
        }
        inventory["items"][0]["scope_decision"] = "include"
        item = inventory["items"][0]
        brief = {
            "protocol": "userese-brief/v1",
            "items": [{"id": item["id"], "location": item["location"], "original": item["original"]}],
            "blocked_items": [],
        }
        errors, _ = VALIDATOR.validate_inventory_against_brief(inventory, brief)
        self.assertEqual(errors, [])

    def test_scan_plan_shows_all_modes_and_unconfirmed_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            map_path = root / "surface-map.json"
            candidate_path = root / "content-candidates.json"
            output_path = root / "scan-plan.md"
            candidates = DISCOVERY.extract_html("<h1>Hello</h1>", mapping(), path="settings.html")
            map_path.write_text(json.dumps(mapping()), encoding="utf-8")
            candidate_path.write_text(
                json.dumps(
                    {
                        "protocol": "userese-candidates/v1",
                        "surface": mapping()["surface"],
                        "observations": DISCOVERY.build_observations(candidates),
                        "candidates": candidates,
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "render_scan_plan.py"),
                    str(map_path),
                    str(output_path),
                    "--candidates",
                    str(candidate_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = output_path.read_text(encoding="utf-8")
            self.assertIn("核心表达 `core`", report)
            self.assertIn("完整界面 `surface`", report)
            self.assertIn("全项目审计 `project`", report)
            self.assertIn("当前决定：未确认", report)

    def test_end_to_end_cli_artifacts_validate_and_render(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            map_path = root / "surface-map.json"
            html_path = root / "settings.html"
            capture_path = root / "api.capture.json"
            candidates_path = root / "content-candidates.json"
            inventory_path = root / "content-inventory.json"
            report_path = root / "content-inventory.md"
            map_path.write_text(json.dumps(mapping()), encoding="utf-8")
            html_path.write_text("<h1>Account settings</h1><img alt='Profile photo'>", encoding="utf-8")
            capture_path.write_text(
                json.dumps(
                    {
                        "protocol": "userese-capture/v1",
                        "entries": [
                            {
                                "text": "No payment method yet",
                                "kind": "status",
                                "content_nature": "system-template",
                                "detail_class": "core",
                                "rendered_at": {"route": "/settings", "state": "default"},
                                "origin_type": "api",
                                "source_locator": {"endpoint": "/api/billing", "field": "empty.message"},
                                "editability": "repository",
                                "trace_confidence": "high",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            discovery = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "discover_content.py"),
                    str(map_path),
                    "--html",
                    str(html_path),
                    "--capture",
                    str(capture_path),
                    "--mode",
                    "core",
                    "--candidates-out",
                    str(candidates_path),
                    "--inventory-out",
                    str(inventory_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(discovery.returncode, 0, discovery.stderr)
            validation = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "validate_artifacts.py"),
                    "--surface-map",
                    str(map_path),
                    "--candidates",
                    str(candidates_path),
                    "--inventory",
                    str(inventory_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(validation.returncode, 0, validation.stderr)
            rendering = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "render_inventory.py"),
                    str(inventory_path),
                    str(report_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(rendering.returncode, 0, rendering.stderr)
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("程序已发现：3 条", report)
            self.assertIn("已发现但分组展示：1 条", report)
            self.assertIn("No payment method yet", report)


if __name__ == "__main__":
    unittest.main()
