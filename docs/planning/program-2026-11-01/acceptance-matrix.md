# 当前需求—能力—场景—唯一任务矩阵

用户确认范围见ADR-0001至0008；当前顶层=符合本次请求要求的顶层语义事实。正式规格仅固化明确确认，其他delta/设计仍为技术候选。所有产品任务未执行，本表仅索引，不是第二套计划。

## 独立交付及版本追溯（ADR-0008）

| 确认依据 | 能力 / Requirement | Scenario | 唯一tasks | 通过依据 |
| --- | --- | --- | --- | --- |
| U02 | independent-delivery / 五类交付职责独立 | 候选实现交接 | define-independent-ddd-delivery 1.1、2.2/2.3及原产品tasks | 五角色独立输入/身份/工件输出，编码者不写测试/改验收结论 |
| U01/U02 | independent-delivery / 独立测试对编码角色不可见 | 仅具备共享工作区；向编码角色反馈失败 | define-independent-ddd-delivery 2.2/2.3 | 编码及candidate进程越权访问被拒，反馈保护隐藏用例；当前无隔离实证则blocked |
| U01 | independent-delivery / 验收用例依据讨论中的真实项目 | 真实项目尚未实际测试 | define-independent-ddd-delivery 2.1及原产品tasks | 固定regex/click来源，实际运行后才报覆盖；20文件研究不冒完整测试 |
| U03/U04 | independent-delivery / 授权范围内持续推进 | 规划完成尚未获开发批准；已授权里程碑具备推进条件 | define-independent-ddd-delivery 1.2、2.3 | 不绕过另批开发、Issue不触发、未部署不称后台运行 |
| U03 | product-versioning / 当前产品版本固定主版本为零 | 递增产品版本 | define-independent-ddd-delivery 2.1/2.3 | 产品0.b.c，当前不改工具/契约版本、不创建产品发布 |

以上新增5项delta，原#5–#12的50项映射及#3继承映射保留。实际隐藏suite的具体用例不进入公开矩阵。

## 用户七点及补充追溯

| 用户确认 | 正式能力 | 执行职责与未来验证 |
| --- | --- | --- |
| 1及补充：本次请求顶层完整、不递归 | semantic-fact-query：默认顶层/目标查询/类成员函数查询 | #7 tasks 1.1/2.1，四类典型问题、完整范围与无递归夹带 |
| 2：指定目录内都分析 | semantic-analysis-scope：指定目录内内容 | #7 1.1、#8 1.1、#10 2.1，嵌套/测试/示例不静默排除，范围全不等于预先全量构造 |
| 3：报告和结构数据 | semantic-fact-query：双输出 | #7 3.1，同一结果/身份/缺口原因一致 |
| 4：查询触发，同主体只补缺 | lazy-semantic-fact-construction两项 | #8 1.1/2.1，首次未分析、后续补充、重复查询无重复全量工作 |
| 5：缺口如实报告原因 | semantic-fact-query状态/原因；quality如实报告 | #7 2.1/3.1与#5 1.1，获取不到不虚构/不说不存在 |
| 6：必要分析操作由设计执行 | semantic-analysis-scope操作授权 | #10 1.1/2.1，必要构建/宏操作可安排，项目不变，环境失败说明原因 |
| 7：不严格定义正确性，性能Token前后自评 | semantic-analysis-quality两项 | #5 1.1/2.1、#11 2.1，不强加金标/SLO；前后结果/缺口/耗时/实际Token一起报告 |

## 当前delta逐项映射

#10本轮仍为原三项Requirement，补入Skill/接口候选、有限结果补取、默认忽略和索引/内部成本Scenario；文档取证归其tasks 0.1–0.3，未来试验归3.1–3.3，产品交付仍归1.1/2.1。所选路径完整性/来源/副作用未实证不冻结；新增场景追溯见`docs/development/reviews/issues/10/acquisition-survey-2026-11-02/report.md`的N01–N09，本矩阵不复制测试或实施待办。

