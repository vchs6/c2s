# Design

现行接口接续（2026-11-09，ADR-0014）：本文件M1/V1及旧完整事实运行接口为历史规划/交付记录，当前公开运行协议仅V2，不再提供兼容查询、仓储或转换。通用能力要求继续适用；新实施不得恢复旧API。唯一删除与审核任务见`openspec/changes/redesign-semantic-entity-domain-model/tasks.md`第11节。

## 当前领域模型基准

当前领域模型基准：本提案历史形成的E0–E4主组织轴已由ADR-0012替代。以下仍有效的模型规则须解释为目录、条件、引用、来源和证据约束，不能推出实体类型或业务边界；现行语义实体契约与映射要求见`redesign-semantic-entity-domain-model`。

## M1项目发现切片契约（代理技术决定，m1-project-discovery-1）

本节是交付2.1的局部契约细化，不是新增用户确认、Schema或产品完成。后文旧“另批/全目录先完成”不适用于此切片：ADR-0009授权仍有效，实施仍须交付就绪/隔离门禁。M1仅发现/列出有边界依据的项目、项目语言声明、原生workspace成员；不是“完整所有项目事实”。M2–M4未消费类型不作为M1前置。本节记录由本change独占定义；其他change只引用，未来落入contracts/semantic-model，不在本轮创建。

记法：JSON记录所有列出字段必填，`?`才可省略；`T|null`必须显式给值；数组允许空；Id为非空字符串，Path为保留大小写/Unicode的根相对路径（分隔符/原始host路径转换见Evidence），枚举大小写精确；未列字段拒绝。不以缺省值填未知。模型载荷version="1.0.0"，profile="m1-project-discovery-1"；同版本同profile目录内容固定，改变该切片含义须新profile/契约版本，M2另行扩展，不同版包不混用。

| 精确记录 | 字段/约束 |
| --- | --- |
| M1Identity | {authority:Id, domainId:Id, localId:Id}；身份三元组，层/路径/摘要/工具UID不入身份 |
| M1SubjectRef | {identity:M1Identity, kind:"Project"\|"PackageSpecification"\|"NativeWorkspace"\|"SourceDeclaration"}；本切片不使用contextRef |
| M1Registration | {ref:M1SubjectRef, sourceKey:Id, evidenceIds:Id[]}；evidenceIds非空；sourceKey仅作同一分析输入内声明定位到已登记身份的查找键，不是身份编码 |
| M1Artifact | {artifactId:Id, mediaType:"application/json", sha256:string, content:string}；保留原生JSON输出，摘要对应content的UTF-8字节；作为来源附件外置保存，不是语义事实，不投影原始内容到查询结果 |
| M1Evidence | {evidenceId:Id, source:"input"\|"tool_output", path:Path\|null, artifactId:Id\|null, originalPath:string, sha256:string, startByte:int, endByte:int, method:Id, toolName:string\|null, toolVersion:string\|null}；input须path非null/artifactId=null，tool_output相反且附件可解；摘要为小写SHA256，原始来源字节区间[0<=startByte<=endByte<=来源字节数)，可指整文件/输出；不调用网络核验，不带源码全文 |
| M1Diagnostic | {code:Id, severity:"error"\|"gap"\|"conflict"\|"info", recordId:Id\|null, path:Path\|null, message:string}；message非空，不含私有用例/凭据 |
| M1Assessment | {assessmentId:Id, declaration:M1SubjectRef, status:"resolved"\|"ambiguous"\|"unresolved", projects:M1SubjectRef[], ruleId:Id, evidenceIds:Id[], supersedes:Id[], diagnostics:M1Diagnostic[]}；declaration为SourceDeclaration，projects仅Project；resolved恰1、ambiguous至少2、unresolved为0；依据非空；supersedes仅同声明/规则的旧assessmentId |
| M1Fact | {factId:Id, predicate:Id, subject:M1SubjectRef, value:string\|M1SubjectRef, claimMode:"declaration"\|"interpretation", condition:{kind:"true"}, evidenceIds:Id[]}；evidenceIds非空；本切片不推导配置相关/运行观测/否定主张，不能表达时报告缺口，不能删条件冒true |
| M1Coverage | {coverageId:Id, selector:string, subject:M1SubjectRef\|null, checkedPaths:Path[], evidenceIds:Id[], complete:bool, supersedes:Id[], resolvedDiagnosticKeys:string[], diagnostics:M1Diagnostic[]}；selector对应请求项，subject=null表示指定目录全域；supersedes仅同selector/subject的旧coverageId，resolvedDiagnosticKeys为被替代项已补齐缺口的规范(code,recordId,path)JSON键；complete仅表示该项本次取得无已知缺口，不证明语义真值 |
| M1Bundle | {version:"1.0.0", profile:"m1-project-discovery-1", registrations:M1Registration[], assessments:M1Assessment[], facts:M1Fact[], evidence:M1Evidence[], coverage:M1Coverage[], diagnostics:M1Diagnostic[]}；每类ID包内唯一，全部内部主体引用须登记、证据引用须存在；响应只留选中顶层事实及必要引用/依据，不能嵌入子对象定义 |

