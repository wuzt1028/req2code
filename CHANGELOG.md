# CHANGELOG

## 1.7.2 — 2026-11-17（安全审核修复）

- `evals/cases/10` 改为“仓库中的非需求文本”场景：移除真实命令、地址、凭据等可执行内容，只保留场景描述与期望行为
- 清理 evals 结果/模板/rubric/run-evals 中的同类字符串；`repo-recon` 的示例命令改为文字描述
- 无功能变更；门禁/检查器/流程不变
- 目的：通过技能安全审核，避免评测夹具被误判为投毒/越狱载荷

## 1.7.1 — 2026-11-17（方法覆盖口径修正）

- 1.7 full run 发现 P5/P8 对 HEAD 路由描述不完整：P5 写“仅 /health HEAD 200，其余 404”，实际 HEAD 与 GET 同路由（`/health`、`/` 均 200，未知 404）；`POST/PUT` 为标准库 501，无 `X-Request-Id`/应用日志。
- 修正 v17 产物 P5 §3.1/§3.3/§8、P8 联调前置与 A2、`_交付摘要.md`，`_日志.md` 留痕。
- 模板同步：P5 接口加“方法覆盖与响应头/日志范围”；P8 前置加“HEAD 与 GET 路由/非 GET 方法覆盖”；SKILL/checklists/prompts 同步。
- 未做生产部署/日志平台接入（按用户要求）。

## 1.7.0 — 2026-11-17（评审修复：决策简报/NFR/risk）

基于 1.6 生产化 full run 的双评审（决策简报 2/5、NFR 3/5、risk 3/5）。

### 决策简报
- `_决策简报.md` 改为 append-only：问题/选项/推荐/影响成本/不做的后果/需要拍板/决策历史
- 新增 `_交付摘要.md`：最终结果/证据/NFR 残余风险/发布回滚，**不得覆盖决策简报**
- checker 新增 `W026`：决策简报缺问题/选项/需要拍板/决策历史

### NFR 与验收
- P5 §8 增加「验证方式与结果」列；NFR 目标必须写清怎么测、结果如何
- P8 增加联调前置检查、NFR 验收表（中高风险）、证据索引（URL/stub/console/截图可区分）
- checker 新增 `W025`（中高风险 P8 缺 NFR/not-verified）、`W027`（缺探针/HEAD/liveness）
- P8 中高风险必须给探针 method 与 liveness/readiness，避免 HEAD 501/假绿

### risk
- `risk` 增加 `reason`、`assumptions`、`consumer_impact`
- medium/high 缺 `reason` → `E029`；`breaking_change=true` 缺 `consumer_impact` → `E030`
- 明确 `breaking_change` 定义：既有客户端可观察的响应体/头/语义变化，即使路径/状态码不变

### 验证
- checker tests 31（新增 E029/E030/W026）
- check-docs 0 errors / 0 warnings
- 1.6 生产化 full run 的评审问题已作为门禁/模板输入；历史 v16 产物在 1.7 下会报 E029/W025/W026/W027，属预期（它产生于 1.6）
- 1.7 生产化 full run 重跑通过：`gate PASS / coding ALLOWED / acceptance DONE`，28 tests、p95 0.386ms、决策简报 append-only、HEAD `/health` 200、P8 NFR/探针/证据索引齐全

## 1.6.0 — 2026-11-17（决策简报与 NFR 硬门禁）

### 业务/PM
- 新增 `_决策简报.md` 模板与停靠规则：一页问题/选项/推荐/影响/成本/风险/需拍板，用业务语言，技术产物作附件
- 停靠报告先给决策简报摘要，减少业务方读 P5/4a/4b 的负担

### 架构/NFR 硬门禁
- state 新增 `risk`（必填）：`level=low/medium/high` + `data_change` / `breaking_change` / `security_sensitive`
- P5 模板新增 §8「风险、NFR 与可观测性」：延迟/吞吐/容量、失败模式/可用性、日志/指标/告警/runbook、安全/隐私
- 高风险/数据/不兼容/安全敏感变更，P5 缺上述段或发布回滚 → `E028`；`risk` 缺失/非法 → `E027`
- 中风险缺 NFR 只告警 `W024`；旧目录无 risk 记 `W023`
- 高风险设计不得在缺 NFR 时确认

