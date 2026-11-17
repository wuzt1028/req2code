#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""req2code 状态与门禁校验器（零依赖，Python 3.8+）。

用法：
    python3 scripts/req2code-check.py <需求目录>
    python3 scripts/req2code-check.py <仓库根> --scan
    python3 scripts/req2code-check.py <需求目录> --json
    python3 scripts/req2code-check.py <需求目录> --strict

退出码：0=通过；1=有 ERROR（或 --strict 下 WARN）；2=参数/路径错误。

设计原则：
- 新格式：`_状态.md` 中 `<!-- req2code:state -->` 与
  `<!-- /req2code:state -->` 之间是 JSON，作为门禁唯一事实源。
- 旧格式：没有 JSON 标记时，按阶段表降级解析，给出 WARN，不阻塞历史目录。
- 只做只读校验，不修改任何文件。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

SCHEMA = "req2code/state@1"
STATE_START = "<!-- req2code:state -->"
STATE_END = "<!-- /req2code:state -->"

PHASES = ["0", "1a", "1b", "2", "3", "4a", "5", "4b", "6", "7", "8"]
LEGACY_PHASE_GROUP = "4"
PHASE_KEYS = set(PHASES) | {LEGACY_PHASE_GROUP}
CONFIRM_REQUIRED = {"1a", "2", "3", "5"}
STATUSES = {"未开始", "进行中", "待确认", "已确认", "已完成", "已跳过", "不适用"}
MODES = {"full", "backend-only", "frontend-only", "analysis-only", "prototype-only", "fast"}
PROTOTYPES = {"html", "annotated", "inline", "none"}
TEST_DEPTHS = {"cases", "smoke", "none"}
VERIFICATION_LEVELS = {"automated", "manual", "not-verified"}
CODING_PHASES = {"6", "7"}

FILE_RE = re.compile(
    r"([A-Za-z0-9_\-.\u4e00-\u9fff]+\.(?:md|markdown|html|htm|json|ya?ml|txt))",
    re.IGNORECASE,
)
VERSION_RE = re.compile(r"\bv(\d+(?:\.\d+)*)\b", re.IGNORECASE)
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
PHASE_RE = re.compile(r"^(?:phase\s*)?([0-8](?:[ab])?)(?!\d)", re.IGNORECASE)


@dataclass
class Issue:
    level: str
    code: str
    phase: str
    message: str
    hint: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "level": self.level,
            "code": self.code,
            "phase": self.phase,
            "message": self.message,
            "hint": self.hint,
        }


@dataclass
class Result:
    directory: str
    mode: str
    gate: str
    coding: str
    acceptance: str
    issues: List[Issue]

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.level == "ERROR"]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.level == "WARN"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dir": self.directory,
            "mode": self.mode,
            "gate": self.gate,
            "coding": self.coding,
            "acceptance": self.acceptance,
            "errors": [i.to_dict() for i in self.errors],
            "warnings": [i.to_dict() for i in self.warnings],
        }


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"[`*_~]", "", text)
    return text.strip()


def clean_person(value: Any) -> str:
    text = clean_text(value)
    if text in {"", "-", "—", "–", "－", "/", "无", "待定", "N/A", "n/a"}:
        return ""
    return text


def clean_ref(value: Any) -> str:
    """审批引用：消息 ID / 邮件 / 会议链接 / 工单都行；占位符不算。"""
    text = clean_text(value)
    if text.lower() in {"", "-", "—", "–", "－", "/", "无", "待定", "todo", "tbd", "n/a", "na"}:
        return ""
    return text if len(text) >= 4 else ""


def parse_date(value: Any) -> str:
    match = DATE_RE.search(str(value or ""))
    return match.group(1) if match else ""


def parse_version(value: Any) -> Optional[str]:
    match = VERSION_RE.search(str(value or ""))
    return match.group(1) if match else None


def normalize_version(value: Any) -> Optional[str]:
    """接受 v0.8 / 0.8 两种写法（state 字段常存裸版本号）。"""
    text = clean_text(value)
    match = VERSION_RE.search(text)
    if match:
        return match.group(1)
    if re.fullmatch(r"\d+(?:\.\d+)*", text):
        return text
    return None


def version_key(version: Optional[str]) -> Optional[Tuple[int, ...]]:
    if not version:
        return None
    return tuple(int(p) for p in version.split("."))


def version_less(a: Optional[str], b: Optional[str]) -> bool:
    ka, kb = version_key(a), version_key(b)
    return bool(ka is not None and kb is not None and ka < kb)


def canonical_phase(value: Any) -> Optional[str]:
    text = clean_text(value).lower().replace("phase", "").strip()
    text = text.replace(" ", "")
    if text in PHASE_KEYS:
        return text
    match = PHASE_RE.match(text)
    if match:
        key = match.group(1).lower()
        return key if key in PHASE_KEYS else None
    return None


def phase_number(phase: Optional[str]) -> int:
    if not phase:
        return -1
    match = re.match(r"(\d+)", phase)
    return int(match.group(1)) if match else -1


def extract_files(value: Any) -> List[str]:
    seen: List[str] = []
    for match in FILE_RE.finditer(str(value or "")):
        name = match.group(1).strip("`")
        if name not in seen:
            seen.append(name)
    return seen


def normalize_status(raw: Any) -> Tuple[Optional[str], List[str]]:
    text = clean_text(raw)
    if text in STATUSES:
        return text, []
    if "待确认是否跳过" in text:
        return "待确认", ["skip_pending"]
    if "待环境" in text or "待联调" in text or "待验收" in text:
        return "待确认", ["pending_env"]
    if "已跳过" in text:
        return "已跳过", []
    if "已确认" in text:
        return "已确认", []
    if "已完成" in text or "已实施" in text or "已交付" in text:
        return "已完成", []
    if "草案" in text or "进行中" in text or "开发中" in text or "实施中" in text:
        return "进行中", []
    if "未开始" in text:
        return "未开始", []
    return None, ["unknown"]


def version_after(line: str, filename: str) -> Optional[str]:
    index = line.find(filename)
    if index < 0:
        return None
    tail = line[index + len(filename) : index + len(filename) + 32]
    return parse_version(tail)


