# Tasks

## 现行范围说明

现行范围说明：此任务表保留原五视角模型契约的规划/实施记录；实体重构提出的实体身份、属性/关系、源码映射、测试验证和新档案迁移要求以当前实体重构任务为准。原E视角任务不得解释为实体分类或业务边界规则。

## M1切片子任务（交付2.1绑定，父任务不勾选）

本组记录原父任务的项目发现/项目列表、语言声明、原生workspace成员M1子切片。历史任务描述保留了原五角色隔离验收要求；用户在当前会话明确要求放宽双盲编写和私有验收隔离门禁以保证开发继续。因此下列勾选代表公开代码及公开测试实现完成，不代表独立私有验收或产品接受；不因此勾对应更广父任务。

- [x] 1.1.1 （M1）M1身份登记与公共记录。依据：主规格单身份/类型化引用及design M1节（父任务1.1）。交付：`contracts/semantic-model/types.json、fact.schema.json与src/c2s_semantic_contract/validation.py的M1切片`。接口/依赖：register_m1及M1Identity/SubjectRef/Registration；输入域由#12绑定，输出供#10/#9。验证/通过/失败：#7/#10可消费同一记录；重复声明保持身份、kind冲突拒绝、字节定位/内部引用明确；身份由路径或图UID替代则失败。 本会话已放宽私有验收隔离；此项完成指公开实现与仓库测试通过。

- [x] 1.2.1 （M1）M1封闭谓词目录。依据：原1.2目录与design M1三谓词表（父任务1.2）。交付：`原types/predicates/catalog.schema/catalog-manifest/rules的M1切片`。接口/依赖：project.name/project.language_declared/workspace.member；依赖1.1.1。验证/通过/失败：逐角色/主层/基数检查，未知谓词拒绝且跨模块不复制目录；workspace成员误指Project或同版悄改内容则失败。 本会话已放宽私有验收隔离；此项完成指公开实现与仓库测试通过。

- [x] 2.1.1 （M1）M1包与分阶段校验。依据：原2.1及主规格引用边界（父任务2.1）。交付：`原fact.schema.json与validate_model的M1结构/引用/不变量阶段`。接口/依赖：M1Bundle→validate_model既有结果；依赖1.1.1/1.2.1。验证/通过/失败：错误后依赖not_run、合法冲突保留、无算法前置；悬空可见或valid冒语义正确则失败。 本会话已放宽私有验收隔离；此项完成指公开实现与仓库测试通过。

- [x] 2.2.1 （M1）M1工程评估结构。依据：原2.2显式工程边界（父任务2.2）。交付：`原rules.md工程章及校验器M1评估约束`。接口/依赖：M1Assessment基数/角色，获取规则由#10唯一拥有；依赖2.1.1。验证/通过/失败：resolved=1/ambiguous>=2/unresolved=0，包与项目不混同；目录/成员自动推所有权则失败。 本会话已放宽私有验收隔离；此项完成指公开实现与仓库测试通过。

- [x] 3.1.1 （M1）M1证据覆盖与诚实缺口。依据：原3.1及ADR-0007（父任务3.1）。交付：`原fact.schema.json/rules/validation.py证据覆盖M1切片`。接口/依赖：M1Evidence/Coverage/Diagnostic，依赖2.1.1/2.2.1；不依赖未消费的2.3 SAT全量。验证/通过/失败：依据引用、Coverage/Assessment的supersedes同键无环与Registration合法补证、coverage.complete与缺口一致，未知/未支持不作否定；丢证据或空即不存在则失败。 本会话已放宽私有验收隔离；此项完成指公开实现与仓库测试通过。


> **For agentic workers:** 阶段二批准后，使用superpowers:subagent-driven-development或superpowers:executing-plans按本清单执行；本轮仅评审与规划。此文件是唯一权威计划，无第二份Superpowers待办。

**Goal:** 形成语言无关领域模型公共契约及可验证的目录、引用、不变量与算法投影基础。

**Architecture:** 推荐A采用类型/谓词目录、JSON Schema结构层和Python跨事实校验；来源覆盖与算法投影分开验收。用户已选择A，任务仍须获得单独实施批准，不能据方案选择或文件存在进入实施。

