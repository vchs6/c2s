# M1公共契约最终交叉设计审查

**最新结论（F1–F4限定复核）：PASS，spec/plan质量通过。** 原始审查记录保留如下；本结论及边界以文末限定复核节为准，不是产品通过或全部交付门禁通过。

日期：2026-11-02。审查对象：`m1-contract-refinement.md`、`m1-contract-review.diff`及九个change当前M1 design/tasks；按`docs/domain/foundation.md`与正式query/lazy/scope/quality/model规格核对。仅规划质量审查，不是产品验收、隐藏用例审查或交付2.1冻结结论。未重跑作者已记录的CLI/测试，未访问私有测试区、凭据或产品运行环境；唯一写入是本报告。

**Verdict：需局部修改后复核。** 26个记录的单owner安排成立，M1领域切片与已确认需求没有发现需重开用户决定的冲突；25个原任务子ID也未发现显式实施依赖环。但是“所有跨模块参数/结果已经闭合”尚不成立。以下是本轮一次性列出的重要文字契约缺陷，修复范围可以保持在M1，不需要冻结M2–M4。后列真实就绪证据缺口与这些缺陷分开处理。

## 一、文字契约缺陷

### F1（重要）：计量档案不足以履行其自身比较、未知总体与失败记录承诺

位置：`define-semantic-analysis-quality-goals/design.md:8–12`，关联`survey-semantic-acquisition-capabilities/design.md:7`、`design-semantic-fact-coordination/design.md:9–13`。

- `compare_m1`只有两个M1Profile输入；档案只保留`obtainedFactIds`，没有事实载荷或规范主张键，不能计算承诺的“跨运行ID不同用#9规范主张等价键”差异。`gapCodes`也无法区分同code出现在不同请求项/路径的缺口变化。会话虽然含store路径，但没有规定比较时重读、内容基点与未保存结果的取得端口，保存失败的档案尤其无法靠重读恢复事实。不能以实现时私自读全局缓存补上公共接口。
- `profile_m1`只接`inventory:list[M1Entry]`，漏掉获取端已有的`inventoryComplete`。空列表或只含已成功枚举项的列表既可能是完整盘点，也可能是尚未盘点/中途失败；函数无法可靠按契约决定fileCount/sourceBytes为0、已知值还是null。复用路径没有重新盘点时也需明确使用哪份已验证盘点或标未知。
- `M1Profile.session`及`profile_m1.session`强制非空，但`open_m1`允许失败，规范化阶段也可以没有合法M1Query。现有“失败也入档案/全链记录”的承诺没有覆盖这些前置失败的合法编码。若仅记录已接受且成功建session的请求，应明确计量总体和被排除项，不能仍声称覆盖全部失败。

修复方向：在#5唯一owner处选择最小的事实/缺口比较摘要或显式比较输入，并定义不可取得时的不可比原因；传入盘点完成性/盘点来源；闭合前置失败的档案形状或明确总量边界。另需明确跨分析比较身份域：#9等价键含主体身份，新analysis随机身份不能仅因事实ID不同就跨域直接判等；允许明确不可比，不要求现在实现跨次身份连续性。对照中的策略标记也需有明确输入位置。

### F2（重要）：补缺后“当前有效覆盖/评估”的选择规则缺失，注册补证与拒绝规则也有歧义

位置：`design-incremental-semantic-fact-storage/design.md:14`，`design-semantic-fact-coordination/design.md:9–11`，`define-layered-semantic-fact-model/design.md`的M1Registration/M1Assessment，`design-lazy-semantic-fact-construction/design.md:7`。

存储允许旧不完整Coverage与新完整Coverage分别留下，并指定“读取按#12规则选择有效记录”；#12只写核验coverage，没有给出这条选择规则。Coverage自身没有代次/替代关系。获取规则同时允许工程评估从unresolved/ambiguous补证收敛为resolved，但存储没有Assessment等价、补证、替代或有效视图规则。这样同一固定输入、同一声明补缺成功后，#7仍可能投影旧未决评估/诊断，#8也可能继续生成Need；反向实现为一见complete就忽略其余记录，又可能吞掉真实冲突。

此外模型登记端明确允许既有Registration补evidenceIds，存储却笼统规定“不同载荷同ID拒绝”；按整条Registration载荷解释会拒绝合法补证。需界定哪些身份/定位字段不可变，以及证据关联如何并集而不成为同ID异内容冲突。

修复方向：由#12明确有效覆盖/评估视图的确定性选择、保留冲突及历史失败诊断与当前缺口的区分，由#9明确持久记录如何支持该视图与Assessment去重，并显式允许Registration的合法补证。这里只解决固定输入的取得进展，不引入源码热更新或跨次撤证政策。

### F3（中等）：混合支持/不支持select的正常化交接有两种相反解释

位置：`define-semantic-fact-query-contracts/design.md:9,13`，`design-lazy-semantic-fact-construction/design.md:7`。