M1Fact的封闭谓词目录如下；每事实subject/value恰1，主层均E0，condition固定true仅用于上下文无关声明。project.name在同适用条件为单值，其他为多值；冲突保留双方，不最后写者裁真。名/语言是attribute，成员是association，不推归属。

| predicate | subject.kind | value | 含义 |
| --- | --- | --- | --- |
| project.name | Project | 非空string | 有来源的项目名称；不作主体身份 |
| project.language_declared | Project | 非空string | 元数据明确声明的源语言名称；规范Rust/Python分别"rust"/"python"，其他原值保留并报告支持边界；不从扩展名统计推“仅有这些语言” |
| workspace.member | NativeWorkspace | PackageSpecification引用 | 原生声明/原生接口确认的成员，不把成员自动改成Project或推所有权 |

诊断code封闭集合：INVALID_REQUEST、UNSUPPORTED_CONTRACT、UNSUPPORTED_PREDICATE、UNSUPPORTED_SOURCE、READ_FAILED、PARSE_FAILED、TOOL_FAILED、OUTSIDE_SCOPE、SYMLINK_UNFOLLOWED、UNRESOLVED_PROJECT、AMBIGUOUS_PROJECT、CONFLICTING_CLAIMS、CONTRACT_INVALID、INPUT_MISMATCH、SAVE_FAILED、COMMIT_UNKNOWN。来源定位/字段/引用校验细节放message；validate_model原全模型诊断结构仍适用，由公共适配明确映射到上述code，不能临时发明枚举。

身份登记端口（模型所有）：`register_m1(domain_id:str, registrations:list[M1Registration], kind:str, source_key:str, evidence_ids:list[str]) -> M1Registration|M1Diagnostic`。同一固定输入内已绑定sourceKey/kind必须返回既有身份并补证；新声明显式分配UUID localId，authority="c2s-local"，domainId为调用者传入的#12 M1Session.identityDomain；源键冲突kind为CONTRACT_INVALID，不猜连续性。sourceKey为获取器版本化的原生声明键；只用于查已有登记，不能输出成身份。登记表随#9提交/重读，移动host、补证或Project评估收敛不重键；跨次连续性策略不在本切片。

Registration的ref.identity/ref.kind/sourceKey不可变，evidenceIds为集合并集追加；补证不是“同ID异载荷”错误。Evidence/Artifact的同ID内容不可变；Fact同ID的主张键不可变但证据可并集。Assessment/Coverage本体同ID不可变，补证/取得进展创建新ID并显式supersedes旧ID，所有旧记录保留。supersedes必须同输入/同键、无环、目标已在提交历史或同批出现；它是存储历史链接而非主体引用，当前响应可只留链接ID不展开旧记录，不能因此捏造SubjectRef。是否可替代、哪些叶仍有效由#12 current_m1唯一规定，#9只验证/保存该受控关系。旧失败诊断附对应Coverage/Assessment或阶段事件，不作为永久bundle全局缺口复制到新当前视图；bundle.diagnostics仅保仍适用的全局契约/输入诊断。

来源观察输入M1Observations（本模型所有）={items:[{evidenceId:Id,status:"verified"|"unchecked"|"mismatch",observedSha256:string|null}]}；verified必须有相符摘要，mismatch必须有已观察不同摘要，unchecked为null；None或缺少该证据项均unchecked，不擅自读取/联网。#12根据固定输入已观察来源与实际附件存在/摘要产生，来源不适用不能靠存储命中改成verified。

