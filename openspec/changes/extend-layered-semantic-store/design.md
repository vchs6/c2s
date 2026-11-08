# Design

## 当前领域模型基准

当前兼容边界：本提案建成的`semantic-fact-model-1`仓储保留为旧档案兼容实现及迁移输入；实体档案成为唯一权威写入、旧档案只读的切换尚待`redesign-semantic-entity-domain-model`的6.2/6.3完成，不在此宣称已执行。

## Scope

本变更历史交付扩展了SQLite以支持`semantic-fact-model-1`完整记录；该profile现作为旧档案兼容边界，不再定义新领域模型主轴。E0–E4是可保留的观察视角，不生成包含关系。M1 profile/接口继续独立；`semantic-entity-model-1`的权威档案及后续默认切换由实体重构提案管理。

## Existing Evidence

- `contracts/semantic-model/fact.schema.json`定义12个顶层记录集合；`semantic-fact-model-1`目录已有完整谓词与类型。
- `project_query_to_semantic_model`已把当前查询支持的所有Fact kind映射到全量profile及来源观察。
- `project_algorithm_to_semantic_model`已产生算法主体、body、region、step、控制关系、调用候选、证据、Coverage与SemanticState。
- 当前`SemanticFactStore._validate_candidate`、`canonicalize_m1`、SQLite表及CLI`--store`仅接受M1；CLI拒绝其他selector。不是模型能力或依赖缺失，而是后端和调用入口范围被限制。

## Data Organization

保留专用的sessions、registrations、facts、evidence、assessments、coverage、diagnostics、artifacts、receipts表；扩展dependencies、dependency_resolutions、semantic_states、context_domains、contexts专用表。每类记录有analysis/profile隔离键、稳定记录键、规范记录ID和JSON payload，关联列为常用关系建立索引。`semantic_refs`记录来源集合/ID、字段、目标集合/ID及序号，保存有序参数/前提且可在read前检查闭合。payload用于无损往返，实体与关系表提供类型化索引；禁止以一次查询JSON blob替代实体记录。

## Canonicalization

- Registration按sourceKey和完整ref身份/kind校验，证据集合并集。
- Evidence按来源、路径、附件内容摘要、字节摘要/跨度、方法及工具版本比较；附件保存原文并校验内容哈希。
- Fact key保留predicate、完整subject identity、value/arguments、claimMode、condition、polarity、negativeBasis及derivation；排除factId、evidenceIds、纯展示sourceMetadata。独立证据和evidenceRefs按规范ID及角色并集；不能证明等价时保留两条。
- Assessment/Coverage/Dependency/Resolution/SemanticState/Context按各自规范schema字段比较，记录ID外的字段不丢；supersedes、factIds、dependencyId和evidence引用在ID合并后重写。
- 同条件冲突同时保留；每次合并后的包按对应profile目录完整校验，校验失败不得提交。
- Artifact按SHA256加原始内容比较，hash相同而bytes不同拒绝。

## Query Path

`query --store`先读取已登记的同root/input/profile session与该selector coverage；状态适用且引用完整时直接从仓库投影最小请求bundle，不执行解析器。缺coverage则matrix选择工具、按需取得候选、投影全量profile、校验并原子提交、规范回读后查询。`algorithm --semantic-facts --store`同样写入full profile，以稳定subject/selector记录AlgorithmDescription与E4 body结构。`--cache`继续仅缓存临时query view，与语义实体表分离。

## Compatibility / Failure

旧M1 API是full store上的兼容端口，仅读写`m1-project-discovery-1`。同analysis的profile/输入身份变化报INPUT_MISMATCH；不同profile以独立analysis登记，不能混包。SQLite事务回滚无半包可见；提交后必须按规范read-back。现有读接口增添profile参数或增加full通用端口，CLI统一消费通用端口。

## Risks / Limits

记录类型增加会提高schema迁移与引用闭合复杂度；每个新增collection需契约驱动表映射及测试。`semantic-fact-model-1`结构有效不证明源真或全语义完整。当前解析器的显式gaps继续保留；本变更不扩大Python/Rust语言支持或声称完整CFG/类型/运行时行为。

## ADR-0013 当前约束（2026-11-08）

该提案记录旧完整档案的历史交付。当前新写入使用实体档案，旧档案只读兼容；历史写入场景不重新授权旧profile写入，不能作为新模型的分层组织依据。 依据：`docs/decisions/0013-非DDD语义事实模型.md`。历史执行记录中的DDD或旧模型表述不构成现行约束。本轮只进行文档修订，产品重构完成状态不变。
