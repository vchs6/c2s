# Issue #3 阶段一中立问题包

battle_id: issue-3-domain-planning-2026-11-01
base_sha: 18370af506d2153d0dae66a4d9536499a2b08114

## Problem / Scope

在已确认规格约束下，评审现有语言无关分层语义事实模型，提出可实现、可验证的公共契约方案和阶段二候选任务。本轮只评审与规划，不写产品、Schema、目录或测试实现，不自动归档；合格规划可直接提交main，状态awaiting-decision。

## User constraints

- Issue原文见issue-input.json，用户本轮授权只完成阶段一，并等待明确实施批准。
- ADR-0001/0002及openspec/specs两份主规格为固定约束，不重开五层、单身份、非强制层级和最小查询响应。
- DDD澄清统一语言、身份、不变量，不预设聚合/数据库/事务边界。
- 既有研究与Battle仅为证据/候选，不能把代理共识当用户批准。
- 继续define-layered-semantic-fact-model，不创建issue-3-*重复领域模型。

## Evidence

- AGENTS.md、openspec/config.yaml、docs/workflow/battle-protocol.md。
- openspec/specs/semantic-fact-model/spec.md、semantic-fact-query/spec.md。
- docs/decisions/0001-five-semantic-layers.md、0002-confirmed-specification-baseline.md。
- openspec/changes/define-layered-semantic-fact-model/{proposal,design,tasks}.md及specs。
- docs/domain/proposals/language-independent-layered-semantic-model.md（完整候选，非用户批准）。
- docs/development/discussions/2026-11-01-specification-baseline/{discussion,semantic-fact-model-candidates}.md。
- docs/development/reviews/2026-11-01/{model-battle-result,case-battle-result,case-evidence-manifest}.json及semantic-model-battle-report.md。

## Unknowns

Q01 主体身份与解释上下文；Q02组成与关联边界；Q03状态公共表达；Q04算法结构及伪代码；Q05契约技术和分阶段校验。以及工程边界、条件依赖、跨项目引用与来源覆盖的可验证性。

## Acceptance criteria

检查五层语义边界/谓词归类、项目与workspace/包/目标区分、配置与条件依赖、算法可表达性、未知与否定、模型支撑默认非递归响应。每条主张给证据、假设与反例；提出至少一个可行替代。识别方案决定与实现批准的差别。阶段二任务有上游Requirement、路径、检查方式、通过/失败条件；未决重大选择不得被悄悄编码成定案。

## Protocol

首轮proposer与challenger独立只读，仅共享本问题包与仓库资料，不读取对方首轮。首轮输出role、round、position、claims(id,statement,evidence_refs,assumptions,falsifier)、responses、unknowns。主代理编号争议，再互传材料交叉质询；最后新建独立reviewer综合。约800中文字/首轮，证据另计。只读角色，不声称操作系统隔离，不修改任何文件。
