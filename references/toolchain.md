# 外部 skill、MCP 与运行环境适配

**默认路径是内置 rubric；外部 skill/MCP 可用时再增强。** 大多数运行环境不会装齐全部增强项，缺什么就地降级，不阻塞流程、不反复提醒。

标注约定：降级执行时在产物中写 `Fallback: {工具} unavailable -> {替代方式}`；同一会话首次降级时一次性告知用户缺失清单。

---

## 一、能力 → 工具映射（DSH 优先）

| 能力 | DSH 工具 | 在流程中的调用点 |
|---|---|---|
| 结构化提问 / 2-4 选项 | `ask_user_question` | Phase 0 定档；1a/2/3/5 停靠；跳过审批 |
| 产物/原型展示 | `present` / `sidebar_open` | Phase 3 原型、Phase 5/8 停靠报告 |
| 浏览器联调（复用登录态） | `browser-cdp` | Phase 8 接口/交互走查 |
| 页面自动化与截图 | `webapp-testing` | Phase 3 实测、Phase 8 回归 |
| 网页正文提取 | `web_fetch` | Phase 0 竞品/调研资料 |
| 可编辑流程图 | `bruce-drawio` | Phase 5 架构/链路图（可选） |
| 并行派发 | `subagent` / `subagent_fork` | Phase 6/7/8，用户要求并行时 |
| 阶段进度 | `todo_write` | 全程（长流程建议） |
| 文件/代码检索 | 内建 `read` / `grep` / `glob` | 仓库侦察、实现、验收 |

其他环境（Claude Code / OpenCode / Codex）按同能力替换工具名；没有对应工具就走降级（手工步骤、Playwright/curl、生成文件让用户打开）。

---

## 二、外部 skill 可用性判定

1. **在列表中**：当前会话的 skill 目录存在该名称。
2. **可被模型调用**：frontmatter 带 `disable-model-invocation: true` 的（如 `grill-me`、`implement`、`handoff`）只能用户手动触发；模型调用一律按不可用处理。
3. **调用未报错**：失败立即降级，不重试、不硬失败。

当前 DSH 会话常见情况：

- **可用**：`grilling`、`code-review`、`security-audit`、`diagnosing-bugs`、`bruce-drawio`、`webapp-testing`、`browser-cdp`。
- **通常缺失**：`prd-writing`、`anti-ui-slop`、`frontend-design`、`implement`、`Defuddle`、`handoff`、Chrome DevTools MCP。
- 因此 **PRD / UI finish gate / 视觉方向 / 正文提取默认走内置 rubric**；把外部 skill 当作加分项，不是前置条件。

---

## 三、集成总表

| 能力 | 首选（可用时） | 默认/降级 |
|---|---|---|
| PRD 结构 | `prd-writing` | 用 artifacts.md 的 P1 模板 + 下方 PRD rubric |
| 需求澄清 | `grilling` | 用 6 维追问清单 + `ask_user_question` 给选项 |
| 用户手动澄清 | `/grill-me` / `/grill-with-docs` | 提示用户手动触发，按其结果继续 |
| UI finish gate | `anti-ui-slop` | 用下方 UI rubric + `webapp-testing` 截图 |
| 视觉方向 | `frontend-design` | 用视觉方向三问，经用户确认 |
| 按规格实施 | `implement`（仅用户手动） | 直接按 P5 与实施模板执行 |
| 改动审查 | `code-review` | 用下方 code review 清单 |
| 安全审查 | `security-audit` | 提示用户单独走，不降级硬做 |
| 疑难 bug | `diagnosing-bugs` | 提示用户单独走 |
| 可编辑流程图 | `bruce-drawio` / `draw.io` | 用 mermaid |
| 浏览器联调 | Chrome DevTools MCP | `browser-cdp`（登录态）/ `webapp-testing`（Playwright）/ curl |
| 网页正文 | `Defuddle` | `web_fetch` + 人工筛选 |
| 跨会话交接 | `handoff` | 按 collaboration.md 的回报格式压缩交接 |
| 并行协作 | Agent/Task | `subagent`；不可用时用户开辅助会话 |

---

## 四、内置 rubric（默认路径）

### PRD rubric（prd-writing 缺失时）

- 有证据：问题背景含数据/用户引述/现象；无证据必须显式标注「无证据，观点驱动」
- 目标量化：每个目标带数字；每个指标配反指标
- 用户具体：「谁 + 什么情境 + 为什么需要」，禁止"产品经理"这类宽泛描述
- 优先级：P0 限 3-5 条；每条一句话；超出的降级或拆分
- 边界：必须有「明确不做」；缺边界视为不合格
- 禁词：improve/enhance 类无数字的模糊目标
- 篇幅：800-1200 字为宜；超过说明思考未完成

### 需求澄清追问清单（grilling 缺失时）

每轮最多 3 个问题，每题给 2-4 个选项：目标可量化吗（指标/反指标）→ 场景真实吗（谁/频率/现状）→ 边界清晰吗（不做什么）→ 优先级对吗（P0 能否砍到 3-5 条）→ 约束漏了吗（技术/合规/时间/依赖方）→ 证据充分吗（哪些观点驱动、需要向谁确认）。

### UI finish gate rubric（anti-ui-slop 缺失时）

- 反模板感：页面是否有明确的风格来源，能否一眼看出属于参考产品的设计语言
- 状态完整：加载/空态/错误态/禁用态（含权限不足态）是否全部覆盖
- 响应式：断点行为是否明确且自洽
- 可访问性：对比度、键盘可达、焦点可见、语义化标签
- 一致性：与参考源的偏离项是否逐条说明原因
- 结论：任一项不达标即整改后再交付

### 视觉方向三问（无参考源且 frontend-design 缺失时）

问用户：受众是谁（谁看、什么场景）→ 首要任务是什么（界面服务于什么动作）→ 想留下什么记忆点（唯一一处差异化）。方向经用户确认后再实现，禁止自由发挥。

### Code review 清单（code-review 缺失时）

- 契约一致：接口路径/字段/错误码与 `P5-开发设计.md` 一致
- 复用检查：是否存在可复用组件被重复实现
- 错误处理：异常分支、边界值、空值、并发/幂等
- 验证证据：6/7 的 `verification` 是否为 automated/manual 且有 evidence
- 兼容性：向后兼容；破坏性变更已标注并确认
- 风格一致：符合仓库既有命名/分层/写法
- 安全：鉴权、越权、注入、敏感信息（触发安全敏感改动时转 security-audit）

---

## 五、DSH 工具调用点（按阶段）

| 阶段 | 工具 | 用法 |
|---|---|---|
| Phase 0 | `ask_user_question` | 一次给出 mode 选项（推荐 full/fast）+ 仓库路径；避免开放式提问 |
| Phase 1a/2/3/5 | `ask_user_question` | 确认项逐条列出，2-4 选项，附推荐项 |
| Phase 3 | `present` / `sidebar_open` | 打开 `P3-交互原型.html` 让用户在 GUI 里看；实测用 `webapp-testing` 截图到 `.verify/` |
| Phase 5 | `bruce-drawio` | 需要可编辑架构/链路图时；否则 mermaid |
| Phase 6/7 | `todo_write` | 记录改动批次与验证状态；并行时用 `subagent` |
| Phase 8 | `browser-cdp` | 复用 Chrome 登录态联调；只读走查优先，写操作前确认 |
| Phase 8 | `webapp-testing` | 无登录态/需自动化回归时；截图与 console 记录入 P8 |
| 交接 | `subagent` / 用户辅助会话 | 按 collaboration.md 的结构化 prompt 与回报格式 |
