# 语义实体模型变更对 OpenSpec 提案的影响核对

核对日期：2026-11-07。权威依据：ADR-0012、`docs/domain/semantic-entity-model.md`及`openspec/changes/redesign-semantic-entity-domain-model/`。

本表覆盖`openspec/changes/`中全部16项非归档提案。旧ADR和已形成的提案记录保留其发生时的历史语境；“受影响”表示其仍有效的需求、设计、规格或后续工作需要按新领域模型解释/对齐，不表示旧提交未曾成立。E0–E4保留为事实观察视角；语义实体才是统一身份主体，属性、类型化关系、证据、覆盖、源码实现映射和测试验证关系均围绕实体表达。源码种类不能自动确定业务边界或实体类型。

| OpenSpec 提案 | 核对结论 | 应对文件和调整 | 理由 |
| --- | --- | --- | --- |
| `define-independent-ddd-delivery` | 无领域模型影响 | 不修改模型需求；其门禁和角色独立要求继续适用 | 只定义交付/验收边界，不规定事实模型 |
| `define-layered-semantic-fact-model` | 历史模型基线被精确替代 | proposal、design、模型/query增量及任务注记ADR-0012替代范围；保留E视角、条件、证据等仍有效要求 | 原提案曾将E0–E4作为主组织方式，当前仅为观察视角 |
| `define-semantic-analysis-quality-goals` | 部分影响 | proposal、scope/quality delta、评价场景明确以请求的语义实体/属性/关系/映射和证据覆盖评价，不以“各层均有记录”充完整 | 质量方法不变，评价对象和完整性边界需更新 |
| `define-semantic-fact-query-contracts` | 直接影响 | proposal/design/query spec/tasks把实体、属性、关系、实现、验证作为查询目标；类/函数只作为源码构造视图 | 旧查询示例以类、函数作为领域对象主分类 |
| `design-incremental-semantic-fact-storage` | 边界需澄清 | proposal/design/spec/tasks区分M1受限profile、旧完整profile兼容和实体档案；实体注册身份与证据补充以稳定实体身份为对象 | 增量去重规则仍适用，但不能以源码事实/层号替代实体身份 |
| `design-lazy-semantic-fact-construction` | 直接影响 | proposal/design/spec/tasks以实体目标与属性/关系/实现/测试覆盖缺项规划；源码构造解析可作依赖工作，不是语义结果 | 原提案把E0与E2–E4语义构造用作工作边界 |
| `design-semantic-fact-coordination` | 部分影响 | proposal/design/spec/tasks说明共享工作按实体身份、请求项、条件和覆盖适用性协调；M1接口自身保持独立 | 请求协调机制仍适用，需防止层级成为共享身份键 |
| `design-semantic-fact-skill-architecture` | 直接影响 | proposal/design/spec明确实体模型、来源解析、语义构造/映射、存储、查询投影的职责及单一身份归属 | 原提案以“已选模型A/语义层”作为架构假设 |
| `enable-issue-driven-development` | 部分影响 | 仅调整非功能指标中Token工作量的度量对象；Issue入口、授权与工作流要求不变 | 原指标以“分层语义事实提取”为度量对象，现改为按请求实体及其所需事实衡量 |
| `extend-layered-semantic-store` | 历史实现范围转为兼容边界 | proposal/design/spec/tasks标明`semantic-fact-model-1`是旧兼容profile；其历史交付保持可读，实体档案切换由当前实体模型提案控制 | 旧提案将旧完整profile作为公开仓储权威档案 |
| `initialize-sdd-ddd-workspace` | 无领域模型影响 | 不修改模型；更新审阅矩阵注明无运行时/领域需求影响 | 只初始化开发工具和工作记录 |
| `minimize-semantic-extraction-tokens` | 部分影响 | proposal/design/spec/tasks按实体请求、属性/关系缺口、证据/实现映射和真实复用范围描述Token工作量；E视角仅作比较切面 | 优化目标不变，不能把E层或源码元素数当作语义需求计量单位 |
| `plan-semantic-fact-skill` | 直接影响 | proposal/design/tasks把语义实体模型纳入已变化的正式基线及跨提案审核 | 原文字称正式模型/查询基线不变，现已过时 |
| `redesign-semantic-entity-domain-model` | 当前权威实施提案 | 增加本次提案影响核对任务及完整矩阵链接；其领域语义要求维持现状 | 本提案是ADR-0012的实现来源 |
| `review-semantic-planning-readiness` | 直接影响 | proposal/design/tasks增加逐项核对全部提案、解决冲突和保留历史边界 | 原范围未纳入本次已批准模型变更后的提案回查 |
| `survey-semantic-acquisition-capabilities` | 直接影响 | proposal/design/spec/tasks按语义构造需要的信息覆盖选择工具组合；工具输出解析器把数据转换为源码构造/证据供实体构造器使用，E层不作工具选择主键 | 工具能力矩阵必须服务于实体事实构造的信息需要 |

## 一致性验收

- 每个非归档提案均在上表出现一次，无遗漏、重复或未判定项。
- 受影响的原始提案仍可解释其历史交付；当前有效语义以ADR-0012和实体重构规格为准。
- 不受影响提案没有被人为加上产品语义要求。
- 旧完整档案的兼容/迁移状态不因本次文档对齐而被误报为已切换；切换任务仍由实体模型实现提案管理。


## 非OpenSpec历史提案原件

| 文件 | 处置 | 说明 |
| --- | --- | --- |
| `docs/domain/proposals/language-independent-layered-semantic-model.md` | 保持原件不变 | 来源摘要在`docs/session/artifact-manifest.json`中固定哈希；当前效力由`docs/domain/proposals/README.md`说明。 |
| `docs/domain/drafts/software-semantic-domain-model.md` | 保持原件不变 | 同属固定哈希的历史导入材料；不改写原证据，当前基准以ADR-0012及实体模型文档为准。 |
