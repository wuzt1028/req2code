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
- **过程可控不失控**：编码前必须过「PRD 已确认 + 开发设计已确认」双门禁，每次确认在产物中留痕；AI 只给选项和建议，拍板永远是你
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
| 「走一遍全流程」「从需求到交付」 | 从 Phase 0 开始全流程 |
| 「只做需求分析 / 只要 PRD / 只出原型」 | 单阶段执行并停靠 |
| 「继续/迭代某需求」 | 按 `_状态.md` 续跑 |

流程要点：

- **文件即交接**：产物落盘到 `{产物仓库}/docs/ai-coding/{YYYYMMDD}-{需求短名}/`（`P0-PRD-P3/P4/P5/P8` 编号与阶段对齐）
- **编码前双门禁**：PRD v2 已确认 + 开发设计已确认，缺一不可
- **确认落盘三件套**：产物状态头 + 确认状态表 + `_状态.md`，口头确认不落盘视为未确认
- **按需裁剪**：纯后端/纯前端/单阶段需求按裁剪矩阵执行，任何跳过都需显式确认

## 阶段与产物

| Phase | 名称 | 产物 |
|---|---|---|
| 0 | 输入确认与仓库侦察 | `P0-输入与仓库侦察.md` |
| 1-2 | 需求分析（PRD）+ 澄清 grill | `P1-PRD.md`（v2 需确认） |
| 3 | 交互设计（按需） | `P3-设计说明.md` + `P3-交互原型.html` + `.verify/` |
| 4 | 场景与测试 Case（默认必做） | `P4-场景与测试Case.md` |
| 5 | 开发设计 | `P5-开发设计.md`（含决策记录 D1..Dn） |
| 6-7 | 后端 / 前端开发（按需） | 代码改动 + `P5` 实施状态回填 |
| 8 | 联调与轻量验收 | `P8-验收记录.md` |

## 可选搭档

流程会优先调用下列 skill 增强质量，**缺失时自动降级到内置 rubric 并在产物中标注 `Fallback`**，不阻塞流程：

- `prd-writing` / `grilling`：PRD 结构与需求澄清
- `anti-ui-slop` / `frontend-design`：原型 finish gate 与视觉方向
- `code-review` / `security-audit` / `diagnosing-bugs`：验收审查与疑难排查
- Chrome DevTools MCP：联调；`draw.io`：流程图；`Defuddle`：网页正文提取

## 仓库结构

```
.
├── SKILL.md          # 流程权威定义（唯一）
├── CHANGELOG.md
└── references/
    ├── artifacts.md  # 产物目录、模板、交接协议
    ├── prompts.md    # 各阶段可粘贴指令模板
    ├── repo-recon.md # 仓库侦察清单
    ├── collaboration.md # 多会话协作
    └── toolchain.md  # 外部 skill 集成与降级 rubric
```

## License

[MIT](LICENSE)
