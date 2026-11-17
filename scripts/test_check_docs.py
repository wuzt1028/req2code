#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-docs.py 的回归测试（零依赖）。"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class CheckDocsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="req2code-docs-"))
        self.root = self.tmp / "req2code"
        shutil.copytree(
            REPO,
            self.root,
            ignore=shutil.ignore_patterns(".git", "__pycache__"),
        )
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_check(self, *args: str):
        return subprocess.run(
            [sys.executable, str(self.root / "scripts" / "check-docs.py"), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def edit(self, path: str, old: str, new: str) -> None:
        file = self.root / path
        text = file.read_text(encoding="utf-8")
        self.assertIn(old, text)
        file.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_repo_passes(self) -> None:
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs check: 0 errors, 0 warnings", result.stdout)

    def test_gate_without_4b_is_rejected(self) -> None:
        self.edit(
            "SKILL.md",
            "（PRD 已确认版本 + 开发设计已确认版本 + 4b 用例就绪）",
            "（PRD 已确认版本 + 开发设计已确认版本）",
        )
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("D011", result.stdout)

    def test_stale_phrase_is_rejected(self) -> None:
        self.edit(
            "SKILL.md",
            "## 输入信任边界（安全）",
            "未确认项不得向下游传递。\n\n## 输入信任边界（安全）",
        )
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("D010", result.stdout)

    def test_phase_table_order_is_rejected(self) -> None:
        self.edit("SKILL.md", "| 4a | 场景清单", "| 9 | 场景清单")
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("D012", result.stdout)

    def test_json_output(self) -> None:
        result = self.run_check("--json")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"], 0)
        self.assertEqual(payload["warnings"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
