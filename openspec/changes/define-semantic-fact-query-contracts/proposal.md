# Proposal

## Why

Issue #7：定义有界、可判歧义的规范请求及逐项结果契约。已确认约束沿用共享context与主规格，相关上游候选见upstream。新结论非用户确认；本Issue讨论与复核有可追溯记录。

## What Changes

- 增补规范请求、逐项覆盖和有界展开规则。
- 自然语言解释为候选入口，不要求每次调用模型。
- 复用模型A身份、状态维度和内嵌白名单。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `semantic-fact-query`: 增补公共请求/结果约束，不改既有四项要求。

## Impact

依赖Issue [3, 5, 6]。仅候选规格和规划，不生成产品代码/Schema/目录/存储/测试，不归档。D01/D02与重大取舍保留决策请求；D03分析内更新前置按ADR-0006收敛，跨次政策不自动选择，不将未决值视为已定。