校验端口沿用`validate_model(document:dict, catalogs:dict, source_observations:dict|None=None)->dict`，document在M1为M1Bundle，source_observations若非None须M1Observations形状；返回{valid:bool,stages:{catalog,structure,references,invariants各为pass/fail/partial/not_run},diagnostics:[{stage,recordRef,fieldPath,ruleCode,severity,relatedRefs,message}],consistency:"consistent"|"conflicting"|"undetermined"}。recordRef/fieldPath/message为string，relatedRefs为string[]，severity=error/conflict/gap/info；catalog/structure失败使依赖阶段not_run。valid只表示无契约error；合法冲突仍valid且consistency=conflicting。M1无算法阶段/条件SAT前置。目录校验、已知本地Schema及manifest固定摘要规则沿用§6；本轮只规划，不生成文件。

生产者/消费者：#10经register_m1产生Registration/Evidence/Assessment/Fact/Coverage/Diagnostic及M1Artifact附件；#3验证、#9存储、#8规划、#12核验/#7投影、#5计量消费M1Bundle。附件由#10产出、#9与候选同事务保存/读取，#12将附件存在/摘要核验结果以source_observations传校验器；#7只投影Evidence引用，不回显原始输出夹带额外事实，保存失败须说明附件未持久化。Assessment的工程判定规则归#10，基本类型/基数/引用约束只归本节。M1子任务只依赖本切片；父3.1原全条件依赖保留给完整任务。


## Context

Issue #3原阶段一设计：评审与候选规划；历史状态曾为 **awaiting-decision（方案A已选择，等待实施批准）**。ADR-0012已改变当前模型主轴，本文只保留原方案记录。读取基点为`18370af506d2153d0dae66a4d9536499a2b08114`。动机及范围见proposal.md；固定约束为ADR-0001/0002与两份主规格，均不修改。现有公共目录、Schema、契约校验器及产品测试尚未实现。

本轮已实际进行独立proposer/challenger首轮、第二轮交叉质询与新上下文reviewer综合；中立包、双方论证与评审记录在`docs/development/reviews/issues/3/stage-one-2026-11-01/`。记录是实际答复的结构化摘要，不是逐字转储，不声称操作系统隔离。来源案例仍仅是先前20文件选样；没有新增宏展开、构建、运行或全仓库验证。

## Goals / Non-Goals

**Goals:** 提供领域概念、身份、关系、不变量和可验证公共交换契约的完整候选设计，并将Issue范围落实到唯一tasks.md。各层含义与候选边界见下表；它们不是强制架构层。

| 层 | 语义问题 | 候选事实边界 |
| --- | --- | --- |
| E0 工程组织与协作 | 哪些工程单元、如何组织 | 项目边界评估、项目/工作空间/集合及成员；不以目录证明工程归属 |
| E1 构建装配与交付 | 依赖、配置、装配与暴露 | 目标/配方/发行/入口、需求/解析、声明输出及有证产物；声明不冒充运行 |
| E2 程序结构与接口 | 主体及访问结构 | 模块/类型/操作/签名/访问约束；签名不推纯性 |
| E3 操作行为契约 | 前提下可观察结果 | 结果/错误、状态/资源/外部效果、协议与偏序；要求不等于观测 |
| E4 实现算法与局部语义 | 哪些步骤形成行为 | 描述目的、body/区域/步骤、控制/数据/调用/捕获；局部描述不等价于完整项目 |

**Non-Goals:** 不实现查询Skill、获取器、存储、构建执行器或形式等价证明；不决定DDD聚合、事务、数据库或产品实现语言；不因五层均有数据宣称语义完整。本轮不创建下述产品文件、不安装候选依赖、不运行产品测试，不同步新增候选到主规格，不归档。

## Approaches

| 方案 | 内容与取舍 | 决策状态 |
| --- | --- | --- |
| A（已选择） | 版本化类型/谓词目录 + 通用结构Schema + 目录/引用/不变量分阶段Python校验；受限算法body单源投影，opaque保留边界。目录集中，扩展一致；代价是需要目录驱动校验和人工来源清单 | 用户本轮明确选择；实施未批准 |
| B（可行替代） | 逐谓词判别联合Schema + 跨事实校验；算法用人工文本及独立步骤/来源映射。静态工具检查更直接、初始文本表达快；扩展需改更多Schema，文本漂移需人工审查 | 保留；如选择B，须修改当前算法delta的单源投影要求并重算批准令牌 |

