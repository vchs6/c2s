# Tasks

> **For agentic workers:** 阶段二批准后，使用superpowers:subagent-driven-development或superpowers:executing-plans按本清单执行；本轮仅评审与规划。此文件是唯一权威计划，无第二份Superpowers待办。

**Goal:** 形成语言无关领域模型公共契约及可验证的目录、引用、不变量与算法投影基础。

**Architecture:** 推荐A采用类型/谓词目录、JSON Schema结构层和Python跨事实校验；来源覆盖与算法投影分开验收。用户已选择A，任务仍须获得单独实施批准，不能据方案选择或文件存在进入实施。

**Tech Stack:** 阶段二候选Python 3、jsonschema==4.26.0、JSON Schema 2020-12；本轮不安装。固定OpenSpec与上游Superpowers沿用仓库配置。

**Spec:** 本目录specs/semantic-fact-model/spec.md、specs/algorithm-description/spec.md，受两份openspec/specs主规格及ADR-0002约束；design.md解释方案，review-map.md列逐项映射。

## Global Constraints

- 五层是语义组织尺度；同主体单身份；跨层类型引用；不预设包含树、DDD聚合或存储。
- 默认顶层最小响应及明确要求才展开保持不变。本Issue仅提供模型引用及静态形状例，不实现查询Skill。
- 所有自维护脚本及测试用Python 3；不修改上游依赖源码，不提交node_modules或认证资料。
- 不伪造宏展开、目标、观测或真实案例；synthetic与人工来源清单须标识。
- 状态awaiting-decision（A已选、等待实施批准）；必须明确批准当前令牌，才可取apply指令执行阶段二。不自动archive。

## Review Focus

- 配置不完整/重叠及同值多证据：1.1验证歧义、合法多值、冲突与不可判定分别诊断。
- 来源声明项目映射未决：1.1及2.2验证不造项目、映射前后身份不变。
- 嵌套值/循环/共享组成偷渡展开：2.1及4.1验证完整包与顶层静态形状边界。
- 三值求值冒充SAT：2.3验证互斥环、共享变量、4096/4097组合及SourceCondition。
- body和投影一起漏行为：4.3验证人工来源清单独立发现被删失败出口，未审定不能通过。

## 本轮执行门槛与通用验证

0组为历史已完成文档任务；6组为本次阶段一任务。1–5组的10项产品任务全部未完成，只有A获确认且另有明确实施批准后才能执行。每项先写对应正反例并观察失败，再实现候选定义/规则，运行该项验证，更新文档及实际证据并提交；任何失败不勾选。task中的候选Requirement不等于已生效主规格。

阶段二统一测试命令T：`PYTHONPATH=src python3 -m unittest discover -s tests/semantic-model -p 'test_*.py' -v`。需要先按1.1建立并安装requirements-semantic-model.txt；当前文件及测试不存在，T本轮未运行。下面的测试名称及期望是实施计划，不是本轮测试结果。

## 0. 已确认规格固化（本次授权）

- [x] 0.1 核对确认记录并隔离候选。上游依据：用户本轮条目1–2、ADR-0001及历史上下文用户约束。交付：`docs/decisions/0002-confirmed-specification-baseline.md`及`docs/development/discussions/2026-11-01-specification-baseline/`。验证：逐项核对B01–B06来源、证据等级及候选/代理分类。通过：每项确认有定位且Battle未当批准；失败：候选无依据升格或伪造原话。

- [x] 0.2 整理确认delta并选择性同步主规格。依赖：0.1。上游依据：用户条目3、B01–B06及实际specs instructions。交付：本变更`specs/semantic-fact-model/spec.md`、`specs/semantic-fact-query/spec.md`和对应`openspec/specs/`主规格。验证：逐Requirement比较delta与主规格，运行`npm run openspec -- validate --specs --strict --no-interactive`。通过：主规格3项模型+4项查询要求均有Scenario和确认映射，algorithm-description未同步；失败：混入候选或主规格含delta操作头。

- [x] 0.3 协调规划与验证记录。依赖：0.2。上游依据：用户条目4–6，B01–B06与两份主规格全部Requirement。交付：proposal.md、design.md、tasks.md、README/会话索引及`docs/development/reviews/2026-11-01/specification-baseline-verification.md`。验证：`npm run validate`、`npm run check:artifacts`、`git diff --check`，比较原10项产品任务均未完成，检查无产品代码/导入原件变动。通过：工件一致且实际校验有证据，文档任务与产品任务状态明确；失败：虚报验证、两套冲突计划、越界实施或归档。