**Tech Stack:** 阶段二候选Python 3、jsonschema==4.26.0、JSON Schema 2020-12；本轮不安装。固定OpenSpec与上游Superpowers沿用仓库配置。

**Spec:** 本目录specs/semantic-fact-model/spec.md、specs/algorithm-description/spec.md，受两份openspec/specs主规格及ADR-0002约束；design.md解释方案，review-map.md列逐项映射。

## Global Constraints

- 五层是语义组织尺度；同主体单身份；跨层类型引用；不预设包含树、DDD聚合或存储。
- 默认顶层最小响应及明确要求才展开保持不变。本Issue仅提供模型引用及静态形状例，不实现查询Skill（请求相对顶层完整行为以ADR-0007及#7为准）。
- 所有自维护脚本及测试用Python 3；不修改上游依赖源码，不提交node_modules或认证资料。
- 不伪造宏展开、目标、观测或真实案例；synthetic与人工来源清单须标识。
- 状态awaiting-decision（A已选、等待实施批准）；本历史单Issue令牌不能单独放行；必须先按#4/#13冻结整体规划集合，再取得绑定新集合摘要的明确产品开发批准，才可取apply指令执行阶段二。不自动archive。

## Review Focus

- 配置不完整/重叠及同值多证据：1.1验证歧义、合法多值、冲突与不可判定分别诊断。
- 来源声明项目映射未决：1.1及2.2验证不造项目、映射前后身份不变。
- 嵌套值/循环/共享组成偷渡展开：2.1及4.1验证完整包与顶层静态形状边界。
- 三值求值冒充SAT：2.3验证互斥环、共享变量、4096/4097组合及SourceCondition。
- body和投影一起漏行为：4.3验证人工来源清单独立发现被删失败出口，未审定不能通过。

## 本轮执行门槛与通用验证

0组为历史已完成文档任务；6组为本次阶段一任务。1–5组的10项产品任务全部未完成，只有A获确认且另有明确实施批准后才能执行。每项由独立作者写正反例、独立执行者观察实际失败，再由编码者实现候选定义/规则，独立审核/执行/最终验证后更新实际证据并提交；任何失败不勾选。task中的候选Requirement不等于已生效主规格。

阶段二验证入口T：由独立执行者调用交付变更2.2绑定的私有runner，通过隔离接口测试固定candidate；旧同进程unittest命令不适用于隐藏suite。实施获批且隔离就绪后再按1.1准备requirements-semantic-model.txt；当前文件及测试不存在，T本轮未运行。下面的测试名称及期望是实施计划，不是本轮测试结果。

## 0. 已确认规格固化（本次授权）

- [x] 0.1 核对确认记录并隔离候选。上游依据：用户本轮条目1–2、ADR-0001及历史上下文用户约束。交付：`docs/decisions/0002-confirmed-specification-baseline.md`及`docs/development/discussions/2026-11-01-specification-baseline/`。验证：逐项核对B01–B06来源、证据等级及候选/代理分类。通过：每项确认有定位且Battle未当批准；失败：候选无依据升格或伪造原话。

- [x] 0.2 整理确认delta并选择性同步主规格。依赖：0.1。上游依据：用户条目3、B01–B06及实际specs instructions。交付：本变更`specs/semantic-fact-model/spec.md`、`specs/semantic-fact-query/spec.md`和对应`openspec/specs/`主规格。验证：逐Requirement比较delta与主规格，运行`npm run openspec -- validate --specs --strict --no-interactive`。通过：主规格3项模型+4项查询要求均有Scenario和确认映射，algorithm-description未同步；失败：混入候选或主规格含delta操作头。

- [x] 0.3 协调规划与验证记录。依赖：0.2。上游依据：用户条目4–6，B01–B06与两份主规格全部Requirement。交付：proposal.md、design.md、tasks.md、README/会话索引及`docs/development/reviews/2026-11-01/specification-baseline-verification.md`。验证：`npm run validate`、`npm run check:artifacts`、`git diff --check`，比较原10项产品任务均未完成，检查无产品代码/导入原件变动。通过：工件一致且实际校验有证据，文档任务与产品任务状态明确；失败：虚报验证、两套冲突计划、越界实施或归档。

