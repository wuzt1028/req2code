# req2code

需求到交付全流程编排的 Agent Skill：需求分析 → PRD → HTML 原型 → 测试 Case → 开发设计 → 前后端编码 → 联调验收。每个阶段的结论固化成文件（`docs/ai-coding/{日期}-{需求名}/`），下一阶段按绝对路径读取，AI 与 AI、人与 AI 之间零信息损耗。

适用于 Claude Code / OpenCode / Codex / OpenClaw 等支持 Agent Skills 的编码代理。

## 适合谁

- **前后端 / 全栈程序员**：不想再让 AI 拿到需求就埋头写码，想把需求分析、设计、开发、联调完整走一遍
- **技术负责人 / 架构师**：要求开发过程规范、决策有依据、历史可追溯
- **小团队 / 独立开发者**：没有专职产品，需要 AI 把需求复述、PRD、澄清这些环节补上

## 它能帮你解决什么

- **全流程一条龙**：需求分析 → PRD → HTML 原型 → 测试 Case → 开发设计 → 前后端编码 → 联调验收，一个入口全搞定
- **物料规范留痕**：每阶段按固定模板产出文档，统一落在 `docs/ai-coding/{日期}-{需求名}/`，进度看 `_状态.md`；需求怎么来的、为什么这么设计、改了什么，随时可查、可复盘
- **过程可控不失控**：编码前必须过「PRD 已确认 + 开发设计已确认 + 4b 用例就绪」三确认，每次确认在产物中留痕；AI 只给选项和建议，拍板永远是你
- **按需裁剪**：只做需求分析、只出原型、纯后端需求……支持单阶段停靠，小需求不必走全流程
- **断点续跑**：会话中断、上下文压缩都不怕，凭 `_状态.md` 接着干
- **贴合你的仓库**：先侦察仓库约定和复用清单，不引入新框架新风格，最简方案优先

## 怎么用

- 全流程：输入 `/req2code 走一遍全流程` 或说「从需求到交付」
- 单阶段：「只做需求分析」「出个原型」「做开发设计」
- 续跑 / 查状态：「继续 / 迭代某需求」，或直接 `/req2code` 看进度

## 安装

推荐用 skills CLI（自动识别本机 agent 并安装）：

```bash
npx skills add wuzt1028/req2code
```

网络受限、HTTPS 克隆失败时，改用 SSH 源：

```bash
npx skills add git@github.com:wuzt1028/req2code.git
```

手动安装：

```bash
git clone git@github.com:wuzt1028/req2code.git ~/.agents/skills/req2code
# Claude Code 用户补一个软链
ln -s ~/.agents/skills/req2code ~/.claude/skills/req2code
```

## 使用

会话内触发：

| 说法 | 行为 |
|---|---|
| `/req2code` | 状态诊断：读产物 `_状态.md` 列出各阶段进度与下一步，不自动执行 |
| 「走一遍全流程」 | 从 Phase 0 开始，先定档 `mode` |
| 「只做需求分析 / 只要 PRD / 只出原型」 | 单阶段执行并停靠 |
| 「继续 docs/ai-coding 下的某需求」 | 按 `_状态.md` 续跑 |
| 单点修复、≤2 文件 | 走快速通道 `fast`，不建流水线产物 |

流程要点：

- **文件即交接**：产物落盘到 `{产物仓库}/docs/ai-coding/{YYYYMMDD}-{需求短名}/`（`P0/P1/P3/P4/P5/P8` 编号与阶段对齐）
- **一次定档**：Phase 0 确认 `mode`（full / backend-only / frontend-only / analysis-only / prototype-only / fast），之后不再逐阶段问跳过
- **编码前三确认**：PRD 已确认版本 + 开发设计已确认 + 4b 用例就绪，缺一不可；由 `scripts/req2code-check.py` 的 `coding: ALLOWED` 判定（`gate: PASS` 不等于编码许可）
- **确认落盘**：`_状态.md` 的 state JSON 记录确认人/日期/审批引用/编码许可/跳过审批；口头确认不落盘视为未确认；过程记录写 `_日志.md`
- **验证证据**：6/7 标完成必须有 `automated`/`manual` 证据；仅编译/构建通过不算
- **风险/NFR 门禁**：state `risk` 必填（含 reason/assumptions/consumer_impact）；高风险/数据/不兼容/安全敏感的 P5 必须含 NFR/失败模式/可观测性/安全/回滚
- **NFR 验收**：中高风险 P8 必须有 NFR 验收项或 `not-verified`；缺探针/HEAD/liveness 会告警
- **证据可区分**：每个用例的 URL/stub、console、截图成套归档，避免多张相同截图
- **决策简报**：每次停靠**追加** `_决策简报.md`（问题/选项/推荐/影响/成本/需要拍板/决策历史），交付摘要另写 `_交付摘要.md`，不覆盖决策历史
- **验收退出标准**：未关闭 P0/P1 Bug=0、A 项全过或豁免、P8「退出结论：通过」

## 模式

| mode | 适用 |
|---|---|
| `full` | 默认全流程 |
| `backend-only` | 纯后端/接口，Phase 7 不适用 |
| `frontend-only` | 接口契约已定，Phase 6 不适用 |
| `analysis-only` | 只做需求分析/PRD，Phase 2 后停靠 |
| `prototype-only` | 只出原型，Phase 3 后停靠 |
| `fast` | 单点修复、≤2 文件，不建流水线产物 |

