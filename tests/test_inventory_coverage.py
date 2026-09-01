from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "validate_artifacts.py"
SPEC = importlib.util.spec_from_file_location("validate_artifacts", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def inventory(status: str = "confirmed") -> dict:
    decision = "include" if status == "confirmed" else "pending"
    return {
        "surface": {"name": "Homepage", "routes": ["/"], "paths": ["index.html"]},
        "coverage": {
            "source_files": ["index.html"],
            "rendered_routes": ["/"],
            "states_checked": ["default"],
            "excluded_source_patterns": [],
            "limitations": [],
        },
        "selection": {
            "status": status,
            "confirmed_at": "2026-09-01T12:00:00Z" if status == "confirmed" else None,
            "note": "User selected the complete homepage." if status == "confirmed" else "",
        },
        "items": [
            {
                "id": "copy-001",
                "location": {"path": "index.html", "line": 10},
                "route": "/",
                "section": "Case study",
                "kind": "body",
                "original": "One dispatcher could assign at most 200 orders a day.",
                "purpose": "Explain the manual dispatch bottleneck.",
                "visibility": "default",
                "proposed_treatment": "keep",
                "proposal_reason": "Concrete and understandable.",
                "scope_decision": decision,
            }
        ],
    }


def brief(items: list[dict] | None = None) -> dict:
    return {
        "items": items if items is not None else [],
        "blocked_items": [],
    }


class InventoryCoverageTest(unittest.TestCase):
    def test_pending_inventory_has_no_preselection(self) -> None:
        errors, _ = VALIDATOR.validate_inventory(inventory("pending"))
        self.assertEqual(errors, [])

    def test_selected_copy_is_accounted_for(self) -> None:
        item = inventory()["items"][0]
        errors, _ = VALIDATOR.validate_inventory_against_brief(
            inventory(),
            brief(
                [
                    {
                        "id": item["id"],
                        "location": item["location"],
                        "original": item["original"],
                    }
                ]
            ),
        )
        self.assertEqual(errors, [])

    def test_selected_copy_cannot_silently_disappear(self) -> None:
        errors, _ = VALIDATOR.validate_inventory_against_brief(inventory(), brief())
        self.assertIn(
            "selected inventory item copy-001 is missing from the brief", errors
        )


if __name__ == "__main__":
    unittest.main()
