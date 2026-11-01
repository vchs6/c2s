# Proposal

## Why

c2s 是新建的软件语义事实提取 Skill 项目，需要可复现的 OpenSpec / Superpowers 开发入口，以及本会话资料的持久、可追溯归档，才能按 DDD 和已确认的五层方向继续开发。

## What Changes

- 使用 OpenSpec CLI 初始化 Codex 工作流，并固定开发工具依赖。
- 使用官方 Superpowers 上游插件，通过 Codex 插件命令安装、验证；固定上游提交，提供复现入口。
- 保存领域草案、案例定义、Battle报告与配置原件，按原件哈希记录来源和状态。
- 建立主代理规则、DDD/SDD协作说明、五层方案确认记录、初始化验证日志。
- 本变更只初始化工具与资料，不实现提取器，不冻结全量公共契约，不提供产品功能；不自动archive。

## Capabilities

### New Capabilities

无。本变更为工具和文档初始化，配置 skip_specs: true，不虚构产品规格满足校验。

### Modified Capabilities

无。正式五层公共模型规格将在后续 define-layered-semantic-fact-model 变更中形成。

## Impact

影响仓库开发配置、工具依赖与文档目录；不改变运行时API。现有Apache-2.0许可证保留；第三方工具保留其许可证。资料中的候选项不因归档而成为已批准规格。
