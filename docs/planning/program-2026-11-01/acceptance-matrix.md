# 需求—能力—任务—验收矩阵（当前）

正式scope仅包含用户明确确认项，其他新能力仍为候选；所有产品任务未执行。原2026-11-01变化场景已按ADR-0006收敛，历史Battle不是当前规范。

| Issue | 能力 / Requirement | Scenario | 唯一tasks | 通过依据 |
| --- | --- | --- | --- | --- |
| #5 | `semantic-analysis-quality` / 可复现评价档案 | 混合组合尚无证据 | `define-semantic-analysis-quality-goals/tasks.md` 1.1 | 评价将该组合标为未验证而不从单语言结果外推支持 |
| #5 | `semantic-analysis-quality` / 全部请求与成功结果分别评价 | 快速缺口响应 | `define-semantic-analysis-quality-goals/tasks.md` 1.1 | 计入请求总体和部分或失败统计，不计为语义完整成功 |
| #5 | `semantic-analysis-quality` / 同质量Token与成本比较 | 热复用没有模型调用 | `define-semantic-analysis-quality-goals/tasks.md` 2.1 | 仅记录该复用场景成本，首次构造和同次后续查询补充成本仍独立测量且不能被推断为零 |
| #5 | `semantic-analysis-quality` / 端到端计时与资源归因 | 首次失败后重试成功 | `define-semantic-analysis-quality-goals/tasks.md` 2.1 | 全链路延迟和成本包含失败尝试，单次尝试可另列但不重置逻辑计时或将前缀标作完整成功 |
| #5 | `semantic-analysis-scope` / 首期源代码语言范围 | 首期语言范围进入规划 | `define-semantic-analysis-quality-goals/tasks.md` 1.1 | 以Rust和Python为已确认语言范围，版本、混合边界及平台组合仍按各自确认与验证记录确定 |
| #5 | `semantic-analysis-scope` / Skill宿主与分析工具运行平台一致 | 在不同宿主平台选择分析工具 | `define-semantic-analysis-quality-goals/tasks.md` 1.1 | 选择与该Skill运行期平台一致的分析工具，不能把其他平台的工具默认视为本机可运行 |
| #5 | `semantic-analysis-scope` / 项目平台依据构造编译环境 | 宿主与项目设定平台不同 | `define-semantic-analysis-quality-goals/tasks.md` 1.1 | 分析工具运行平台仍与Linux宿主一致，项目语义按其Windows构造／编译环境解释，不因host为Linux而改作Linux项目 |
| #5 | `semantic-analysis-scope` / 负载范围依据实际测试确定 | 当前尚无实际负载测试 | `define-semantic-analysis-quality-goals/tasks.md` 1.1, 2.1 | 负载范围保持延期，不猜定规模且不因此单独阻塞当前规划；实际分析测试后再据结果记录适用范围 |
| #5 | `semantic-analysis-scope` / 单次分析期间项目保持不变 | 固定项目输入上的后续查询 | `define-semantic-analysis-quality-goals/tasks.md` 1.1, 2.1 | 在该分析输入下复用适用成果并补充所需内容，不要求通过项目热更新流程才能取得新增事实 |
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
| #9 | `incremental-semantic-fact-storage` / 固定输入内补充不等于来源更新 | 同一操作按后续请求补充契约 | `design-incremental-semantic-fact-storage/tasks.md` 1.1 | 保持主体身份，复用已存内容并保存新增事实/证据，不重复保存原事实或启动源码热更新 |
| #9 | `incremental-semantic-fact-storage` / 幂等与引用一致发布 | 中断后重试 | `design-incremental-semantic-fact-storage/tasks.md` 2.1 | 重读已发布结果且只补未发布内容，完整性保持；不重复主张或暴露悬空引用；循环内部引用单元未发布时整体不可见 |
| #9 | `incremental-semantic-fact-storage` / 补证不吞适用与覆盖差异 | 相同主张不同target | `design-incremental-semantic-fact-storage/tasks.md` 1.1 | 保留各自条件和证据范围，不因相同值跳过必要内容或合成完整性 |
| #10 | `semantic-acquisition-capabilities` / 能力证据与支持承诺分开 | 只有文档能力 | `survey-semantic-acquisition-capabilities/tasks.md` 1.1 | 仅记为文档候选，不宣称本Skill或混合边界已验证支持 |
| #10 | `semantic-acquisition-capabilities` / 适配不损身份与来源 | 目标配置缺失 | `survey-semantic-acquisition-capabilities/tasks.md` 2.1 | 保留配置缺口，不用host默认配置证明目标语义 |
| #10 | `semantic-acquisition-capabilities` / 确定性成果和局部模型分工 | 解析工具需执行项目插件 | `survey-semantic-acquisition-capabilities/tasks.md` 2.1 | 停止该路径并报告能力/权限缺口，选择获准且保持质量的替代或部分响应 |
| #11 | `token-efficient-semantic-extraction` / 模型参与须有必要性 | 结构事实可直接转换 | `minimize-semantic-extraction-tokens/tasks.md` 1.1 | 经公共契约转换而不默认再让模型阅读整包或逐层重提 |
| #11 | `token-efficient-semantic-extraction` / 上下文最小化保持必要语义 | 后续查询依赖仍不明确 | `minimize-semantic-extraction-tokens/tasks.md` 1.1 | 扩大有理由核验或报告影响缺口，不能仅取得本文件的局部信息就宣称全请求完整 |
| #11 | `token-efficient-semantic-extraction` / 收益须同质量全链路证实 | 模型核验失败重试 | `minimize-semantic-extraction-tokens/tasks.md` 2.1 | 两次输入输出及核验成本全部归原请求，不只报告成功那次成本 |
| #12 | `semantic-fact-coordination` / 固定分析输入下复用与提交一致 | 同次分析多次查询共享成果 | `design-semantic-fact-coordination/tasks.md` 1.1 | 复用相应成果并只补必要缺口，不要求为每次查询重建来源更新闭环 |
| #12 | `semantic-fact-coordination` / 共享执行保持独立订阅与范围 | 相同主体不同target | `design-semantic-fact-coordination/tasks.md` 1.1 | 不将不等价语义工作合并，分别核验并保持各自响应范围 |
| #12 | `semantic-fact-coordination` / 失败恢复不伪造持久化成功 | 保存断连结果未知 | `design-semantic-fact-coordination/tasks.md` 2.1 | 先核已发布内容，重用仍有效成果只补缺失，不立即重复模型全读或声称保存成功 |
| #12 | `semantic-fact-coordination` / 观测可归因且区分证据种类 | 失败后局部重试 | `design-semantic-fact-coordination/tasks.md` 3.1 | 保留首次及重试成本和原因归原请求，不能只呈现最后成功尝试 |
| #12 | `semantic-fact-coordination` / 代际取消不污染新工作 | 最后退订后新订阅到来 | `design-semantic-fact-coordination/tasks.md` 1.1 | 为新订阅保留独立新代，旧代取消/晚到结果不得影响新代 |
| #12 | `semantic-fact-coordination` / 共享成本只计实际调用一次 | 两个订阅共享一次模型调用 | `design-semantic-fact-coordination/tasks.md` 3.1 | 全局实际Token计一次，各请求延迟及受益分别列出 |
| #12 | `semantic-fact-coordination` / 已知输入归属不一致不得混用 | 成果无法确认属于本分析输入 | `design-semantic-fact-coordination/tasks.md` 2.1 | 不无条件复用该成果，报告相应缺口或在本输入下按需取得，不自动执行跨次覆盖更新 |

