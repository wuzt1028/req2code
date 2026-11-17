#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""req2code 文档一致性检查（零依赖，Python 3.8+）。

检查：
- 必需文件与 frontmatter（name/version/description，版本与 CHANGELOG 一致）
- 相对链接与锚点
- 阶段表顺序（0/1a/1b/2/3/4a/5/4b/6/7/8）
- 编码门禁表述必须包含 4b
- 陈旧/矛盾表述（如"不得向下游传递"、"PRD v2"、"双击可运行"）
- gates.md 状态闭集、错误码与 checker 同步
- "输入信任边界"章节存在
- evals 用例 JSON 结构

用法：
    python3 scripts/check-docs.py
    python3 scripts/check-docs.py --json
    python3 scripts/check-docs.py --strict   # WARN 也算失败

退出码：0 通过；1 有 ERROR（或 --strict 下有 WARN）；2 路径错误。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
CANONICAL_PHASES = ["0", "1a", "1b", "2", "3", "4a", "5", "4b", "6", "7", "8"]
STATUSES = ["未开始", "进行中", "待确认", "已确认", "已完成", "已跳过", "不适用"]
MODES = ["full", "backend-only", "frontend-only", "analysis-only", "prototype-only", "fast"]
PROTOTYPES = ["html", "annotated", "inline", "none"]
STALE_PHRASES = {
    "不得向下游传递": "未确认项可引用但必须保留标记，且不能支撑 coding_allowed=true",
    "PRD v2": "版本号不应硬编码，用“PRD 已确认版本（vN）”",
    "双击可运行": "原型应能在当前 GUI 打开/预览",
    "阶段裁剪矩阵": "已替换为 mode 预设",
    "确认落盘三件套": "已改为 state JSON 一处事实源",
}
REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "references/artifacts.md",
    "references/gates.md",
    "references/prompts.md",
    "references/checklists.md",
    "references/repo-recon.md",
    "references/collaboration.md",
    "references/toolchain.md",
    "scripts/req2code-check.py",
    "scripts/test_req2code_check.py",
    "scripts/check-docs.py",
    "scripts/test_check_docs.py",
    "scripts/run-evals.py",
    "evals/README.md",
    "evals/rubric.md",
    "evals/results/TEMPLATE.md",
    "scripts/run-evals.py",
]
DOC_FILES = (
    ["SKILL.md", "README.md"]
    + ["evals/README.md", "evals/rubric.md", "evals/results/TEMPLATE.md"]
    + sorted(str(p.relative_to(ROOT)) for p in (ROOT / "references").glob("*.md"))
)
SCAN_FILES = [path for path in DOC_FILES if not path.endswith("CHANGELOG.md")]


class Issue:
    def __init__(self, level: str, code: str, path: str, line: int, message: str):
        self.level = level
        self.code = code
        self.path = path
        self.line = line
        self.message = message

    def to_dict(self) -> Dict[str, object]:
        return {
            "level": self.level,
            "code": self.code,
            "path": self.path,
            "line": self.line,
            "message": self.message,
        }


