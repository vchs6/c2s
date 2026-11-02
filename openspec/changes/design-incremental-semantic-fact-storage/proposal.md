# Proposal

## Why

Issue #9：只保存尚未存储的内容并在重复、补充与变化之间保持身份和证据语义。已确认约束沿用共享context与主规格，相关上游候选见upstream。新结论非用户确认；本Issue讨论与复核有可追溯记录。

## What Changes

- 定义确定性比较、幂等提交和引用一致发布。
- 将同次固定输入下新增主张/补证/重复/冲突分开。
- 分析内无项目变化，不要求D03更新政策；跨次政策另议，不默选数据库或历史服务。

## Capabilities

### New Capabilities

- `incremental-semantic-fact-storage`: 只保存尚未存储的内容并在重复、补充与变化之间保持身份和证据语义

### Modified Capabilities

无。

## Impact

依赖Issue [3, 6, 7, 8]。仅候选规格和规划，不生成产品代码/Schema/目录/存储/测试，不归档。D01/D02与重大取舍保留决策请求；D03分析内更新前置按ADR-0006收敛，跨次政策不自动选择，不将未决值视为已定。