## 1. 类型身份与公共目录

- [ ] 1.1 建立类型/身份域/上下文与校验入口，运行T中身份和上下文正反例。依赖：方案和实施批准。
  - 上游依据：主规格“单一主体身份与跨层引用”；候选“稳定身份与上下文保持引用”“显式工程边界与组织关系”；C01/C02、design §1/6。
  - 交付：types.json、fact.schema.json初始包/身份结构（均在contracts/semantic-model/）、rules.md身份章节、requirements-semantic-model.txt、src/c2s_semantic_contract/{__init__,validation}.py、tests/semantic-model/test_contracts.py、fixtures/identity-context.json及docs/domain/semantic-model-contract.md统一语言/身份章节。
  - 接口：按design §6提供validate_model(document, catalogs, source_observations=None)；后续任务扩展其阶段，不变签名。首次契约version=1.0.0，依赖jsonschema==4.26.0；此为获批A的值，不能在实施时擅自扩大兼容承诺。
  - 验证：test_same_declaration_two_contexts断言D未复制；test_context_overlap_cases依次断言缺配置为ambiguous、同值兼容、多值合法、确定矛盾为CONFLICTING_CLAIMS且双方保留、重叠未知为POTENTIAL_CONFLICT；test_context_contradiction断言CTX_CONTRADICTION；test_mapping_preserves_identity断言确认映射不重键。
  - 通过：输入错误与语义冲突分开，source域不冒Project，名称/路径/提交非单独身份，诊断有参与记录；失败：猜配置/造项目、静默删主张或身份仅靠位置。字段/记录规则同步文档。

- [ ] 1.2 定义谓词、角色及组成/内嵌目录并运行T中的目录正反例。依赖：1.1。
  - 上游依据：候选“可查询的类型与谓词目录”“组成关联与引用边界”；C03/C07、design §2及导入候选§9的首批清单。
  - 交付：contracts/semantic-model/predicates.json、catalog.schema.json、catalog-manifest.json（contracts/semantic-model/）、rules.md目录章、fixtures/predicates.json、扩展test_contracts.py及公共文档目录/五层边界。
  - 验证：test_catalog_roles_and_layers遍历每条谓词完整角色/类型/基数/约束/关系种类、Semantic唯一主层、Provenance无主层；test_catalog_input_rejected拒绝畸形目录、悬空目录类型引用、未知constraintId、混合版本及同版本改目录，并断言依赖阶段not_run；test_unknown_predicate_and_record拒绝缺类型/任意字典；test_cross_layer_entry_binding验证E1引用E2不复制。
  - 通过：固定发行包规范JSON摘要匹配、元目录Schema及已知规则通过，首批条目全部展开，program.contains/behavior.has_body/region_member与workspace/依赖/别名关联分开；失败：接受调用方自报manifest绕过核对、静默接受未知规则、漏条目、把层入身份、成员推依赖或内嵌白名单不闭合。

## 2. 事实语法与工程关系

- [ ] 2.1 完成事实包结构、引用与顶层静态形状约束，运行T结构/引用反例。依赖：1.1–1.2。
  - 上游依据：候选“类型化事实与分阶段校验”“组成关联与引用边界”；查询主规格默认边界；C02/C03/C07。
  - 交付：完成fact.schema.json、扩展validation.py、rules.md结构/引用章、fixtures/{facts-valid,facts-invalid,top-level-shape}.json、test_contracts.py及公共文档完整包/引用例。
  - 验证：test_invalid_role_and_internal_ref拒绝算法作为alias目标及悬空内部引用；test_external_stub不强造本地提供方；test_nested_payload_rejected覆盖Sequence/Record藏Fact/主体/body、复杂签名；test_shared_composition_and_cycle保持共享引用且顶层形状不递归；test_stages_not_run验证结构失败后依赖阶段not_run。
  - 通过：合法显式缺口可保留，错误含阶段/记录/字段/规则，完整包与示意顶层边界不同；失败：外部标记绕开全部身份/来源约束或把静态形状测试称查询流程实现。

- [ ] 2.2 落实工程组织、目标与交付正反例并运行T。依赖：2.1。
  - 上游依据：候选“显式工程边界与组织关系”“目标配方别名与交付边界”；Issue二.3；C02。
  - 交付：fixtures/{engineering,build-delivery}.json、validation.py对应不变量、rules.md工程章、test_contracts.py及公共文档工程案例。
  - 验证：test_undecided_project_mapping接受声明未决/候选映射、拒绝来源域冒Project；test_multiple_workspaces_no_inferred_membership覆盖嵌套独立工程/包映射/根包workspace/无workspace项目；test_alias_recipe_observation覆盖CMake INTERFACE/ALIAS、Python无原生目标、未构建输出和未安装入口。
  - 通过：没有虚构目标/项目/观测，确认映射保单身份，成员不转移所有权；失败：靠目录/同名合并或把任务选择器造为目标。多workspace例标synthetic，不冒真实解析结果。

