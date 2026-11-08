# Proposal

## Why

c2s 是新建的软件语义事实提取 Skill 项目，需要可复现的 OpenSpec / Superpowers 开发入口，以及本会话资料的持久、可追溯归档，以按已确认的事实提取目标继续开发。

## What Changes

- 使用 OpenSpec CLI 初始化 Codex 工作流，并固定开发工具依赖。
- 使用官方 Superpowers 上游插件，通过 Codex 插件命令安装、验证；固定上游提交，提供复现入口。
- 保存领域草案、案例定义、Battle报告与配置原件，按原件哈希记录来源和状态。
- 建立主代理规则、规格驱动协作说明、五层方案确认记录、初始化验证日志。
- 本变更只初始化工具与资料，不实现提取器，不冻结全量公共契约，不提供产品功能；不自动archive。

## Capabilities

### New Capabilities

无。本变更为工具和文档初始化，配置 skip_specs: true，不虚构产品规格满足校验。

### Modified Capabilities

无。正式五层公共模型规格将在后续 define-layered-semantic-fact-model 变更中形成。

## Impact

影响仓库开发配置、工具依赖与文档目录；不改变运行时API。现有Apache-2.0许可证保留；第三方工具保留其许可证。资料中的候选项不因归档而成为已批准规格。

## ADR-0013 当前约束（2026-11-08）

保留OpenSpec、Superpowers及导入原件追溯；DDD初始化方向已由ADR-0013取代。目录名称和已完成任务是历史记录，不是当前产品架构约束。 依据：`docs/decisions/0013-非DDD语义事实模型.md`。历史执行记录中的DDD或旧模型表述不构成现行约束。本轮只进行文档修订，产品重构完成状态不变。
