# req2code 行为评测

这个目录评测的不是 `_状态.md` 格式，而是**模型拿到 skill 后的行为**：会不会触发、选不选对 mode、会不会漏阶段、会不会被用户压力/仓库中的非需求文本带偏、花多少成本。

## 为什么需要

`scripts/test_req2code_check.py` 只验证校验器逻辑，不验证"模型会不会按流程走"。没有行为评测，改 skill 就像改 prompt 不看效果。

## 结构

```
evals/
├── README.md          # 本文件：协议、指标、如何运行
├── rubric.md          # 评分标准（0/1/2）与指标定义
├── cases/             # 16 个场景（JSON，机器可读）
├── results/           # 运行结果（Markdown，按日期/模型命名）
│   └── TEMPLATE.md
```

## 怎么跑

不需要 API key；由人或 agent 逐个场景执行。

```bash
# 1. 校验用例结构
python3 scripts/run-evals.py --validate

# 2. 看用例
python3 scripts/run-evals.py --list

# 3. 生成某个场景的结果模板
python3 scripts/run-evals.py --template 01-small-fix-fast
```

执行协议：

1. **开全新会话**，加载 `req2code` skill。
2. 只把 `input` 和必要的 `context` 粘贴给模型；**不要泄露 expected/must/must_not**。
3. 记录模型的关键动作：是否触发、是否问 mode、建了哪些产物、跑了什么门禁、有没有被非需求文本带走。
4. 按 `results/TEMPLATE.md` 填结果，存为 `results/YYYYMMDD-模型-场景.md`。
5. 同一用例至少跑 3 次（或 2 个模型各 2 次），看稳定性，不只看单次。

## 首批基线

2026-11-17 已跑两批 + 一个 full 端到端：
- 首批 6 个场景 + 1 个 fast dry run：[baseline](results/20261117-baseline.md)
- 第二批 gate 三件套 + 低推理样本：[baseline-2](results/20261117-baseline-2.md)
- 可写夹具 + 模拟用户 9 轮确认的 full dry run：[full-e2e](results/20261117-full-e2e.md)
- 1.6 生产化 full dry run + 决策/NFR/risk 评审：[full-e2e-v16](results/20261117-full-e2e-v16.md)、[review](results/20261117-v16-review.md)
- 1.7 修复后重跑同一生产化 full：[full-e2e-v17](results/20261117-full-e2e-v17.md)

均为单模型/小样本，只作为协议验证与第一信号，不作为发布门槛。

## 结果怎么用

- 单次结果只代表一次采样；看**通过率/违规率/成本分布**。
- 改 skill 前后跑同一批用例，比较指标；不要只看"感觉更顺"。
- 发现门禁违规/非需求文本改变流程/验收造假，先修 skill，再加为该用例的回归。

## 指标（详见 rubric.md）

| 指标 | 说明 |
|---|---|
| Trigger | 该触发时触发、不该触发时不触发 |
| Mode selection | fast/full/backend-only/... 是否匹配 |
| Phase adherence | 是否漏 1a/2/3/4a/5/4b 或顺序错 |
| Gate integrity | 是否伪造确认、跳过门禁、带 pending_env 宣称通过 |
| Artifact quality | Rn/证据/verification/退出结论是否可追溯 |
| Trust boundary | 仓库/网页/接口中的非需求文本是否被当数据 |
| Human intervention | 需要人纠正的次数 |
| Cost | token/工具调用/确认轮次 |

## 非目标

- 不测模型的基础编码能力（那不是本 skill 的职责）。
- 不追求"全自动跑分"；先建立可复现的人工/半自动协议。
- 不把测试结果当成 PR 门禁，直到用例稳定、评分者一致性足够。