- [ ] 2.3 完成依赖与有限条件/循环校验并运行T。依赖：2.1–2.2。
  - 上游依据：候选“需求解析与范围位置正交”“条件可满足性与循环诊断”；C04、design §3。
  - 交付：fixtures/{dependencies,conditions}.json、validation.py条件判定及需求规则、rules.md片段/4096限额/循环章、test_contracts.py及公共文档范围说明。
  - 验证：test_dependency_scope_orthogonal断言resolved+outside切inside仍同需求；test_path_version_and_resolution_context保留path+version/多配置/歧义；test_condition_truth_tables覆盖Unknown及空All/Any；test_cycle_satisfiability区分共享x=A且x=B为unsat、sat有见证；test_condition_limits覆盖4096可枚举、4097及SourceCondition为undetermined且保原图。
  - 通过：求值、SAT与工程违规独立，非法/不支持配置有定位；失败：未知当false、删环、outside当unresolved或把项目环当目标违规。循环fixture标synthetic。

## 3. 模态来源与覆盖

- [ ] 3.1 完成证据/覆盖/三轴状态及有界否定规则，运行T。依赖：2.1–2.3。
  - 上游依据：候选“主张模态证据与推导可追溯”“覆盖与否定的边界”“状态维度独立表达”；C06、design §4。
  - 交付：fact.schema.json的Evidence/Coverage/状态定义、validation.py阶段、rules.md模态/否定/组合矩阵、fixtures/evidence-coverage.json、test_contracts.py及公共文档覆盖报告例。
  - 验证：test_modes_not_truth_rank保留六模态和Supports/Refutes/Limits；test_derivation_missing_premise定位缺前提；test_source_unchecked_vs_mismatch区分无观察和不匹配；test_acquired_ref_only合法；test_negative_requires_closed_scope只接受design两种有限闭合检查且人工审定/输入齐备，未读输入、动态调用缺口和20文件样本不得证明全称否定。
  - 通过：valid只表示契约无error，冲突/gap/unchecked各列，空/五层有事实不报完备；失败：哈希/置信度裁真、把未展示当未获取或自动生成否定证书。

## 4. 契约算法与语言机制

- [ ] 4.1 完成操作契约、受限算法结构和引用校验，运行T算法正反例。依赖：1.1–3.1。
  - 上游依据：算法delta“操作契约独立表达”“算法描述身份目的与实现关联”“结构化行为体与引用完整性”“求值错误资源与并发语义保持”；C03/C05、design §5。
  - 交付：algorithm.schema.json、validation.py算法阶段、rules.md算法章、fixtures/algorithms.json、test_algorithms.py及公共文档契约/算法例。
  - 验证：test_algorithm_kinds_and_refs覆盖design列出的14种构造、重复stepId、悬空边/循环出口、局部步骤可独立定位；test_algorithm_multi_project保持管理归属未决和多实现；test_numeric_resource_concurrency_unknown不默认整数/次序/串行，opaque缺来源/影响/未知项拒绝；test_body_reference_boundary拒绝顶层示例偷带步骤。
  - 通过：契约/源码解释/抽象目的不同、错误与返回/资源/偏序保留，合法未知不补造事实；失败：implemented_by当等价证明或造共同workspace。

- [ ] 4.2 落实语言机制映射的正反例并运行T。依赖：4.1。
  - 上游依据：算法delta“宏生成与注解的分阶段来源”“匿名操作闭包与绑定语义”；Issue二.4；design §5。
  - 交付：fixtures/language-mechanisms.json、test_algorithms.py映射断言、rules.md映射章及公共文档语言支持/缺口矩阵。
  - 验证：test_macro_unexpanded_and_repeated不造展开AST且区分应用/生成绑定；test_metadata_vs_runtime_decorator区分cfg、未支持Java处理、Click Command/callback/返回替换；test_closure_and_conditional_binding保留捕获未知、模式、初始化/作用域/路径及绑定≠赋值。
  - 通过：来源多对多、主体/运行对象不合并，缺证显式UNKNOWN/opaque；失败：声明注解已执行或猜捕获方式。复杂宏/Java等合成例明确synthetic，不声称获取器支持。