## 独立交付约束（ADR-0008，优先于旧同角色步骤）

本清单所有测试步骤由独立用例作者编写、独立执行者运行，编码者只改实现与公开说明，不编写或读取测试；代码审核与最终验证另用独立身份。所有测试/fixture交付与测试命令均在交付变更2.2绑定的私有测试区，不落入编码可读产品仓库/历史/日志；本文既有名称与期望只是公开契约示例，不是隐藏suite。本轮未创建这些文件或运行产品测试。旧T/unittest直接同进程导入candidate不能用于隐藏验收，实际隔离runner命令须先绑定再执行。具体交接及红绿验证见`../define-independent-ddd-delivery/design.md` §2–4；里程碑仅索引本tasks，不复制产品任务。公共类型/路径及runner接口须先经交付2.1/2.2就绪检查；整体设计未冻结，实施另批，当前全部产品checkbox保持未完成。

## 1. 类型身份与公共目录

- [x] 1.1 建立类型/身份域/上下文与校验入口并运行公开正反例。已实现身份保持、引用、有限上下文/条件求解、条件重叠与矛盾诊断；公开语义模型单测覆盖44项相关用例。用户明确要求继续开发并放宽双盲/私有验收隔离门禁；此勾选只代表代码和公开测试完成，不代表独立私有验收。
  - 上游依据：主规格“单一主体身份与跨层引用”；候选“稳定身份与上下文保持引用”“显式工程边界与组织关系”；C01/C02、design §1/6。
  - 交付：types.json、fact.schema.json初始包/身份结构（均在contracts/semantic-model/）、rules.md身份章节、requirements-semantic-model.txt、src/c2s_semantic_contract/{__init__,validation}.py、独立测试区/suites/semantic-model/test_contracts.py、独立测试区/suites/semantic-model/fixtures/identity-context.json及docs/domain/semantic-model-contract.md统一语言/身份章节。
  - 接口：按design §6提供validate_model(document, catalogs, source_observations=None)；后续任务扩展其阶段，不变签名。首次契约version=1.0.0，依赖jsonschema==4.26.0；此为获批A的值，不能在实施时擅自扩大兼容承诺。
  - 验证：test_same_declaration_two_contexts断言D未复制；test_context_overlap_cases依次断言缺配置为ambiguous、同值兼容、多值合法、确定矛盾为CONFLICTING_CLAIMS且双方保留、重叠未知为POTENTIAL_CONFLICT；test_context_contradiction断言CTX_CONTRADICTION；test_mapping_preserves_identity断言确认映射不重键。
  - 通过：输入错误与语义冲突分开，source域不冒Project，名称/路径/提交非单独身份，诊断有参与记录；失败：猜配置/造项目、静默删主张或身份仅靠位置。字段/记录规则同步文档。

- [ ] 1.2 定义谓词、角色及组成/内嵌目录并运行T中的目录正反例。依赖：1.1。
  - 上游依据：候选“可查询的类型与谓词目录”“组成关联与引用边界”；C03/C07、design §2及导入候选§9的首批清单。
  - 交付：contracts/semantic-model/predicates.json、catalog.schema.json、catalog-manifest.json（contracts/semantic-model/）、rules.md目录章、独立测试区/suites/semantic-model/fixtures/predicates.json、扩展test_contracts.py及公共文档目录/五层边界。
  - 验证：test_catalog_roles_and_layers遍历每条谓词完整角色/类型/基数/约束/关系种类、Semantic唯一主层、Provenance无主层；test_catalog_input_rejected拒绝畸形目录、悬空目录类型引用、未知constraintId、混合版本及同版本改目录，并断言依赖阶段not_run；test_unknown_predicate_and_record拒绝缺类型/任意字典；test_cross_layer_entry_binding验证E1引用E2不复制。
  - 通过：固定发行包规范JSON摘要匹配、元目录Schema及已知规则通过，首批条目全部展开，program.contains/behavior.has_body/region_member与workspace/依赖/别名关联分开；失败：接受调用方自报manifest绕过核对、静默接受未知规则、漏条目、把层入身份、成员推依赖或内嵌白名单不闭合。
  - 进展（2026-11-06）：扩展profile目录已新增并固定manifest，当前获取器全部事实种类均有谓词映射；`project_query_to_semantic_model`已在固定版本Click/regex逐项投影。此进展不满足本任务要求的全部组成关系、嵌入白名单及完整目录用例，父任务继续开放。
  - 进展（2026-11-06）：再补入独立的`program.contains`、`behavior.has_body`、`region.member`及`BehaviorBody`/`BehaviorRegion`/`BehaviorStep`身份类型；M1明确拒绝扩展类型。其余工程、签名、契约、调用/捕获/读写、数据流及来源关系目录与高阶角色语法仍待实现，故本任务不勾选。
  - 进展（2026-11-06）：新增E3的precondition/outcome/effect/ordering四类独立谓词；当前值仍为字符串主张，结构化主体/偏序参与者与实际源提取未实现。
  - 进展（2026-11-06）：E2新增signature/access关系；E4新增implementation/call/bind/capture/read/write/algorithm-description/pseudocode关系及无层Provenance generated_from。捕获模式、调用候选集合等高阶参数目前超出二元值结构，且这些关系尚无语言提取器。
  - 进展（2026-11-06）：补入E0 project-boundary/group-member与E1 usage/entry/order/dependency/provider谓词。目录并未把新增候选等同于已有跨事实校验，且高阶参数/来源获取尚缺，1.2继续未完成。

