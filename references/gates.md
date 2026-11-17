# 状态机与门禁（req2code/state@1）

`_状态.md` 里有两个部分：

1. `<!-- req2code:state -->` 与 `<!-- /req2code:state -->` 之间的 JSON：**门禁唯一事实源**；
2. 下方阶段表：给人看的视图，**状态必须与 JSON 一致**。

门禁不再靠"模型记得确认过"：确认人、确认日期、编码许可、跳过审批、待环境项全部落成字段，由 `scripts/req2code-check.py` 校验。脚本不过，不得进入 Phase 6/7，也不得宣称验收通过。

---

## 一、最小示例

````markdown
# 流水线状态：{需求名}

<!-- req2code:state -->
```json
{
  "schema": "req2code/state@1",
  "demand": "{需求名}",
  "dir": "{产物目录绝对路径}",
  "updated_at": "{YYYY-MM-DD}",
  "mode": "full",
  "prototype": "html",
  "test_depth": "cases",
  "prd_version": "",
  "design_version": "",
  "coding_allowed": false,
  "coding_granted_by": "",
  "coding_granted_at": "",
  "phases": {
    "0":  {"status": "未开始", "artifact": "P0-输入与仓库侦察.md"},
    "1a": {"status": "未开始", "artifact": "P1-PRD.md#0", "approval_ref": ""},
    "1b": {"status": "未开始", "artifact": "P1-PRD.md"},
    "2":  {"status": "未开始", "artifact": "P1-PRD.md", "approval_ref": ""},
    "3":  {"status": "未开始", "artifact": "P3-设计说明.md", "approval_ref": ""},
    "4a": {"status": "未开始", "artifact": "P4-场景与测试Case.md#scenarios"},
    "5":  {"status": "未开始", "artifact": "P5-开发设计.md", "approval_ref": ""},
    "4b": {"status": "未开始", "artifact": "P4-场景与测试Case.md#cases"},
    "6":  {"status": "未开始", "verification": {"level": "", "evidence": ""}},
    "7":  {"status": "未开始", "verification": {"level": "", "evidence": ""}},
    "8":  {"status": "未开始", "artifact": "P8-验收记录.md"}
  },
  "skipped": [],
  "pending_env": []
}
```
<!-- /req2code:state -->

| 阶段 | 产物 | 状态 | 版本 | 确认人 | 日期 | 审批引用 | 门禁 |
|---|---|---|---|---|---|---|---|
| 0 输入与仓库侦察 | P0-输入与仓库侦察.md | 未开始 | | | | | |
| 1a 需求理解复述 | P1-PRD.md#0 | 未开始 | | | | | |
| 1b 需求分析 | P1-PRD.md | 未开始 | | | | | |
| 2 需求澄清 | P1-PRD.md | 未开始 | | | | | |
| 3 交互设计 | P3-设计说明.md | 未开始 | | | | | |
| 4a 场景清单 | P4-场景与测试Case.md#scenarios | 未开始 | | | | | |
| 5 开发设计 | P5-开发设计.md | 未开始 | | | | | |
| 4b 测试用例 | P4-场景与测试Case.md#cases | 未开始 | | | | | |
| 6 后端开发 | 代码改动 / P5 实施状态 | 未开始 | | | | | |
| 7 前端开发 | 代码改动 / P5 实施状态 | 未开始 | | | | | |
| 8 联调与验收 | P8-验收记录.md | 未开始 | | | | | |
````

---

## 二、允许值

### 阶段状态（闭集）

`未开始` / `进行中` / `待确认` / `已确认` / `已完成` / `已跳过` / `不适用`

- `待环境` 不是阶段状态：把 Phase 8 设为 `待确认`，并把待跑项写进 `pending_env`。
- `已跳过` 必须有 `skipped` 审批记录；`不适用` 表示该阶段对本次需求不存在（如纯后端的 Phase 7）。
- 编码阶段的 6/7 用 `已完成`，不要求 `confirmed_by`，但必须有 `verification`（automated/manual + evidence）；其余确认类阶段（1a/2/3/5）用 `已确认`。