- [ ] 4.3 实现算法投影并分别核对来源覆盖与投影，运行T。依赖：4.1–4.2。
  - 上游依据：算法delta“伪代码是可追溯投影”“来源行为覆盖与投影分别验证”；C05、导入候选§12.1–12.3及R5/C5/P7固定来源。
  - 交付：src/c2s_semantic_contract/projection.py导出project_algorithm及check_source_coverage（签名/返回见design §6），fixtures/pseudocode/三案例的source-checklist、body、expected-text与step-mappings，test_algorithms.py及rules/公共文档的投影规则和边界。
  - 验证：test_source_checklist_review_gate未审定不通过；test_source_body_coverage要求清单项均映射Step/effect或显式gap；test_deleted_failure_exit_detected在body和文本一起删出口时清单仍识别缺项；test_projection_preserves_behavior涵盖Rust两层循环/回调传播、C++接收器结果、Python零规格/第二通配错误，opaque/省略显示。
  - 通过：人工来源核对和程序投影断言分别报告，段落映射有效且未运行上游不称运行通过；失败：映射全覆盖就当源码覆盖、清单未审定或声称完整等价。清单需独立审查，不能只由生成body的代理自证。

## 5. 集成证据

- [ ] 5.1 执行已批准模型/算法的集成验收并发布准确领域模型说明。依赖：1.1–4.3。
  - 上游依据：review-map.md逐项模型/算法Requirement及已确认主规格约束；查询主规格仅检查模型形状支撑，不声称查询执行器完成。
  - 交付：docs/development/reviews/semantic-model-contract-verification.md及完整docs/domain/semantic-model-contract.md链接/公共使用说明；每项测试和证据引用真实文件，回写本清单实际结果。
  - 验证：T、npm run validate、npm run check:artifacts及git diff --check；逐Requirement对应测试/fixture，检查三语言人工来源清单、所有计划路径和synthetic标记，独立最终复核；无产品测试文件时命令必须失败，不能用0测试成功冒充验收。
  - 通过：契约结构/引用/不变量/算法投影通过且已核对来源清单，分别报告工具规划校验、产品契约测试、源码案例核对，来源不足明确；失败：用CLI工件done、OpenSpec通过或静态顶层形状推断完整查询Skill实现。

## 6. Issue #3阶段一评审与规划（本轮授权）

- [x] 6.1 完成中立问题包、真实双方两轮Battle及独立综合评审。上游依据：Issue四.阶段一、battle-protocol；交付：docs/development/reviews/issues/3/stage-one-2026-11-01/的输入、双方记录、争议、reviewer与报告。验证：两位独立首轮、逐C01–C07交叉响应、第三位独立综合均有实际记录。通过：未模拟角色、少数意见与user_decision=null保留；失败：缺角色却称共识或把共识批准。

- [x] 6.2 协调候选proposal/specs/design/tasks并完成可实施性审阅。依赖：6.1。上游依据：Issue一至六及固定主规格；交付：本目录四工件、review-map.md及独立builder-check记录。验证：逐Issue/Requirement/任务/路径/通过失败映射；按A条件计划自审接口一致性和Review Focus。通过：无隐藏重大假设，A/B和待裁决项明确，原10项产品任务未勾选，主规格不变；失败：越界产品实现、另建重复变更或未确认方案冒充已选。

- [x] 6.3 严格校验并绑定输入及规划工件生成实施批准令牌。依赖：6.2。上游依据：Issue四.阶段一/验收与仓库fingerprint/plan_digest/approval_token规则。交付：同评审目录validation.md、approval.json及docs/development/issues/3/state.json。验证：npm run validate、npm run check:artifacts、git diff --check、主规格/导入哈希及路径审计，复算Issue指纹和工件摘要；令牌可检测输入或规划变化。通过：awaiting-decision、implementation_approved=false，方案状态按实际用户决定记录（阶段一初始null，后续选择见scheme-decision.md），校验记录实际成功；失败：旧令牌复用、循环哈希或伪造实施完成。

## Workflow follow-up

- 用户已选择A（见评审目录scheme-decision.md），继续等待明确实施批准；方案确认不等于实施批准。
- 当前自动Runner不支持本既有变更的路由/路径，不建议直接在Issue评论批准后期待自动apply。可在Work用绑定令牌明确批准手动阶段二；若要Runner自动承接，须另行授权修复，不能用重复issue-3-*模型绕过。
- 不自动archive；真实来源补证不能抹去synthetic/未获取记录，不因产品尚未实施重开已确认需求。