## 2. 事实语法与工程关系

- [ ] 2.1 完成事实包结构、引用与顶层静态形状约束，运行T结构/引用反例。依赖：1.1–1.2。
  - 上游依据：候选“类型化事实与分阶段校验”“组成关联与引用边界”；查询主规格默认边界；C02/C03/C07。
  - 交付：完成fact.schema.json、扩展validation.py、rules.md结构/引用章、独立测试区/suites/semantic-model/fixtures/{facts-valid,facts-invalid,top-level-shape}.json、test_contracts.py及公共文档完整包/引用例。
  - 验证：test_invalid_role_and_internal_ref拒绝算法作为alias目标及悬空内部引用；test_external_stub不强造本地提供方；test_nested_payload_rejected覆盖Sequence/Record藏Fact/主体/body、复杂签名；test_shared_composition_and_cycle保持共享引用且顶层形状不递归；test_stages_not_run验证结构失败后依赖阶段not_run。
  - 通过：合法显式缺口可保留，错误含阶段/记录/字段/规则，完整包与示意顶层边界不同；失败：外部标记绕开全部身份/来源约束或把静态形状测试称查询流程实现。
  - 进展（2026-11-06）：full profile新增命名`arguments`多元角色表，按固定谓词目录逐角色验证类型与内部引用；二元M1语法未变。参数可变基数、嵌套Fact禁止与完整组成图/循环白名单仍未全部实现，父任务保持开放。

- [ ] 2.2 落实工程组织、目标与交付正反例并运行T。依赖：2.1。
  - 上游依据：候选“显式工程边界与组织关系”“目标配方别名与交付边界”；Issue二.3；C02。
  - 交付：独立测试区/suites/semantic-model/fixtures/{engineering,build-delivery}.json、validation.py对应不变量、rules.md工程章、test_contracts.py及公共文档工程案例。
  - 验证：test_undecided_project_mapping接受声明未决/候选映射、拒绝来源域冒Project；test_multiple_workspaces_no_inferred_membership覆盖嵌套独立工程/包映射/根包workspace/无workspace项目；test_alias_recipe_observation覆盖CMake INTERFACE/ALIAS、Python无原生目标、未构建输出和未安装入口。
  - 通过：没有虚构目标/项目/观测，确认映射保单身份，成员不转移所有权；失败：靠目录/同名合并或把任务选择器造为目标。多workspace例标synthetic，不冒真实解析结果。
  - 进展（2026-11-06）：full-profile类型/目录已分别建模Project声明Target与Recipe、Alias解析Target、声明OutputSpecification及ArtifactObservation；当前仅提供类型化事实表达与契约引用，不含构建系统获取器、管理归属推断或真实产物观察，故父任务仍开放。
  - 进展（2026-11-06）：校验器现拒绝条件重叠时同一Target由多个Project管理，并要求Alias目标在当前事实集中有Target声明；条件互斥时保持可并存。获取器和recipe/output/artifact的来源核验规则仍未完成。
  - 进展（2026-11-06）：`build.observed_artifact`已要求observation claim mode及至少一项已核验tool-output证据；仍没有构建/安装获取器和真实产物端到端案例。