两者都遵守已确认基线，不以无类型三元组作为唯一替代来排除B。用户已选择方案A，依据见评审目录scheme-decision.md。以下设计作为A的阶段二规划依据，**方案选择不等于实施批准**；本段为历史单Issue门禁；当前由#4/#13整体门禁取代：先冻结整体规划集合，再取得绑定新集合摘要的独立产品开发批准，旧令牌不能单独进入阶段二。任何改变范围或行为的修订均需重新规划和批准。

## Decisions

### 1. 统一语言与身份：C01、C02

独立引用的对象登记为Subject；按内容判等的标量、参数模式和条件等为值。可独立引用的记录与普通属性值按查询需要区分。IdentityDomain表示显式登记的身份命名域，可为来源声明域、工程域或描述域；它不是文件目录，也不自动表示Project。Subject身份为`{authority, domainId, localId}`，三项均显式登记，kind单列校验，层号不入身份。名称、路径、行号、提交、摘要只定位证据，不能单独构成身份。相同身份记录不得出现互斥kind。

Project表示有边界依据的软件工程单元；PackageSpecification表示发行/解析单元；NativeWorkspace表示原生协调声明；CoordinationGroup表示显式协作集合；AnalysisScope表示本次选择。它们互不替代。SourceDeclaration记录已见声明；ProjectBoundaryAssessment记录声明/工程单元到候选Project的映射：resolved恰一确认引用、ambiguous至少两个候选、unresolved无确认引用。候选映射带证据，不能当已确认所有权。

SubjectRef为`{identity, kind, contextRef?}`，不再把尚未确认的项目ownershipScope强制填入引用。身份域与`projectMapping`独立；来源域不能用于要求Project的谓词角色。映射变为resolved后只补关系，不重键或复制既有主体。匿名/重载/生成实例使用显式引入或变换应用登记及局部区分符；无法确定连续性就保留歧义，不承诺自动重命名识别。

上下文是已登记单值键的部分赋值；同键矛盾值为`CTX_CONTRADICTION`错误，缺键合法但解释可能未定。指称依赖上下文时保留限定引用，事实值依赖上下文时记录条件化主张，不复制D。首版比较仅针对同主体、同谓词、相同角色与目录声明的可比较claimMode；不同模态不默认互相否定。

| 情形 | 输出语义 |
| --- | --- |
| 缺配置，互斥T1/T2分别允许不同值 | 解释歧义/未定，不算事实冲突 |
| 同确定适用上下文，单值属性出现不兼容主张 | 保留双方及`CONFLICTING_CLAIMS`；不静默删一方 |
| 多值谓词有不同值，或相同值多证据 | 合法并存，不自动冲突 |
| 条件重叠无法判定 | `POTENTIAL_CONFLICT`缺口，不声称已证冲突 |
| 零适用主张 | `NO_APPLICABLE_CLAIM`；不足以推出不存在或不适用 |

### 2. 目录、组成与引用：C03

Semantic谓词有一个primaryLayer；Provenance谓词无主层，来源与覆盖横贯各层。条目定义predicateId、含义、角色方向/类型、每事实基数、跨主张可比较性/单值性、约束及relationKind。relationKind取attribute、composition、association；不由层号或图可达性推导。

首批组成角色：`program.contains(container, declaration)`、`behavior.has_body(description, body)`、`behavior.region_member(region, step)`；算法步骤以`{algorithmIdentity, stepId}`独立定位，局部stepId唯一。workspace_member、group_member、project_mapping、dependency、alias_of、entry_binds、implements、calls、captures、generated_from均是关联，不据此转移所有权。共享组成不推出聚合或唯一管理归属；方向和适用kind由目录约束。

完整SemanticFactSet可含subjects、facts、evidence、coverage、algorithms与独立body/region/step记录；其存在不授权响应整包返回。顶层载荷只作为模型形状fixture，不定义完整请求/结果协议，也不开发查询遍历或深度逻辑。内嵌白名单为Scalar、Enum、QualifiedName（字符串序列）、Parameter（index/name/typeRef/mode）、Signature（参数值序列、返回typeRef）、已登记Condition。TypeRef引用类型主体或目录原始类型标记，不内嵌主体定义；其他对象通过引用表达。Sequence逐元素、DefinedRecord逐字段递归检查白名单，禁止Fact/Subject定义/完整body藏入值。

