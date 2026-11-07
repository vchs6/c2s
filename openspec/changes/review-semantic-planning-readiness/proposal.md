# Proposal

## Why

Issue#13需要核对全部规划、验收覆盖和批准边界，防止工件存在/严格校验被当作产品完成或开发批准。依据#3及#5–#12工件、用户授权和真实讨论证据。

## What Changes

- 汇总需求—能力—契约—任务—验收矩阵、跨提案修订及未决项。
- 生成可审查候选集合与内容摘要，定义冻结和独立开发批准入口。
- 报告就绪边界；基本系统需求按ADR-0007确认，技术设计未收敛不能冒充已冻结；D03分析内事项按ADR-0006收敛。

## Capabilities

### New Capabilities

无；skip_specs仅适用于本审核协调变更，不给产品新建能力。

### Modified Capabilities

无；不修改正式基线。

## Impact

交付docs/planning/program-2026-11-01/及本Issue评审记录，引用各变更唯一tasks。没有产品实现/测试运行，不apply、不archive，Issue保持open。

## 2026-11-02 系统需求确认接续

以ADR-0007及后续“当前一层=符合用户请求要求的顶层语义事实”为用户确认依据；需求与工具/接口等代理设计决定分开。人机双输出、缺口原因、查询触发与同主体补充、必要操作可执行及优化前后自评已明确。需求基线不等于全部设计已批准，当前仍不实施/归档。

## 领域模型对齐复核（2026-11-07）

领域模型对齐：本次审核必须将全部非归档OpenSpec提案与 ADR-0012 对照，逐项标为实质更新、历史兼容说明或不受影响；不能把OpenSpec严格校验通过等同于跨提案语义一致。完整逐项结果见 `docs/development/reviews/semantic-facts/semantic-entity-proposal-alignment.md`。