- [x] 2.3 完成依赖与有限条件/循环校验并运行公开回归。依赖记录含path/version、解析状态/配置和独立scopePosition；条件求值实现Kleene三值、SAT/UNSAT见证、4096/4097限额与unknown保留；条件环按配置联合判定并保留原图。测试覆盖共享键互斥环、可满足见证、source条件未定和循环预算。用户已放宽双盲/私有验收隔离门禁；勾选只代表公开代码/测试，不代表独立私有验收。
  - 上游依据：候选“需求解析与范围位置正交”“条件可满足性与循环诊断”；C04、design §3。
  - 交付：独立测试区/suites/semantic-model/fixtures/{dependencies,conditions}.json、validation.py条件判定及需求规则、rules.md片段/4096限额/循环章、test_contracts.py及公共文档范围说明。
  - 验证：test_dependency_scope_orthogonal断言resolved+outside切inside仍同需求；test_path_version_and_resolution_context保留path+version/多配置/歧义；test_condition_truth_tables覆盖Unknown及空All/Any；test_cycle_satisfiability区分共享x=A且x=B为unsat、sat有见证；test_condition_limits覆盖4096可枚举、4097及SourceCondition为undetermined且保原图。
  - 通过：求值、SAT与工程违规独立，非法/不支持配置有定位；失败：未知当false、删环、outside当unresolved或把项目环当目标违规。循环fixture标synthetic。

## 3. 模态来源与覆盖

- [x] 3.1 完成证据/覆盖/状态表达及有界否定规则并运行公开回归。实现独立presentation/acquisition semanticStates、六种claimMode、evidence role、derivation前提/无环、输入闭合negativeBasis、来源核验、coverage缺口和lineage约束。校验只确认结构与已给证据，不能声称调用方输入已穷尽。用户已放宽双盲/私有验收隔离门禁；勾选只代表公开代码/测试，不代表独立私有验收。依赖：2.1–2.3。
  - 上游依据：候选“主张模态证据与推导可追溯”“覆盖与否定的边界”“状态维度独立表达”；C06、design §4。
  - 交付：fact.schema.json的Evidence/Coverage/状态定义、validation.py阶段、rules.md模态/否定/组合矩阵、独立测试区/suites/semantic-model/fixtures/evidence-coverage.json、test_contracts.py及公共文档覆盖报告例。
  - 验证：test_modes_not_truth_rank保留六模态和Supports/Refutes/Limits；test_derivation_missing_premise定位缺前提；test_source_unchecked_vs_mismatch区分无观察和不匹配；test_acquired_ref_only合法；test_negative_requires_closed_scope只接受design两种有限闭合检查且人工审定/输入齐备，未读输入、动态调用缺口和20文件样本不得证明全称否定。
  - 通过：valid只表示契约无error，冲突/gap/unchecked各列，空/五层有事实不报完备；失败：哈希/置信度裁真、把未展示当未获取或自动生成否定证书。

## 4. 契约算法与语言机制

- [x] 4.1 完成操作契约、受限算法结构和引用校验并运行公开算法测试。JSON Schema与校验器覆盖15种步骤构造、源跨度、区域/控制/数据引用、契约六类别、compute未知语义、opaque边界、管理项目状态基数及多实现引用；Python/Rust lowering保留结构与缺口。真实click/regex函数样本均通过结构校验。用户已放宽私有验收隔离门禁；本状态代表公开实现/测试，不代表私有独立审查。
  - 上游依据：算法delta“操作契约独立表达”“算法描述身份目的与实现关联”“结构化行为体与引用完整性”“求值错误资源与并发语义保持”；C03/C05、design §5。
  - 交付：algorithm.schema.json、validation.py算法阶段、rules.md算法章、独立测试区/suites/semantic-model/fixtures/algorithms.json、test_algorithms.py及公共文档契约/算法例。
  - 验证：test_algorithm_kinds_and_refs覆盖design列出的14种构造、重复stepId、悬空边/循环出口、局部步骤可独立定位；test_algorithm_multi_project保持管理归属未决和多实现；test_numeric_resource_concurrency_unknown不默认整数/次序/串行，opaque缺来源/影响/未知项拒绝；test_body_reference_boundary拒绝顶层示例偷带步骤。
  - 通过：契约/源码解释/抽象目的不同、错误与返回/资源/偏序保留，合法未知不补造事实；失败：implemented_by当等价证明或造共同workspace。