### 模式与档位（Phase 0 定档）

| mode | 阶段预设 | 说明 |
|---|---|---|
| `full` | 0→1a→1b→2→3→4a→5→4b→6→7→8 | 默认全流程 |
| `backend-only` | 0→1a→1b→2→3→4a→5→4b→6→8；7 标 `不适用` | 纯后端/接口；原型通常 `inline` 或 `none` |
| `frontend-only` | 0→1a→1b→2→3→4a→5→4b→7→8；6 标 `不适用` | 接口契约已定 |
| `analysis-only` | 0→1a→1b→2 后停靠；3 起未开始 | 只做需求分析/PRD |
| `prototype-only` | 0→1a→1b→2→3 后停靠；4a 起未开始 | 只出原型 |
| `fast` | 不建流水线产物 | 单点修复、≤2 文件、无接口/数据/交互契约变化；见 SKILL「快速通道」 |

| 字段 | 允许值 | 说明 |
|---|---|---|
| `mode` | 上表 | **必填**；缺失报 `E024` |
| `prototype` | `html` / `annotated` / `inline` / `none` | 完整 HTML / 现有页面截图批注 / 设计文档内联线框 / 不做 |
| `test_depth` | `cases` / `smoke` / `none` | 用例 / 冒烟 / 不单独出用例 |

> 偏离预设的阶段跳过，仍必须写入 `skipped` 并带审批；同一 mode 下不再逐阶段询问。

---

## 三、字段与规则

### 1. 阶段对象

| 字段 | 何时必填 | 说明 |
|---|---|---|
| `status` | 总是 | 闭集之一 |
| `artifact` | 有产物时 | 相对产物目录的文件名，可带 `#锚点`；多个用 `/` 分隔 |
| `version` | 已确认/已完成时推荐 | `v0.8` 或 `0.8`；与 `prd_version`/`design_version` 对齐 |
| `confirmed_by` | `已确认`，以及 1a/2/3/5 的 `已完成` | 确认人姓名或角色（不能是 `—`/`-`） |
| `confirmed_at` | 同上 | `YYYY-MM-DD` |
| `approval_ref` | 同上 | 消息 ID / 邮件 / 会议纪要 / 工单链接；占位符不算；缺报 `E025`（旧目录 `W021`） |
| `completed_at` | 非确认类阶段的 `已完成`（4a/4b/6/7/8） | `YYYY-MM-DD` |
| `verification` | 6/7 标 `已完成` 时 | `{"level": "automated|manual", "evidence": "测试文件/命令/结果"}`；`build-only` 不算 |
| `notes` | 可选 | Phase 8 备注里的"待…/未完成"会触发 W008 |

**4a / 4b**：4a 场景清单在 Phase 3 后产出（随 2/3 确认），4b 测试用例在 Phase 5 后产出（随 5 确认）；两者共用 `P4-场景与测试Case.md`，用 `#scenarios` / `#cases` 锚点。编码前 4b 必须已完成、已跳过或不适用。

### 2. 门禁字段

| 字段 | 说明 |
|---|---|
| `coding_allowed` | `true` 才允许 Phase 6/7 进入 `进行中/已完成` |
| `coding_granted_by` | 授予编码许可的人；`coding_allowed=true` 时必填 |
| `coding_granted_at` | 授予日期；`coding_allowed=true` 时必填 |
| `prd_version` | 当前已确认的 PRD 版本，与 phases.2.version 一致 |
| `design_version` | 当前已确认的开发设计版本，与 phases.5.version 一致 |
| `risk` | `{"level":"low|medium|high","data_change":bool,"breaking_change":bool,"security_sensitive":bool,"reason":"...","assumptions":["..."],"consumer_impact":["..."]}`；必填；medium/high 必须有 `reason`；`breaking_change=true` 必须有非空 `consumer_impact`（受影响客户端/调用方+兼容性结论） |
| `breaking_change` | 既有客户端可观察的响应体/响应头/语义变化（即使路径/状态码不变）；为 true 时必须在 P5 做消费方影响分析并写 `consumer_impact` |

