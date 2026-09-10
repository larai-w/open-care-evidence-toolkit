from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("public_repo_guard", ROOT / "scripts" / "check_public_repo.py")
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class PublicRepoGuardTests(unittest.TestCase):
    def test_allows_a_normal_public_file(self) -> None:
        self.assertEqual(guard.check_paths([Path("README.md")]), [])

    def test_rejects_known_internal_material(self) -> None:
        self.assertEqual(
            guard.check_paths([Path("docs-private/launch-notes.md")]),
            ["internal-only path is not allowed: docs-private/launch-notes.md"],
        )

    def test_rejects_private_key_format(self) -> None:
        fixture = ROOT / "tests" / "_temporary_secret.txt"
        fixture.write_text("-----BEGIN " + "PRIVATE KEY-----\n", encoding="utf-8")
        try:
            self.assertEqual(guard.check_paths([fixture.relative_to(ROOT)]), ["possible private key in: tests/_temporary_secret.txt"])
        finally:
            fixture.unlink()


if __name__ == "__main__":
    unittest.main()
