# 需求—能力—任务—验收矩阵

以下均为候选/未来验收，不是已运行的产品测试。每行对应delta的WHEN/THEN；任务给候选交付路径、输入、通过/失败和阻塞。

| Issue | 能力 / Requirement | Scenario | 唯一tasks | 主要反例/通过依据 |
| --- | --- | --- | --- | --- |
| #5 | `semantic-analysis-quality` / 可复现评价档案 | 混合组合尚无证据 | `define-semantic-analysis-quality-goals/tasks.md` 1.1 | 评价将该组合标为未验证而不从单语言结果外推支持 |
| #5 | `semantic-analysis-quality` / 全部请求与成功结果分别评价 | 快速缺口响应 | `define-semantic-analysis-quality-goals/tasks.md` 1.1 | 计入请求总体和部分或失败统计，不计为语义完整成功 |
| #5 | `semantic-analysis-quality` / 同质量Token与成本比较 | 热复用没有模型调用 | `define-semantic-analysis-quality-goals/tasks.md` 2.1 | 仅记录该复用场景成本，首次构造和来源变化成本仍独立测量且不能被推断为零 |
| #5 | `semantic-analysis-quality` / 端到端计时与资源归因 | 首次失败后重试成功 | `define-semantic-analysis-quality-goals/tasks.md` 2.1 | 全链路延迟和成本包含失败尝试，单次尝试可另列但不重置逻辑计时或将前缀标作完整成功 |
| #6 | `semantic-fact-orchestration` / 公共语义单点归属 | 多获取器看到同一操作 | `design-semantic-fact-skill-architecture/tasks.md` 1.1 | 复用同一主体身份及类型引用，保留证据与冲突信息而不产生按层副本 |
| #6 | `semantic-fact-orchestration` / 内部范围与投影分离 | 顶层事实依赖外部声明 | `design-semantic-fact-skill-architecture/tasks.md` 2.1 | 记录内部读取理由，仅响应请求所需事实，不自动展开依赖对象或全仓构造 |
| #6 | `semantic-fact-orchestration` / 来源核验结果不得被吞并 | 命中但无法核验来源 | `design-semantic-fact-skill-architecture/tasks.md` 1.1 | 保留事实和核验缺口，不无条件作为当前有效结果或自动覆盖存储 |
| #7 | `semantic-fact-query` / 规范请求不静默扩大 | 同名操作跨项目 | `define-semantic-fact-query-contracts/tasks.md` 1.1 | 只返回歧义及候选定位，依赖该选择的获取不执行 |
| #7 | `semantic-fact-query` / 逐项结果保留独立状态 | 混合结果 | `define-semantic-fact-query-contracts/tasks.md` 2.1 | 分别报告并将总体标为部分，B不能变不存在或完整成功 |
| #7 | `semantic-fact-query` / 展开图有界且不夹带 | 组成存在循环 | `define-semantic-fact-query-contracts/tasks.md` 2.1 | 只跨允许的一条边，后续保留引用而不递归构造响应定义 |
| #7 | `semantic-fact-query` / 语义完成与持久化结果独立 | 完整回答而保存失败 | `define-semantic-fact-query-contracts/tasks.md` 2.1 | 语义维度完成、持久化维度失败、操作汇总部分，不能丢弃已得事实或声称已保存 |
| #8 | `lazy-semantic-fact-construction` / 查询触发具体语义构造 | 尚无查询 | `design-lazy-semantic-fact-construction/tasks.md` 1.1 | 不构造具体E0–E4语义内容或后台遍历全仓 |
| #8 | `lazy-semantic-fact-construction` / 必要依赖有理由与停止边界 | 混合边界不能解析 | `design-lazy-semantic-fact-construction/tasks.md` 1.1 | 保留已有证据、指出边界缺口并停止该分支，不无限扫描或猜定契约 |
| #8 | `lazy-semantic-fact-construction` / 共享成果而不重复全量模型 | 两层共享来源 | `design-lazy-semantic-fact-construction/tasks.md` 2.1 | 核有效性和适用后复用该成果，不因层号再次全量模型通读 |
| #8 | `lazy-semantic-fact-construction` / 不完备停止不变成功 | 循环与限额同时存在 | `design-lazy-semantic-fact-construction/tasks.md` 1.1 | 停止调度并保留未决依赖和限额原因，不因图已去重声称完成 |
| #8 | `lazy-semantic-fact-construction` / 取消不污染共享成果 | 取消一个共享订阅 | `design-lazy-semantic-fact-construction/tasks.md` 2.1 | 解除该查询订阅，其他查询继续；未核验或发布未定的结果不作有效命中 |
| #9 | `incremental-semantic-fact-storage` / 语义去重不改变身份 | 补充证据 | `design-incremental-semantic-fact-storage/tasks.md` 1.1 | 仅新增证据及关联，保持原主体/主张身份而不重复保存 |
| #9 | `incremental-semantic-fact-storage` / 变化政策不隐式决定 | 同主体源码已变 | `design-incremental-semantic-fact-storage/tasks.md` 1.1 | 明确变化和需政策处理，不静默跳过或执行upsert |
| #9 | `incremental-semantic-fact-storage` / 幂等与引用一致发布 | 中断后重试 | `design-incremental-semantic-fact-storage/tasks.md` 2.1 | 重读已发布结果且只补未发布内容，完整性保持；不重复主张或暴露悬空引用；循环内部引用单元未发布时整体不可见 |
| #9 | `incremental-semantic-fact-storage` / 补证不吞适用与覆盖差异 | 相同主张不同target | `design-incremental-semantic-fact-storage/tasks.md` 1.1 | 保留各自条件和证据范围，不因相同值跳过必要内容或合成完整性 |
| #10 | `semantic-acquisition-capabilities` / 能力证据与支持承诺分开 | 只有文档能力 | `survey-semantic-acquisition-capabilities/tasks.md` 1.1 | 仅记为文档候选，不宣称本Skill或混合边界已验证支持 |
| #10 | `semantic-acquisition-capabilities` / 适配不损身份与来源 | 目标配置缺失 | `survey-semantic-acquisition-capabilities/tasks.md` 2.1 | 保留配置缺口，不用host默认配置证明目标语义 |
| #10 | `semantic-acquisition-capabilities` / 确定性成果和局部模型分工 | 解析工具需执行项目插件 | `survey-semantic-acquisition-capabilities/tasks.md` 2.1 | 停止该路径并报告能力/权限缺口，选择获准且保持质量的替代或部分响应 |
| #11 | `token-efficient-semantic-extraction` / 模型参与须有必要性 | 结构事实可直接转换 | `minimize-semantic-extraction-tokens/tasks.md` 1.1 | 经公共契约转换而不默认再让模型阅读整包或逐层重提 |
| #11 | `token-efficient-semantic-extraction` / 上下文最小化保持必要语义 | 局部变化影响未知 | `minimize-semantic-extraction-tokens/tasks.md` 1.1 | 扩大有理由核验或报告影响缺口，不能仅重提本文件就宣称全请求完整 |
| #11 | `token-efficient-semantic-extraction` / 收益须同质量全链路证实 | 模型核验失败重试 | `minimize-semantic-extraction-tokens/tasks.md` 2.1 | 两次输入输出及核验成本全部归原请求，不只报告成功那次成本 |
| #12 | `semantic-fact-coordination` / 来源核验与提交基点一致 | 构造后来源变化 | `design-semantic-fact-coordination/tasks.md` 1.1 | 报告变化并拒绝以旧基点作为当前有效发布，不静默覆盖或盲复用 |
| #12 | `semantic-fact-coordination` / 共享执行保持独立订阅与范围 | 相同主体不同target | `design-semantic-fact-coordination/tasks.md` 1.1 | 不将不等价语义工作合并，分别核验并保持各自响应范围 |
| #12 | `semantic-fact-coordination` / 失败恢复不伪造持久化成功 | 保存断连结果未知 | `design-semantic-fact-coordination/tasks.md` 2.1 | 先核已发布内容，重用仍有效成果只补缺失，不立即重复模型全读或声称保存成功 |
| #12 | `semantic-fact-coordination` / 观测可归因且区分证据种类 | 失败后局部重试 | `design-semantic-fact-coordination/tasks.md` 3.1 | 保留首次及重试成本和原因归原请求，不能只呈现最后成功尝试 |
| #12 | `semantic-fact-coordination` / 代际取消不污染新工作 | 最后退订后新订阅到来 | `design-semantic-fact-coordination/tasks.md` 1.1 | 为新订阅保留独立新代，旧代取消/晚到结果不得影响新代 |
| #12 | `semantic-fact-coordination` / 共享成本只计实际调用一次 | 两个订阅共享一次模型调用 | `design-semantic-fact-coordination/tasks.md` 3.1 | 全局实际Token计一次，各请求延迟及受益分别列出 |
| #12 | `semantic-fact-coordination` / 一致性能力不足显式降级 | 外部来源没有原子核验能力 | `design-semantic-fact-coordination/tasks.md` 2.1 | 只报告所见观察边界，若请求需强一致则保持缺口而不冒充成功 |

