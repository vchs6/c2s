## 1. Full-profile normalization and canonicalization

现行接口接续（2026-11-09，ADR-0014）：本文件M1/V1及旧完整事实运行接口为历史规划/交付记录，当前公开运行协议仅V2，不再提供兼容查询、仓储或转换。通用能力要求继续适用；新实施不得恢复旧API。唯一删除与审核任务见`openspec/changes/redesign-semantic-entity-domain-model/tasks.md`第11节。

## 现行范围说明

现行范围说明：原任务交付的`semantic-fact-model-1`属于旧档案能力；实体重构的6.2/6.3完成前，不将其描述成已只读或已迁移。旧档案可作为兼容和导出对象。

- [x] 1.1 （M1）完整profile记录规范化。依据：`contracts/semantic-model/fact.schema.json`及`design-incremental-semantic-fact-storage` M1比较契约。交付：全模型各记录collection映射、规范键及引用重写。验证：facts/evidence/registrations/assessments/coverage/dependencies/resolutions/states/contexts全量往返；补证不复制主张；冲突保留；乱序/重复/断引用拒绝或规范化。全部模型层字段丢失、引用悬空、把层号推成包含关系失败。
- [x] 1.2 （M1）全量SQLite表与模式兼容。依据：任务1.1及现有M1 store。交付：新collection表/索引/refs及M1向后兼容迁移。验证：M1历史数据库可读；full bundle事务原子保存及恢复；故障不暴露半包；bytes/hash碰撞拒绝。

## 2. Constructor and query integration

- [x] 2.1 （M1）普通selector全模型构造和持久化。依据：`project_query_to_semantic_model`及能力矩阵。交付：query CLI使用full profile和规范回读。验证：project/classes/members/functions/local-bindings/behavior-contracts/algorithm-structure/all-supported-facts被写入full store且覆盖/缺口准确；M1选择兼容。
- [x] 2.2 （M1）算法语义存储与仓库查询。依据：`project_algorithm_to_semantic_model`及`semantic-fact-query`。交付：算法CLI保存E4 facts，query --store从覆盖命中回读范围bundle。验证：重复查询不重复执行工具；请求selector隔离；同subject只补缺层；source/profile失配不复用。
- [x] 2.3 （M1）端到端项目验证。依据：ADR-0011开发侧工作模式。交付：真实Python与Rust项目全selector存储/查询测试与README。验证：遍历所有支持事实并逐ID比对构造结果和仓库结果；验证schema、OpenSpec、artifact；如实标注未做私有盲验收。

## ADR-0013 当前约束（2026-11-08）

该提案记录旧完整档案的历史交付。当前新写入使用实体档案，旧档案只读兼容；历史写入场景不重新授权旧profile写入，不能作为新模型的分层组织依据。 依据：`docs/decisions/0013-非DDD语义事实模型.md`。历史执行记录中的DDD或旧模型表述不构成现行约束。本轮只进行文档修订，产品重构完成状态不变。
