# OpenSpec 提案与语义实体领域模型对齐实施计划

> **执行方式：** 本代理按任务顺序直接修改文档，最后进行一次整体审查。

**目标：** 检查所有活动 OpenSpec 提案，更新受 ADR-0012 影响的提案与规格，并记录未受影响提案的审查结论。

**架构：** ADR-0012 与 `docs/domain/semantic-entity-model.md` 是领域基准；E0–E4 仍是可组合观察视角，源码构造与测试入口具有独立身份。保留已完成/历史提案的原始语境，仅为当前仍有效的要求补充取代关系和衔接说明。

**技术栈：** Markdown、OpenSpec CLI、仓库既有规格校验。

**依据：** `docs/decisions/0012-semantic-entity-centered-domain-model.md`、`docs/domain/semantic-entity-model.md`、`openspec/changes/redesign-semantic-entity-domain-model/`。

## 全局约束

- 所有新增或改写的说明文字使用中文；模型名、路径和命令保留代码标识。
- 不改写已接受 ADR-0001 至 ADR-0011 的历史决定；按 ADR-0012 的精确替代边界说明其当前效力。
- 不修改实现代码、测试行为或运行时契约。
- 不把 E0–E4 观察视角误写成实体类别、实体身份、业务边界或包含关系。
- 不把类、函数、字段、宏、泛型、测试函数等源码构造直接等同语义实体。
- 每个活动提案均须有审查处置；无影响也要明确记为“无需模型变更”并说明理由。

## 审查关注点

- 已完成提案的历史需求是否被误删或错误地重新打开。
- 源码类/函数查询是否保留为实现映射视图，而不是新领域模型的根分类。
- E0–E4 是否只在事实观察、工具覆盖和质量评估需要时保留。
- 旧 `semantic-fact-model-1`、M1 与新 `semantic-entity-model-1` 的迁移/只读边界是否一致。
- 协调、按需构造、存储和 token 优化提案是否共享同一语义实体身份与覆盖概念。

---

### 任务 1：建立全提案影响矩阵

**文件：**
- 新建：`docs/development/reviews/semantic-facts/semantic-entity-proposal-alignment.md`
- 修改：`docs/superpowers/plans/2026-11-07-align-proposals-with-semantic-entity-domain-model.md`

**步骤：**
- [x] 列出 `openspec/changes/` 下全部16项非归档提案。
- [x] 对每项标记：需实质更新、仅添加当前基准说明、或无领域模型影响。
- [x] 记录所依据的 ADR-0012 条款和将修改的具体文件。
- [x] 检查列表覆盖率与文件系统提案数一致。

### 任务 2：修订受影响提案（14项）

**文件范围：**
`define-layered-semantic-fact-model`、`define-semantic-analysis-quality-goals`、`define-semantic-fact-query-contracts`、`design-lazy-semantic-fact-construction`、`design-incremental-semantic-fact-storage`、`extend-layered-semantic-store`、`design-semantic-fact-skill-architecture`、`design-semantic-fact-coordination`、`enable-issue-driven-development`（仅Token指标对象）、`minimize-semantic-extraction-tokens`、`survey-semantic-acquisition-capabilities`、`plan-semantic-fact-skill`、`review-semantic-planning-readiness` 及当前实体模型提案。

**步骤：**
- [x] 将仍有效的模型/查询/存储要求改为语义实体、实体属性、类型化关系、证据、覆盖和实现/验证映射为中心。
- [x] 对 E0–E4 保留观察维度，不从层级推身份或组成。
- [x] 保留旧提案的历史交付范围，通过明确“被 ADR-0012 取代/需由当前提案完成”的文字消除现行冲突。
- [x] 更新相关 `proposal.md`、`design.md`、`specs/`、`tasks.md` 中的陈旧主张，并保持 OpenSpec delta 自洽。

### 任务 3：记录无影响提案与整体复核

**步骤：**
- [x] 对交付门禁与工作区初始化等不定义领域模型的提案记录无需变更及理由；Issue工作流要求保持不变，其Token指标对象随模型更新。
- [x] 复核影响矩阵中的每个文件处置与实际 diff 一致。
- [x] 运行受影响 change 的严格校验及全库 `npm run validate`。
- [x] 运行全仓陈旧模型表述搜索，剩余命中已逐项识别为历史记录、观察视角、兼容边界或源码实现参考。