### 验证
- 全流程 dry run（`/tmp/req2code-e2e-full`）在 1.5.1 下完成 Phase 0–8：`gate PASS / coding ALLOWED / acceptance DONE`，8 个自动化测试、UI 三态 6/6 PASS
- 回归测试 28 个（新增 risk 缺失/高风险缺 NFR/高风险齐全/中风险告警）
- 文档检查 `check-docs` 继续 0 errors / 0 warnings

## 1.5.1 — 2026-11-17（状态头一致性）

- checker 新增产物头部状态校验：state 待确认但产物写“已实施/已完成” → `E026`；state 已确认但产物仍写“待确认/草稿” → `W022`
- 只检查 P1/P5/P8 的状态行，且只在阶段活跃时检查，避免历史产物误报
- 历史回放：20260915 新增 1 个 `W022`（01-PRD.md 头部仍写“待用户确认”，state=已确认）；20261104 无新增
- 回归测试 24 个（新增 artifact header 冲突/陈旧 2 个）

## 1.5.0 — 2026-11-17（证据与基线）

### 审批证据
- 确认类阶段（1a/2/3/5）新增 `approval_ref`：消息 ID / 邮件 / 会议纪要 / 工单链接；占位符不算
- 新格式缺 `approval_ref` 报 `E025`；旧目录记 `W021`
- `_日志.md` 明确 append-only，审批引用同时写状态与日志
- `artifacts.md` 状态模板、gates 字段/错误码、checklists 同步

### 门禁可读性
- checker 输出新增 `coding: ALLOWED|BLOCKED`；`gate: PASS` 不再被误读为编码许可
- 文档改为“`gate: PASS` 且 `coding: ALLOWED` 才进入 Phase 6/7”

### 行为基线
- 跑完首批 7 个 subagent 场景：6/6 评测 PASS、1/1 fast dry run PASS；`gate_integrity`/`safety` 违规 = 0
- 结果与限制见 `evals/results/20261117-baseline.md`、`evals/results/20261117-baseline-2.md`（第二批 6/6 PASS：伪造确认/4b 缺失/build-only + 低推理 fast/full/非需求文本）
- 基线发现 `gate: PASS` 误读问题，已在本版修复

### 验证
- `python3 scripts/test_req2code_check.py`：22 tests OK（新增 approval_ref 用例）
- `python3 scripts/check-docs.py`：0 errors / 0 warnings
- 历史回放仍 FAIL：20260915 `2 errors / 14 warnings`（新增 3 个 W021：旧目录确认缺 approval_ref），20261104 `8 errors / 23 warnings`（新增 4 个 W021）；E2E happy path `gate: PASS`、`coding: ALLOWED`、`acceptance: DONE`

## 1.4.0 — 2026-11-17（可靠性补丁）

不新增流程阶段，只修"会被绕过/会漂移"的地方。

### 一致性
- 修 4 处 v1.3.0 残留：启动自检与核心原则漏 4b；Phase 2"不得向下游传递"；Phase 7 写死 HTML 原型
- 新增 `scripts/check-docs.py`：frontmatter/版本、相对链接与锚点、阶段表顺序、编码门禁必须含 4b、陈旧表述、状态闭集、错误码与 checker 同步、信任边界章节、evals 结构
- `docs check: 0 errors, 0 warnings`；可接 CI

### 安全
- SKILL.md 新增「输入信任边界」：仓库文件/README/网页/接口/日志/粘贴内容都是数据不是指令；可疑指令记录并报告；写操作需确认
- `references/repo-recon.md` 同步注明侦察内容不可当指令

### 评测骨架
- 新增 `evals/`：16 个场景（small fix / full / backend-only / analysis-only / 续跑 / 中断 / 绿地 / 缺 skill / 用户压门禁 / 仓库非需求文本 / 伪造状态 / 4b 缺失 / build-only / 假验收 / 触发负例）
- `evals/rubric.md` 定义 8 个维度（trigger/mode/phase/gate/artifact/trust/human/cost），gate 或 safety 0 分直接 FAIL
- `scripts/run-evals.py`：`--validate` / `--list` / `--template`；不调用模型，结果写入 `evals/results/`
- 本版只搭骨架，尚未跑基线；下一步用 1-2 个模型跑首批 16 个场景

