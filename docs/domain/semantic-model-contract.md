# 语义模型契约说明

## 状态与范围

当前领域模型以`semantic-entity-model-1`为权威profile，包含语义实体、实体属性、类型化关系、主张、证据、覆盖、源码构造、实现映射和测试验证映射。项目及其语义模块也按实体表达；E0–E4保留为事实观察视角，不是实体类别或身份组成部分。

`m1-project-discovery-1`继续作为独立的窄范围项目/workspace发现profile。`semantic-fact-model-1`现为旧完整档案只读兼容格式和迁移输入；运行时`commit_bundle`拒绝新写入，`read_bundle`/`query_bundle`保留旧档案读取能力。默认CLI查询和算法档案写入均转向`semantic-entity-model-1`，M1接口不变。实现与切换验证记录见`openspec/changes/redesign-semantic-entity-domain-model/tasks.md`及同目录实体模型验证报告。

既有`project_query_to_semantic_model`把Python/Rust分析器当时支持的事实投影到旧`semantic-fact-model-1`档案。固定Click和regex检出曾分别产生23,779与54,313条旧事实；这些数量只表示该分析器的支持范围，不表示项目全部语义。Cargo元数据不可用时仍有明确缺口。旧校验可检查结构、引用和声明的不变量，不能证明源码解释为真、完整还原E0–E4内容或运行时行为正确。

## 身份术语

`SemanticEntityRef`标识可独立引用的语义实体，身份由authority、domainId和localId组成，kind使用类型目录约束。实体身份不包含路径、名称、层号、提交、内容摘要或工具节点ID。注册表的sourceKey只用于将新的来源证据关联到已登记实体；冲突时报告诊断，不按名称或路径猜测。

`SourceConstruct`拥有独立于实体的源码身份，保存语言、语法种类、源码位置、声明形状和源码包含关系。`SourceDeclaration`是旧M1 profile的主体类别；不能仅凭该旧身份将声明提升为语义实体。软件包、workspace成员、目录和源码模块也不自动成为领域项目、模块或能力。

## 校验与证据边界

`contracts/semantic-model/`中的实体模式和目录规定结构化记录；`src/c2s_semantic_contract/validation.py`负责实体身份、属性、关系端点、源码映射、证据和覆盖等局部一致性检查。Skill构造器应保留分析输入指纹、来源摘要和原始获取元数据，空结果不得转换成全称否定主张。契约有效不等于来源判断为真；覆盖仅对实际提交的输入、请求和分析配置有效。共享工作区测试是公开实现证据，不构成独立验收。

当前方法与目标依据ADR-0013：不采用DDD；语义实体是事实查询模型，源码构造是独立实现参考。历史原件和旧决策保留来源记录，不作为恢复DDD约束的依据。