- [ ] 4.2 落实语言机制映射的正反例并运行T。依赖：4.1。
  - 上游依据：算法delta“宏生成与注解的分阶段来源”“匿名操作闭包与绑定语义”；Issue二.4；design §5。
  - 交付：独立测试区/suites/semantic-model/fixtures/language-mechanisms.json、test_algorithms.py映射断言、rules.md映射章及公共文档语言支持/缺口矩阵。
  - 验证：test_macro_unexpanded_and_repeated不造展开AST且区分应用/生成绑定；test_metadata_vs_runtime_decorator区分cfg、未支持Java处理、Click Command/callback/返回替换；test_closure_and_conditional_binding保留捕获未知、模式、初始化/作用域/路径及绑定≠赋值。
  - 通过：来源多对多、主体/运行对象不合并，缺证显式UNKNOWN/opaque；失败：声明注解已执行或猜捕获方式。复杂宏/Java等合成例明确synthetic，不声称获取器支持。

- [x] 4.3 实现算法投影并分别核对固定来源清单与投影。`project_algorithm`输出逐Step文本映射及省略；`check_source_coverage`核对已审定清单映射。R5/regex与P7/Click由分析器读取锁定真实commit并逐项映射；C5/nlohmann-json锁定commit并以手工审阅的opaque来源步骤保留接收器parse_error原样返回、strict/non-strict分支，不宣称有C++自动lowering。测试核对源代码片段、Step/effect/gap映射及删掉失败Step后来源清单仍报警。用户明确放宽双盲/私有独立验收；该勾选指开发者公开核验，不代表独立评审或行为等价证明。依赖：4.1–4.2。
  - 上游依据：算法delta“伪代码是可追溯投影”“来源行为覆盖与投影分别验证”；C05、导入候选§12.1–12.3及R5/C5/P7固定来源。
  - 交付：src/c2s_semantic_contract/projection.py导出project_algorithm及check_source_coverage（签名/返回见design §6），独立测试区/suites/semantic-model/fixtures/pseudocode/三案例的source-checklist、body、expected-text与step-mappings，test_algorithms.py及rules/公共文档的投影规则和边界。
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
- 当前规则优先于本阶段一的历史批准流程：Issue/评论/标签/定时不触发；旧单Issue令牌及A选型都不能放行手动或自动阶段二。须先完成#4/#13集合冻结，再在显式会话取得绑定该新摘要的独立开发批准；当前Runner仅plan/smoke，不能用重复模型或旧令牌绕过。
- 不自动archive；真实来源补证不能抹去synthetic/未获取记录，不因产品尚未实施重开已确认需求。


## Progress — 2026-11-06, contextual claim integration

- Implemented the separate `semantic-fact-model-1` profile with finite context domains, partial context assignments, reference-level context annotations that preserve subject identity, condition satisfiability and contradiction diagnostics, and single-valued claim overlap checks. The M1 project-discovery profile rejects contexts and conditional facts. Unsupported/unknown conditions remain gaps or potential conflicts rather than being treated as false. Forty-six focused contract/solver tests pass. Full repository tests pass 81/81; strict OpenSpec validation passes 21/21; artifact hash checks and Python compilation pass.
- This is a bounded contract/validator slice over the initial M1 predicate catalog; it does not implement the remaining product-wide E0–E4 extraction, language-specific condition discovery, dependency graph checks, evidence completeness, or algorithm behavior proofs.


## Progress — 2026-11-06, condition truth evaluation

