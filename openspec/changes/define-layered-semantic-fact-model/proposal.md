# Proposal

## Why

Issue #3需要将已有语言无关领域模型候选完善为可评审、可实现、可验证的公共契约规划，为后续语义事实查询Skill提供前置基础。此前已固化的五层与最小响应只是确认基线，不能代替完整领域定义和机器契约。

## What Changes

- 在现有变更继续阶段一：按brainstorming澄清边界、比较A/B方案，实际进行独立双方两轮Battle及独立综合评审。
- 在已确认约束下补齐工程单元/工作空间/目标、身份与配置、类型化事实/谓词/引用、来源/覆盖/状态及算法/伪代码候选规格。
- 用户已选择A（见scheme-decision.md）：JSON目录、结构Schema与分阶段Python校验，明确有限条件判定、组成引用边界、来源到body及body到伪代码分别验收；保留B等替代与异议。
- 更新design及唯一tasks.md，提供Issue范围—Requirement—任务—路径—验收映射，方案A已由用户选择、实施仍为awaiting-decision；不将Battle共识当作用户确认。
- 保留当前正式主规格与导入原件，绑定当前Issue输入及规划工件生成批准令牌；本次仅提交候选规划，方案选择已记录，继续等待用户明确批准实施。

## Capabilities

### New Capabilities

- `algorithm-description`：操作契约、结构化算法与可追溯伪代码的候选能力，增加受限构造/opaque及来源覆盖和投影分开验证；尚无主规格，不同步。

### Modified Capabilities

- `semantic-fact-model`：在已同步的三项确认要求之外，提议新增工程、身份/上下文、目录/引用、组成、状态/证据/覆盖、有限条件与循环诊断要求。本变更此前引入的前三项ADDED保持原文以保留同一活动变更的基线同步记录，不重开它们。

已完成的`semantic-fact-query`确认delta作为本活动变更历史工件保留，主规格四项不变，本轮不新增或修改查询行为、不开发查询流程。历史delta不表示本Issue承诺实现查询Skill。

## Impact

本轮只修改本活动变更及`docs/development/reviews/issues/3/`评审/批准记录和`docs/development/issues/3/state.json`状态。不创建产品代码、目录、Schema、测试或依赖清单，不安装候选依赖，不修改主规格、原始研究、workflow、代理规则或发布脚本，不自动归档。

阶段二若获批准，将按design/tasks产生领域模型文档、公共JSON目录/Schema、Python契约校验与算法投影辅助工具、正反例及准确验收记录；不涉及语言获取器、查询入口或存储服务。实现选择及不支持边界均明确为代理候选，不冒充用户决策。

本轮是用户授权的人工Work会话，允许维护既有变更及直接main提交。旧自动Runner只允许issue-3-*规划路径，不能直接承接本既有变更；此限制记入评审而不另建重复模型或修改权限绕过。
