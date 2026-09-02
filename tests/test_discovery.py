from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "scripts" / "discover_content.py"
SPEC = importlib.util.spec_from_file_location("discover_content", MODULE_PATH)
assert SPEC and SPEC.loader
DISCOVERY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DISCOVERY)


def surface_map(*, unavailable: bool = False) -> dict:
    limitations = []
    states = [
        {"name": "default", "access": "accessed"},
        {
            "name": "signed-in",
            "access": "unavailable" if unavailable else "accessed",
            "reason": "requires a test account" if unavailable else "",
        },
    ]
    if unavailable:
        limitations.append("Signed-in CMS content was not accessible.")
    return {
        "protocol": "userese-surface-map/v1",
        "surface": {
            "name": "Homepage",
            "routes": ["/"],
            "role": "public visitor",
            "locale": "zh-CN",
            "viewport": "desktop",
            "states": states,
        },
        "sources": [
            {
                "id": "source-html",
                "origin_type": "source",
                "status": "accessed",
                "locator": {"path": "index.html"},
            }
        ],
        "limitations": limitations,
    }


class DiscoveryAcceptanceTest(unittest.TestCase):
    def test_a01_core_and_surface_share_discovery_evidence(self) -> None:
        html = """
        <html><head><title>Acme home</title></head><body>
          <h1>Make planning clear</h1><p>A concrete case study.</p>
          <a href='/start'>Start now</a><span aria-label='Next slide'>→</span>
          <footer>Build 42</footer>
        </body></html>
        """
        candidates = DISCOVERY.extract_html(html, surface_map(), path="index.html")
        core = DISCOVERY.build_inventory(surface_map(), candidates, mode="core")
        complete = DISCOVERY.build_inventory(surface_map(), candidates, mode="surface")

        self.assertLess(len(core["items"]), len(complete["items"]))
        self.assertEqual(core["coverage"]["discovered_count"], len(candidates))
        self.assertEqual(complete["coverage"]["discovered_count"], len(candidates))
        grouped = {group["category"] for group in core["coverage"]["groups"]}
        self.assertTrue({"accessibility", "decorative"} & grouped)

    def test_a02_api_title_keeps_endpoint_and_field(self) -> None:
        entries = [
            {
                "text": "Plan with evidence",
                "kind": "heading",
                "content_nature": "authored-copy",
                "detail_class": "core",
                "rendered_at": {"route": "/", "state": "default"},
                "origin_type": "api",
                "source_locator": {"endpoint": "/api/home", "field": "hero.title"},
                "editability": "external-admin",
                "trace_confidence": "high",
            }
        ]
        candidates = DISCOVERY.extract_capture({"protocol": "userese-capture/v1", "entries": entries}, surface_map())
        item = DISCOVERY.build_inventory(surface_map(), candidates, mode="core")["items"][0]
        self.assertEqual(item["original"], "Plan with evidence")
        self.assertEqual(item["origin_type"], "api")
        self.assertEqual(item["source_locator"]["field"], "hero.title")
        self.assertEqual(item["content_nature"], "authored-copy")

    def test_a03_business_data_is_not_a_writer_item(self) -> None:
        entries = [
            self.capture_entry("Order #4831", "business-data", "order.number"),
            self.capture_entry("No orders yet", "authored-copy", "empty.message"),
        ]
        candidates = DISCOVERY.extract_capture({"protocol": "userese-capture/v1", "entries": entries}, surface_map())
        inventory = DISCOVERY.build_inventory(surface_map(), candidates, mode="core")
        self.assertEqual([item["original"] for item in inventory["items"]], ["No orders yet"])
        self.assertEqual(inventory["coverage"]["groups"][0]["category"], "business-data")

    def test_a04_user_content_is_not_a_writer_item(self) -> None:
        entries = [
            self.capture_entry("I loved it", "user-generated", "comments[].body"),
            self.capture_entry("No comments yet", "system-template", "empty.comments"),
        ]
        candidates = DISCOVERY.extract_capture({"protocol": "userese-capture/v1", "entries": entries}, surface_map())
        inventory = DISCOVERY.build_inventory(surface_map(), candidates, mode="surface")
        self.assertEqual([item["original"] for item in inventory["items"]], ["No comments yet"])
        self.assertEqual(inventory["coverage"]["groups"][0]["category"], "user-generated")

    def test_a05_accessibility_and_runtime_expand_only_in_surface(self) -> None:
        html = "<h1>Status</h1><img alt='Map of delayed routes'><svg><text>Delayed</text></svg>"
        runtime = self.capture_entry("Vehicle 7 delayed", "system-template", "canvas.status")
        runtime.update({"origin_type": "runtime-template", "detail_class": "supplemental"})
        candidates = DISCOVERY.extract_html(html, surface_map(), path="index.html")
        candidates += DISCOVERY.extract_capture({"protocol": "userese-capture/v1", "entries": [runtime]}, surface_map())
        core = DISCOVERY.build_inventory(surface_map(), candidates, mode="core")
        complete = DISCOVERY.build_inventory(surface_map(), candidates, mode="surface")
        self.assertNotIn("Map of delayed routes", [item["original"] for item in core["items"]])
        self.assertIn("Map of delayed routes", [item["original"] for item in complete["items"]])
        self.assertIn("Vehicle 7 delayed", [item["original"] for item in complete["items"]])

    def test_a06_unavailable_state_prevents_complete_claim(self) -> None:
        mapping = surface_map(unavailable=True)
        candidates = DISCOVERY.extract_html("<h1>Public home</h1>", mapping, path="index.html")
        inventory = DISCOVERY.build_inventory(mapping, candidates, mode="surface")
        self.assertFalse(inventory["coverage"]["complete"])
        self.assertIn("Signed-in CMS content was not accessible.", inventory["coverage"]["limitations"])

    def test_a07_observations_route_knowledge_to_items(self) -> None:
        observations = DISCOVERY.build_observations(
            [self.capture_entry("Save 80%", "authored-copy", "case.result")],
            knowledge_reads=[{"source": "evidence.md", "item_ids": ["copy-claim"], "characters": 120}],
        )
        self.assertEqual(observations["knowledge_reads"][0]["item_ids"], ["copy-claim"])
        self.assertEqual(observations["duplicate_full_reads"], 0)

    def test_capture_rejects_secret_bearing_fields(self) -> None:
        capture = {"protocol": "userese-capture/v1", "entries": [], "authorization": "secret"}
        with self.assertRaisesRegex(ValueError, "secret-bearing field"):
            DISCOVERY.extract_capture(capture, surface_map())

    def test_cli_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            html_path = root / "index.html"
            map_path = root / "surface-map.json"
            html_path.write_text("<h1>Hello</h1><p>World</p>", encoding="utf-8")
            map_path.write_text(json.dumps(surface_map()), encoding="utf-8")
            first = DISCOVERY.extract_html(html_path.read_text(), surface_map(), path="index.html")
            second = DISCOVERY.extract_html(html_path.read_text(), surface_map(), path="index.html")
            self.assertEqual(first, second)

    @staticmethod
    def capture_entry(text: str, nature: str, field: str) -> dict:
        return {
            "text": text,
            "kind": "status",
            "content_nature": nature,
            "detail_class": "core",
            "rendered_at": {"route": "/", "state": "default"},
            "origin_type": "api",
            "source_locator": {"endpoint": "/api/orders", "field": field},
            "editability": "read-only" if nature in {"business-data", "user-generated"} else "repository",
            "trace_confidence": "high",
        }


if __name__ == "__main__":
    unittest.main()