## 门禁校验

```bash
# 单个需求
python3 scripts/req2code-check.py docs/ai-coding/20261104-告警处置记录

# 扫描全部需求；有 ERROR 退出码为 1
python3 scripts/req2code-check.py . --scan

# 机器可读 / 严格模式（WARN 也失败）
python3 scripts/req2code-check.py . --scan --json
python3 scripts/req2code-check.py . --scan --strict
```

脚本以 `_状态.md` 的 `<!-- req2code:state -->` JSON 为事实源，校验状态闭集、确认留痕、三确认门禁、4b 用例、验证证据、跳过审批、产物存在、表格一致与待环境清单。旧目录没有 JSON 时按阶段表降级解析并告警，可不迁移。字段与错误码见 [`references/gates.md`](references/gates.md)。

## 阶段与产物

| Phase | 名称 | 产物 |
|---|---|---|
| 0 | 定档 + 输入确认 + 仓库侦察 | `mode` 决策 + `P0-输入与仓库侦察.md` |
| 1-2 | 需求分析（PRD）+ 澄清 grill | `P1-PRD.md`（已确认版本需留痕） |
| 3 | 交互设计（按 prototype 档位） | `P3-设计说明.md` + 原型/批注/线框（按 `html`/`annotated`/`inline`） + `.verify/` |
| 4a | 场景清单（默认必做） | `P4-场景与测试Case.md` §4a |
| 5 | 开发设计 | `P5-开发设计.md`（含决策记录 D1..Dn） |
| 4b | 测试用例（默认必做） | `P4-场景与测试Case.md` §4b |
| 6-7 | 后端 / 前端开发（按需） | 代码改动 + `P5` 实施状态（含验证等级/证据） |
| 8 | 联调与轻量验收 | `P8-验收记录.md` + 退出结论 |

> 4a 在 Phase 3 后产出，4b 在 Phase 5 后产出；两者共用 `P4-场景与测试Case.md`，用 `#scenarios` / `#cases` 锚点。

## 快速通道（fast）

单点修复、`≤2` 个文件、无接口/数据/交互契约变化时，走 `fast`：Phase 0-lite（读仓库约定 + 风险确认）→ 直接实施 → 报告改动/验证/风险。不创建 `docs/ai-coding` 产物，不走三确认门禁；仍须按仓库约定跑测试/构建，不得跳过验证。超过 2 文件或改接口/表结构/权限/交互时，升级为 full / backend-only / frontend-only。

## 可选搭档

内置 rubric 是默认路径，外部 skill/MCP 可用时增强，**缺失时自动降级并在产物中标注 `Fallback`**，不阻塞流程：

- `grilling`：需求澄清；`code-review` / `security-audit` / `diagnosing-bugs`：审查与排查
- `bruce-drawio`：可编辑流程图；`webapp-testing` / `browser-cdp`：浏览器实测与联调
- `prd-writing` / `anti-ui-slop` / `frontend-design` / `implement` / `Defuddle` 常缺，按内置 rubric 执行
- DSH 工具映射（`ask_user_question` / `present` / `sidebar_open` / `web_fetch`）见 [`references/toolchain.md`](references/toolchain.md)

## 可靠性与评测

```bash
# 文档一致性：frontmatter/链接/阶段表/门禁表述/错误码/信任边界/evals 结构
python3 scripts/check-docs.py
python3 scripts/test_check_docs.py

# 行为评测用例结构（16 个场景；不调用模型）
python3 scripts/run-evals.py --validate
python3 scripts/run-evals.py --list
```

`evals/` 是**行为评测骨架**：场景、rubric（8 维）、结果模板、手工/agent 执行协议。它不替代真实跑模型；当前只完成骨架，尚未跑基线。

## 仓库结构

```
.
├── SKILL.md          # 流程权威定义（唯一）
├── CHANGELOG.md
├── scripts/
│   ├── req2code-check.py      # 状态/门禁校验（零依赖）
│   ├── check-docs.py          # 文档一致性检查（零依赖）
│   ├── run-evals.py           # 评测用例校验/模板（不调用模型）
│   ├── test_req2code_check.py # 校验器回归测试
│   └── test_check_docs.py     # 文档检查回归测试
├── evals/
│   ├── README.md              # 评测协议与指标
│   ├── rubric.md              # 0/1/2 评分标准
│   ├── cases/                 # 16 个场景
│   └── results/               # 运行结果模板
└── references/
    ├── artifacts.md  # 产物目录、模板、交接协议
    ├── gates.md      # 状态机、门禁与错误码
    ├── checklists.md # 交付前分组自检清单
    ├── prompts.md    # 各阶段可粘贴指令模板
    ├── repo-recon.md # 仓库侦察清单
    ├── collaboration.md # 多会话协作
    └── toolchain.md  # 能力→工具映射与降级 rubric
```

## 已知边界

- `fast` 不建流水线产物、不走三确认门禁；超过 2 文件或改接口/数据/交互时升级为完整 mode。
- 旧目录无需迁移；合并阶段 4、旧 P8/验证证据由脚本降级解析并告警。
- 增强 skill/MCP 常缺，内置 rubric 是默认路径；`Fallback` 会标在产物里。
- 本 skill 不替代安全审计、性能压测和专项测试；安全敏感改动走 security-audit。
- `_状态.md` 只放状态/门禁/待环境；过程日志写 `_日志.md`，避免状态文件变成流水账。

## License

[MIT](LICENSE)
