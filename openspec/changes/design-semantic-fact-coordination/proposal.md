# Proposal

## Why

Issue #12：协调构造、核验、提交、取消与恢复，保持可观察一致性并减少重复模型工作。已确认约束沿用共享context与主规格，相关上游候选见upstream。新结论非用户确认；本Issue讨论与复核有可追溯记录。

## What Changes

- 规定固定分析输入的归属/适用性检查、共享需求与订阅边界。
- 覆盖半失败/进程中断/存储失败的恢复与响应。
- 统一阶段计时、Token和复用/覆盖诊断归因。

## Capabilities

### New Capabilities

- `semantic-fact-coordination`: 协调构造、核验、提交、取消与恢复，保持可观察一致性并减少重复模型工作

### Modified Capabilities

无。

## Impact

依赖Issue [3, 6, 7, 8, 9, 10, 11]。仅候选规格和规划，不生成产品代码/Schema/目录/存储/测试，不归档。D01/D02与重大取舍保留决策请求；D03分析内更新前置按ADR-0006收敛，跨次政策不自动选择，不将未决值视为已定。