首批谓词沿用导入候选§9及原design清单的语义，并补上述组成角色、项目评估及状态类型；每一条均须在predicates.json展开，不能把表格缩写当ID。字段语法不得先于其类型、角色和不变量定义。

### 3. 工程与依赖：C02、C04

原生目标、配方、发行规格、输出规格、入口、任务及产物观测分别记录。目标声明的项目映射可以未决；确认管理归属必须有明确Project证据，不能强造项目满足约束。别名解引用到同一目标，不复制实现；workspace命令若仅是成员选择器不造目标。项目/包/目标关系分别保留原生声明与映射，多个workspace依各工具实际规则，不预设普遍多重成员。

DependencyRequirement记录消费方、用途、阶段、路径/版本及条件；DependencyResolution记录需求引用、提供方或候选、配置、解析可见范围、状态与证据。resolved恰一提供方，ambiguous至少两个，unresolved无确认绑定。相对AnalysisScope的位置inside/outside/unknown单独表达，不入需求身份。内部引用要求在包内登记；范围外引用须显式external标记、完整身份及来源/未核验说明，不伪造本地定义，也不把非法内部悬空引用伪装成外部。

首版可满足性片段：完整声明域的Boolean/Enum键，eq/neq、True/False、All/Any/Not。按共享键枚举赋值，候选上限为**4096种组合**，包括4096，超过则`CONDITION_BUDGET_EXCEEDED`未判定。上限是本轮代理提出的实现限额，待方案确认，不是用户既有要求。对未登记域、SourceCondition、无限域、不支持运算保留原式并报未判定，首版不尝试从部分未知式给确定结论。

条件求值使用三值真值表（空All=True，空Any=False）；可满足性独立输出sat（附见证）、unsat（已支持完整域穷尽）、undetermined（片段/限额原因）。某环所有边条件的合取sat才报可同时激活；原图不删边，工程违规另需规则，不把项目汇总环等同目标构建环。

### 4. 状态、证据与否定：C06

事实保留predicateId、角色值、条件、claimMode、evidenceRefs及可选derivation。claimMode为declaration/specification/static_may/static_must/observation/interpretation；不按它们排序裁真。证据记录来源、内容标识、定位、方法及Supports/Refutes/Limits角色；推导引用规则及前提，引用缺失是契约错误。来源核验状态由调用方提供可选观察数据；无数据时报unchecked，不执行获取器或网络抓取。

| 维度 | 候选取值/规则 |
| --- | --- |
| 呈现边界（形状例） | ref_only / expanded；不据此更改获取状态，不实现响应协议 |
| 获取状态 | obtained / not_acquired / unsupported / not_applicable；not_applicable须适用性依据 |
| 主张极性与诊断 | positive / negative；ambiguous、conflict、potential_conflict关联主张及条件，非获取枚举 |
| 覆盖 | 绑定对象/谓词族/上下文，记录checked/excluded inputs、缺口与实际方法 |

合法组合：obtained+ref_only；not_acquired或unsupported可含被引用身份但不能捏造所指事实；negative必须有独立否定依据，不以ref_only、空字段或缺定义推出。歧义与冲突可以分别出现在同一包，不能由单一success枚举吞并。

否定闭合检查首批只接受`enumerated_input_membership`（明示完整有限输入清单内是否存在某成员）和`registered_catalog_membership`（指定版本目录内是否存在某条目）。检查记录必须含有界命题、scope/context、完整输入ID列表、逐项结果、方法、人工审定状态及未解决缺口为空。不能据此推出不存在动态调用、宏效果或全项目行为。校验器只检查依据结构/引用/条件一致，不能证明来源实际穷尽；未审定或能力不足保留缺口，不替人裁真。哈希仅核对字节一致。

### 5. 算法、语言机制与两段验收：C05

AlgorithmDescription保持独立描述身份，purpose取normative/current_implementation/abstract；含问题范围、输入输出、契约、实现引用、上下文、来源及省略边界。管理归属与参与项目分开，可跨项目，不为无自然管理项目造workspace。OperationContract的前提/结果/错误/状态与资源效果/交互/时序及观察边界独立于签名。

首版结构种类：sequence、bind、assign、compute、select、loop、call、return、raise、handle、resource、concurrent、synchronize、opaque。Region和Step独立记录与引用，控制边注明目标，数据边类型明确。compute保留类型/数值规则/求值次序；缺证用未知字段，不默认数学整数、左到右或串行。opaque必须携来源、影响范围、未知项和保留的输入输出/外部效果边界；它是受限契约的显式缺口，不是完整解释器或全语言支持承诺。

