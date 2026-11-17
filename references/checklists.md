# 交付前自检清单

按门禁分组核对，过门时只核对对应组；完整状态字段与错误码见 [gates.md](gates.md)。

## 需求门禁（Phase 2 后）

- [ ] Phase 0 的 `mode` 已确认并写入 `_状态.md`（fast 不建产物）
- [ ] 5 要素复述已确认，待确认清单无遗留未答复项
- [ ] 结论均有证据标注，AI 推断项已显式标记
- [ ] 确认状态三态标记完整，未确认项未改标、未作为编码门禁依据；确认项有 `approval_ref`

## 原型门禁（Phase 3 + 4a 后）

- [ ] 参考源（或方向设定）已声明并经用户确认，token 映射表经用户确认
- [ ] 按 prototype 档位产出：html 原型 / annotated 批注 / inline 线框 / none 有理由
- [ ] 原型或批注已实测/走查，证据在 `.verify/`，finish gate 方式已标注
- [ ] Phase 4a 场景清单已产出（或跳过已确认并记入 `skipped`）

## 编码门禁（Phase 5 + 4b 后）

- [ ] 开发设计含复用点与不复用理由、最简方案对比、可行性结论有证据；接口契约完整（字段/错误码/鉴权/幂等）
- [ ] 决策记录 D1..Dn 完整；无新增未确认依赖；设计遵循仓库现有约定
- [ ] Phase 4b 用例就绪（或标 `不适用` 并记录理由）；Rn 从 PRD 贯穿到原型/接口/改动点/用例
- [ ] `req2code-check.py` 的 `gate: PASS` 且 `coding: ALLOWED` 已在 `_状态.md` 留痕（gate PASS 不等于编码许可）
- [ ] state `risk` 已填，含 `reason`/`assumptions`/`consumer_impact`；breaking_change 有消费方分析（`E029/E030`）
- [ ] 高风险/数据/不兼容/安全敏感时 P5 含 NFR/失败模式/可观测性/安全/回滚（`E028`）
- [ ] 每次停靠有 `_决策简报.md`（业务语言，一页，append-only；交付摘要另写 `_交付摘要.md`）
- [ ] 中高风险 P8 有 NFR 验收（或 `not-verified`）与证据索引；探针/HEAD 路由/非 GET 方法覆盖/liveness/readiness 已写
- [ ] 证据按用例可区分（URL/stub/console/截图成套）
- [ ] Phase 6/7 的 `verification` 为 `automated`/`manual` 且有 evidence；仅构建通过不算

## 交付门禁（Phase 8 后）

- [ ] Rn 逐条核对实现情况，验收项与 bug 清单齐全（A/B 编号）
- [ ] 未关闭 P0/P1 Bug = 0；A 项全过或有书面豁免；`pending_env` 为空（或用户接受且 Phase 8 不标完成）
- [ ] P8 有「退出结论：通过」；脚本 `gate: PASS`、`acceptance: DONE`
- [ ] 每阶段产物已落盘且下游按路径 + 版本引用（同目录相对、跨仓库绝对），`_状态.md` 与产物状态一致、已更新
- [ ] 状态与日志分离：过程记录在 `_日志.md`，`_状态.md` 只放状态/门禁/待环境