## 固定模型与查询基线

五层非树、同主体单身份与跨层类型引用继续由semantic-fact-model正式规格约束；默认顶层最小响应、仅明确展开、状态区别继续由semantic-fact-query四项正式要求约束，#7 tasks 1.1/2.1提供对应正反例。新增scope正式规格仅确认语言、平台定义、负载延期与单次固定项目输入，见ADR-0003至0006。

## #3逐项继承（唯一任务仍在原变更）

| #3 Requirement | 原依据 | 唯一任务 | 未来验收 |
| --- | --- | --- | --- |
| semantic-fact-model / 五层语义组织 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.2 | test_catalog_roles_and_layers |
| semantic-fact-model / 分层不强制包含或细化 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.2,2.2 | test_cross_layer_entry_binding |
| semantic-fact-model / 单一主体身份与跨层引用 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.1 | test_same_declaration_two_contexts |
| semantic-fact-model / 显式工程边界与组织关系 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.1,2.2 | test_undecided_project_mapping |
| semantic-fact-model / 目标配方别名与交付边界 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 2.2 | test_alias_recipe_observation |
| semantic-fact-model / 需求解析与范围位置正交 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 2.3 | test_dependency_scope_orthogonal |
| semantic-fact-model / 稳定身份与上下文保持引用 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.1 | test_context_overlap_cases |
| semantic-fact-model / 类型化事实与分阶段校验 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 2.1 | test_invalid_role_and_internal_ref |
| semantic-fact-model / 可查询的类型与谓词目录 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.2 | test_catalog_roles_and_layers |
| semantic-fact-model / 组成关联与引用边界 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.2,2.1,4.1 | test_nested_payload_rejected |
| semantic-fact-model / 主张模态证据与推导可追溯 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 3.1 | test_modes_not_truth_rank |
| semantic-fact-model / 覆盖与否定的边界 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 3.1 | test_negative_requires_closed_scope |
| semantic-fact-model / 状态维度独立表达 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 3.1 | test_acquired_ref_only |
| semantic-fact-model / 条件可满足性与循环诊断 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 2.3 | test_cycle_satisfiability |
| algorithm-description / 操作契约独立表达 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.1 | test_numeric_resource_concurrency_unknown |
| algorithm-description / 算法描述身份目的与实现关联 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.1 | test_algorithm_multi_project |
| algorithm-description / 结构化行为体与引用完整性 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.1 | test_algorithm_kinds_and_refs |
| algorithm-description / 求值错误资源与并发语义保持 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.1 | test_numeric_resource_concurrency_unknown |
| algorithm-description / 宏生成与注解的分阶段来源 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.2 | test_macro_unexpanded_and_repeated |
| algorithm-description / 匿名操作闭包与绑定语义 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.2 | test_closure_and_conditional_binding |
| algorithm-description / 伪代码是可追溯投影 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.3 | test_projection_preserves_behavior |
| algorithm-description / 来源行为覆盖与投影分别验证 | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 4.3 | test_deleted_failure_exit_detected |

## 全局验收边界

#5拥有工作负载/质量/性能/资源和Token测量口径；#10区分语言/混合边界、host与项目构造环境，文档能力不等验证；#11按相同必要语义/质量/证据比较三组实际模型工作，计失败重试；#12共享物理Token单计、订阅独立、保存失败两维呈现。固定项目下事实按需增加，不能以完整性虚报省Token。负载范围实测后确定，不阻塞当前规划冻结；跨次变化策略不自动纳入同次分析验收。所有运行收益均未实测。
