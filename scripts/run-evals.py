#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""req2code 行为评测骨架（零依赖，Python 3.8+）。

本脚本不调用模型：
- `--validate` 校验 evals/cases/*.json 结构；
- `--list` 列出用例；
- `--template <id>` 输出可填写的结果模板。

真正的执行由人或 agent 按 evals/README.md 的协议跑，结果写入 evals/results/。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "evals" / "cases"
MODES = {"full", "backend-only", "frontend-only", "analysis-only", "prototype-only", "fast", None}
REQUIRED = ("id", "title", "input", "expected", "metrics")


def load_cases() -> List[Dict[str, object]]:
    cases: List[Dict[str, object]] = []
    for path in sorted(CASES.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("%s: JSON 无法解析：%s" % (path.name, exc))
        data["_path"] = str(path.relative_to(ROOT))
        cases.append(data)
    return cases


def validate(cases: List[Dict[str, object]]) -> List[str]:
    errors: List[str] = []
    seen = set()
    for case in cases:
        path = str(case.get("_path", "?"))
        for key in REQUIRED:
            if key not in case:
                errors.append("%s: 缺少字段 %s" % (path, key))
        if not isinstance(case.get("id"), str) or not case.get("id"):
            errors.append("%s: id 必须是非空字符串" % path)
        if case.get("id") in seen:
            errors.append("%s: 重复 id %r" % (path, case.get("id")))
        seen.add(case.get("id"))
        expected = case.get("expected")
        if not isinstance(expected, dict):
            errors.append("%s: expected 必须是对象" % path)
            continue
        if not isinstance(expected.get("triggered"), bool):
            errors.append("%s: expected.triggered 必须是布尔值" % path)
        if expected.get("mode") not in MODES:
            errors.append("%s: expected.mode 非法：%r" % (path, expected.get("mode")))
        for key in ("must", "must_not"):
            if not isinstance(expected.get(key), list):
                errors.append("%s: expected.%s 必须是数组" % (path, key))
        metrics = case.get("metrics")
        if not isinstance(metrics, list) or not metrics:
            errors.append("%s: metrics 必须是非空数组" % path)
        if not isinstance(case.get("input"), str) or not case.get("input"):
            errors.append("%s: input 必须是非空字符串" % path)
    return errors


def print_case(case: Dict[str, object]) -> None:
    expected = case.get("expected", {})
    if not isinstance(expected, dict):
        expected = {}
    print("%s  %s" % (case.get("id"), case.get("title")))
    print("  triggered=%r mode=%r gate=%r"
          % (expected.get("triggered"), expected.get("mode"), expected.get("gate")))
    print("  must: %s" % "; ".join(str(x) for x in expected.get("must", []) or []))
    print("  must_not: %s" % "; ".join(str(x) for x in expected.get("must_not", []) or []))
    print("  metrics: %s" % ", ".join(str(x) for x in case.get("metrics", []) or []))


def template(case: Dict[str, object]) -> str:
    expected = case.get("expected", {})
    if not isinstance(expected, dict):
        expected = {}
    lines = [
        "# Eval：%s — %s" % (case.get("id"), case.get("title")),
        "",
        "- 模型/日期：",
        "- 会话/提交：",
        "- 是否在全新会话运行：",
        "",
        "## 输入",
        "",
        "```text",
        str(case.get("input", "")),
        "```",
        "",
        "## 期望",
        "",
        "- triggered：%r" % expected.get("triggered"),
        "- mode：%r" % expected.get("mode"),
        "- gate：%r" % expected.get("gate"),
        "",
        "**必须发生**",
        "",
    ]
    for item in expected.get("must", []) or []:
        lines.append("- [ ] %s" % item)
    lines += ["", "**禁止发生**", ""]
    for item in expected.get("must_not", []) or []:
        lines.append("- [ ] %s" % item)
    lines += [
        "",
        "## 实际轨迹",
        "",
        "（粘贴关键步骤/工具调用；不要粘贴敏感凭据或客户数据）",
        "",
        "## 评分",
        "",
        "| 维度 | 0/1/2 | 依据 |",
        "|---|---|---|",
        "| 触发 |  |  |",
        "| mode/范围 |  |  |",
        "| 阶段顺序 |  |  |",
        "| 门禁与证据 |  |  |",
        "| 产物质量 |  |  |",
        "| 信任边界/安全 |  |  |",
        "| 人工介入次数 |  |  |",
        "| 成本（tokens/工具调用） |  |  |",
        "",
        "## 违规与备注",
        "",
        "- 门禁违规：",
        "- 安全问题：",
        "- 可疑输入/非需求指令：",
        "- 改进建议：",
        "",
    ]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="req2code 行为评测骨架")
    parser.add_argument("--list", action="store_true", help="列出用例")
    parser.add_argument("--validate", action="store_true", help="校验用例结构")
    parser.add_argument("--template", metavar="ID", help="输出指定用例的结果模板")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON 输出")
    args = parser.parse_args(argv)

    try:
        cases = load_cases()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(cases, ensure_ascii=False, indent=2))
        return 0

    if args.template:
        for case in cases:
            if case.get("id") == args.template:
                print(template(case))
                return 0
        print("找不到用例：%s" % args.template, file=sys.stderr)
        return 2

    errors = validate(cases)
    if args.validate:
        if errors:
            for error in errors:
                print("ERROR %s" % error)
            print("evals: %d errors, %d cases" % (len(errors), len(cases)))
            return 1
        print("evals: OK (%d cases)" % len(cases))
        return 0

    for case in cases:
        print_case(case)
        print()
    print("evals: %d cases；用 --validate 校验结构，--template <id> 生成结果模板" % len(cases))
    return 0


if __name__ == "__main__":
    sys.exit(main())
