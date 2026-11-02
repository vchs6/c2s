# Proposal

## Why

#5要求将查询性能、构造成本、Token、正确性和支持范围置于同一可验证口径，避免空结果或缓存命中制造虚假收益。依据：本Issue输入、共享context与battle.json；新评价定义是候选，非用户确认或实测。

## What Changes

- 建立绑定场景、规模、环境、质量和支持组合的评价档案。
- 区分全部请求的结果分布、成功延迟、首结果和完整成功，比较首次/复用/变化的实际Token。
- 用户决定首期支持组合及数值目标后方可冻结验收；本提案不填猜测值。

## Capabilities

### New Capabilities
- `semantic-analysis-scope`: 用户已确认的首期源语言范围（Rust和Python）；仅该确认同步基线。
- `semantic-analysis-quality`: 质量、性能和成本的可比评价及证据边界。

### Modified Capabilities

无。

## Impact

关联#6–#13；仅新增用户已确认的语言范围主规格，不修改原模型/查询主规格，不实现基准或产品。候选定义待整体审核，D01/D02阻塞范围和数值验收冻结。