class Checker:
    def __init__(self, directory: Path):
        self.dir = directory
        self.md = directory / "_状态.md"
        self.text = ""
        self.state: Dict[str, Any] = {}
        self.mode = "legacy"
        self.issues: List[Issue] = []
        self.table_rows: List[Dict[str, str]] = []

    # ---------- 基础 ----------

    def issue(self, level: str, code: str, phase: str, message: str, hint: str = "") -> None:
        self.issues.append(Issue(level, code, phase, message, hint))

    def run(self) -> Result:
        if not self.md.exists():
            self.issue("ERROR", "E000", "-", "找不到 _状态.md", "传入需求产物目录，而不是仓库根")
            return self._result()
        try:
            self.text = self.md.read_text(encoding="utf-8")
        except OSError as exc:
            self.issue("ERROR", "E000", "-", "无法读取 _状态.md：%s" % exc)
            return self._result()

        if STATE_START in self.text:
            self.mode = "json"
            try:
                self.state = self._load_state_json()
            except ValueError as exc:
                self.issue("ERROR", "E001", "-", "state JSON 无法解析：%s" % exc,
                           "修复 <!-- req2code:state --> 内的 JSON；或删除标记回退旧表格")
                return self._result()
            self.table_rows = self._parse_table()
            self._validate_json_header()
        else:
            self.mode = "legacy"
            self.table_rows = self._parse_table()
            if not self.table_rows:
                self.issue("ERROR", "E000", "-", "既没有 state JSON，也找不到阶段表",
                           "按 artifacts.md 模板补 _状态.md")
                return self._result()
            self.state = self._legacy_state()
            self.issue("WARN", "W001", "-", "旧格式：未找到 state JSON，按阶段表降级解析",
                       "新需求请使用 <!-- req2code:state --> JSON 作为事实源")

        self._validate_phases()
        self._validate_mode_alignment()
        self._validate_prototype()
        self._validate_gate()
        self._validate_risk_gates()
        self._validate_skips()
        self._validate_artifacts()
        self._validate_artifact_headers()
        self._validate_decision_brief()
        self._validate_p8_quality()
        self._validate_inputs()
        self._validate_env()
        if self.mode == "json":
            self._validate_json_table()
        return self._result()

    def _result(self) -> Result:
        errors = [i for i in self.issues if i.level == "ERROR"]
        gate = "PASS" if not errors else "FAIL"
        phases = self.state.get("phases") if isinstance(self.state, dict) else None
        phase8 = phases.get("8", {}) if isinstance(phases, dict) else {}
        pending = bool(self.state.get("pending_env")) if isinstance(self.state, dict) else False
        notes = clean_text(phase8.get("notes", "")) if isinstance(phase8, dict) else ""
        notes_pending = bool(notes) and ("待" in notes or "未完成" in notes)
        acceptance = "PENDING" if (pending or notes_pending or phase8.get("status") not in {"已完成", "不适用"}) else "DONE"
        error_codes = {issue.code for issue in errors}
        coding_blockers = {"E007", "E008", "E009", "E014"}
        coding = "ALLOWED" if self.state.get("coding_allowed") and not (error_codes & coding_blockers) else "BLOCKED"
        return Result(str(self.dir), self.mode, gate, coding, acceptance, self.issues)

    # ---------- 解析 ----------

    def _load_state_json(self) -> Dict[str, Any]:
        start = self.text.index(STATE_START) + len(STATE_START)
        end = self.text.find(STATE_END, start)
        if end < 0:
            raise ValueError("state 结束标记缺失")
        raw = self.text[start:end].strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("顶层必须是对象")
        phases = data.get("phases")
        if phases is not None and not isinstance(phases, dict):
            raise ValueError("phases 必须是对象")
        return data

    def _parse_table(self) -> List[Dict[str, str]]:
        lines = self.text.splitlines()
        header: Optional[List[str]] = None
        rows: List[Dict[str, str]] = []
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("|"):
                if header is not None and rows:
                    break
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if header is None:
                lowered = [c.lower().replace(" ", "") for c in cells]
                has_status = any("状态" in c for c in cells)
                has_phase = any(("阶段" in c) or ("phase" in c) for c in lowered)
                if has_status and has_phase:
                    header = cells
                continue
            if all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in cells):
                continue
            if len(cells) < len(header):
                cells += [""] * (len(header) - len(cells))
            rows.append(dict(zip(header, cells[: len(header)])))
        return rows

    def _find_col(self, keys: Iterable[str]) -> Optional[int]:
        header = self.table_rows[0].keys() if self.table_rows else []
        for index, name in enumerate(header):
            lowered = name.lower().replace(" ", "")
            if any(key.lower() in lowered for key in keys):
                return index
        return None

    def _row_value(self, row: Dict[str, str], keys: Iterable[str]) -> str:
        for key, value in row.items():
            lowered = key.lower().replace(" ", "")
            if any(k.lower() in lowered for k in keys):
                return value
        return ""

    def _legacy_state(self) -> Dict[str, Any]:
        phases: Dict[str, Dict[str, Any]] = {}

        for row in self.table_rows:
            phase = canonical_phase(row.get("Phase") or row.get("阶段") or "")
            if phase is None:
                phase = canonical_phase(self._row_value(row, ["phase", "阶段"]))
            if phase is None:
                continue
            raw_status = self._row_value(row, ["状态"])
            status, flags = normalize_status(raw_status)
            if status is None:
                status = "未开始"
                flags = flags + ["unknown"]
            raw_clean = clean_text(raw_status)
            if status is not None and raw_clean not in STATUSES:
                self.issue("WARN", "W002", phase,
                           "非标准状态 %r，按 %r 解析" % (raw_clean, status),
                           "新格式只允许闭集状态")
            artifact = self._row_value(row, ["产物"])
            confirmer = clean_person(self._row_value(row, ["确认人"]))
            date = parse_date(self._row_value(row, ["日期"]))
            version = normalize_version(raw_status) or normalize_version(artifact)
            notes = self._row_value(row, ["下一步", "备注"])
            if phase in phases:
                self.issue("WARN", "W002", phase, "阶段在表格中重复，采用最后一行")
            phases[phase] = {
                "status": status,
                "artifact": artifact,
                "confirmed_by": confirmer,
                "confirmed_at": date,
                "completed_at": date,
                "version": version,
                "notes": notes,
                "_raw_status": clean_text(raw_status),
                "_flags": flags,
            }

        state: Dict[str, Any] = {
            "schema": SCHEMA,
            "demand": self._legacy_demand(),
            "updated_at": self._legacy_updated_at(),
            "phases": phases,
            "skipped": [],
            "pending_env": [],
            "coding_allowed": None,
            "_legacy": True,
        }
        if LEGACY_PHASE_GROUP in phases:
            self.issue("WARN", "W015", LEGACY_PHASE_GROUP,
                       "旧目录使用合并阶段 4；新需求请拆 4a 场景 / 4b 用例")
        if "5" in phases and phases["5"].get("status") in {"已确认", "已完成"}:
            self.issue("WARN", "W023", "5", "旧格式无 risk 字段，按 low 处理",
                       "补 state JSON 的 risk 后走严格校验")

        for phase, data in phases.items():
            if "skip_pending" in data.get("_flags", []):
                state["skipped"].append(
                    {
                        "phase": phase,
                        "reason": "状态为“待确认是否跳过”",
                        "approved_by": "",
                        "approved_at": "",
                    }
                )
            if "pending_env" in data.get("_flags", []):
                state["_pending_env_flag"] = True

        self._apply_gate_lines(state)
        for phase in ("2", "5"):
            if phase in phases and not phases[phase].get("version"):
                key = "prd_version" if phase == "2" else "design_version"
                if state.get(key):
                    phases[phase]["version"] = state[key]
        if state.get("coding_allowed") is None:
            active = any(phases.get(p, {}).get("status") in {"进行中", "已完成"} for p in CODING_PHASES)
            state["coding_allowed"] = active
            if active:
                self.issue("WARN", "W012", "-", "旧格式无 coding_allowed，按 6/7 状态推断为已授予",
                           "补 state JSON，并在确认时记录 coding_granted_by/at")
        return state

    def _legacy_demand(self) -> str:
        match = re.search(r"^#\s*(.+)$", self.text, re.MULTILINE)
        if match:
            return clean_text(match.group(1)).replace("流水线状态：", "").replace("需求流水线状态 · ", "").strip()
        match = re.search(r"需求短名[：:]\s*(.+)", self.text)
        return clean_text(match.group(1)) if match else ""

    def _legacy_updated_at(self) -> str:
        match = re.search(r"最后更新[：:]\s*(20\d{2}-\d{2}-\d{2})", self.text)
        return match.group(1) if match else ""

    def _apply_gate_lines(self, state: Dict[str, Any]) -> None:
        for line in self.text.splitlines():
            if "PRD 已确认" in line:
                state["prd_version"] = parse_version(line) or state.get("prd_version")
            if "开发设计已确认" in line:
                state["design_version"] = parse_version(line) or state.get("design_version")
            if "编码许可" in line:
                granted = bool(re.search(r"授予|允许|批准|granted|yes|true", line, re.IGNORECASE))
                state["coding_allowed"] = granted
                state["coding_granted_by"] = "用户" if "用户" in line else ""
                state["coding_granted_at"] = parse_date(line)
            if "跳过阶段" in line:
                match = re.search(r"Phase\s*(\d+[ab]?)", line, re.IGNORECASE)
                if not match:
                    continue
                phase = match.group(1).lower()
                approved = ("待" not in line) and bool(
                    re.search(r"确认|批准|approved", line, re.IGNORECASE)
                )
                entry = {
                    "phase": phase,
                    "reason": clean_text(line.split("：", 1)[-1].split(":", 1)[-1]),
                    "approved_by": "用户" if approved else "",
                    "approved_at": parse_date(line) if approved else "",
                }
                existing = [e for e in state["skipped"] if canonical_phase(e.get("phase")) == phase]
                if not existing:
                    state["skipped"].append(entry)

    # ---------- 校验 ----------

    def _validate_json_header(self) -> None:
        if self.state.get("schema") != SCHEMA:
            self.issue("ERROR", "E002", "-", "state.schema 缺失或不是 %s" % SCHEMA)
        if not clean_text(self.state.get("demand")):
            self.issue("ERROR", "E019", "-", "state.demand 不能为空")
        if not clean_text(self.state.get("updated_at")):
            self.issue("ERROR", "E018", "-", "state.updated_at 不能为空")
        elif not parse_date(self.state.get("updated_at")):
            self.issue("ERROR", "E018", "-", "state.updated_at 不是 YYYY-MM-DD")

        mode = self.state.get("mode")
        if not clean_text(mode):
            self.issue("ERROR", "E024", "-", "state.mode 缺失",
                       "Phase 0 定档：full / backend-only / frontend-only / analysis-only / prototype-only / fast")
        elif mode not in MODES:
            self.issue("ERROR", "E021", "-", "mode 不在允许集合：%s" % mode)
        if self.state.get("prototype") is not None and self.state.get("prototype") not in PROTOTYPES:
            self.issue("ERROR", "E021", "-", "prototype 不在允许集合：%s" % self.state.get("prototype"))
        if self.state.get("test_depth") is not None and self.state.get("test_depth") not in TEST_DEPTHS:
            self.issue("ERROR", "E021", "-", "test_depth 不在允许集合：%s" % self.state.get("test_depth"))
        risk = self.state.get("risk")
        if not isinstance(risk, dict):
            self.issue("ERROR", "E027", "-", "state.risk 缺失或不是对象",
                       "补 risk.level + data_change/breaking_change/security_sensitive")
        else:
            level = risk.get("level")
            if level not in {"low", "medium", "high"}:
                self.issue("ERROR", "E027", "-", "risk.level 必须是 low/medium/high")
            for key in ("data_change", "breaking_change", "security_sensitive"):
                if not isinstance(risk.get(key), bool):
                    self.issue("ERROR", "E027", "-", "risk.%s 必须是布尔值" % key)
            reason = risk.get("reason")
            if reason is not None and not isinstance(reason, str):
                self.issue("ERROR", "E027", "-", "risk.reason 必须是字符串")
            if level in {"medium", "high"} and not clean_text(reason):
                self.issue("ERROR", "E029", "-", "medium/high 风险缺 risk.reason",
                           "写清为什么是这个等级（影响/可能性/可逆性）")
            assumptions = risk.get("assumptions")
            if assumptions is not None and not isinstance(assumptions, list):
                self.issue("ERROR", "E027", "-", "risk.assumptions 必须是数组")
            consumer_impact = risk.get("consumer_impact")
            if consumer_impact is not None and not isinstance(consumer_impact, list):
                self.issue("ERROR", "E027", "-", "risk.consumer_impact 必须是数组")
            if risk.get("breaking_change"):
                if not (isinstance(consumer_impact, list) and any(clean_text(x) for x in consumer_impact)):
                    self.issue("ERROR", "E030", "-", "breaking_change=true 但缺 risk.consumer_impact",
                               "列出受影响的客户端/调用方与兼容性结论")

        phases = self.state.get("phases")
        if not isinstance(phases, dict):
            self.issue("ERROR", "E003", "-", "state.phases 缺失或不是对象")
            self.state["phases"] = {}
            return

        normalized: Dict[str, Dict[str, Any]] = {}
        for key, value in phases.items():
            canonical = canonical_phase(key)
            if canonical is None:
                self.issue("ERROR", "E003", str(key), "未知阶段键 %r" % key)
                continue
            if not isinstance(value, dict):
                self.issue("ERROR", "E003", canonical, "阶段值必须是对象")
                continue
            normalized[canonical] = value
        self.state["phases"] = normalized

        has_legacy = LEGACY_PHASE_GROUP in normalized
        has_4a = "4a" in normalized
        has_4b = "4b" in normalized
        if has_legacy and (has_4a or has_4b):
            self.issue("ERROR", "E003", "4", "阶段键冲突：4 与 4a/4b 不能并存")
        elif has_legacy:
            self.issue("WARN", "W015", "4", "使用合并阶段 4；B 版起建议拆成 4a 场景 / 4b 用例")
        for phase in PHASES:
            if phase in normalized:
                continue
            if phase in {"4a", "4b"} and has_legacy:
                continue
            self.issue("ERROR", "E003", phase, "state.phases 缺少阶段 %s" % phase,
                       "未涉及的后端/前端阶段标为“不适用”")
        if self.state.get("dir"):
            declared = Path(str(self.state.get("dir")))
            try:
                if declared.resolve() != self.dir.resolve():
                    self.issue("WARN", "W011", "-", "state.dir 与实际目录不一致", str(declared))
            except OSError:
                self.issue("WARN", "W011", "-", "state.dir 无法解析", str(declared))
        if self.state.get("coding_allowed") is not None and not isinstance(
            self.state.get("coding_allowed"), bool
        ):
            self.issue("ERROR", "E021", "-", "coding_allowed 必须是 true/false")
        if not isinstance(self.state.get("skipped", []), list):
            self.issue("ERROR", "E021", "-", "skipped 必须是数组")
            self.state["skipped"] = []
        if not isinstance(self.state.get("pending_env", []), list):
            self.issue("ERROR", "E021", "-", "pending_env 必须是数组")
            self.state["pending_env"] = []

    def _validate_phases(self) -> None:
        phases = self.state.get("phases", {})
        if not isinstance(phases, dict):
            return
        for phase, data in phases.items():
            if not isinstance(data, dict):
                continue
            status = data.get("status")
            if status not in STATUSES:
                self.issue("ERROR", "E004", phase, "非法状态 %r（允许：%s）" % (status, " / ".join(sorted(STATUSES))))
                continue
            if status == "已确认" or (status == "已完成" and phase in CONFIRM_REQUIRED):
                missing = []
                if not clean_person(data.get("confirmed_by")):
                    missing.append("confirmed_by")
                if not parse_date(data.get("confirmed_at")):
                    missing.append("confirmed_at")
                if missing:
                    self.issue("ERROR", "E005", phase, "确认类阶段缺 %s" % " / ".join(missing),
                               "在 state JSON 的 phases.%s 补确认人/确认日期" % phase)
                if not clean_ref(data.get("approval_ref")):
                    level = "ERROR" if self.mode == "json" else "WARN"
                    code = "E025" if self.mode == "json" else "W021"
                    self.issue(level, code, phase, "确认缺少审批引用 approval_ref",
                               "补消息 ID / 邮件 / 会议纪要 / 工单链接；只口头确认不算")
            if status == "已完成" and phase not in CONFIRM_REQUIRED:
                if not parse_date(data.get("completed_at") or data.get("confirmed_at")):
                    level = "ERROR" if self.mode == "json" else "WARN"
                    code = "E006" if self.mode == "json" else "W006"
                    self.issue(level, code, phase, "已完成阶段缺 completed_at",
                               "补完成日期（旧目录可先记 WARN）")
            if status == "已完成" and phase in CODING_PHASES:
                verification = data.get("verification")
                verify_level = verification.get("level") if isinstance(verification, dict) else ""
                evidence = clean_text(verification.get("evidence")) if isinstance(verification, dict) else ""
                if verify_level not in {"automated", "manual"} or not evidence:
                    level = "ERROR" if self.mode == "json" else "WARN"
                    code = "E023" if self.mode == "json" else "W017"
                    self.issue(level, code, phase, "已完成但验证证据不足（需 automated|manual + evidence）",
                               "构建/编译通过只是 build-only，不能把 6/7 标已完成")
            if status == "已跳过":
                self._require_skip_entry(phase)

    def _validate_mode_alignment(self) -> None:
        if self.mode != "json":
            return
        mode = self.state.get("mode")
        if mode not in MODES:
            return
        if mode == "fast":
            self.issue("WARN", "W019", "-", "mode=fast 不应创建流水线状态", "快速通道不建 docs/ai-coding 产物")
            return
        rules = {
            "analysis-only": ("3", "4a", "5", "4b", "6", "7", "8"),
            "prototype-only": ("4a", "5", "4b", "6", "7", "8"),
            "backend-only": ("7",),
            "frontend-only": ("6",),
        }
        for phase in rules.get(mode, ()):  # type: ignore[arg-type]
            status = self._status(phase)
            if status not in {"未开始", "不适用", "已跳过"}:
                self.issue("WARN", "W019", phase,
                           "mode=%s 预设下该阶段应为未开始/不适用（当前 %r）" % (mode, status),
                           "调整 mode，或把该阶段标为不适用/已跳过")

    def _validate_prototype(self) -> None:
        if self.mode != "json":
            return
        prototype = self.state.get("prototype")
        phase3 = self.state.get("phases", {}).get("3", {})
        status = phase3.get("status") if isinstance(phase3, dict) else None
        if status not in {"进行中", "已确认", "已完成"}:
            return
        artifact = str(phase3.get("artifact", "")) if isinstance(phase3, dict) else ""
        if prototype == "html":
            if "P3-交互原型.html" not in artifact and not (self.dir / "P3-交互原型.html").exists():
                self.issue("WARN", "W020", "3", "prototype=html，但 Phase 3 没有 P3-交互原型.html",
                           "补 HTML 原型，或把 prototype 改为 annotated/inline/none")
        elif prototype == "annotated":
            if "P3-原型批注.md" not in artifact and not (self.dir / "P3-原型批注.md").exists():
                self.issue("WARN", "W020", "3", "prototype=annotated，但 Phase 3 没有 P3-原型批注.md",
                           "补批注文件，或调整 prototype")
        elif prototype == "none":
            self.issue("WARN", "W020", "3", "prototype=none，但 Phase 3 仍处于 %r" % status,
                       "把 Phase 3 标为不适用/已跳过，或选择 html/annotated/inline")

    def _find_skip(self, phase: str) -> Optional[Dict[str, Any]]:
        for entry in self.state.get("skipped", []) or []:
            if isinstance(entry, dict) and canonical_phase(entry.get("phase")) == phase:
                return entry
        return None

    def _status(self, phase: str) -> Optional[str]:
        phases = self.state.get("phases", {})
        if not isinstance(phases, dict):
            return None
        data = phases.get(phase)
        if isinstance(data, dict):
            return data.get("status")
        legacy = phases.get(LEGACY_PHASE_GROUP)
        if phase in {"4a", "4b"} and isinstance(legacy, dict):
            return legacy.get("status")
        if phase == LEGACY_PHASE_GROUP:
            nested = [
                phases.get(p, {}).get("status")
                for p in ("4a", "4b")
                if isinstance(phases.get(p), dict)
            ]
            if nested:
                if all(s in {"已确认", "已完成", "已跳过", "不适用"} for s in nested):
                    return "已完成"
                return "待确认"
        return None

    def _require_skip_entry(self, phase: str) -> None:
        entry = self._find_skip(phase)
        if entry is None:
            self.issue("ERROR", "E010", phase, "阶段标为已跳过，但 skipped 中没有对应审批记录")
            return
        missing = [
            key
            for key in ("approved_by", "approved_at", "reason")
            if not clean_text(entry.get(key))
        ]
        if missing:
            self.issue("ERROR", "E010", phase, "跳过记录缺 %s" % " / ".join(missing),
                       "补 approved_by / approved_at / reason")

    def _validate_gate(self) -> None:
        phases = self.state.get("phases", {})
        if not isinstance(phases, dict):
            return
        active = any(phases.get(p, {}).get("status") in {"进行中", "已完成"} for p in CODING_PHASES)
        allowed = self.state.get("coding_allowed")
        if allowed is None:
            allowed = active
            self.state["coding_allowed"] = allowed

        if allowed:
            grant_missing = [
                key
                for key in ("coding_granted_by", "coding_granted_at")
                if not (clean_text(self.state.get(key)) if key == "coding_granted_by" else parse_date(self.state.get(key)))
            ]
            if grant_missing:
                self.issue("ERROR", "E014", "-", "coding_allowed=true 但缺 %s" % " / ".join(grant_missing),
                           "补授予人/日期；只口头确认不落盘视为未确认")
            for phase in ("2", "5"):
                status = self._status(phase)
                if status not in {"已确认", "已完成"}:
                    self.issue("ERROR", "E007", phase, "编码已许可，但该阶段状态为 %r（需已确认/已完成）" % status,
                               "先完成该阶段的用户确认并写入 state JSON")
            upstream = ["0", "1a", "1b", "3"]
            if LEGACY_PHASE_GROUP in phases:
                upstream.append(LEGACY_PHASE_GROUP)
            else:
                upstream.extend(["4a", "4b"])
            for phase in upstream:
                status = self._status(phase)
                if status not in {"已确认", "已完成", "已跳过", "不适用"}:
                    hint = "先完成、确认或显式跳过该阶段"
                    if phase == "4b":
                        hint = "测试用例未就绪；先按 P5 契约生成 4b 用例，或标“不适用”"
                    self.issue("ERROR", "E009", phase, "编码已开始/已许可，但该阶段状态为 %r" % status, hint)
            self._check_version_alignment()
        else:
            for phase in CODING_PHASES:
                status = self._status(phase)
                if status in {"进行中", "已完成"}:
                    self.issue("ERROR", "E008", phase, "未授予编码许可，但该阶段已 %r" % status,
                               "先完成 PRD + 开发设计确认，再设 coding_allowed=true")

    def _validate_risk_gates(self) -> None:
        if self.mode != "json":
            return
        risk = self.state.get("risk")
        if not isinstance(risk, dict):
            return
        phases = self.state.get("phases", {})
        phase5 = phases.get("5") if isinstance(phases, dict) else None
        if not isinstance(phase5, dict) or phase5.get("status") not in {"已确认", "已完成"}:
            return
        level = risk.get("level")
        strict = (
            level == "high"
            or bool(risk.get("data_change"))
            or bool(risk.get("breaking_change"))
            or bool(risk.get("security_sensitive"))
        )
        medium = level == "medium"
        if not strict and not medium:
            return
        path = self.dir / "P5-开发设计.md"
        if not path.exists():
            for name in extract_files(phase5.get("artifact", "")):
                candidate = Path(name) if Path(name).is_absolute() else self.dir / name
                if candidate.exists():
                    path = candidate
                    break
        if not path.exists():
            return
        try:
            text = path.read_text(encoding="utf-8").lower()
        except OSError:
            return
        groups = {
            "NFR（延迟/吞吐/容量）": ("nfr", "延迟", "吞吐", "容量"),
            "失败模式/可用性": ("失败模式", "可用性", "降级"),
            "可观测性（日志/指标/告警/runbook）": ("可观测性", "监控", "指标", "告警", "runbook", "日志"),
            "安全/隐私（鉴权/越权/PII/审计）": ("安全", "鉴权", "越权", "pii", "审计", "权限"),
        }
        if risk.get("data_change") or risk.get("breaking_change"):
            groups["发布与回滚"] = ("发布与回滚", "回滚", "灰度")
        missing = [name for name, keys in groups.items() if not any(key in text for key in keys)]
        if not missing:
            return
        if strict:
            self.issue("ERROR", "E028", "5",
                       "高风险变更的 P5 缺：%s" % "、".join(missing),
                       "在 P5 补 NFR/失败模式/可观测性/安全（及发布回滚）后再确认")
        else:
            self.issue("WARN", "W024", "5",
                       "中风险变更的 P5 缺：%s" % "、".join(missing),
                       "建议补齐；高风险时会升级为 ERROR")

    def _check_version_alignment(self) -> None:
        phases = self.state.get("phases", {})
        for phase, key in (("2", "prd_version"), ("5", "design_version")):
            declared = normalize_version(self.state.get(key))
            current = normalize_version(phases.get(phase, {}).get("version"))
            if declared and current and declared != current:
                self.issue("ERROR", "E016" if phase == "2" else "E017", phase,
                           "%s=%s 与阶段版本 v%s 不一致" % (key, declared, current),
                           "确认后再更新 state 版本号")
            if declared and not current:
                self.issue("WARN", "W013", phase, "state 有 %s，但阶段未记录 version" % key)

    def _validate_skips(self) -> None:
        phases = self.state.get("phases", {})
        for entry in self.state.get("skipped", []) or []:
            if not isinstance(entry, dict):
                self.issue("ERROR", "E010", "-", "skipped 条目必须是对象")
                continue
            phase = canonical_phase(entry.get("phase"))
            if phase is None:
                self.issue("ERROR", "E020", "-", "skipped 条目阶段无法识别：%r" % entry.get("phase"))
                continue
            missing = [
                key for key in ("approved_by", "approved_at", "reason") if not clean_text(entry.get(key))
            ]
            if missing:
                self.issue("ERROR", "E010", phase, "跳过记录缺 %s" % " / ".join(missing),
                           "补 approved_by / approved_at / reason")
            status = phases.get(phase, {}).get("status")
            if status not in {"已跳过", "不适用"}:
                self.issue("ERROR", "E011", phase,
                           "skipped 有记录，但阶段状态是 %r（应为已跳过/不适用）" % status,
                           "把阶段状态改为已跳过，或删除该 skipped 记录")

    def _validate_artifacts(self) -> None:
        phases = self.state.get("phases", {})
        for phase, data in phases.items():
            if not isinstance(data, dict):
                continue
            status = data.get("status")
            artifact = data.get("artifact")
            if status not in {"进行中", "已确认", "已完成"} or not artifact:
                continue
            files = extract_files(artifact)
            if not files:
                if phase not in CODING_PHASES and status in {"已确认", "已完成"}:
                    self.issue("WARN", "W014", phase, "无法从产物字段解析文件名：%r" % artifact)
                continue
            for name in files:
                path = Path(name)
                if not path.is_absolute():
                    path = self.dir / name
                if not path.exists():
                    self.issue("ERROR", "E012", phase, "产物不存在：%s" % path,
                               "确认产物已落盘，或修正 artifact 字段")
        phase8 = phases.get("8", {}) if isinstance(phases, dict) else {}
        p8_file = self.dir / "P8-验收记录.md"
        if p8_file.exists() and "P8-验收记录.md" not in str(phase8.get("artifact", "")):
            if phase8.get("status") in {"进行中", "待确认", "已确认", "已完成"}:
                self.issue("WARN", "W009", "8", "Phase 8 产物未指向 P8-验收记录.md（文件已存在）")

    def _artifact_status_header(self, phase: str) -> Optional[Tuple[Path, int, str]]:
        phases = self.state.get("phases", {})
        data = phases.get(phase) if isinstance(phases, dict) else None
        if not isinstance(data, dict):
            return None
        names = {
            "2": "P1-PRD.md",
            "5": "P5-开发设计.md",
            "8": "P8-验收记录.md",
        }
        candidates: List[Path] = []
        if phase in names:
            candidates.append(self.dir / names[phase])
        for name in extract_files(data.get("artifact", "")):
            candidates.append(Path(name) if Path(name).is_absolute() else self.dir / name)
        seen: Set[str] = set()
        for path in candidates:
            key = str(path)
            if key in seen or not path.exists() or path.suffix.lower() != ".md":
                continue
            seen.add(key)
            try:
                lines = path.read_text(encoding="utf-8").splitlines()[:40]
            except OSError:
                continue
            for index, line in enumerate(lines, 1):
                if re.search(r"状态\s*[：:]", line):
                    return path, index, clean_text(line)
        return None

    def _validate_artifact_headers(self) -> None:
        """产物头部「状态」与 state JSON 的明显矛盾。

        不追求精确语义：只抓“state 待确认，产物写已实施/已完成”这类硬矛盾；
        以及 state 已确认，产物还写待确认/草稿 的陈旧头。
        """
        positive_words = ("已确认", "已实施", "已完成", "已交付", "验收通过")
        confirm_pending = ("待确认", "待用户确认", "待客户确认", "草稿")
        env_pending = ("待环境", "未完成")
        phases = self.state.get("phases", {})
        if not isinstance(phases, dict):
            return
        for phase in ("2", "5", "8"):
            data = phases.get(phase)
            if not isinstance(data, dict):
                continue
            status = data.get("status")
            if status in {"未开始", "已跳过", "不适用"}:
                continue
            header = self._artifact_status_header(phase)
            if header is None:
                continue
            path, line_no, text = header
            positive = any(word in text for word in positive_words)
            pending = any(word in text for word in confirm_pending)
            if phase == "8":
                pending = pending or any(word in text for word in env_pending)
            critical = False
            stale = False
            if status == "待确认" and positive and not pending:
                critical = True
            elif status in {"已确认", "已完成"} and pending and not positive:
                stale = True
            elif status == "进行中" and positive and not pending:
                critical = True
            elif phase == "8" and status == "已完成" and pending and not positive:
                stale = True
            if critical:
                level = "ERROR" if self.mode == "json" else "WARN"
                code = "E026" if self.mode == "json" else "W022"
                self.issue(level, code, phase,
                           "产物头部状态与 state JSON 矛盾：%s:%d 写 %r，state=%r"
                           % (path.name, line_no, text[:60], status),
                           "以 state JSON 为准修正产物头部状态，或回退 state")
            elif stale:
                self.issue("WARN", "W022", phase,
                           "产物头部状态陈旧：%s:%d 写 %r，state=%r"
                           % (path.name, line_no, text[:60], status),
                           "同步产物头部状态，避免读者误判")

    def _validate_decision_brief(self) -> None:
        path = self.dir / "_决策简报.md"
        if not path.exists():
            return
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return
        required = {
            "问题": "要解决的问题",
            "选项": "选项与推荐",
            "需要拍板": "需要用户拍板的事项",
            "决策历史": "append-only 决策历史",
        }
        missing = [label for marker, label in required.items() if marker not in text]
        if "需要你拍板" in text and "需要拍板" in missing:
            missing.remove("需要拍板")
        if missing:
            self.issue("WARN", "W026", "-",
                       "决策简报缺：%s" % "、".join(missing),
                       "决策简报应含问题/选项/需要拍板/决策历史；交付总结另写 _交付摘要.md")

    def _p8_path(self) -> Optional[Path]:
        path = self.dir / "P8-验收记录.md"
        if path.exists():
            return path
        phases = self.state.get("phases", {})
        data = phases.get("8") if isinstance(phases, dict) else None
        if isinstance(data, dict):
            for name in extract_files(data.get("artifact", "")):
                candidate = Path(name) if Path(name).is_absolute() else self.dir / name
                if candidate.exists():
                    return candidate
        return None

    def _validate_p8_quality(self) -> None:
        if self.mode != "json":
            return
        phases = self.state.get("phases", {})
        phase8 = phases.get("8") if isinstance(phases, dict) else None
        if not isinstance(phase8, dict) or phase8.get("status") != "已完成":
            return
        risk = self.state.get("risk")
        if not isinstance(risk, dict) or risk.get("level") not in {"medium", "high"}:
            return
        path = self._p8_path()
        if path is None:
            return
        try:
            text = path.read_text(encoding="utf-8").lower()
        except OSError:
            return
        if "nfr" not in text and "not-verified" not in text and "未验证" not in text:
            self.issue("WARN", "W025", "8",
                       "中高风险需求 P8 缺 NFR 验收项或 not-verified 说明",
                       "补 NFR 验收表（目标/测量/结果），未测量项标 not-verified")
        if not any(word in text for word in ("探针", "head", "liveness", "readiness")):
            self.issue("WARN", "W027", "8",
                       "P8 缺联调前置：探针 method/HEAD/liveness/readiness",
                       "补探针语义与部署拓扑（是否反代、XFF、仅 localhost）")

    def _file_to_phase(self) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for phase, data in self.state.get("phases", {}).items():
            if not isinstance(data, dict):
                continue
            for name in extract_files(data.get("artifact", "")):
                if name not in mapping or phase_number(phase) > phase_number(mapping[name]):
                    mapping[name] = phase
        return mapping

    def _phase_version(self, phase: str) -> Optional[str]:
        data = self.state.get("phases", {}).get(phase, {})
        if not isinstance(data, dict):
            return None
        return normalize_version(data.get("version")) or normalize_version(data.get("_raw_status"))

    def _validate_inputs(self) -> None:
        mapping = self._file_to_phase()
        missing: List[str] = []
        for md in sorted(self.dir.glob("*.md")):
            if md.name in {"_状态.md", "_日志.md"}:
                continue
            try:
                lines = md.read_text(encoding="utf-8").splitlines()[:60]
            except OSError:
                continue
            line = next((l for l in lines if "输入来源" in l), None)
            if line is None:
                line = next((l for l in lines if re.search(r"输入[：:]", l)), None)
                if line is not None:
                    self.issue("WARN", "W003", self._phase_of_file(md.name, mapping),
                               "%s 使用“输入：”而非“输入来源”字段" % md.name)
            if line is None:
                missing.append(md.name)
                continue
            current = self._phase_of_file(md.name, mapping)
            if current is None:
                continue
            for name in extract_files(line):
                target = mapping.get(name)
                if target is None:
                    continue
                if current in {"4a", "4b"} and target == "5":
                    continue  # 4b 用例需要 P5 契约，文件级引用不算下游
                if phase_number(current) < phase_number(target):
                    self.issue("WARN", "W004", current,
                               "%s 引用了下游产物 %s（阶段 %s）" % (md.name, name, target))
                ref_version = version_after(line, name)
                target_version = self._phase_version(target)
                if ref_version and target_version and version_less(ref_version, target_version):
                    self.issue("WARN", "W005", current,
                               "%s 引用 %s v%s，当前为 v%s" % (md.name, name, ref_version, target_version))
        if missing:
            self.issue("WARN", "W003", "-", "%d 个产物缺少「输入来源」：%s" % (len(missing), ", ".join(missing)),
                       "按 artifacts.md 交接协议补一行相对路径 + 版本")

    def _phase_of_file(self, filename: str, mapping: Dict[str, str]) -> Optional[str]:
        if filename in mapping:
            return mapping[filename]
        for name, phase in mapping.items():
            if Path(name).name == filename:
                return phase
        return None

    def _validate_env(self) -> None:
        phases = self.state.get("phases", {})
        pending = self.state.get("pending_env") or []
        phase8 = phases.get("8", {}) if isinstance(phases, dict) else {}
        candidates = [self.dir / "P8-验收记录.md"]
        for name in extract_files(phase8.get("artifact", "")):
            candidates.append(Path(name) if Path(name).is_absolute() else self.dir / name)
        p8_path = next((p for p in candidates if p.exists()), candidates[0])
        positive_claim = False
        p8_text = ""
        if p8_path.exists():
            try:
                p8_text = p8_path.read_text(encoding="utf-8")
            except OSError:
                p8_text = ""
            for line in p8_text.splitlines():
                if "验收通过" in line and not any(
                    word in line for word in ("不得", "禁止", "不能", "未", "待环境", "不可")
                ):
                    positive_claim = True
                    break
        if pending and phase8.get("status") == "已完成":
            self.issue("ERROR", "E013", "8", "pending_env 非空，但 Phase 8 标为已完成",
                       "把 Phase 8 改为待确认/待环境，或清空 pending_env")
        if positive_claim and (pending or phase8.get("status") not in {"已完成", "不适用"}):
            self.issue("ERROR", "E013", "8", "P8 宣称“验收通过”，但仍有待环境/未完成项",
                       "去掉通过结论，或补齐验证并回填")
        if self.state.get("_pending_env_flag") and not pending:
            self.issue("WARN", "W008", "8", "Phase 8 标“待环境”，但 pending_env 为空",
                       "列出待环境项（用例号/负责人/恢复后动作）")
        notes = clean_text(phase8.get("notes", "")) if isinstance(phase8, dict) else ""
        if phase8.get("status") == "已完成" and notes and ("待" in notes or "未完成" in notes):
            self.issue("WARN", "W008", "8", "Phase 8 已标完成，但备注仍有待办：%s" % notes[:60],
                       "把待办项列入 pending_env，或改回待确认")

        if phase8.get("status") == "已完成":
            conclusion = next(
                (line for line in p8_text.splitlines() if re.search(r"退出结论\s*[：:]", line)), ""
            )
            bugs = re.search(r"未关闭\s*P0/P1[^\d]*(\d+)", p8_text)
            bad_conclusion = any(word in conclusion for word in ("不通过", "待环境", "待确认"))
            conclusion_ok = "通过" in conclusion and not bad_conclusion
            bugs_ok = bool(bugs) and int(bugs.group(1)) == 0
            if not p8_text or not conclusion_ok or not bugs_ok:
                level = "ERROR" if self.mode == "json" else "WARN"
                code = "E022" if self.mode == "json" else "W016"
                reason = "缺 P8 文件" if not p8_text else "退出结论不是“通过”或未关闭 P0/P1 Bug 不为 0"
                self.issue(level, code, "8", "Phase 8 已完成，但%s" % reason,
                           "补「退出结论：通过」与「未关闭 P0/P1 Bug：0」，或改回待确认")

    def _validate_json_table(self) -> None:
        if not self.table_rows:
            self.issue("WARN", "W010", "-", "state JSON 存在，但缺少人工阅读的阶段表",
                       "按 artifacts.md 模板补表格（与 JSON 一致）")
            return
        phases = self.state.get("phases", {})
        for row in self.table_rows:
            phase = canonical_phase(self._row_value(row, ["phase", "阶段"]))
            if phase is None:
                continue
            raw_status = self._row_value(row, ["状态"])
            status, _ = normalize_status(raw_status)
            if phase not in phases:
                self.issue("ERROR", "E015", phase, "表格有阶段 %s，但 state JSON 没有" % phase)
                continue
            json_status = phases[phase].get("status")
            if status != json_status:
                self.issue("ERROR", "E015", phase,
                           "表格状态 %r 与 JSON %r 不一致" % (clean_text(raw_status), json_status),
                           "以 JSON 为准修正表格")