- Added `evaluate_condition` for partial assignments with three-valued Kleene semantics, separate from exhaustive `condition_satisfiability`. Missing assignments retain an unknown reason; decisive false in `all` and decisive true in `any` dominate unknown children, and empty All/Any follow Boolean identity. Dependency requirements/resolutions and configuration-separated cycle candidates are integrated into `validate_model`; explicit status and scope position are checked independently. Focused regressions cover SAT/UNSAT, source conditions, enumeration budgets, resolution cardinalities and context conflicts.


## Progress — 2026-11-06, semantic acquisition/presentation states

- Added full-profile `semanticStates` that separate obtained/not-acquired/unsupported/not-applicable acquisition from ref-only/expanded presentation and from semantic claims. Validation requires explanatory gaps for unavailable states, justification/evidence for not-applicable, registered fact and evidence references, and subject/predicate scope consistency. Existing coverage/supersedes/source-observation checks remain distinct. Tests verify acquired ref-only facts and reject unjustified not-applicable states.


## Progress — 2026-11-06, algorithm contract structure

- Extended the algorithm schema with explicit management mapping state and candidate Project subject IDs, separate from a many-valued implementation reference list. Language lowerers set management unresolved rather than guessing project ownership. Regression coverage enumerates all 15 step kinds, validates ambiguous candidate cardinality, multiple implementations, operation coverage, source spans, and region/control/data refs. The full Skill suite passed after fixing an environment-sensitive Cargo-unavailable test.

## Progress — 2026-11-06, language mechanism gaps (4.2 partial)

- Added regression cases proving Rust macro invocations remain source-bound opaque steps and Python decorator expressions do not leak into body steps. Lowering now reports decorator/wrapper semantics, closure capture, Rust macro expansion, and `cfg` selection as explicit omissions. This preserves unknowns without inventing expansion or capture bindings. A complete language mechanism mapping, behavior for conditional binding, and broader callback/decorator source relations remain outstanding; task 4.2 stays open.
- Extended closure regressions: Rust closure expressions now produce a dedicated omission for deferred body/capture semantics and a direct closure expression remains an opaque source-bound step; Python lambda-containing operations explicitly report that the anonymous body is not independently lowered. Tests verify Rust closure operations are not attributed as direct outer-body steps. Conditional binding, Rust macro application-to-generated-binding relations, and Click runtime callback/decorator mapping remain open.

## Progress — 2026-11-06, algorithm text projection and checklist primitive (4.3 partial)

- Added `project_algorithm` to render one algorithm's steps, regions, control/data edges, partial contract categories and omissions with per-step line mappings. Added `check_source_coverage` to enforce human review and verify checklist mappings to existing steps/effects or explicit gaps; an omitted step named by the source checklist remains uncovered even if generated text is also changed. These utilities do not read source or prove checklist exhaustiveness. The three fixed R5/C5/P7 source checklists, independent review, and full source-vs-body validation remain open, so task 4.3 stays unchecked.


## Progress — 2026-11-06, fixed real-source algorithm checklists

- Added pinned, reviewed R5/regex, P7/Click, and C5/nlohmann-json source checklists. Tests verify exact source snippets at fixed commits. R5 and P7 cases map to source-lowered steps with explicit omissions for the nested fetch helper and zero-count fallthrough. The C5 C++ case is deliberately a manually authored opaque algorithm description, not an automatic C++ parse; it preserves the strict/non-strict path and exact `sax.parse_error(...)` result and marks unsupported C++ lowering. The generic deletion test removes a failure-path step and the projected text together; the independent source checklist still marks that source item uncovered. This closes task 4.3's public implementation/test slice under the user's relaxed isolation gate, without claiming independent acceptance or semantic equivalence.

## Progress — 2026-11-07, algorithm facts in full semantic profile

- Added `project_algorithm_to_semantic_model` to map algorithm steps, regions, body links and typed control edges into a full-profile bundle. Python/Rust lowerers now retain the source file digest, and projection rejects stale source text, invalid spans and root escapes. Opaque operations, omissions and unlocated steps remain gaps. Query-declaration identities are not implicitly merged with algorithm-local implementation IDs. Python and Rust targeted projection tests pass; the full Skill suite passed 88 tests, the semantic-model suite passed 74 tests, root `npm test` passed 109 tests, strict OpenSpec validation passed 21 items, and artifact/diff checks passed.