M1Query说select“仅支持”三个值，`normalize_m1`返回`M1Query|M1Diagnostic`，却同时要求未知select逐项诊断、支持项继续。若未知select被视为正常化错误，单个Diagnostic返回会丢掉继续执行的规范请求；若保留未知字符串返回M1Query，又需明确它是合法的“尚待支持性检查”的规范请求，而不是违反Query契约。#8已经有逐项未知select诊断出口，可以复用，但目前#7/#8的责任边界尚未写定。

修复方向：选择并明确一种路径。例如结构有效的select保留全部字符串交#8逐项诊断，只有结构/contract错误才返回单个Diagnostic，并明确结果requested和partial/unavailable/退出码；或定义能同时携带规范请求与诊断的返回。无需增加第二查询协议。

### F4（中等）：存储规范化后的身份/引用没有明确回到本次投影的路径

位置：`design-incremental-semantic-fact-storage/design.md:6,10,14`，`design-semantic-fact-coordination/design.md:11`，`define-semantic-fact-query-contracts/design.md:13`。

存储承诺等价主张返回原factId，并把证据/附件等引用重写为已存规范ID。但`commit_m1`仅返回M1Receipt的addedIds/existingIds列表，没有候选→规范ID映射或规范bundle；协调顺序直接由commit进入project，未说明成功提交后重读/重建哪个bundle。不能确定#7接收到的是候选ID版本还是持久化规范版本，也未定义已得暂存与已存包合并后的投影输入。保存失败路径有暂存原则，但无法替代成功/去重路径的交接。

修复方向：明确由谁、通过何端口形成投影用规范bundle；可以提交返回映射/规范结果，也可以#12成功后读取并按固定规则融合，只需选择一种。unknown经lookup确认成功时应走同一路径，失败仍使用已校验暂存并如实标未持久化。不要求公开原生JSON内容，也不要求新增复杂事务机制。

## 二、已成立的设计质量结论

- **26个公共记录单owner成立。** 模型11、查询3、构造2、存储3、获取2、质量3、Token1、协作1，总计26；架构重导出而不复制定义。M1Observations也归模型，原生附件M1Artifact由模型定义、获取生产、存储保存，职责清楚。上面的F1–F4是字段/结果流和状态规则问题，不是否认owner安排。
- **Project没有被Package或Workspace偷换。** SourceDeclaration、PackageSpecification、Project、NativeWorkspace分别登记；workspace.member的value明确为PackageSpecification；工程Project需独立Assessment与规则依据，目录/包名/workspace成员均不自动推出Project。Rust/Flit判定是可复核的技术规则，不是新用户确认。尚未覆盖所有工程形式通过缺口表达，符合最小切片定位。
- **语言声明和顶层范围清楚。** 只承诺明确声明，不从扩展名推出语言全集；三个选择项不默认递归展开关联包或更深事实。原生stdout作为附件保存、结果返回引用，避免以证据夹带完整语义图。确定性Markdown与JSON同源，保存结果与语义完整分列，符合正式query规格。
- **目录全域、host/target与成本原则成立。** 明确包含忽略/未跟踪/嵌套/测试/示例/隐藏目录；symlink、越界、不可读、未支持均披露。必要盘点不等全语义预构造。外置副本保持源不变，host和项目target分开，未知target不从host补；全平台和负载不预先虚报。F1需要修正的是计量数据通路，而非要求用户补SLO或语义金标。
- **基本增量/失败边界方向正确。** 同次分析、稳定身份、规范主张/证据去重、SQLite自洽提交、保存失败仍返事实、unknown先查回执、进程暂存不保证崩溃零Token，均不违反既定需求。F2/F4是实现这些承诺所需的最后交接规则。
- **25个原tasks子ID保留且未勾选，未见显式实施依赖环。** 获取试验3.1.1→3.2.1可先执行；模型及各owner公开契约作为输入后，能力选择、规划、获取、存储、投影、协调、装配可分步实施。记录类型互相引用不等于实现任务互相依赖；任务已明确区分“公开契约”与完整实现。M1节覆盖历史“另批/全量先冻结”，未重新要求M2–M4全部冻结。上述缺陷应绑定已有对应子ID修正，不创建第二套产品任务计划。
- **没有发现隐藏测试泄露或伪产品完成声明。** 变更是公开记录/签名/验收边界，未包含隐藏suite内容；报告未以文档校验冒充产品验收，候选产品0.1.0与模型/开发工具版本分开。五角色真实隔离仍保留门禁，未因设计细化而宣告产品通过。

## 三、实际就绪证据缺口（与文字缺陷分开）

1. Cargo选定metadata命令/版本/格式字段、离线行为、外置副本映射/副作用与Flit入口规则仍需获取3.1.1/3.2.1对固定regex/click基点的公开实证。已有AST/CRG探索不自动证明这些路径。缺实测阻止声称路径已验证，不否定Rust/Python需求或最小切片设计本身。
2. 目录全范围和异常项、实际复制/读取/写入/耗时仍需真实记录；未测host/target组合和负载继续标unknown。无需等所有候选工具、全部平台、M2–M4算法一起完成。
3. 交付2.2/2.3的五角色隔离、合法制品交接、独立runner入口及实际验收证据仍须协调者绑定。它们不是本次审查能够补造的证据，不应将本报告当作产品就绪或冻结证明。

