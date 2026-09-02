from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]


class ProjectStructureTest(unittest.TestCase):
    def test_development_entrypoints_exist(self) -> None:
        required = [
            "AGENTS.md",
            "README.md",
            "CONTEXT.md",
            "spec/v0.3/REQUIREMENTS.md",
            "design/INHERITANCE.md",
            "design/versions/v0.3/DESIGN_SPEC.md",
            "docs/agents/version-development.md",
            "docs/adr/0001-keep-installable-skill-at-repository-root.md",
        ]
        missing = [path for path in required if not (ROOT / path).is_file()]
        self.assertEqual(missing, [])

    def test_repository_root_remains_the_installable_skill(self) -> None:
        self.assertTrue((ROOT / "SKILL.md").is_file())
        self.assertFalse((ROOT / "skill" / "SKILL.md").exists())

    def test_runtime_entry_does_not_load_development_documents(self) -> None:
        entrypoint = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for development_path in (
            "spec/v0.3/",
            "design/versions/v0.3/",
            "docs/agents/",
            "docs/adr/",
        ):
            self.assertNotIn(development_path, entrypoint)


if __name__ == "__main__":
    unittest.main()