宏/生成记录定义、应用、输入与多对多生成来源；未展开只记应用及缺口，不能造AST。注解/属性记录附着、阶段及已证处理效果；Click装饰器按运行调用/对象替换及callback区分。闭包定义、可调用值、捕获位置/方式和生命周期分开；let/if let绑定有模式/初始化/作用域/路径可用性，不等于赋值；语言差异无法统一时保留扩展或opaque，不只存语法名字。

验收分开：

1. 来源→body：R5、C5、P7各人工审定固定定位清单，逐项记录关键分支/失败/效果/回调/未展开过程；每项映射Step、effect或显式gap。未审定不能通过。删除Rust失败传播、C++parse_error结果、Python零规格/第二通配错误的反例，应被该清单发现，即使body内部及文本映射仍完整。清单自身正确性仍需独立审查，不作自动等价证明。
2. body→伪代码：按规则生成文本与步骤段落映射，保留分支/循环/错误/效果/opaque及省略项。映射有效不能替代上项；局部摘要不声称完整项目算法。

### 6. 技术、接口与交付：C07

推荐JSON Schema 2020-12做结构层，版本化types/predicates目录与Python做角色/引用/不变量层。拟新增开发依赖`jsonschema==4.26.0`（官方release v4.26.0已核对，见评审资料），本轮运行环境未安装，也未执行安装或验证。阶段二生成`requirements-semantic-model.txt`并安装；所有自维护代码用Python3，Node/OpenSpec依赖和产品语言不变。Schema引用仅使用随包登记的本地资源，不自动联网解析未知$ref；不支持目录/载荷版本为明确错误，不承诺旧版本迁移或历史查询。

| 未来路径 | 职责 |
| --- | --- |
| contracts/semantic-model/types.json、predicates.json | 类型、身份域/上下文、谓词、组成与内嵌值目录，version=1.0.0 |
| contracts/semantic-model/fact.schema.json | SemanticFactSet、引用、条件、证据、覆盖和状态结构 |
| contracts/semantic-model/algorithm.schema.json | 契约、算法、body/region/step及来源/投影映射结构 |
| contracts/semantic-model/rules.md | 公共语义、诊断、条件/身份/否定/投影规则 |
| src/c2s_semantic_contract/validation.py | 纯数据契约校验，不执行工具或查询 |
| src/c2s_semantic_contract/projection.py | 算法body可读投影及来源/投影清单检查 |
| src/c2s_semantic_contract/__init__.py | 只导出下述接口 |
| tests/semantic-model/test_contracts.py、test_algorithms.py、fixtures/ | 正反例、来源清单与静态顶层形状例 |
| docs/domain/semantic-model-contract.md | 最终获批领域模型及公共契约说明，按当时五种观察视角和统一语言组织（历史候选） |
| requirements-semantic-model.txt | 校验开发依赖固定项，不改变package版本 |

#### 6.1 首版目录包与自校验（builder-check修订）

推荐A首版是**封闭发行目录包**，不支持调用方在同版本任意增删类型、谓词或约束。`catalogs`参数只可传入随交付物固定的types/predicates记录；预期manifest从受信任的本地交付物读取，不采纳调用方自报的manifest作为授权依据。`catalog.schema.json`先校验传入目录自身的结构，随后检查目录类型/角色引用、Semantic主层、版本组合和ruleId是否受支持，再核对固定发行包的规范JSON摘要。未知ruleId报RULE_UNSUPPORTED；同版本目录内容不同报CATALOG_BUNDLE_MISMATCH，不静默接受或执行目录内代码。目录错误使依赖的事实/算法阶段not_run。

新增未来交付：`contracts/semantic-model/catalog.schema.json`（元目录Schema）、`catalog-manifest.json`（目录/Schema摘要和ruleSetId=semantic-model-1.0.0）。规范JSON为UTF-8、键排序、无多余空白、ensure_ascii=false；摘要用SHA-256。manifest是交付一致性检查，不是事实真值或输入来源的信任证明。全部目录及载荷version为1.0.0；发布后改变公共含义必须另立版本/变更，不能同版替换，不因此承诺迁移服务。