## 固定基线与全局目标

| 约束/目标 | 归属与验证 |
| --- | --- |
| 五层非树、同主体单身份、跨层类型引用 | 主规格semantic-fact-model；#3目录与公共校验，#6跨适配身份负例 |
| 默认顶层、仅明确展开、状态区别 | 主规格semantic-fact-query四项 → #7具体请求例与投影任务；#8不将响应深度当内部闭包 |
| 按查询构造 / 仅保存未存内容 | #8触发停止、#9重复/补证/冲突；同身份变化D03未决 |
| 性能/质量/资源/存储/扩展维护 | #5档案、总体分母、端到端指标；#6可替换职责、#10能力扩展、#12恢复/观测；数值D02待定 |
| 跨语言含混合、host/target分离 | #5组合证据、#10R01–06与参数矩阵；未运行均unknown，不宣称全面支持 |
| 实际Token最小化 | #11每机制工作减量/失效、A/B/C同质量对照；#8/#9/#10/#12协作，非预算替代 |
| 不开发、不归档、不自动触发 | AGENTS/planning-mode；变更文件范围审计，正式基线/产品/维护代码字节不变 |

## 验证层次

规划严格校验仅验证工件结构。独立Battle/reviewer检查语义一致性；未来产品任务验证行为、质量/性能/Token。文档能力≠组合验证；无任何产品运行或收益数据。