### 3. 跳过与待环境

```json
"skipped": [
  {
    "phase": "3",
    "reason": "无 UI 变更，复用 P5 第 6 节线框",
    "approved_by": "张三",
    "approved_at": "2026-11-17"
  }
],
"pending_env": ["T01-T36", "A8", "A11"]
```

- `skipped` 每条必须有 `approved_by` / `approved_at` / `reason`，且对应阶段状态为 `已跳过` 或 `不适用`。
- `pending_env` 非空时，Phase 8 不得为 `已完成`；P8 不得出现肯定的"验收通过"。

---

## 四、脚本

在 skill 根目录运行：

```bash
# 单个需求
python3 scripts/req2code-check.py <需求目录>

# 扫描 docs/ai-coding 下全部需求
python3 scripts/req2code-check.py <仓库根> --scan

# 机器可读
python3 scripts/req2code-check.py <需求目录> --json

# CI / 提交前：WARN 也算失败
python3 scripts/req2code-check.py <仓库根> --scan --strict
```

退出码：`0` 通过；`1` 有 ERROR（`--strict` 下 WARN 也算）；`2` 路径/参数错误。

### 主要错误码

| 码 | 含义 | 典型修法 |
|---|---|---|
| `E000` | 找不到/无法读取 `_状态.md` | 传需求产物目录，不是仓库根 |
| `E001` | state JSON 无法解析 | 修 JSON，或删标记回退旧表格 |
| `E002` | `schema` 缺失/不符 | 改为 `req2code/state@1` |
| `E003` | 缺少阶段键 / 未知阶段 | 补全 phases；未涉及阶段标 `不适用` |
| `E004` | 非法状态 | 用闭集值 |
| `E005` | 确认类阶段缺确认人/日期 | 补 `confirmed_by` / `confirmed_at` |
| `E006` | 已完成阶段缺完成日期 | 补 `completed_at` |
| `E007` | 编码已许可，但 PRD/设计未确认 | 先确认 Phase 2/5 |
| `E008` | 未授编码许可，6/7 已开始 | 回退代码状态，或补门禁 |
| `E009` | 编码已开始，上游阶段未完成 | 补完/确认/显式跳过 |
| `E010` | 跳过缺审批 | 补 `approved_by/at/reason` |
| `E011` | skipped 与阶段状态不一致 | 改状态或删记录 |
| `E012` | 产物文件不存在 | 修正 artifact 或补落盘 |
| `E013` | 有待环境项却宣称完成/通过 | 改回待确认，或补齐验证 |
| `E014` | 编码许可缺授予人/日期 | 补 `coding_granted_by/at` |
| `E015` | 表格与 JSON 状态不一致 | 以 JSON 为准修表 |
| `E016/E017` | PRD/设计版本与阶段版本不一致 | 对齐版本号 |
| `E018` | `updated_at` 缺失/非法 | 补 `YYYY-MM-DD` |
| `E019` | `demand` 为空 | 补需求名 |
| `E020` | skipped 阶段无法识别 | 用 `0/1a/1b/2/3/4a/5/4b/6/7/8` |
| `E021` | 枚举/类型错误 | 按本文允许值修正 |
| `E022` | Phase 8 已完成但退出标准未满足 | 补「退出结论：通过」与「未关闭 P0/P1 Bug：0」，或改回待确认 |
| `E023` | Phase 6/7 已完成但验证证据不足 | 补 `verification`：`automated`/`manual` + evidence；只编译/构建不算 |
| `E024` | `mode` 缺失 | Phase 0 定档后写入 |
| `E025` | 确认缺 `approval_ref` | 补消息/邮件/会议/工单引用，只口头确认不算 |
| `E026` | 产物头部状态与 state JSON 矛盾 | 以 state 为准修产物头部，或回退 state |
| `E027` | `risk` 缺失/非法 | 补 level + 三个布尔标志 |
| `E028` | 高风险变更的 P5 缺 NFR/失败模式/可观测性/安全/回滚 | 补 P5 §8（及 §7）后再确认设计 |
| `E029` | medium/high 风险缺 `risk.reason` | 写清等级依据（影响/可能性/可逆性） |
| `E030` | `breaking_change=true` 但缺 `risk.consumer_impact` | 列受影响客户端/调用方 + 兼容性结论 |

