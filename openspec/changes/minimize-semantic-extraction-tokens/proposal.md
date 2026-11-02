# Proposal

## Why

Issue #11：通过减少必须交给LLM的实际工作最小化分层事实提取Token。已确认约束沿用共享context与主规格，相关上游候选见upstream。新结论非用户确认；本Issue讨论与复核有可追溯记录。

## What Changes

- 定义确定性与模型必要性分工、跨层复用、增量和必要上下文策略。
- 对每项机制列保持语义/证据与失效反例。
- 同质量全链路对照，预算/重试上限仅治理。

## Capabilities

### New Capabilities

- `token-efficient-semantic-extraction`: 通过减少必须交给LLM的实际工作最小化分层事实提取Token

### Modified Capabilities

无。

## Impact

依赖Issue [3, 5, 6, 7, 8, 9, 10]。仅候选规格和规划，不生成产品代码/Schema/目录/存储/测试，不归档。D01/D02与重大取舍保留决策请求；D03分析内更新前置按ADR-0006收敛，跨次政策不自动选择，不将未决值视为已定。
