# Proposal

## Why

Issue #8：仅在有查询时按必要缺口构造具体语义并复用有效成果。已确认约束沿用共享context与主规格，相关上游候选见upstream。新结论非用户确认；本Issue讨论与复核有可追溯记录。

## What Changes

- 定义查询触发、最小必要工作、依赖理由和停止条件。
- 分开定位索引、具体语义与响应投影。
- 失败、取消和不完备闭包保留缺口，合并执行由#12负责。

## Capabilities

### New Capabilities

- `lazy-semantic-fact-construction`: 仅在有查询时按必要缺口构造具体语义并复用有效成果

### Modified Capabilities

无。

## Impact

依赖Issue [3, 6, 7]。仅候选规格和规划，不生成产品代码/Schema/目录/存储/测试，不归档。D01/D02与重大取舍保留决策请求；D03分析内更新前置按ADR-0006收敛，跨次政策不自动选择，不将未决值视为已定。
