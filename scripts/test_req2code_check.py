#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""req2code-check.py 的回归测试（零依赖，python3 -m unittest 或直接运行）。"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECK = Path(__file__).with_name("req2code-check.py")


def state_template(directory: Path) -> dict:
    return {
        "schema": "req2code/state@1",
        "demand": "示例需求",
        "dir": str(directory),
        "updated_at": "2026-11-17",
        "mode": "full",
        "prototype": "html",
        "test_depth": "cases",
        "risk": {"level": "low", "data_change": False, "breaking_change": False, "security_sensitive": False},
        "prd_version": "v1",
        "design_version": "v1",
        "coding_allowed": False,
        "coding_granted_by": "",
        "coding_granted_at": "",
        "phases": {
            "0": {"status": "已完成", "completed_at": "2026-11-17", "artifact": "P0-输入与仓库侦察.md"},
            "1a": {"status": "已确认", "confirmed_by": "张三", "confirmed_at": "2026-11-17", "approval_ref": "msg-20261117-001", "artifact": "P1-PRD.md#0"},
            "1b": {"status": "已完成", "completed_at": "2026-11-17", "artifact": "P1-PRD.md"},
            "2": {"status": "已确认", "version": "v1", "confirmed_by": "张三", "confirmed_at": "2026-11-17", "approval_ref": "msg-20261117-002", "artifact": "P1-PRD.md"},
            "3": {"status": "已跳过"},
            "4a": {"status": "已完成", "completed_at": "2026-11-17", "artifact": "P4-场景与测试Case.md#scenarios"},
            "5": {"status": "已确认", "version": "v1", "confirmed_by": "张三", "confirmed_at": "2026-11-17", "approval_ref": "msg-20261117-003", "artifact": "P5-开发设计.md"},
            "4b": {"status": "已完成", "completed_at": "2026-11-17", "artifact": "P4-场景与测试Case.md#cases"},
            "6": {"status": "未开始"},
            "7": {"status": "未开始"},
            "8": {"status": "未开始", "artifact": "P8-验收记录.md"},
        },
        "skipped": [
            {"phase": "3", "reason": "无 UI 变更", "approved_by": "张三", "approved_at": "2026-11-17"}
        ],
        "pending_env": [],
    }


def table_from_state(state: dict) -> str:
    rows = [
        "| 阶段 | 产物 | 状态 | 版本 | 确认人 | 日期 |",
        "|---|---|---|---|---|---|",
    ]
    for phase in ("0", "1a", "1b", "2", "3", "4a", "5", "4b", "6", "7", "8"):
        data = state["phases"][phase]
        artifact = data.get("artifact", "-")
        version = data.get("version", "")
        confirmer = data.get("confirmed_by", "")
        date = data.get("completed_at") or data.get("confirmed_at", "")
        rows.append(
            "| %s | %s | %s | %s | %s | %s |"
            % (phase, artifact, data.get("status", ""), version, confirmer, date)
        )
    return "\n".join(rows) + "\n"


class CheckerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="req2code-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def make_demand(self, name: str = "demand", state: dict = None, table: str = None,
                    write_artifacts: bool = True, with_source: bool = True,
                    raw_state: str = None) -> Path:
        directory = self.tmp / name
        directory.mkdir(parents=True, exist_ok=True)
        if write_artifacts:
            for filename in (
                "P0-输入与仓库侦察.md",
                "P1-PRD.md",
                "P4-场景与测试Case.md",
                "P5-开发设计.md",
            ):
                source = "> 输入来源：P0-输入与仓库侦察.md（2026-11-17）\n" if with_source else ""
                (directory / filename).write_text("# %s\n\n%s" % (filename, source), encoding="utf-8")
        data = state if state is not None else state_template(directory)
        data["dir"] = str(directory)
        table_text = table if table is not None else table_from_state(data)
        if raw_state is not None:
            body = raw_state
        else:
            body = (
                "# 流水线状态：示例需求\n\n<!-- req2code:state -->\n```json\n"
                + json.dumps(data, ensure_ascii=False, indent=2)
                + "\n```\n<!-- /req2code:state -->\n\n"
                + table_text
            )
        (directory / "_状态.md").write_text(body, encoding="utf-8")
        return directory

    def run_check(self, directory: Path, *args: str):
        return subprocess.run(
            [sys.executable, str(CHECK), str(directory), *args],
            capture_output=True,
            text=True,
        )

    def test_valid_state_passes(self) -> None:
        directory = self.make_demand()
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("gate: PASS", result.stdout)

    def test_coding_without_permission_fails(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["phases"]["6"] = {
            "status": "已完成",
            "completed_at": "2026-11-17",
            "verification": {"level": "automated", "evidence": "pytest -q"},
        }
        directory = self.make_demand("gate", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E008", result.stdout)

    def test_missing_confirmer_fails(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["phases"]["5"].pop("confirmed_by", None)
        directory = self.make_demand("confirmer", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E005", result.stdout)

    def test_missing_risk_fails(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state.pop("risk", None)
        directory = self.make_demand("risk-missing", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E027", result.stdout)

    def test_high_risk_missing_nfr_fails(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["risk"] = {"level": "high", "data_change": True, "breaking_change": False, "security_sensitive": False, "reason": "数据变更"}
        directory = self.make_demand("risk-high", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E028", result.stdout)

    def test_high_risk_with_nfr_passes(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["risk"] = {"level": "high", "data_change": True, "breaking_change": False, "security_sensitive": True, "reason": "数据+安全"}
        directory = self.make_demand("risk-ok", state=state)
        (directory / "P5-开发设计.md").write_text(
            "# P5\n\n## 8. 风险、NFR 与可观测性\n"
            "- NFR：延迟/吞吐/容量目标\n- 失败模式与可用性\n"
            "- 可观测性：日志/指标/告警/runbook\n- 安全：鉴权/越权/PII/审计\n"
            "## 7. 发布与回滚\n- 回滚步骤\n\n> 输入来源：P1-PRD.md v1\n",
            encoding="utf-8",
        )
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_medium_risk_missing_reason_fails(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["risk"] = {"level": "medium", "data_change": False, "breaking_change": False, "security_sensitive": False}
        directory = self.make_demand("risk-reason", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E029", result.stdout)

    def test_breaking_change_without_consumer_impact_fails(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["risk"] = {
            "level": "medium",
            "data_change": False,
            "breaking_change": True,
            "security_sensitive": False,
            "reason": "既有页面响应体变化",
        }
        directory = self.make_demand("risk-breaking", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E030", result.stdout)

    def test_decision_brief_missing_fields_warns(self) -> None:
        directory = self.make_demand()
        (directory / "_决策简报.md").write_text("# 决策简报\n\n交付完成，验收通过。\n", encoding="utf-8")
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("W026", result.stdout)

    def test_medium_risk_missing_nfr_warns(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["risk"] = {"level": "medium", "data_change": False, "breaking_change": False, "security_sensitive": False, "reason": "安全敏感"}
        directory = self.make_demand("risk-medium", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("W024", result.stdout)

    def test_artifact_header_conflict_fails(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["phases"]["5"] = {"status": "待确认", "version": "v1", "artifact": "P5-开发设计.md"}
        directory = self.make_demand("header-conflict", state=state)
        (directory / "P5-开发设计.md").write_text(
            "# P5\n\n> 状态：已实施\n\n> 输入来源：P1-PRD.md v1\n", encoding="utf-8"
        )
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E026", result.stdout)

    def test_stale_artifact_header_warns(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        directory = self.make_demand("header-stale", state=state)
        (directory / "P5-开发设计.md").write_text(
            "# P5\n\n> 状态：待用户确认\n\n> 输入来源：P1-PRD.md v1\n", encoding="utf-8"
        )
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("W022", result.stdout)

    def test_missing_approval_ref_fails(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["phases"]["5"].pop("approval_ref", None)
        directory = self.make_demand("approval-ref", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E025", result.stdout)

    def test_skip_without_approval_fails(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["skipped"] = []
        directory = self.make_demand("skip", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E010", result.stdout)

    def test_table_json_mismatch_fails(self) -> None:
        base = state_template(self.tmp)
        table = table_from_state(base).replace("| 5 | P5-开发设计.md | 已确认", "| 5 | P5-开发设计.md | 未开始")
        directory = self.make_demand("mismatch", table=table)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E015", result.stdout)

    def test_missing_mode_fails(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state.pop("mode", None)
        directory = self.make_demand("nomode", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E024", result.stdout)

    def test_mode_alignment_warns(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["mode"] = "analysis-only"
        directory = self.make_demand("mode-align", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 0)
        self.assertIn("W019", result.stdout)

    def test_prototype_html_missing_warns(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["phases"]["3"] = {
            "status": "已确认",
            "confirmed_by": "张三",
            "confirmed_at": "2026-11-17",
            "approval_ref": "msg-20261117-004",
            "artifact": "P3-设计说明.md",
        }
        state["skipped"] = []
        directory = self.make_demand("proto", state=state)
        (directory / "P3-设计说明.md").write_text("# P3\n\n> 输入来源：P1-PRD.md v1\n", encoding="utf-8")
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 0)
        self.assertIn("W020", result.stdout)

    def test_log_file_is_ignored(self) -> None:
        directory = self.make_demand()
        (directory / "_日志.md").write_text("# 运行日志\n\n## 2026-11-17\n- 过程记录\n", encoding="utf-8")
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("W003", result.stdout)

    def test_coding_requires_4b_cases(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["coding_allowed"] = True
        state["coding_granted_by"] = "张三"
        state["coding_granted_at"] = "2026-11-17"
        state["phases"]["4b"] = {"status": "未开始"}
        directory = self.make_demand("need4b", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E009 [4b]", result.stdout)
        self.assertIn("coding: BLOCKED", result.stdout)

    def test_completed_coding_requires_verification(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["coding_allowed"] = True
        state["coding_granted_by"] = "张三"
        state["coding_granted_at"] = "2026-11-17"
        state["phases"]["6"] = {"status": "已完成", "completed_at": "2026-11-17"}
        directory = self.make_demand("verify-needed", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E023", result.stdout)

    def test_completed_coding_with_verification_passes(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["coding_allowed"] = True
        state["coding_granted_by"] = "张三"
        state["coding_granted_at"] = "2026-11-17"
        state["phases"]["6"] = {
            "status": "已完成",
            "completed_at": "2026-11-17",
            "verification": {"level": "automated", "evidence": "pytest -q tests/test_feature.py"},
        }
        state["phases"]["7"] = {"status": "不适用"}
        directory = self.make_demand("verify-ok", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("gate: PASS", result.stdout)
        self.assertIn("coding: ALLOWED", result.stdout)

    def test_p8_completed_without_exit_conclusion_fails(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["phases"]["8"] = {
            "status": "已完成",
            "completed_at": "2026-11-17",
            "artifact": "P8-验收记录.md",
        }
        directory = self.make_demand("p8-no-exit", state=state)
        (directory / "P8-验收记录.md").write_text("# P8\n\n验收通过\n", encoding="utf-8")
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E022", result.stdout)

    def test_p8_completed_with_exit_conclusion_passes(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["phases"]["8"] = {
            "status": "已完成",
            "completed_at": "2026-11-17",
            "artifact": "P8-验收记录.md",
        }
        directory = self.make_demand("p8-exit-ok", state=state)
        (directory / "P8-验收记录.md").write_text(
            "# P8\n\n## 退出结论\n- 退出结论：通过\n- 未关闭 P0/P1 Bug：0\n", encoding="utf-8"
        )
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("gate: PASS", result.stdout)

    def test_pending_env_with_completed_phase8_fails(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["pending_env"] = ["T01"]
        state["phases"]["8"] = {"status": "已完成", "completed_at": "2026-11-17", "artifact": "P8-验收记录.md"}
        directory = self.make_demand("pending", state=state)
        (directory / "P8-验收记录.md").write_text(
            "# P8\n\n退出结论：通过\n未关闭 P0/P1 Bug：0\n\n验收通过\n", encoding="utf-8"
        )
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E013", result.stdout)

    def test_bad_json_fails(self) -> None:
        directory = self.make_demand(raw_state="# 状态\n\n<!-- req2code:state -->\n{bad json}\n<!-- /req2code:state -->\n")
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E001", result.stdout)

    def test_missing_artifact_fails(self) -> None:
        directory = self.make_demand()
        state = state_template(directory)
        state["phases"]["5"]["artifact"] = "missing.md"
        directory = self.make_demand("artifact", state=state)
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E012", result.stdout)

    def test_legacy_table_is_parsed(self) -> None:
        directory = self.tmp / "legacy"
        directory.mkdir()
        (directory / "_状态.md").write_text(
            "# 流水线状态：旧需求\n\n"
            "| 阶段 | 产物 | 状态 | 确认人 | 日期 | 下一步 |\n"
            "|---|---|---|---|---|---|\n"
            "| 0 输入与仓库侦察 | P0.md | 已完成 | - | 2026-09-15 | |\n"
            "| 1a 需求理解复述 | P1-PRD.md | 已确认 | 操作者 | 2026-09-15 | |\n"
            "| 1b 需求分析 | P1-PRD.md | 已完成 | - | 2026-09-15 | |\n"
            "| 2 需求澄清 | P1-PRD.md | 已确认 | 操作者 | 2026-09-15 | |\n"
            "| 3 交互设计 | - | 已确认 | 操作者 | 2026-09-15 | |\n"
            "| 4 场景与测试 Case | P4.md | 已完成 | 操作者 | 2026-09-15 | |\n"
            "| 5 开发设计 | P5-开发设计.md | 待确认 | | | |\n"
            "| 6 后端开发 | 代码 | 已完成 | - | 2026-09-15 | |\n"
            "| 7 前端开发 | 代码 | 已完成 | - | 2026-09-15 | |\n"
            "| 8 联调与验收 | P8.md | 待环境 | - | | |\n",
            encoding="utf-8",
        )
        result = self.run_check(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("W001", result.stdout)
        self.assertIn("E007", result.stdout)

    def test_json_output(self) -> None:
        directory = self.make_demand()
        result = self.run_check(directory, "--json")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate"], "PASS")
        self.assertEqual(payload["coding"], "BLOCKED")
        self.assertEqual(payload["errors"], [])

    def test_strict_turns_warnings_into_failure(self) -> None:
        directory = self.make_demand(with_source=False)
        result = self.run_check(directory, "--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("W003", result.stdout)

    def test_scan_finds_all_demands(self) -> None:
        root = self.tmp / "repo" / "docs" / "ai-coding"
        root.mkdir(parents=True)
        first = self.make_demand("repo/docs/ai-coding/20261117-a")
        second = self.make_demand("repo/docs/ai-coding/20261117-b")
        result = self.run_check(self.tmp / "repo", "--scan", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual({Path(item["dir"]).name for item in payload}, {"20261117-a", "20261117-b"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