作者已报告的21项OpenSpec校验、artifact检查与diff检查可支持文档结构质量；本审查没有重复运行，也不将其升级为API/产品实测。结论限于：认可M1范围、领域方向、owner与任务拆分；F1–F4修正后可重新核对接口闭合，所选路径实证及隔离门禁仍按原任务推进。


## 四、F1–F4限定复核（2026-11-02，最新结论）

复核对象仅为`.superpowers/sdd/tasks/m1-contract-f1-f4.diff`、作者追加的细化报告及相应当前M1节；另只读`.local/m1-native-runtime/result.json`了解协调者新增的公开原生试验。未重跑CLI/测试，未访问私有区，没有扩大到M2–M4或产品验收。

**Spec/plan verdict：PASS。** F1–F4的实质接口缺陷均已闭合，修订未发现新的重要领域或依赖破坏；原“需局部修改后复核”结论被本节替代。仍有一句不影响实现路径选择的架构摘要应同步清理，见下文。此结论不表示产品实现、隐藏验收或五角色隔离已通过。

| 原审查项 | 限定复核结果 |
| --- | --- |
| F1 计量输入/比较/前置失败 | 已闭合。M1Profile保存由唯一#9 fact_key_m1产生的自包含factSummary、逐项gaps和strategyId；比较只消费这些数据，跨inputId/identityDomain明确不可比。profile_m1显式接受盘点归属、完成性、来源与entries，未盘点不再等于完整空目录。可空query/session及received/accepted时间、备用requestId和事件关联覆盖规范化/open失败；总体边界明确，不靠隐式存储重读恢复保存失败的事实。 |
| F2 当前视图/登记补证 | 已闭合。模型区分不可变载荷与可并集证据；Assessment/Coverage显式supersedes，获取器引用当前叶生成有依据的进展，存储保完整历史并规范ID，#12 current_m1唯一验证替代边并选当前叶。未决/冲突保留、旧失败仅历史/事件、全部有效叶完整才可复用，#8/#7消费同一视图。规则仍只处理固定输入的取得进展，没有引入源码更新策略。 |
| F3 未知select交接 | 已闭合。结构有效Query保全部非空字符串，#8逐项能力诊断，#12通过project_m1.request_diagnostics传#7；混合项继续、全未知不获取/不提交、退出2，结构/contract错误才64。requested、语义状态与诊断的去向已明确。 |
| F4 规范ID回传 | 已闭合。#9 canonicalize_m1明确暂存与已存数据的规范合并；commit/lookup成功后必须重读同session且generation不早于回执的规范历史，经current_m1再投影。失败/未知使用已校验暂存合并视图且不冒持久化；规范重读失败回unknown。#7不再凭回执ID列表猜映射。 |

动态version澄清合适：M1未请求版本事实，已有足够名称/Flit入口依据时不因无关version阻断整个Project；真正影响本次名称、语言或入口的动态映射仍报受影响项缺口。此处没有把Project等同Package、增加版本查询或声称动态version实际反例已经运行。

26记录的owner及25个原子任务ID保持原安排；新增fact_key_m1/canonicalize_m1/current_m1是各原owner端口，未复制公共类型或创建第二套任务。任务的修改绑定原F1–F4验收边界，未增加M2–M4全部冻结依赖；按公开契约分步实现仍可行。新增supersedes是存储历史链接，响应仅留历史ID而不展开旧记录，不改变请求顶层范围。

**非阻断编辑清理：** `design-semantic-fact-skill-architecture/design.md`的M1末段还留“未知select由#7诊断”，应与紧前新增段及#7/#8的精确端口统一为“#8判定，经#12传递，#7呈现”。本轮已把这句告知协调者。详细producer/consumer与签名一致，因此不重新打开F3的实质接口缺陷，也不要求为这一句新增实施任务或重新跑CLI。

原生实证更新：协调者结果记录了Linux x86_64/Python 3.12.14，固定regex基点的Cargo 1.99.1 metadata格式1命令成功、7个成员均能关联packages、目标路径均在副本内且存在；固定click基点的Flit绑定得到唯一`src/click/__init__.py`入口。两个副本没有排除目录项，原始内容/副本内容不变及Git干净均有结果字段，盘点和复制成本已记录。因此原第三级证据缺口中的“完全没有所选原生成功路径证据”已经被这次结果补充，不能继续重复列为全空白。

该JSON也明确没有覆盖畸形/不可读/symlink/工具错误/其他backend、没有编译或其他host证明，click.version_dynamic=false。本复核仅接受其公开工具接口、范围盘点与副本成功路径的有限证据，不升级成完整M1获取器/持久化/失败恢复或隐藏产品验收。剩余异常与隔离验证仍属于原实施/交付任务，不是已确认需求或本次通过的规划质量缺陷。