WARN 主要提示：旧格式（W001）、状态非闭集（W002）、缺输入来源（W003）、引用下游（W004）、引用旧版本（W005）、旧目录缺完成日期（W006）、待环境未列清单（W008）、Phase 8 产物未指向 P8（W009）、缺阶段表（W010）、`dir` 不一致（W011）、无 `coding_allowed` 时按 6/7 推断（W012）、版本未回填（W013）、产物字段无法解析（W014）、旧目录用合并阶段 4（W015）、旧目录 P8 缺退出结论（W016）、旧目录 6/7 缺验证证据（W017）、mode 与阶段状态不一致（W019）、prototype 档位与 Phase 3 产物不匹配（W020）、旧目录确认缺审批引用（W021）、产物头部状态陈旧（W022）、旧目录无 risk（W023）、中风险 P5 建议补 NFR（W024）、中高风险 P8 缺 NFR 验收/not-verified（W025）、决策简报缺决策字段/历史（W026）、P8 缺探针/HEAD/liveness/readiness（W027）。WARN 不阻塞，但 `--strict` 下会失败。

### Phase 8 退出标准

Phase 8 标 `已完成` 必须同时满足：

1. `P8-验收记录.md` 有「退出结论：通过」（`不通过` / `待环境` 不算）；
2. 「未关闭 P0/P1 Bug：0」；
3. `pending_env` 为空（或用户书面接受待环境，且 Phase 8 不标完成）；
4. `req2code-check.py` 无 ERROR。

P8 抬头、退出结论与 `_状态.md` 三者不一致时，以脚本报错为准，先修状态再宣布交付。

---

## 五、旧目录兼容

没有 `<!-- req2code:state -->` 标记的目录按旧表格解析，并给 `W001`：

- 状态值会被映射（`已确认 v0.8` → 已确认；`草案 v0.8` → 进行中；`待环境` → 待确认；`待确认是否跳过` → 待确认 + 跳过待审批）；
- 旧目录的合并阶段 `4` 同时作为 4a/4b 的兜底（`W015`）；旧 6/7 已完成但无验证证据记 `W017`，旧 P8 缺退出结论记 `W016`；
- 表格里的 `确认人/日期` 列支持合并（`确认人/日期`）或分列；
- 旧目录缺完成日期只记 `W006`，不阻塞；
- 一旦补上 state JSON，脚本改走严格校验。

历史目录不需要迁移；新需求请直接用 JSON 模板。

---

## 六、在流程中的调用点

| 时点 | 动作 |
|---|---|
| 启动自检 | 扫描 `docs/ai-coding/*/_状态.md`，有 ERROR 先报告并停靠 |
| Phase 0 | 一次定档 `mode` + 仓库路径；非 fast 用 artifacts.md 模板创建 `_状态.md` |
| 每次确认 | 更新 JSON 的 `confirmed_by/confirmed_at`，再同步表格；跑脚本 |
| Phase 6/7 前 | `gate: PASS` 且 `coding: ALLOWED` 才实施；`gate: PASS` 不等于编码许可；`E007/E009/E014` 必须先修；4b 未就绪不得编码 |
| Phase 6/7 完成 | 6/7 标 `已完成` 前补 `verification`（automated/manual + evidence） |
| Phase 8 前 | `pending_env` 与 Phase 8 状态一致；P8 补退出结论与 Bug 计数 |
| 需求关闭 | `gate: PASS` 且 `acceptance: DONE` 才算闭环 |