## #3逐项继承映射

本集合直接继承[模型A完整review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md)的22项Requirement—任务—候选验收映射（公共模型14项、算法描述8项），不复制第二套计划。模型A同时包含query delta的形状约束，见对应spec文件；本期#7补的是执行契约，不能用形状fixture声称查询已实现。下表逐项链接原要求与任务，验收命令仍按原tasks，均未运行。

| #3 Requirement | 定义及确认边界 | 唯一任务 | 未来验收 |
| --- | --- | --- | --- |
| semantic-fact-model / 五层语义组织 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.2 | test_catalog_roles_and_layers |
| semantic-fact-model / 分层不强制包含或细化 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.2,2.2 | test_cross_layer_entry_binding |
| semantic-fact-model / 单一主体身份与跨层引用 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.1 | test_same_declaration_two_contexts |
| semantic-fact-model / 显式工程边界与组织关系 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.1,2.2 | test_undecided_project_mapping |
| semantic-fact-model / 目标配方别名与交付边界 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 2.2 | test_alias_recipe_observation |
| semantic-fact-model / 需求解析与范围位置正交 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 2.3 | test_dependency_scope_orthogonal |
| semantic-fact-model / 稳定身份与上下文保持引用 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.1 | test_context_overlap_cases |
| semantic-fact-model / 类型化事实与分阶段校验 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 2.1 | test_invalid_role_and_internal_ref |
| semantic-fact-model / 可查询的类型与谓词目录 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.2 | test_catalog_roles_and_layers |
| semantic-fact-model / 组成关联与引用边界 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.2,2.1,4.1 | test_nested_payload_rejected |
| semantic-fact-model / 主张模态证据与推导可追溯 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 3.1 | test_modes_not_truth_rank |
| semantic-fact-model / 覆盖与否定的边界 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 3.1 | test_negative_requires_closed_scope |
| semantic-fact-model / 状态维度独立表达 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 3.1 | test_acquired_ref_only |
| semantic-fact-model / 条件可满足性与循环诊断 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 2.3 | test_cycle_satisfiability |
| algorithm-description / 操作契约独立表达 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.1 | test_numeric_resource_concurrency_unknown |
| algorithm-description / 算法描述身份目的与实现关联 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.1 | test_algorithm_multi_project |
| algorithm-description / 结构化行为体与引用完整性 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.1 | test_algorithm_kinds_and_refs |
| algorithm-description / 求值错误资源与并发语义保持 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.1 | test_numeric_resource_concurrency_unknown |
| algorithm-description / 宏生成与注解的分阶段来源 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.2 | test_macro_unexpanded_and_repeated |
| algorithm-description / 匿名操作闭包与绑定语义 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.2 | test_closure_and_conditional_binding |
| algorithm-description / 伪代码是可追溯投影 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.3 | test_projection_preserves_behavior |
| algorithm-description / 来源行为覆盖与投影分别验证 | [原映射](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.3 | test_deleted_failure_exit_detected |