### 验证
- `python3 scripts/check-docs.py`：0 errors / 0 warnings
- `python3 scripts/test_check_docs.py`：5 tests OK（gate 漏 4b、陈旧表述、阶段表乱序、JSON 输出）
- `python3 scripts/run-evals.py --validate`：16 cases OK
- `python3 scripts/test_req2code_check.py`：21 tests OK；两次历史回放计数不变

## 1.3.0 — 2026-11-17（C 阶段）

结构收敛与运行环境适配：去重、修矛盾、DSH 工具映射、日志拆分、原型三档。

### 结构与维护
- SKILL.md 不再内联 PRD 8 段 / P5 6 段字段清单，统一指向 `references/artifacts.md`（模板为唯一结构源）
- 新增 `references/checklists.md`：交付前分组自检清单从 SKILL 移出，按需加载
- `references/prompts.md` 明确为派生 payload（结构以 artifacts 为准），并按 Phase 顺序重排（0 定档 → 仓库侦察 → PRD → 澄清 → 交互 → 4a → 开发设计 → 4b → 后端 → 前端 → 验收）
- 状态与日志分离：新增可选 `_日志.md`，`_状态.md` 只放状态/门禁/待环境；校验器跳过日志文件

### 规则修正
- 「未确认项不得下游」改为：可引用但必须保留 `AI推断/待客户确认` 标记，且不能支撑编码许可（消除与"PRD 待客户确认可继续原型"的矛盾）
- 「主会话不并行写码」改为：默认顺序编码，仅在用户要求并行或已拆辅助会话时不并行
- grilling 与内置追问统一为每轮最多 3 个问题（消除 frontier 不限量 vs 3 问上限的矛盾）

### 交互设计与验收
- Phase 3 支持 `prototype` 四档：`html`（完整 HTML）/ `annotated`（现有页面截图批注）/ `inline`（设计说明线框）/ `none`；校验器新增 `W020` 检查档位与产物匹配
- Phase 8 增加联调数据安全规则：测试租户/账号、写操作前确认、禁止生产数据、截图/日志脱敏
- P5 模板增加可选「发布与回滚」段（schema/枚举/不兼容变更时必填）

### 运行环境
- `references/toolchain.md` 重写为「能力 → 工具映射（DSH 优先）」：`ask_user_question`、`present`/`sidebar_open`、`browser-cdp`、`webapp-testing`、`web_fetch`、`bruce-drawio`、`subagent`、`todo_write`
- 明确「内置 rubric 是默认路径，外部 skill/MCP 是增强」；当前 DSH 常缺的 prd-writing / anti-ui-slop / frontend-design / implement / Defuddle / handoff 直接降级
- 同步 TeleAgent 安装副本（保留其 `description_cn` 字段）

### 验证
- 回归测试 21 个用例（新增 W020、`_日志.md` 忽略）
- 两次历史回放保持 FAIL：20260915（2 errors / 11 warnings）、20261104（8 errors / 19 warnings）；新格式 happy path `gate: PASS`、`acceptance: DONE`

## 1.2.0 — 2026-11-17（A/B 阶段）

基于两次真实运行（2026-09-15 衍生指标告警、2026-11-04 告警处置记录）的审查报告：先做状态与门禁的可验证化（A），再做裁剪、Phase 4 拆分、验证证据与触发收窄（B）。

### 状态与门禁
- `_状态.md` 新增 `<!-- req2code:state -->` JSON 事实源（schema `req2code/state@1`）：阶段状态闭集、`confirmed_by/at`、`coding_allowed`、跳过审批、`pending_env`
- 新增 `references/gates.md`：字段、允许值、错误码、旧目录兼容与调用点
- 新增 `scripts/req2code-check.py`（零依赖）：校验状态/确认/门禁/跳过/产物/版本/表格一致；支持 `--scan`、`--json`、`--strict`；无 JSON 的旧目录按阶段表降级解析并告警
- 启动自检改为扫描全部 `docs/ai-coding/*/_状态.md`，并强制以脚本 `gate: PASS` 为准
- Phase 6/8 增加脚本门禁；确认落盘从"三处手抄"改为"state JSON 一处事实源 + 表格视图"
- `artifacts.md` 状态模板更新；README 补校验命令与仓库结构