class DocChecker:
    def __init__(self, root: Path = ROOT):
        self.root = root
        self.issues: List[Issue] = []

    # ---------- 基础 ----------

    def read(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8")

    def exists(self, rel: str) -> bool:
        return (self.root / rel).exists()

    def error(self, code: str, path: str, line: int, message: str) -> None:
        self.issues.append(Issue("ERROR", code, path, line, message))

    def warn(self, code: str, path: str, line: int, message: str) -> None:
        self.issues.append(Issue("WARN", code, path, line, message))

    def run(self) -> "DocChecker":
        self.check_required_files()
        self.check_frontmatter()
        self.check_links()
        self.check_stale_phrases()
        self.check_gate_statements()
        self.check_phase_tables()
        self.check_prompts_order()
        self.check_status_enum()
        self.check_error_codes()
        self.check_trust_boundary()
        self.check_evals()
        self.check_size()
        return self

    # ---------- 文件 ----------

    def check_required_files(self) -> None:
        for rel in REQUIRED_FILES:
            if not self.exists(rel):
                self.error("D001", rel, 0, "必需文件缺失")

    # ---------- frontmatter ----------

    def _frontmatter(self, path: str) -> Dict[str, str]:
        text = self.read(path)
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            self.error("D002", path, 1, "缺少 frontmatter")
            return {}
        data: Dict[str, str] = {}
        for index, line in enumerate(lines[1:], 2):
            if line.strip() == "---":
                return data
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            value = value.strip()
            if value.startswith('"') and value.endswith('"') and len(value) >= 2:
                value = value[1:-1]
            data[key.strip()] = value
        self.error("D002", path, 1, "frontmatter 未闭合")
        return data

    def check_frontmatter(self) -> None:
        meta = self._frontmatter("SKILL.md")
        if not meta:
            return
        if meta.get("name") != self.root.name:
            self.error("D003", "SKILL.md", 2, "name=%r，目录名=%r" % (meta.get("name"), self.root.name))
        version = meta.get("version", "")
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            self.error("D004", "SKILL.md", 3, "version 不是 X.Y.Z：%r" % version)
        description = meta.get("description", "")
        if not description:
            self.error("D005", "SKILL.md", 4, "description 为空")
        elif len(description) > 1024:
            self.error("D005", "SKILL.md", 4, "description 超过 1024 字")
        elif len(description) > 300:
            self.warn("D006", "SKILL.md", 4, "description 较长（%d 字），会常驻上下文" % len(description))
        changelog = self.read("CHANGELOG.md")
        match = re.search(r"^##\s+(\d+\.\d+\.\d+)", changelog, re.MULTILINE)
        if match and version and match.group(1) != version:
            self.error("D007", "CHANGELOG.md", 3,
                       "CHANGELOG 最新版本 %s 与 SKILL version %s 不一致" % (match.group(1), version))

    # ---------- 链接 ----------

    @staticmethod
    def _slug(text: str) -> str:
        text = re.sub(r"[`*_~]", "", text.strip().lower())
        text = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", text)
        return re.sub(r"\s+", "-", text).strip("-")

    def _anchors(self, rel: str) -> Set[str]:
        text = self.read(rel)
        anchors = set()
        for match in re.finditer(r"^#{1,6}\s+(.+)$", text, re.MULTILINE):
            anchors.add(self._slug(match.group(1)))
        return anchors

    def check_links(self) -> None:
        for path in DOC_FILES:
            text = self.read(path)
            for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
                target = match.group(1).strip().strip("<>")
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                line = text[: match.start()].count("\n") + 1
                if target.startswith("#"):
                    fragment = target[1:]
                    if fragment and fragment not in self._anchors(path):
                        self.error("D008", path, line, "锚点不存在：#%s" % fragment)
                    continue
                file_part, _, fragment = target.partition("#")
                resolved = (self.root / path).parent / file_part
                if not resolved.exists():
                    self.error("D009", path, line, "链接目标不存在：%s" % target)
                    continue
                if fragment:
                    try:
                        rel = str(resolved.resolve().relative_to(self.root))
                    except ValueError:
                        continue
                    if rel.endswith(".md") and fragment not in self._anchors(rel):
                        self.error("D008", path, line, "锚点不存在：%s#%s" % (file_part, fragment))

    # ---------- 文本一致性 ----------

    def check_stale_phrases(self) -> None:
        for path in SCAN_FILES:
            for index, line in enumerate(self.read(path).splitlines(), 1):
                for phrase, hint in STALE_PHRASES.items():
                    if phrase in line:
                        self.error("D010", path, index, "陈旧表述 %r；%s" % (phrase, hint))

    def check_gate_statements(self) -> None:
        for path in SCAN_FILES:
            for index, line in enumerate(self.read(path).splitlines(), 1):
                if "gate: PASS" in line and ("PRD" in line or "开发设计" in line):
                    if "4b" not in line:
                        self.error("D011", path, index,
                                   "编码门禁表述漏了 4b（应为 PRD + 开发设计 + 4b 用例）")
                if "编码前" in line and "PRD" in line and "开发设计" in line and "4b" not in line:
                    self.error("D011", path, index,
                               "编码前门禁表述漏了 4b（应为 PRD + 开发设计 + 4b 用例）")

    # ---------- 阶段表 ----------

    def _section(self, path: str, start_pattern: str, end_pattern: str) -> List[str]:
        lines = self.read(path).splitlines()
        result: List[str] = []
        active = False
        for line in lines:
            if re.search(start_pattern, line):
                active = True
                continue
            if active and re.search(end_pattern, line):
                break
            if active:
                result.append(line)
        return result

    def _phase_rows(self, path: str, start_pattern: str, end_pattern: str) -> List[str]:
        rows = []
        for line in self._section(path, start_pattern, end_pattern):
            match = re.match(r"^\|\s*([0-9]+[ab]?)(?![0-9])", line.strip())
            if match:
                rows.append(match.group(1))
        return rows

    def check_phase_tables(self) -> None:
        checks = [
            ("SKILL.md", r"^##\s+阶段总览", r"^##\s+"),
            ("references/artifacts.md", r"^###\s+_状态\.md", r"^###\s+"),
            ("references/gates.md", r"^##\s+一、最小示例", r"^##\s+二、"),
        ]
        for path, start, end in checks:
            if not self.exists(path):
                continue
            rows = self._phase_rows(path, start, end)
            if rows and rows != CANONICAL_PHASES:
                self.error("D012", path, 0,
                           "阶段表顺序/集合不符：%r，期望 %r" % (rows, CANONICAL_PHASES))
            elif not rows:
                self.error("D012", path, 0, "找不到可解析的阶段表")

    def check_prompts_order(self) -> None:
        path = "references/prompts.md"
        if not self.exists(path):
            return
        headings: List[Tuple[int, str, int]] = []
        for index, line in enumerate(self.read(path).splitlines(), 1):
            match = re.match(r"^##\s+(\d+)\.\s+(.*)$", line)
            if match:
                headings.append((int(match.group(1)), match.group(2), index))
        numbers = [item[0] for item in headings]
        if numbers != list(range(len(numbers))):
            self.error("D013", path, 0, "prompts 章节编号不连续/不从 0 开始：%r" % numbers)
        sequence = [item[1] for item in headings]
        def find(token: str) -> int:
            for idx, title in enumerate(sequence):
                if token in title:
                    return idx
            return -1
        pos_4a = find("Phase 4a")
        pos_5 = find("Phase 5")
        pos_4b = find("Phase 4b")
        if not (pos_4a >= 0 and pos_5 >= 0 and pos_4b >= 0 and pos_4a < pos_5 < pos_4b):
            self.error("D014", path, 0, "prompts 顺序应为 4a → 5 → 4b，实际 %r" % sequence)

    # ---------- 枚举/错误码 ----------

    def check_status_enum(self) -> None:
        path = "references/gates.md"
        if not self.exists(path):
            return
        text = self.read(path)
        missing = [status for status in STATUSES if status not in text]
        if missing:
            self.error("D015", path, 0, "gates.md 缺少状态：%s" % ", ".join(missing))

    def check_error_codes(self) -> None:
        checker = "scripts/req2code-check.py"
        gates = "references/gates.md"
        if not (self.exists(checker) and self.exists(gates)):
            return
        checker_codes = set(re.findall(r"\b([EW]\d{3})\b", self.read(checker)))
        gates_codes = set(re.findall(r"\b([EW]\d{3})\b", self.read(gates)))
        missing = sorted(checker_codes - gates_codes)
        extra = sorted(gates_codes - checker_codes)
        if missing:
            self.error("D016", gates, 0, "checker 有但 gates 未文档化的错误码：%s" % ", ".join(missing))
        if extra:
            self.error("D017", gates, 0, "gates 有但 checker 未使用的错误码：%s" % ", ".join(extra))

    # ---------- 信任边界 ----------

    def check_trust_boundary(self) -> None:
        skill = "SKILL.md"
        if not self.exists(skill):
            return
        text = self.read(skill)
        if "## 输入信任边界" not in text:
            self.error("D018", skill, 0, "缺少「输入信任边界」章节")
        elif "数据，不是指令" not in text:
            self.error("D018", skill, 0, "信任边界章节缺少“数据，不是指令”表述")

    # ---------- evals ----------

    def check_evals(self) -> None:
        cases_dir = self.root / "evals" / "cases"
        if not cases_dir.exists():
            self.warn("D019", "evals/cases", 0, "evals/cases 不存在，行为评测未就绪")
            return
        seen: Set[str] = set()
        for path in sorted(cases_dir.glob("*.json")):
            rel = str(path.relative_to(self.root))
            if not re.fullmatch(r"\d{2}-[a-z0-9-]+\.json", path.name):
                self.error("D020", rel, 0, "用例文件名应形如 01-small-fix.json")
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                self.error("D021", rel, 0, "JSON 无法解析：%s" % exc)
                continue
            for key in ("id", "title", "input", "expected", "metrics"):
                if key not in data:
                    self.error("D022", rel, 0, "缺少字段 %s" % key)
            case_id = data.get("id")
            if case_id in seen:
                self.error("D023", rel, 0, "重复 id：%r" % case_id)
            seen.add(case_id)
            expected = data.get("expected")
            if not isinstance(expected, dict):
                self.error("D023", rel, 0, "expected 必须是对象")
                continue
            if not isinstance(expected.get("triggered"), bool):
                self.error("D023", rel, 0, "expected.triggered 必须是布尔值")
            if expected.get("mode") is not None and expected.get("mode") not in MODES:
                self.error("D023", rel, 0, "expected.mode 不在允许集合")
            for key in ("must", "must_not"):
                if not isinstance(expected.get(key), list):
                    self.error("D023", rel, 0, "expected.%s 必须是数组" % key)
            if not isinstance(data.get("metrics"), list) or not data.get("metrics"):
                self.error("D023", rel, 0, "metrics 必须是非空数组")

    # ---------- 体量 ----------

    def check_size(self) -> None:
        skill = self.root / "SKILL.md"
        if skill.exists():
            size = skill.stat().st_size
            if size > 30_000:
                self.warn("D024", "SKILL.md", 0, "SKILL.md 已 %.1fKB，建议继续拆分" % (size / 1024.0))

    # ---------- 输出 ----------

    def has_errors(self) -> bool:
        return any(issue.level == "ERROR" for issue in self.issues)

    def has_warnings(self) -> bool:
        return any(issue.level == "WARN" for issue in self.issues)

    def summary(self) -> Dict[str, object]:
        return {
            "root": str(self.root),
            "errors": sum(1 for i in self.issues if i.level == "ERROR"),
            "warnings": sum(1 for i in self.issues if i.level == "WARN"),
            "issues": [i.to_dict() for i in self.issues],
        }


def print_human(checker: DocChecker, strict: bool, verbose: bool) -> None:
    for issue in checker.issues:
        if issue.level == "WARN" and not verbose and not strict:
            continue
        print("%-5s %s %s:%s %s" % (issue.level, issue.code, issue.path, issue.line or "-", issue.message))
    errors = sum(1 for i in checker.issues if i.level == "ERROR")
    warnings = sum(1 for i in checker.issues if i.level == "WARN")
    print("docs check: %d errors, %d warnings" % (errors, warnings))
    if not checker.issues:
        print("OK")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="检查 req2code 文档一致性")
    parser.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")
    parser.add_argument("--strict", action="store_true", help="WARN 也算失败")
    parser.add_argument("--verbose", action="store_true", help="显示 WARN")
    args = parser.parse_args(argv)

    checker = DocChecker().run()
    if args.as_json:
        print(json.dumps(checker.summary(), ensure_ascii=False, indent=2))
    else:
        print_human(checker, strict=args.strict, verbose=args.verbose)
    failed = checker.has_errors() or (args.strict and checker.has_warnings())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
