# Issue #3需求、规格与任务映射

状态：阶段一候选，awaiting-decision。此文件是追溯矩阵，不是第二份计划；唯一任务清单为tasks.md。B01–B06是既有确认；Issue定义工作范围，不能自动批准本轮提出的字段/状态/算法与技术方案。新delta均为待裁决候选，不同步主规格。

## Requirement覆盖

| 能力/Requirement | 上游依据 | 任务 | 候选验收（尚未运行） |
| --- | --- | --- | --- |
| semantic-fact-model / 五层语义组织 | B01/B03 | 1.2 | test_catalog_roles_and_layers |
| semantic-fact-model / 分层不强制包含或细化 | B02/B03 | 1.2,2.2 | test_cross_layer_entry_binding |
| semantic-fact-model / 单一主体身份与跨层引用 | B02 | 1.1 | test_same_declaration_two_contexts |
| semantic-fact-model / 显式工程边界与组织关系 | Issue二.1/二.3; C02 | 1.1,2.2 | test_undecided_project_mapping |
| semantic-fact-model / 目标配方别名与交付边界 | Issue二.3; C02 | 2.2 | test_alias_recipe_observation |
| semantic-fact-model / 需求解析与范围位置正交 | Issue二.3; C04 | 2.3 | test_dependency_scope_orthogonal |
| semantic-fact-model / 稳定身份与上下文保持引用 | Issue二.1/二.2/六; C01/C02 | 1.1 | test_context_overlap_cases |
| semantic-fact-model / 类型化事实与分阶段校验 | Issue二.5; C07 | 2.1 | test_invalid_role_and_internal_ref |
| semantic-fact-model / 可查询的类型与谓词目录 | Issue二.5; C03/C07 | 1.2 | test_catalog_roles_and_layers |
| semantic-fact-model / 组成关联与引用边界 | Issue三; C03 | 1.2,2.1,4.1 | test_nested_payload_rejected |
| semantic-fact-model / 主张模态证据与推导可追溯 | Issue二.6; C06 | 3.1 | test_modes_not_truth_rank |
| semantic-fact-model / 覆盖与否定的边界 | Issue二.6; C06 | 3.1 | test_negative_requires_closed_scope |
| semantic-fact-model / 状态维度独立表达 | B06/Issue二.6; C06 | 3.1 | test_acquired_ref_only |
| semantic-fact-model / 条件可满足性与循环诊断 | Issue二.3; C04 | 2.3 | test_cycle_satisfiability |
| algorithm-description / 操作契约独立表达 | Issue二.4; C05 | 4.1 | test_numeric_resource_concurrency_unknown |
| algorithm-description / 算法描述身份目的与实现关联 | Issue二.4; C01/C05 | 4.1 | test_algorithm_multi_project |
| algorithm-description / 结构化行为体与引用完整性 | Issue二.4; C03/C05 | 4.1 | test_algorithm_kinds_and_refs |
| algorithm-description / 求值错误资源与并发语义保持 | Issue二.4; C05 | 4.1 | test_numeric_resource_concurrency_unknown |
| algorithm-description / 宏生成与注解的分阶段来源 | Issue二.4; C05 | 4.2 | test_macro_unexpanded_and_repeated |
| algorithm-description / 匿名操作闭包与绑定语义 | Issue二.4; C05 | 4.2 | test_closure_and_conditional_binding |
| algorithm-description / 伪代码是可追溯投影 | Issue二.4; C05 | 4.3 | test_projection_preserves_behavior |
| algorithm-description / 来源行为覆盖与投影分别验证 | Issue二.4/六; C05 | 4.3 | test_deleted_failure_exit_detected |

## Issue范围覆盖

| Issue条目 | 规格/设计入口 | 交付与验收边界 |
| --- | --- | --- |
| 二.1 统一语言、实体/值、身份、不变量 | design §1、模型身份/工程要求 | types/rules/领域文档，1.1/2.2；不预设DDD聚合 |
| 二.2 五层 | 已确认三项模型主规格、design Goals与§2 | 1.2角色/谓词归类，不改已确认层数 |
| 二.3 项目、workspace、目标、依赖、循环 | 模型工程/交付/需求/循环要求 | 2.2/2.3，未知与synthetic标明 |
| 二.4 结构/操作契约/算法/语言机制 | 八项算法delta、design §5 | 4.1–4.3，两段来源/投影检查，不作等价证明 |
| 二.5 类型/谓词/事实契约及校验 | 模型类型/目录/组成要求、design §2/6 | 1.1/1.2/2.1，结构/引用/不变量分开 |
| 二.6 来源、覆盖、状态 | 模型模态/覆盖/状态要求、design §4 | 3.1，闭合依据不自动证明真值 |
| 三 查询前置 | 模型组成边界及查询主规格四项固定约束 | 2.1/4.1静态形状支撑；查询执行四项未在本Issue实施，不能标其产品验收通过 |
| 四 阶段一 | problem-package、双方两轮、reviewer、design Approaches | 6.1–6.3为初始评审记录；后续用户已选A，实施未批准，当前服从#4/#13整体新摘要门禁 |
| 五/六 交付与验收 | design路径表、tasks全部10项产品任务 | 5.1分别报告契约测试/源码核对/规划校验 |

## 方案裁决入口与修订依据

- Q01→C01/C02：推荐身份域与项目映射分开；部分上下文、兼容多值、冲突和零匹配分别定义。拒绝“多种值一概歧义”。
- Q02→C03：推荐有限内嵌白名单及独立引用。完整包不授权响应整包；静态形状不是查询实现。
- Q03→C06：推荐三轴与两种有限闭合检查。枚举/字段编码是代理方案，非B06既有批准。
- Q04→C05：推荐受限构造+opaque、body单源投影及人工来源清单；保留人工文本+映射替代。
- Q05→C07：推荐JSON目录/2020-12 Schema/Python分阶段；保留逐谓词联合Schema替代。
- builder-check补充目录信任边界：推荐A首版固定发行包，元目录/目录引用/已知规则/版本组合先验；同版篡改拒绝，运行时自定义扩展不承诺。1.2增加catalog.schema/manifest及test_catalog_input_rejected。
- C04新增明确有限条件片段及4096预算；这是代理实现选择，用户尚未确认。

用户已选择A，依据见评审目录scheme-decision.md；未将其扩大为所有字段的额外逐项主规格批准，implementation_approved=false。选择B或改公共行为须先改候选工件并重审整体集合摘要，旧单Issue令牌不再单独放行。未改变主规格，无需重开既有需求；新反例若要求修改已确认行为，另列修订依据，经用户确认后处理。