| Issue | 能力 / Requirement | Scenario | 唯一tasks | 通过依据 |
| --- | --- | --- | --- | --- |
| #5 | `semantic-analysis-quality` / 可复现评价档案 | 混合组合尚无证据 | `define-semantic-analysis-quality-goals/tasks.md` 1.1 | 评价将该组合标为未验证而不从单语言结果外推支持 |
| #5 | `semantic-analysis-quality` / 全部请求与成功结果分别评价 | 快速缺口响应 | `define-semantic-analysis-quality-goals/tasks.md` 1.1, 2.1 | 计入请求总体和部分或失败统计，不计为语义完整成功 |
| #5 | `semantic-analysis-quality` / 优化前后Token与成本比较 | 热复用没有模型调用 | `define-semantic-analysis-quality-goals/tasks.md` 2.1 | 仅记录该复用场景成本，首次构造和同次后续查询补充成本仍独立测量且不能被推断为零 |
| #5 | `semantic-analysis-quality` / 端到端计时与资源归因 | 首次失败后重试成功 | `define-semantic-analysis-quality-goals/tasks.md` 2.1 | 全链路延迟和成本包含失败尝试，单次尝试可另列但不重置逻辑计时或将前缀标作完整成功 |
| #5 | `semantic-analysis-quality` / 结果如实报告而不虚报严格正确性 | 无法证明完整行为语义 | `define-semantic-analysis-quality-goals/tasks.md` 1.1 | 报告实际取得内容和无法取得原因，不宣称严格正确或已完整获得，也不要求用户先给出完备语义金标才能查询 |
| #5 | `semantic-analysis-quality` / 性能与Token由优化前后对照评价 | 比较优化前后同一查询 | `define-semantic-analysis-quality-goals/tasks.md` 2.1 | 报告耗时、实际Token及取得内容/缺口的差异，不将省掉所需事实或隐瞒缺口当作优化收益 |
| #5 | `semantic-analysis-scope` / 首期源代码语言范围 | 首期语言范围进入规划 | `define-semantic-analysis-quality-goals/tasks.md` 1.1/2.1 | 以Rust和Python为已确认语言范围，版本、混合边界及平台组合仍按各自确认与验证记录确定 |
| #5 | `semantic-analysis-scope` / Skill宿主与分析工具运行平台一致 | 在不同宿主平台选择分析工具 | `define-semantic-analysis-quality-goals/tasks.md` 1.1/2.1 | 选择与该Skill运行期平台一致的分析工具，不能把其他平台的工具默认视为本机可运行 |
| #5 | `semantic-analysis-scope` / 项目平台依据构造编译环境 | 宿主与项目设定平台不同 | `define-semantic-analysis-quality-goals/tasks.md` 1.1/2.1 | 分析工具运行平台仍与Linux宿主一致，项目语义按其Windows构造／编译环境解释，不因host为Linux而改作Linux项目 |
| #5 | `semantic-analysis-scope` / 负载范围依据实际测试确定 | 当前尚无实际负载测试 | `define-semantic-analysis-quality-goals/tasks.md` 1.1/2.1 | 负载范围保持延期，不猜定规模且不因此单独阻塞当前规划；实际分析测试后再据结果记录适用范围 |
| #5 | `semantic-analysis-scope` / 单次分析期间项目保持不变 | 固定项目输入上的后续查询 | `define-semantic-analysis-quality-goals/tasks.md` 1.1/2.1 | 在该分析输入下复用适用成果并补充所需内容，不要求通过项目热更新流程才能取得新增事实 |
| #5 | `semantic-analysis-scope` / 指定目录内内容纳入分析范围 | 目录包含多个及嵌套项目 | `define-semantic-fact-query-contracts/tasks.md` 1.1；`design-lazy-semantic-fact-construction/tasks.md` 1.1 | 这些内容均在分析范围内，按本次请求取得必要事实；不能静默排除某类目录，不能取得的事实报告原因 |
| #5 | `semantic-analysis-scope` / 必要分析操作由设计选择执行 | 获取事实需要构建或宏相关操作 | `survey-semantic-acquisition-capabilities/tasks.md` 1.1/2.1 | 可按设计执行并保持被分析项目不变；环境或工具不能执行时明确报告获取不到及原因，不假称已执行或已取得 |
| #6 | `semantic-fact-orchestration` / 公共语义单点归属 | 多获取器看到同一操作 | `design-semantic-fact-skill-architecture/tasks.md` 1.1 | 复用同一主体身份及类型引用，保留证据与冲突信息而不产生按层副本 |
| #6 | `semantic-fact-orchestration` / 内部范围与投影分离 | 顶层事实依赖外部声明 | `design-semantic-fact-skill-architecture/tasks.md` 2.1 | 记录内部读取理由，仅响应请求所需事实，不自动展开依赖对象或全仓构造 |
| #6 | `semantic-fact-orchestration` / 来源核验结果不得被吞并 | 命中但无法核验来源 | `design-semantic-fact-skill-architecture/tasks.md` 2.1 | 保留事实和核验缺口，不无条件作为当前有效结果或自动覆盖存储 |
| #7 | `semantic-fact-query` / 查询限定响应事实范围 | 已有事实多于请求所需 | `define-semantic-fact-query-contracts/tasks.md` 1.1, 2.1 | 响应仅包含符合本次请求的信息，不自动附送其他对象或完整实现事实 |
| #7 | `semantic-fact-query` / 默认顶层最小事实集 | 查询项目有哪些类；查询某类有哪些成员 | `define-semantic-fact-query-contracts/tasks.md` 2.1 | 返回该请求范围内取得的类清单及必要顶层信息，缺失项说明原因，不递归展开每个类的成员及实现；返回该请求范围内取得的成员顶层事实并披露缺口，不额外递归展开每个成员的实现或关联类型 |
| #7 | `semantic-fact-query` / 按明确要求展开 | 查询指定成员定义；查询函数如何实现 | `define-semantic-fact-query-contracts/tasks.md` 1.1, 2.1 | 以该成员的定义为本次请求目标返回其顶层事实，不附送整个类或关联类型的递归定义；返回符合该请求的顶层定义/实现事实及缺口，不递归展开被调用函数或无关对象 |
| #7 | `semantic-fact-query` / 未展开与获取状态可区分 | 已获取内容未展开；请求事实无法取得 | `define-semantic-fact-query-contracts/tasks.md` 2.1, 3.1 | 可表达为未展开，不将其标为未获取或不存在；如实报告已得事实、未取得部分及原因；原因本身不明确时也如实说明，不猜作不存在或完整 |
| #7 | `semantic-fact-query` / 规范请求不静默扩大 | 同名操作跨项目 | `define-semantic-fact-query-contracts/tasks.md` 1.1 | 只返回歧义及候选定位，依赖该选择的获取不执行 |
| #7 | `semantic-fact-query` / 逐项结果保留独立状态 | 混合结果 | `define-semantic-fact-query-contracts/tasks.md` 2.1, 3.1 | 分别报告并将总体标为部分，B不能变不存在或完整成功 |
| #7 | `semantic-fact-query` / 顶层结果不夹带递归内容 | 类成员有循环类型引用 | `define-semantic-fact-query-contracts/tasks.md` 2.1 | 返回本次所需成员顶层事实和必要类型引用，不沿循环递归返回全部类型定义 |
| #7 | `semantic-fact-query` / 语义完成与持久化结果独立 | 完整回答而保存失败 | `define-semantic-fact-query-contracts/tasks.md` 3.1 | 语义维度完成、持久化维度失败、操作汇总部分，不能丢弃已得事实或声称已保存 |
| #7 | `semantic-fact-query` / 按请求查询语义实体及源码构造视图 | 从类清单继续查询成员 | `define-semantic-fact-query-contracts/tasks.md` 1.1, 2.1 | 两次请求分别返回各自所需顶层事实，后一次不要求前一次已递归取得所有成员 |
| #7 | `semantic-fact-query` / 同时提供可读报告与结构化数据 | 同一次查询供用户与Skill消费 | `define-semantic-fact-query-contracts/tasks.md` 3.1 | 可读报告和结构数据均保留相同的事实范围与缺口原因，不在其中一种形式虚报完整 |
| #8 | `lazy-semantic-fact-construction` / 查询触发具体语义构造 | 尚无查询 | `design-lazy-semantic-fact-construction/tasks.md` 1.1 | 不构造实体属性、关系、实现/验证映射或后台遍历全仓 |
| #8 | `lazy-semantic-fact-construction` / 必要依赖有理由与停止边界 | 混合边界不能解析 | `design-lazy-semantic-fact-construction/tasks.md` 1.1 | 保留已有证据、指出边界缺口并停止该分支，不无限扫描或猜定契约 |
| #8 | `lazy-semantic-fact-construction` / 共享成果而不重复全量模型 | 两层共享来源 | `design-lazy-semantic-fact-construction/tasks.md` 2.1 | 核有效性和适用后复用该成果，不因共享同一源码证据而重复全量模型通读 |
| #8 | `lazy-semantic-fact-construction` / 不完备停止不变成功 | 循环与限额同时存在 | `design-lazy-semantic-fact-construction/tasks.md` 1.1, 2.1 | 停止调度并保留未决依赖和限额原因，不因图已去重声称完成 |
| #8 | `lazy-semantic-fact-construction` / 取消不污染共享成果 | 取消一个共享订阅 | `design-lazy-semantic-fact-construction/tasks.md` 2.1 | 解除该查询订阅，其他查询继续；未核验或发布未定的结果不作有效命中 |
| #8 | `lazy-semantic-fact-construction` / 查询触发按需分析 | 首次查询尚未分析的函数 | `design-lazy-semantic-fact-construction/tasks.md` 1.1 | 针对该请求开始分析并返回已取得的所需顶层事实；无法取得的部分明确告知原因 |
| #8 | `lazy-semantic-fact-construction` / 同主体后续查询仅补未完成内容 | 函数结构已分析而实现尚未分析 | `design-lazy-semantic-fact-construction/tasks.md` 2.1 | 复用已得结构与适用证据，仅补本次尚未完成内容，不重复全量分析或要求源码发生变化 |
| #9 | `incremental-semantic-fact-storage` / 语义去重不改变身份 | 补充证据 | `design-incremental-semantic-fact-storage/tasks.md` 1.1 | 仅新增证据及关联，保持原主体/主张身份而不重复保存 |
| #9 | `incremental-semantic-fact-storage` / 固定输入内补充不等于来源更新 | 同一操作按后续请求补充契约 | `design-incremental-semantic-fact-storage/tasks.md` 1.1 | 保持主体身份，复用已存内容并保存新增事实/证据，不重复保存原事实或启动源码热更新 |
| #9 | `incremental-semantic-fact-storage` / 幂等与引用一致发布 | 中断后重试 | `design-incremental-semantic-fact-storage/tasks.md` 2.1 | 重读已发布结果且只补未发布内容，完整性保持；不重复主张或暴露悬空引用；循环内部引用单元未发布时整体不可见 |
| #9 | `incremental-semantic-fact-storage` / 补证不吞适用与覆盖差异 | 相同主张不同target | `design-incremental-semantic-fact-storage/tasks.md` 1.1 | 保留各自条件和证据范围，不因相同值跳过必要内容或合成完整性 |
| #10 | `semantic-acquisition-capabilities` / 能力证据与支持承诺分开 | 只有文档能力 | `survey-semantic-acquisition-capabilities/tasks.md` 1.1 | 仅记为文档候选，不宣称本Skill或混合边界已验证支持 |
| #10 | `semantic-acquisition-capabilities` / 适配不损身份与来源 | 目标配置缺失 | `survey-semantic-acquisition-capabilities/tasks.md` 2.1 | 保留配置缺口，不用host默认配置证明目标语义 |
| #10 | `semantic-acquisition-capabilities` / 确定性成果和局部模型分工 | 所需事实依赖宏或构建步骤 | `survey-semantic-acquisition-capabilities/tasks.md` 1.1, 2.1 | 可按设计执行必要操作并保留来源/局限；工具或环境无法执行时报告获取不到及原因，不虚构结果 |
| #11 | `token-efficient-semantic-extraction` / 模型参与须有必要性 | 结构事实可直接转换 | `minimize-semantic-extraction-tokens/tasks.md` 1.1 | 经公共契约转换而不默认再让模型阅读整包或逐层重提 |
| #11 | `token-efficient-semantic-extraction` / 上下文最小化保持必要语义 | 后续查询依赖仍不明确 | `minimize-semantic-extraction-tokens/tasks.md` 1.1 | 扩大有理由核验或报告影响缺口，不能仅取得本文件的局部信息就宣称全请求完整 |
| #11 | `token-efficient-semantic-extraction` / 优化前后全链路对照 | 模型核验失败重试 | `minimize-semantic-extraction-tokens/tasks.md` 2.1 | 两次输入输出及核验成本全部归原请求，不只报告成功那次成本 |
| #12 | `semantic-fact-coordination` / 固定分析输入下复用与提交一致 | 同次分析多次查询共享成果 | `design-semantic-fact-coordination/tasks.md` 1.1 | 复用相应成果并只补必要缺口，不要求为每次查询重建来源更新闭环 |
| #12 | `semantic-fact-coordination` / 共享执行保持独立订阅与范围 | 相同主体不同target | `design-semantic-fact-coordination/tasks.md` 1.1 | 不将不等价语义工作合并，分别核验并保持各自响应范围 |
| #12 | `semantic-fact-coordination` / 失败恢复不伪造持久化成功 | 保存断连结果未知 | `design-semantic-fact-coordination/tasks.md` 2.1 | 先核已发布内容，重用仍有效成果只补缺失，不立即重复模型全读或声称保存成功 |
| #12 | `semantic-fact-coordination` / 观测可归因且区分证据种类 | 失败后局部重试 | `design-semantic-fact-coordination/tasks.md` 3.1 | 保留首次及重试成本和原因归原请求，不能只呈现最后成功尝试 |
| #12 | `semantic-fact-coordination` / 代际取消不污染新工作 | 最后退订后新订阅到来 | `design-semantic-fact-coordination/tasks.md` 1.1 | 为新订阅保留独立新代，旧代取消/晚到结果不得影响新代 |
| #12 | `semantic-fact-coordination` / 共享成本只计实际调用一次 | 两个订阅共享一次模型调用 | `design-semantic-fact-coordination/tasks.md` 3.1 | 全局实际Token计一次，各请求延迟及受益分别列出 |
| #12 | `semantic-fact-coordination` / 已知输入归属不一致不得混用 | 成果无法确认属于本分析输入 | `design-semantic-fact-coordination/tasks.md` 2.1 | 不无条件复用该成果，报告相应缺口或在本输入下按需取得，不自动执行跨次覆盖更新 |

## #3模型/算法逐项继承

#3原任务记录建模与校验基础。ADR-0012已更新领域模型：语义实体为身份/关系主轴，E0–E4为观察视角；以下旧22项用于追溯原requirements与tasks，不作为旧层级组织轴仍有效的依据。模型与提案对照见`docs/development/reviews/semantic-facts/semantic-entity-proposal-alignment.md`。

| Requirement | 原依据 | 唯一任务 | 未来验收 |
| --- | --- | --- | --- |
| semantic-fact-model / E0–E4事实观察视角（已由ADR-0012调整） | [原review-map](../../../openspec/changes/define-layered-semantic-fact-model/review-map.md) | `define-layered-semantic-fact-model/tasks.md` 1.2 | test_catalog_roles_and_layers |
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

## 验证层次

严格OpenSpec验证工件结构；独立核对确认传播与一致性；未来产品测试检查结构/引用/行为/复用/缺口，不冒充严格语义正确性。运行性能/Token和工具能力目前均未实测。负载实际测试后定，必要操作已委托设计；整体设计未冻结，产品开发未批准。