# ---------- CLI ----------

def find_demands(target: Path) -> List[Path]:
    if target.is_file():
        return [target.parent] if target.name == "_状态.md" else []
    if (target / "_状态.md").exists():
        return [target]
    for candidate in (target / "docs" / "ai-coding", target if target.name == "ai-coding" else None):
        if candidate is not None and candidate.is_dir():
            return sorted(
                p for p in candidate.iterdir() if p.is_dir() and (p / "_状态.md").exists()
            )
    return sorted(p.parent for p in target.glob("*/_状态.md"))


def print_result(result: Result, quiet: bool = False) -> None:
    print("req2code check · %s" % result.directory)
    print("state: %s | gate: %s (%d errors, %d warnings) | coding: %s | acceptance: %s"
          % (result.mode, result.gate, len(result.errors), len(result.warnings), result.coding, result.acceptance))
    for issue in result.issues:
        if quiet and issue.level != "ERROR":
            continue
        print("  %-5s %s [%s] %s" % (issue.level, issue.code, issue.phase, issue.message))
        if issue.hint:
            print("        fix: %s" % issue.hint)
    if not result.issues:
        print("  OK")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="校验 req2code 需求目录的 _状态.md 与门禁一致性",
    )
    parser.add_argument("target", nargs="?", default=".", help="需求目录、_状态.md 或仓库根")
    parser.add_argument("--scan", action="store_true", help="扫描 docs/ai-coding 下的全部需求")
    parser.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")
    parser.add_argument("--strict", action="store_true", help="把 WARN 也视为失败")
    parser.add_argument("--quiet", action="store_true", help="只显示 ERROR")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    target = Path(args.target).expanduser()
    if not target.exists():
        print("路径不存在：%s" % target, file=sys.stderr)
        return 2

    if args.scan:
        demands = find_demands(target)
    else:
        demands = [target if target.is_dir() else target.parent]
        if target.is_dir() and not (target / "_状态.md").exists():
            found = find_demands(target)
            if found:
                demands = found
            else:
                print("未找到 _状态.md：%s" % target, file=sys.stderr)
                return 2

    results = [Checker(d).run() for d in demands]
    if args.strict:
        for result in results:
            for warning in list(result.warnings):
                warning.level = "ERROR"
            if result.errors:
                result.gate = "FAIL"

    if args.as_json:
        payload = [r.to_dict() for r in results]
        print(json.dumps(payload if args.scan else payload[0], ensure_ascii=False, indent=2))
    else:
        for index, result in enumerate(results):
            if index:
                print()
            print_result(result, quiet=args.quiet)
        if len(results) > 1:
            failed = sum(1 for r in results if r.errors)
            print("\nsummary: %d 个需求，%d 个未通过" % (len(results), failed))

    return 1 if any(r.errors for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