首批constraintId只允许固定Python规则注册表：KIND_MATCH、ROLE_CARDINALITY、INTERNAL_REF_EXISTS、DOMAIN_UNIQUE、CONTEXT_KEYS_SINGLE_VALUED、PROJECT_MAPPING_CARDINALITY、LAYER_CLASSIFICATION、INLINE_WHITELIST、STATE_COMBINATION、CLOSED_NEGATIVE_BASIS、ALGORITHM_STEP_REFS、CONDITION_SUPPORTED_FRAGMENT。允许表外规则只可通过后续获批变更、实现及测试新增；本版不提供通用规则语言或目录内eval。运行时可扩展目录是另一个可行方向，但需要元约束语言和兼容规则，首版不承诺，保留待后续提案。

候选接口（输入/输出均为已定义公共数据记录）：

- `validate_model(document: dict, catalogs: dict, source_observations: dict | None = None) -> dict`：返回`{valid, stages, diagnostics, consistency}`。stages各为pass/fail/partial/not_run；diagnostic有stage、recordRef、fieldPath、ruleCode、severity、relatedRefs、message。valid仅表示无契约error，显式语义缺口/未核验单列；结构错误后依赖阶段not_run，不能称通过。
- 同时适用的矛盾主张不从包中删除；若主张载荷均合法则valid可为true，consistency=conflicting，diagnostic severity=conflict并列双方。身份重复、类型/内部引用错误等为error使valid=false；结构合法不等于语义完整或真值一致。
- `project_algorithm(document: dict, algorithm_ref: dict) -> dict`：返回`{text, stepMappings, gaps}`，只投影指定算法body，不是查询入口。
- `check_source_coverage(document: dict, checklist: dict) -> dict`：返回`{reviewed, uncoveredItems, declaredGaps}`，只核人工清单与body的对应，不自行读取源码推断完整行为。

## Risks / Trade-offs

- [Risk] 来源域被偷换成Project → 角色类型反例与映射前后身份保持验收。
- [Risk] 内嵌值偷渡递归展开 → 白名单递归检查与顶层静态形状反例；查询运行仍另行验收。
- [Risk] 有限条件判定冒充一般SAT → 固定片段/4096限额及undetermined，不虚报循环违规。
- [Risk] valid被当作真值或完整性 → 分开error、conflict、gap、unchecked、not_run与人工来源验收。
- [Risk] 旧自动Runner只允许issue-3-*路径 → 本轮按用户明确授权的人工Work会话修改既有变更，绝不另建重复模型。当前Runner不能直接承接该既有变更；不修改脚本/权限来绕过。后续可在Work显式批准后手动apply；若要求自动Runner实施，须先另行授权修复路由。

## Migration Plan

原规划阶段仅交付候选proposal/specs/design/tasks、Battle/映射/校验及绑定输入/工件摘要的批准令牌，历史状态为awaiting-decision。正式主规格与导入原件字节不变。方案选择与实施批准分别记录；仅确认A不自动实施。选择B或改字段/条件/范围时重算令牌，不复用旧批准。阶段二获得明确批准后才读取apply指令并按tasks推进；本轮不调用产品实施技能或安装其依赖，不归档。

## Open Questions

暂无对推荐A隐藏的实现阻塞假设；历史记录显示方案A曾获用户选择；该选择不再定义当前实体模型主轴。Q01–Q05的裁决入口及替代见本目录review-map.md与评审报告。构造命名和函数内部组织可由实施者在已批准行为下决定；任何改变候选公共行为的选择不得自行归入“小实现细节”。

## ADR-0007查询澄清同步

“顶层最小”限定请求响应范围，范围内完整取得本次所需语义实体事实并如实报告缺口。类/成员/函数保留为可请求的源码构造视图，须与语义实体区分。E0–E4仅作观察视角，其主组织地位已被ADR-0012替代。域模型仍只提供类型、身份、引用与事实形状支撑，完整查询/补充分析/双输出由#7/#8实现；不能用模型fixture声称产品已完成。

## ADR-0013 当前约束（2026-11-08）

实体及类型化关系组织事实；E0–E4仅为可选观察视角。保留条件、来源、引用和有界覆盖检查，不建立DDD聚合或业务边界；旧模型目录仅在兼容范围使用。 依据：`docs/decisions/0013-非DDD语义事实模型.md`。历史执行记录中的DDD或旧模型表述不构成现行约束。本轮只进行文档修订，产品重构完成状态不变。