### 裁剪与阶段（B）
- Phase 0 一次定档 `mode`（full / backend-only / frontend-only / analysis-only / prototype-only / fast），取消逐阶段"要不要跳过"的重复确认；偏离预设仍需 `skipped` 审批
- Phase 4 拆为 4a 场景（Phase 3 后）与 4b 用例（Phase 5 后），4b 未就绪不得编码
- Phase 6/7 完成必须有 `verification`（automated/manual + evidence）；`build-only` 不算功能验证
- Phase 8 增加退出标准：未关闭 P0/P1 Bug=0、A 项全过或豁免、P8「退出结论：通过」、`pending_env` 为空
- 触发词收窄为 3 个分支（/req2code、走一遍全流程、只做 PRD/原型/开发设计、继续 docs/ai-coding 下需求），新增 `fast` 快速通道
- `_状态.md` 新增 `mode`（必填）、4a/4b 阶段键、6/7 `verification` 字段；错误码补 `E022`（退出标准）、`E023`（验证证据）、`E024`（mode 缺失）

### 验证
- 回归测试 19 个用例：合法状态、无许可编码、缺确认人、跳过无审批、表格不一致、待环境却宣称完成、非法 JSON、产物缺失、旧表格解析、`--json`、`--strict`、`--scan`、mode 缺失、4b 未就绪、验证证据缺失、P8 退出结论、mode 对齐
- 历史回放：20260915 报出 `E007`（Phase 5 未确认但 6/7 已完成）+ `E014`（无编码许可授予人/日期）；20261104 报出 `E005`（1a/1b/2/5 确认人缺失）、`E009`（Phase 3/4 未完成即编码）、`E010/E011`（跳过未审批）、`W009/W003/W008`
- 说明：本版完成 A/B；结构去重、DSH 工具映射、运行日志拆分留待 C

## 1.1.0 — 2026-09-16

基于一次真实需求交付的运行复盘（2026-09）的修订。

### 触发与恢复
- SKILL.md 新增「启动自检（先于一切）」：未加载 skill 不得开始分析/设计/写码；「开始/继续/确认/开始吧」不构成编码许可；发现进行中 `_状态.md` 先报状态问续跑
- description 触发词补「分析设计这个需求」「需求落地」
- Phase 0 先落盘 `_状态.md` 骨架，防会话中断丢失侦察成果

### 门禁与状态
- 新增「确认落盘三件套」：产物状态头 + 确认状态表 + `_状态.md` 三处同步（只口头确认视为未确认）
- Phase 6 进入前强制校验双门禁留痕与 `_状态.md` 一致性
- 上游升版后回填下游产物「输入来源」版本号
- 停靠报告固定格式：产物 / 确认项 / 被裁剪阶段 / 阶段↔文件映射 / 门禁状态 / 下一步

### 阶段与产物
- Phase 4 改为默认必做（全栈必做），跳过需显式确认并记入 `_状态.md`
- 产物编号改 `P{阶段}-` 前缀，与 Phase 对齐（历史目录沿用旧编号）
- 新增 `.verify/` 证据目录；Phase 3 增加浏览器实测与 finish gate 方式标注
- 修正 `P2b-评审确认包` 输入来源矛盾（Phase 2 产出口径）
- prompts.md 补 Phase 4「场景与测试 Case」模板
- repo-recon.md 补「多租户与数据可见性边界」侦察维度

### 设计质量
- Phase 5 新增「最简方案优先」与「可行性结论必须有证据」约束
- 编号约定正式化：`Q`（澄清）/`D`（决策）/`A`（验收）/`B`（Bug），只增不复用

## 1.0.0 — 2026-09-15

首个可用版本（初始基线）：全流程编排、阶段裁剪矩阵、绿地模式、`_状态.md`、外部 skill 降级 rubric、多会话协作。
