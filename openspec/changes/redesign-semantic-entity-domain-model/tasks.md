# Tasks

## 1. 公共领域与版本化契约

- [x] 1.1 **先决：用户审核并批准本变更设计。** 输入：本目录提案/规格/设计文档及`docs/superpowers/specs/2026-11-07-semantic-entity-domain-model-design.md`。输出：用户确认记录。验证：确认覆盖实体中心、E0–E4视角、属性/子实体查询规则、注册表身份和旧版兼容；用户已于2026-11-07明确批准按此方案进入实施。负责：领域评审/用户确认。
- [x] 1.2 固化领域语言和对旧决策的替代关系。依据：1.1及用户要求。输出：`docs/domain/semantic-entity-model.md`、新ADR及本变更内`semantic-fact-model`/`semantic-fact-query`/`lazy-semantic-fact-construction`增量规格（归档时进入主规格）。验证：`npm run validate`与本变更严格校验通过；旧ADR不改写，新ADR指出精确替代范围；模型/规格的实体、属性、子实体、源码构造、视角和状态词汇一致。负责：领域规格维护；失败条件：规格矛盾或校验失败。完成证据：2026-11-07，23项OpenSpec全库校验通过，本变更严格校验通过。
- [x] 1.3 定义`semantic-entity-model-1`模型档案类型、谓词、结构模式和校验。依据：语义事实模型变更规格。输入：领域词汇和现有结构模式/目录。输出：`contracts/semantic-model/`中新版本结构模式、类型/谓词目录及版本清单；`src/c2s_semantic_contract/validation.py`的实体模型校验。必须定义实体身份范围、来源连续性候选、属性类型/值域、关系端点、主张/证据/覆盖/观察视角。验证：正反夹具覆盖合法结构、实体类型冲突、范围错配、悬空关系/证据、连续性未决和无证值域拒绝；`PYTHONPATH=src .local/analysis-venv/bin/python -m unittest discover -s tests/semantic_model -v`通过。持久注册表复用/并发、源码移动后候选生成、注册表丢失、歧义人工映射和属性提升跨存储边界，分别由2.2/3.1测试验证。负责：契约实现与公开测试；失败条件：任一结构、身份或引用测试不通过。完成证据：实体档案结构模式/目录/清单已固定；12项新测试、86项模型测试及121项仓库测试通过。

## 2. 源构造解析与语义实体构造

- [x] 2.1 建立语言无关源码构造（`SourceConstruct`）和工具解析契约。依据：语义事实模型的源码构造要求。输入：Python抽象语法树、Rust Tree-sitter、Cargo和已选工具结果；输出：统一源码构造、成员组织、字节定位、语言/工具来源、版本和解析缺口。修改：`skill/src/c2s_skill/acquisition.py`、`capability_matrix.py`及对应测试。验证：Python/Rust夹具覆盖类/结构体/字段/方法/函数/枚举/泛型/宏/注解/λ匿名函数/闭包；保留不透明语法错误边界；项目根目录命名空间隔离；源跨度可逐字节复核。`PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -v`通过。依赖：1.3。负责：获取器实现与公开测试；失败条件：源定位/来源不准确或输入构造丢失。完成证据：固定Click/regex测试解析全部受支持源文件；Skill全套132项测试通过。
- [x] 2.2 实现证据驱动的语义实体构造和属性值域。依据：实体/属性/映射要求。输入：2.1的源码构造（`SourceConstruct`）与文档/测试/工具证据；输出：项目/模块/能力/数据/计算实体候选、属性、关系、推导和源映射。修改构造器及投影调用。验证：类成员变量分别映射到数据属性、成员方法映射到计算实体；枚举/范围/校验提供值域依据；裸`String`不推语义类型；同名/同路径不合并；冲突与无映射源码构造保留；证据不充分时生成未知/缺口；属性提升保留稳定来源映射。依赖：2.1。负责：语义构造实现与公开测试；失败条件：无证据主张被当成确认事实或证据丢失。完成证据：新增候选构造器并把源码/文档证据路径、SHA-256、字节区间、解析器版本写入证据模型；项目清单名、枚举值、显式文档章节可生成暂定候选，未发现模块/能力时明确输出缺口。裸实现类型保持语义类型未知；类/结构体字段分别作为数据属性证据，函数单独映射计算候选；源码映射与候选身份分离。`test_entity_construction.py` 5/5、构造器+解析器定向测试27/27、实体契约14/14通过。局部验证不等于SQLite持久化/查询已完成；相关任务为3.1、4.x。
- [x] 2.3 建立`TestEntity`和验证目标关系。依据：测试实体要求。输入：测试声明、调用、断言、预期结果证据；输出：测试实体、验证的`SemanticEntity`或`FactClaimRef`、测试入口`SourceConstruct`。验证：多测试可验证同一行为主张；测试实体与测试函数身份分离；未知目标保留缺口；只基于测试源码的正反夹具通过。依赖：2.1、2.2。负责：测试映射实现与公开测试；失败条件：把入口当目标或无依据声称覆盖。完成证据：测试函数构造独立暂定`TestEntity`；Python断言/raises与Rust断言宏作为验证信号；仅当调用目标唯一解析到本地计算候选时生成暂定`verified_by`关系，多测试可共同指向同一目标，未知目标保留`TEST_TARGET_UNRESOLVED`缺口。候选构造测试7/7通过。

## 3. 仓储、注册表及旧版兼容

- [x] 3.1 SQLite持久化实体模型档案和原子注册表。依据：新模型档案与按需构造要求。输入：1.3 结构模式、2.1/2.2领域记录；输出：`skill/src/c2s_skill/semantic_store.py`中的模型档案隔离实体、属性、关系、构造、映射、主张、证据和覆盖范围持久化及索引。验证：原子注册、并发重复键、稳定回读标识、完整payload往返、引用闭合、补证合并、冲突保留和崩溃回滚；M1/旧完整模型档案既有测试继续通过。依赖：1.3。负责：仓储实现与公开测试；失败条件：悬空引用、身份重键、半包可见或数据字段丢失。完成证据：新增`SemanticEntityStore`及独立`semantic_entity_archives`/`semantic_entity_registry`/`semantic_entity_index`表；档案全量通过实体模型契约验证后在单事务写入并重建索引，身份注册以范围+源码键确定性派生身份、并发互斥、证据追加合并、类型冲突拒绝。回读完整payload、无效引用拒绝、冲突合并回滚、稳定身份和8线程并发补证测试通过。全仓测试123/123、Skill全套146/146、OpenSpec全库23/23、工件检查通过。
- [x] 3.2 在隔离模型档案/测试夹具中实现旧档案导入/查询/确定性导出。依据：设计兼容决策。输入：M1和`semantic-fact-model-1`真实/测试夹具仓储；输出：旧记录受限导入、旧档案投影及无法映射字段的信息损失/缺口诊断；M1发现入口仍独立，开发期间旧默认写入路径保持不变。验证：已知身份映射可迁移；孤立`SourceDeclaration`不自动变为`SemanticEntity`；导出确定且不静默丢字段；旧命令行接口兼容选择器回归；备份/重复导入可恢复，模型档案不得混写。不得在本任务切换默认模型档案。依赖：3.1。负责：迁移实现与公开测试；失败条件：旧数据/证据丢失或新旧写入无权威边界。完成证据：新增受限导入和确定性导出API；已知实体映射的事实转为有证据暂定主张，未映射事实/注册和旧集合均以loss记录明示；旧属性值域、关系、覆盖等不能无损表示时导出显式损失诊断；M1 `SourceDeclaration`不会被自动升为语义实体。4项迁移测试通过；没有切换默认模型档案，旧入口保持独立。

## 4. 查询、算法和按需构造

- [x] 4.5 为算法描述新增来源可追溯的伪代码渲染器，并接入函数查询与实体档案。依据：本变更查询需求及函数伪代码请求。输入：Python/Rust算法步骤、来源跨度、证据引用和缺口；输出：可读伪代码投影，函数查询响应及持久化实现视图均可回读。验证：Python/Rust条件与返回查询、证据引用、部分完整性标记和实体档案往返测试通过；不支持步骤须保留并标出未解析；不得声称行为等价。依赖：4.1–4.3。负责：查询投影实现与公开测试；失败条件：查询不到伪代码、来源不可追溯或静态投影被误标为完整。完成证据：新增`render_pseudocode`投影，`function:<名称>`的JSON/Markdown查询返回Python/Rust伪代码和步骤证据引用，`algorithm`单函数响应也包含伪代码；`semantic-entity-model-1`实现视图允许并保存该结构，实体详情可读回。函数查询及档案回读专项测试通过；Skill全套171项、仓库125项、语义模型90项、OpenSpec全库23项和工件校验4项通过。

- [x] 4.1 定义实体查询请求与目标解析。依据：语义事实查询规格增量。输入：请求和语义实体模型档案；输出：`skill/src/c2s_skill/query.py`及`skill/contracts/semantic-fact-query.schema.json`中的实体/属性/关系/实现/测试查询目标、描述面、直接范围、展开界限和请求状态。验证：项目实体清单返回直接成员引用/短摘要；实体详情返回自身全部属性；明确请求成员完整描述时逐个展开其属性；中文/结构化请求与未知/歧义目标用例通过；旧查询选择器仍可路由源码构造视图。依赖：1.3、2.2。负责：查询实现与公开测试；失败条件：无法区分清单与详情、遗漏目标属性或把未识别当不存在。完成证据：新增`semantic_entity_query.py`及独立请求结构模式；项目清单只返回直接子实体短摘要，详情返回目标实体全部属性和状态/覆盖信息，子实体默认只引用，显式展开才逐个取详情并限制深度/循环；支持中文目标解析、结构化请求、未知/歧义缺口和实体仓储读取。查询测试6/6通过；旧源码事实查询未改动。
- [x] 4.2 实现查询投影、缺口和双输出一致性。依据：查询与按需构造规格增量。输入：4.1计划及3.1仓储数据；输出：Markdown/JSON格式共用结果投影。验证：详情目标已取得的所有属性一次返回；子实体仅引用除非显式展开；主张状态/覆盖范围/呈现状态/新鲜度正交；任一来源版本或源指纹变化使相关覆盖范围需复核；两种输出实体标识、属性、关系、证据标识和缺口逐项一致；`skill/tests/test_query.py`及contract测试通过。依赖：3.1、4.1。负责：查询投影实现与公开测试；失败条件：属性截断、状态混淆或投影不一致。完成证据：同一查询结果对象生成确定性JSON和Markdown；详情包含实体标识、全部属性和值域、主张、关联关系、证据完整字段及覆盖/呈现/新鲜度状态；差异只限呈现格式，子实体默认短引用，显式展开受深度界限控制。请求方提供当前输入指纹/分析器版本时，失配的覆盖标记`review_required`并返回缺口；投影测试7/7通过。
- [x] 4.3 迁移算法/实现视图到计算实体关联。依据：语义事实模型实现关系及现有算法契约。输入：旧算法描述和`SourceConstruct`；输出：算法主体/步骤/调用/数据流证据映射到`ComputationEntity`或待定状态。修改`skill/src/c2s_skill/algorithm.py`、projection、命令行接口/结构模式及算法测试。验证：Python/Rust 测试夹具保留源跨度/控制流/数据流/不透明 缺口；步骤不是业务实体；无映射允许查询；测试/调用引用闭合。依赖：2.2、3.1、4.1。负责：算法集成实现与公开测试；失败条件：丢步骤/证据或无证据映射。完成证据：实体候选构造为每个计算实体附加可调用事实中的算法步骤/局部绑定实现视图，逐项保留源路径、字节区间、原事实标识及新鲜源码证据；Python/Rust夹具均通过，步骤仍是实现视图而非独立语义实体。构造器测试9/9通过；原算法/投影实现与测试保持不变。
- [x] 4.4 完成按需复用、失效与连续性候选处理。依据：lazy 规格增量与状态不变量。输入：同一项目连续查询、注册表与项目输入/工具/分析器/解释模型版本；输出：已完成覆盖复用、缺项构造、过期/需复核状态和`continuity_unresolved`候选。修改查询/仓储及测试。验证：工具调用计数证明有效覆盖范围不重复分析；仅补属性/关系缺口；输入/解析器/工具/推导模型变化使适用覆盖范围失效；源码移动/注册表重建不按路径猜合并；歧义查询返回候选/缺口。依赖：3.1、4.1、4.2。负责：增量查询实现与公开测试；失败条件：错误缓存命中、事实被静默重键或过期记录作为当前结论。完成证据：`all-entities`覆盖保存合并源码及工具/解析器矩阵指纹；相同输入连续请求复用并由测试断言不调用扫描器，源码/解析器配置变化触发重新构造，旧覆盖回读为`review_required`；源码移动保持新旧身份分离并生成`continuity_unresolved`候选；注册表为空时不按名称猜合并；未知/歧义实体返回独立状态和缺口。更新覆盖按新输入快照补齐全项目受支持候选，扫描粒度为项目全量，尚无按实体逐属性定向的增量解析器。Python/Rust夹具和Click/regex全量清单验证通过。

## 5. 真实项目遍历、完整性和成本

- [x] 5.1 对锁定Click Python项目执行受支持实体全集遍历。依据：分析范围、语义模型、查询和按需构造规格。输入：真实Click固定检出版本；输出：`docs/development/reviews/semantic-facts/entity-model-click-inventory.json`及验证记录，逐项列实体/属性/关系/源码映射/测试映射/证据/覆盖范围/缺口。验证：构造→校验→SQLite写入→所有支持查询目标遍历→回读逐标识和证据比对；不可采样替代，不把未识别语义对象当不存在。依赖：2.3、3.2、4.2、4.4。负责：Python项目遍历执行与记录；失败条件：支持范围内任一记录或缺口未被遍历/比较。完成证据：Click `2247b35ea1c47c727d7a06e51fa280e12a863ff6`全新隔离档案经实体契约校验、SQLite往返及逐实体查询回读比对，2610/2610实体完整，属性283项、关系2668条、证据14921条、源码映射15464条；74条未映射源码构造、556个测试目标未解析及2项领域边界缺口逐项保留于JSON报告。2026-11-07切换复核重复运行同一遍历，逐项再次通过；报告只保留当前分析指纹，避免把历史档案合并值误作当前证据。
- [x] 5.2 对锁定regex Rust项目执行受支持实体全集遍历。依据及产物同5.1，项目含Cargo workspace；输出`docs/development/reviews/semantic-facts/entity-model-regex-inventory.json`及验证记录。额外逐项核查软件包/工作空间/源码模块差异及泛型/enum/macro实际支持；不得把Cargo package/Rust module直接等同语义模块。依赖：5.1的验证程序及所有2–4任务。负责：Rust项目遍历执行与记录；失败条件：支持范围内任一记录或缺口未被遍历/比较。完成证据：regex `94ac45b2a6e7b1c30927feb5b66c5ded5b7ad447`全新隔离档案经实体契约校验、SQLite回读及逐实体查询比对，4712/4712实体完整，属性1034项、关系4712条、证据35227条、源码映射36445条；6081条未映射源码构造、9个测试目标未解析及2项领域边界缺口逐项保留。Cargo metadata使用仓库本地toolchain和离线`--no-deps`运行，根包regex及6个workspace成员共7个包，Skill的workspace-members查询7/7且无gap；实体模型仍不把Cargo package或Rust module直接等同语义实体/业务模块。源码构造中263个Rust module声明，语义Module实体为0。generic/enum/macro源码构造计数与映射见报告；Rust构建测试未运行。2026-11-07切换复核重复运行全实体遍历，逐项再次通过；报告只保留当前分析指纹，避免把历史档案合并值误作当前证据。
- [x] 5.3 对照旧路径测量时间、存储、解析调用和实际大语言模型词元。依据：semantic-analysis-quality及项目资源约束。输入：同项目、同请求、同范围/缺口、同环境下旧模型档案与新模型档案；输出`docs/development/reviews/semantic-facts/entity-model-cost-comparison.md`和Python3复测脚本。验证：未调用LLM记为“未测/无使用量”，不得伪造零个词元节省；覆盖范围不相等不宣称收益；脚本可重复运行。依赖：5.1、5.2。负责：性能/词元测量与复核；失败条件：比较口径不可复现或收益无实测依据。完成证据：在相同容器固定检出、以`all-supported-facts`对比新`all-entities`，两项目各实测耗时、解析调用、记录/缺口数、SQLite体量；明确两模型覆盖不等，不声称吞吐或成本收益；无LLM调用，词元记为未测/未使用。复测脚本`measure_semantic_entity_cost.py`可重复运行。

## 6. 文档与整体验证

- [x] 6.1 更新`skill/README.md`、公共模型契约说明及查询示例。依据：实际实现和5.x测试记录。输出：新模型档案/旧模型档案兼容边界、依赖/版本/安装自检/平台、缓存/写入副作用、实体/属性/子实体/实现/测试概念、运行命令与缺口说明。验证：README命令在当前环境可运行；不得宣称全语义正确、未测平台或私有验收通过。依赖：5.1–5.3。负责：文档维护与命令核验；失败条件：命令不可用或文档超出证据。完成证据：补充`entities` CLI命令、语义实体档案隔离/副作用/边界和可运行命令；命令在锁定Click检出上成功构造并返回实体清单，Skill CLI测试13/13通过。全文明确旧`query`默认路径尚未切换、Cargo metadata及私有盲验收未验证。
- [x] 6.2 在完整验证通过后执行模型档案切换。依据：设计迁移计划。输入：已通过的1–6.1任务结果及旧仓储备份；输出：命令行接口默认写入`semantic-entity-model-1`、旧`semantic-fact-model-1`只读兼容端口、保留M1独立入口；切换记录与可回滚备份。验证：切换前检查5.1/5.2全量遍历、5.3成本对照、全部查询/存储/兼容导出测试通过；备份可读；切换后新写入只进入新模型档案、旧完整模型档案写入明确拒绝；M1入口行为不变；失败则保持切换前默认路径。依赖：1.3、3.1–3.2、4.1–4.4、5.1–5.3、6.1。负责：版本迁移与公开测试；失败条件：任何前置验证未通过、无法回滚或出现双模型档案写入。完成证据：`query --store`和`algorithm --semantic-facts --store`均写入独立实体档案；CLI通过新/旧数据库同文件回归证明既有完整档案不变且仍可读；切换前以SQLite在线备份API复制旧档案，并在切换后读取备份与原档案逐项相等；`commit_bundle`公开写接口拒绝旧完整档案写入；`commit_m1`保持独立。切换写入新增实体表而不改写旧表；回退可恢复前一代码版本并继续读取原完整档案，迁移前旧表及原始数据库文件均保留。
- [x] 6.3 执行切换后的整体验证并形成报告。依据：全部前序任务及ADR-0011共享模式。输出公开测试、规格校验、真实项目遍历、迁移回滚和交付文件清单。验证：`npm test`、模型契约测试、Skill测试、5.1/5.2全量遍历、旧版导出和`npm run validate`均实际运行；受支持记录无悬空引用、仓储回读无损；未完成任务/隔离限制显式列出。依赖：6.2。负责：最终验证与报告；失败条件：任一验证失败或证据不足仍被标完成。完成证据：`npm test`125项、Skill全套167项（含算法实现投影持久化/回读及外部图结果变更回归）、模型契约90项、实体/迁移/CLI定向51项通过；Click 2610/2610及regex 4712/4712逐实体查询比对成功；旧档案兼容导出确定性测试通过；OpenSpec严格校验23/23、产物检查4/4及`git diff --check`通过。共享工作区隔离及Cargo默认toolchain限制见验证报告。

## Workflow follow-up

- 用户批准设计后按本表顺序实施；审查、验证通过后依项目流程提交到`main`。共享开发测试不得描述为私有盲验收。


## 7. 提案模型一致性核对

- [x] 7.1 逐项检查所有非归档OpenSpec提案并对齐实体中心领域模型。输入：ADR-0012、语义实体模型规格与全部16个提案；输出：`docs/development/reviews/semantic-facts/semantic-entity-proposal-alignment.md`及受影响提案/设计/规格/任务的现行边界说明。验证：每项提案都有影响结论；实体身份、属性/关系、源码构造映射、测试验证、E0–E4观察视角和旧档案迁移边界无冲突；对无影响项不添加产品语义要求。完成证据：14项受影响提案已更新并链接实体基准，2项无影响提案经矩阵记录；16项全覆盖，历史决定与旧实现范围保留，不宣称档案切换已完成。

## 8. 切换后复核补充

- [x] 8.1 验证本地Cargo metadata并持久化E1 workspace观察。依据：6.3复核发现本地Cargo shim需要显式`RUSTUP_HOME`/`CARGO_HOME`；Cargo packages不等同语义模块。输出：Project上的`workspaceMemberPackage`主张、E1视角、证据与coverage；metadata失败时记录`not_acquired`；README/规格/验证记录同步。验证：真实regex项目Cargo metadata和`workspace-members`查询返回7/7且无gap；隔离Cargo fixture写入实体档案后逐项查询包主张；缺少Cargo时返回not_acquired及gap；不创建Cargo package语义实体；虚拟workspace以暂定Project范围保存构建观察，不制造package实体。完成证据：本地toolchain离线元数据7/7、真实regex经同库实体详情查询读回7条E1主张；成功、工具不可用、虚拟workspace正反fixture通过；Skill全套170/170、OpenSpec全库23/23、仓库测试125/125、模型契约90/90、工件4/4全部通过。

## ADR-0013 当前约束（2026-11-08）

保留语义实体、属性、关系、源码构造、证据及测试映射；取消DDD解释。既有实现和切换任务记录保留其原证据，新目标下的实现差距须另行核对，不因旧任务完成自动通过。 依据：`docs/decisions/0013-非DDD语义事实模型.md`。历史执行记录中的DDD或旧模型表述不构成现行约束。本轮只进行文档修订，产品重构完成状态不变。

## 9. ADR-0013规格与提案修订

- [x] 9.1 核对全部7份正式规格、全部16项活动提案及其规格增量，修订目标、非DDD方法、源码/实体映射、查询、证据覆盖和工具点亮规则；同步受影响设计、任务边界及当前入口。输出：`docs/development/reviews/semantic-facts/非DDD规格提案审核-2026-11-08.md`及逐文件矩阵。验证：OpenSpec全库严格校验、原件完整性、仓库测试及差异检查；保留历史ADR/原件、旧任务证据，不归档或修改产品实现。审核为当前会话文档自审，不声称独立盲验收。

## 10. 非DDD上游事实提取重构（当前唯一实施任务）

设计：`docs/superpowers/specs/2026-11-08-非DDD事实提取重构设计.md`。本节路径未写目录前缀的产品.py文件均位于`skill/src/c2s_skill/`。本节按用户授权进入实施；实际状态以各任务勾选及交付核验为准。前1–9节是历史交付/文档记录，不代表本节通过。以本节为唯一新版本整合任务表；其他提案中的M1/既有父任务不因本节完成自动勾选。执行前读取设计及对应正式规格，采用superpowers:executing-plans；公开开发测试与私有独立验收分开。

角色：每项实现者负责产品及公开说明，开发侧公开测试按ADR-0011执行；独立审核/验收保持其输出所有权，隔离不足时不得称盲验收。每项只修改所列文件及同职责文档，不修改隐藏suite或其期望。

- [x] 10.1 **v2公共契约和反例**
  - 完成证据：先运行新测试得到接口ImportError，再实现v2验证器及封闭Schema；模型测试98项通过（包含8项新v2正反测试），v1未改。
  - 依据/依赖：无；读取设计数据协议及正式模型/查询规格。
  - 交付与修改范围：新增 `contracts/semantic-model/semantic-entity-model-2.schema.json`、`skill/contracts/semantic-fact-request-2.schema.json`、`semantic-fact-result-2.schema.json`；修改公共类型目录/manifest及 `src/c2s_semantic_contract/validation.py`。
  - 输入/输出接口：`validate_semantic_entity_model_v2(document: object) -> dict`；返回valid及逐项diagnostics；新增sourceRecords、origin/premiseIds、acquisitionRuns及双coverage。
  - 公开验证断言：`tests/semantic_model/test_model_v2.py`：test_source_entity_identity_separated、test_missing_premise_rejected、test_source_relation_dangling_rejected、test_optional_views_not_entity_kind、test_unclassified_legacy_requires_original_payload；非法目标/缺字段必须拒绝，v1夹具原样可读。
  - 执行步骤：先新增上述失败测试并运行取得真实失败；再实现所列最小接口；运行定向命令并检查退出码；补齐对应文档与产物，自审差异后提交。不得仅新增与实现逐行同构的断言。
  - 定向命令：`PYTHONPATH=src .local/analysis-venv/bin/python -m unittest discover -s tests/semantic_model -v`。
  - 通过/失败与证据：输出契约与`docs/domain/semantic-model-contract.md`同步；结构、引用和direct/derived约束正反测试全过，任一v1破坏或来源身份冒实体则失败。 每项绑定提交、输入版本、命令与实跑结果，失败保留未完成，不用历史测试数代替新测试。

- [x] 10.2 **独立来源组织与有界解析**
  - 完成证据：新增来源记录7项测试先ImportError后全部通过；原有获取器回归通过。支持有界源文件解析、嵌套清单组织、稳定来源身份及解析分歧证据；默认查询尚未切换。
  - 依据/依赖：10.1。保留上游组织与实现参考、全目录范围规格。
  - 交付与修改范围：新增 `skill/src/c2s_skill/source_records.py`；修改 `acquisition.py`、`inventory.py`；测试 `skill/tests/test_source_records.py`、`test_acquisition.py`。
  - 输入/输出接口：`collect_source_records(root: Path, scan: ProjectScan, request: dict) -> dict`；`scan_project`新增source_paths，None显式全扫描，集合只解析选定路径。
  - 公开验证断言：test_module_without_semantic_mapping_queryable、test_nested_manifest_ownership_unresolved、test_hidden_examples_inventory_retained、test_selected_paths_do_not_parse_unrelated、test_reacquisition_same_source_record_id、test_tool_disagreement_preserves_claims；对照实际文件和构造字节跨度。
  - 执行步骤：先新增上述失败测试并运行取得真实失败；再实现所列最小接口；运行定向命令并检查退出码；补齐对应文档与产物，自审差异后提交。不得仅新增与实现逐行同构的断言。
  - 定向命令：`PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -p test_source_records.py -v`。
  - 通过/失败与证据：`skill/README.md`记录来源查询与范围；模块未映射仍可查、嵌套工程不伪归属，未处理文件列明；静默丢路径或越界则失败。 每项绑定提交、输入版本、命令与实跑结果，失败保留未完成，不用历史测试数代替新测试。

- [x] 10.3 **规范请求和按需计划**
  - 完成证据：接口缺失红测试后实现规范请求及计划；5项计划测试与3项请求测试通过，覆盖同名歧义、单函数算法、已得描述面复用和工具缺口。
  - 依据/依赖：10.1–10.2；查询触发/同主体补缺和实体自身属性完整要求。
  - 交付与修改范围：新增 `fact_request.py`、`construction_plan.py`；修改 `capability_matrix.py`；测试 `skill/tests/test_fact_request.py`、`test_construction_plan.py`。
  - 输入/输出接口：`normalize_fact_request(value: dict | str) -> dict`；`plan_fact_request(request: dict, available: dict, inventory: list[dict]) -> dict`；needs包含目标、facets、前置及理由。
  - 公开验证断言：test_self_detail_includes_all_own_attributes、test_ambiguous_name_returns_candidates、test_first_algorithm_request_targets_one_function、test_repeat_request_only_plans_missing_facet、test_tool_unavailable_is_gap；校验解析/算法调用记录，不仅测试返回数量。
  - 执行步骤：先新增上述失败测试并运行取得真实失败；再实现所列最小接口；运行定向命令并检查退出码；补齐对应文档与产物，自审差异后提交。不得仅新增与实现逐行同构的断言。
  - 定向命令：`PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -p test_construction_plan.py -v`。
  - 通过/失败与证据：另运行test_fact_request.py；更新设计接口示例；请求未命中不触发全仓候选或算法，缺工具不伪成功；无界扩取失败。 每项绑定提交、输入版本、命令与实跑结果，失败保留未完成，不用历史测试数代替新测试。

- [x] 10.4 **证据分类与按目标构造**
  - 完成证据：新接口红测试后实现局部构造；8项v2测试及11项既有构造测试通过。额外红绿回归证明算法实体映射通过v2校验且步骤证据引用闭合；无固定kind→视角映射。
  - 依据/依赖：10.1–10.3；非DDD解释边界、属性与子实体和源码映射要求。
  - 交付与修改范围：修改 `entity_construction.py`、`algorithm.py`；新增 `skill/tests/test_construction_v2.py`。
  - 输入/输出接口：`construct_requested_entities(root: Path, scan: ProjectScan, plan: dict) -> dict`返回v2局部实体、来源记录、主张/证据、映射和逐need覆盖；复用现有算法函数。
  - 公开验证断言：test_class_does_not_confirm_business_requirement、test_rule_claim_records_premises、test_views_derived_from_content_not_kind、test_unmapped_construct_retained、test_algorithm_not_run_for_attribute_request、test_attribute_unknown_domain_preserved。
  - 执行步骤：先新增上述失败测试并运行取得真实失败；再实现所列最小接口；运行定向命令并检查退出码；补齐对应文档与产物，自审差异后提交。不得仅新增与实现逐行同构的断言。
  - 定向命令：`PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -p test_construction_v2.py -v`。
  - 通过/失败与证据：文档标明direct_source不是行为证明；只有实际完成need发布覆盖，来源解释标暂定并有premises；固定kind→E视角或全仓构造则失败。 每项绑定提交、输入版本、命令与实跑结果，失败保留未完成，不用历史测试数代替新测试。

- [x] 10.5 **细粒度持久化与原子补缺**
  - 完成证据：先观察7项接口缺失失败，后8项存储测试通过（含8次并发操作补证和SQLite触发器失败注入）；既有实体存储回归通过。v2独立按scope/输入/配置隔离，事务内合并、注册、覆盖及回执原子提交。
  - 依据/依赖：10.1及10.4；增量存储、状态独立和输入固定约束。
  - 交付与修改范围：修改 `semantic_store.py`；新增 `skill/tests/test_request_store.py`，保留现有M1/v1存储测试。
  - 输入/输出接口：`SemanticEntityStore.read_request(scope_id, request, input_fingerprint, configuration_digest) -> dict`；`commit_request(operation_id, document, request) -> dict`；v2独立表、事务内读取generation合并。
  - 公开验证断言：test_duplicate_operation_idempotent、test_operation_id_different_payload_rejected、test_concurrent_missing_facets_no_lost_update、test_cancel_keeps_unfinished_gap、test_readback_without_analysis、test_input_changed_not_reused；失败注入证明无半包可见。
  - 执行步骤：先新增上述失败测试并运行取得真实失败；再实现所列最小接口；运行定向命令并检查退出码；补齐对应文档与产物，自审差异后提交。不得仅新增与实现逐行同构的断言。
  - 定向命令：`PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -p test_request_store.py -v`。
  - 通过/失败与证据：`skill/README.md`描述外置数据库与状态；源输入/profile不匹配不复用；冲突和证据保留，存储失败与语义取得分别报告；丢失补证或虚报保存失败。 每项绑定提交、输入版本、命令与实跑结果，失败保留未完成，不用历史测试数代替新测试。

- [x] 10.6 **可选CodeGraph解析及生产矩阵验证**
  - 完成证据：解析器红绿7测试、固定Click/regex四类真实JSON共8次运行解析通过，原始响应/stderr及来源核对入验证工件；无净覆盖收益证据，依任务条件保留candidate而不点亮完整图能力。
  - 依据/依赖：10.1–10.2；非商用工具组合及解析点亮要求，现有CRG不重写。
  - 交付与修改范围：新增 `skill/src/c2s_skill/codegraph_adapter.py`、`skill/tests/test_codegraph_adapter.py`；修改 `capability_matrix.py`、`skill/contracts/tool-capabilities.json`；验证记录 `docs/development/reviews/semantic-facts/CodeGraph适配验证.md`。
  - 输入/输出接口：`parse_codegraph_response(response: dict | list, root: Path, query_kind: str) -> dict`返回来源/调用候选、原始工件、工具版本及coverage诊断；通过tool_runner执行显式query/files/callers/callees子命令，不运行宿主安装/自动配置。
  - 公开验证断言：test_cli_array_parsed、test_path_escape_rejected、test_unbounded_search_not_full_enumeration、test_missing_freshness_is_gap、test_raw_response_preserved；隔离Click/regex运行固定1.6.2并解析真实JSON，核对源码及遗漏。
  - 执行步骤：先新增上述失败测试并运行取得真实失败；再实现所列最小接口；运行定向命令并检查退出码；补齐对应文档与产物，自审差异后提交。不得仅新增与实现逐行同构的断言。
  - 定向命令：`PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -p test_codegraph_adapter.py -v`。
  - 通过/失败与证据：按信息覆盖对比CRG/原生组合及许可、冷索引成本；仅具体已验证能力点亮。未获得覆盖净收益时保留候选并记录不选择原因；任务完成不等于工具必须选入必需栈，未测能力不得点亮。 每项绑定提交、输入版本、命令与实跑结果，失败保留未完成，不用历史测试数代替新测试。

- [x] 10.7 **统一查询和算法回读**
  - 完成证据：缺统一模块/CLI参数红测试后，15项查询测试、2项v2 CLI测试、19项原CLI回归通过。覆盖档案回读无重构、缓存跨版本隔离、实体属性/循环/保存失败、原始图响应及实体ref算法映射；固定Click两条README命令已实跑。
  - 依据/依赖：10.3–10.5；10.6可选后端未通过不阻塞原生组合。
  - 交付与修改范围：新增 `fact_query.py`；修改 `query.py`、`semantic_entity_query.py`、`store.py`、`__main__.py`；新增 `skill/tests/test_fact_query_v2.py`、`test_cli_v2.py`。
  - 输入/输出接口：`execute_fact_query(root: Path, request: dict, store, *, tool_runner=None) -> dict`；JSON/Markdown从semantic-fact-result-2投影；CLI增加--model-profile，旧选择器转source视图，函数伪代码复用现有渲染器。
  - 公开验证断言：test_stored_algorithm_query_no_reconstruction、test_unmapped_module_returned、test_own_attributes_not_depth_limited、test_cycle_depth_eight_stops、test_json_markdown_same_ids_and_gaps、test_save_error_preserves_facts、test_target_not_found_vs_not_acquired、test_v1_cache_never_hits_v2、test_normalized_request_profile_cache_key、test_input_config_change_cache_miss；请求/结果profile、规范请求摘要、输入及配置全部进入缓存键。
  - 执行步骤：先新增上述失败测试并运行取得真实失败；再实现所列最小接口；运行定向命令并检查退出码；补齐对应文档与产物，自审差异后提交。不得仅新增与实现逐行同构的断言。
  - 定向命令：`PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -p test_fact_query_v2.py -v`。
  - 通过/失败与证据：另运行test_cli_v2.py；README每个命令实跑；同一实体细节与source视图均可查，失败明确、不自动挑同名目标，不回退全仓重建；双输出差异失败。 每项绑定提交、输入版本、命令与实跑结果，失败保留未完成，不用历史测试数代替新测试。

- [x] 10.8 **v1兼容转换与可回滚候选**
  - 完成证据：新增接口红测试后，5项v2迁移与4项旧迁移测试通过；实体ref/证据与原始payload保留，旧主张标unclassified_legacy，导出具名losses，SQLite在线备份逐表回读一致且拒绝覆盖既有文件。默认profile尚未切换。
  - 依据/依赖：10.5、10.7；兼容档案边界。
  - 交付与修改范围：修改 `semantic_entity_migration.py`；新增 `skill/tests/test_model_v2_migration.py`，更新 `docs/domain/semantic-model-contract.md`。
  - 输入/输出接口：`import_entity_v1(document: dict) -> dict`、`export_entity_v1(document: dict) -> dict`；导出包含document及losses；实体ref保持，新增解释来源不明确时记录unclassified_legacy、legacyPayloadArtifactId及UNCLASSIFIED_LEGACY诊断，不捏造premises。
  - 公开验证断言：test_v1_refs_evidence_unchanged、test_unknown_origin_not_direct、test_export_reports_unrepresentable_sources、test_backup_readback_equal、test_failed_upgrade_keeps_v1_default。
  - 执行步骤：先新增上述失败测试并运行取得真实失败；再实现所列最小接口；运行定向命令并检查退出码；补齐对应文档与产物，自审差异后提交。不得仅新增与实现逐行同构的断言。
  - 定向命令：`PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -p test_model_v2_migration.py -v`。
  - 通过/失败与证据：v1、旧完整profile、M1原档案不改写；切换前备份可回读，新profile显式选择，信息损失具名报告；无损声明不实或反写旧表失败。 每项绑定提交、输入版本、命令与实跑结果，失败保留未完成，不用历史测试数代替新测试。

- [x] 10.9 **真实项目全集遍历与同范围成本集成**
  - 完成证据：验证器缺失接口/遗漏主张检测红测试后6项测试通过；固定Click来源4138/实体2610、regex来源19041/实体4712逐项查询回读，全部主张/关系/映射及字节证据核对通过。原生普通类型/函数声明分别2078、4907；两项目各显式验证1个核心算法，未请求算法不冒称已展开；冷热事实/缺口一致，重复解析0文件。
  - 依据/依赖：10.2–10.8；质量、范围、词元和来源证据要求。
  - 交付与修改范围：新增 Python3 `scripts/verify_source_fact_refactor.py`；新增 `skill/tests/test_refactor_verifier.py`；产物 `docs/development/reviews/semantic-facts/非DDD真实项目验证.md`及对应JSON。
  - 输入/输出接口：脚本参数--project、--expected-commit、--store、--output；调用公开v2接口，遍历所有已发布记录与缺口及每个来源/实体查询目标，逐项比较存储回读和证据摘要。
  - 公开验证断言：test_verifier_detects_missing_record、test_verifier_rejects_changed_source、test_verifier_does_not_equate_source_with_semantic_coverage；固定Click/regex提交分别独立运行，包含嵌套项目、测试及示例；原生清单对照来源覆盖，候选语义不冒真值。
  - 执行步骤：先新增上述失败测试并运行取得真实失败；再实现所列最小接口；运行定向命令并检查退出码；补齐对应文档与产物，自审差异后提交。不得仅新增与实现逐行同构的断言。
  - 定向命令：`PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -p test_refactor_verifier.py -v`。
  - 通过/失败与证据：真实运行记录所有命令、环境、指纹、逐项差异；比较同请求冷/热耗时、解析数、算法调用数、工具索引/SQLite及实际模型词元。范围不等禁止报收益；任何悬空引用、回读丢数据或隐瞒gap失败。 每项绑定提交、输入版本、命令与实跑结果，失败保留未完成，不用历史测试数代替新测试。

- [x] 10.10 **默认切换与交付核验**
  - 完成证据：默认仅写v2、旧档案读取、自动验证备份与回滚4项通过；最终审核7类Important全部复现并修复，13项回归通过；Skill全套270/270、npm133/133、契约98/98、严格OpenSpec23/23、原件4项及diff检查通过。固定Click/regex最终配置全集遍历valid，增加定向→全量→定向一致性；证据见`docs/development/reviews/semantic-facts/非DDD重构交付核验.md`。远程CI未核实，私有盲验收未执行，不自动归档。
  - 依据/依赖：10.8–10.9全部通过；不由任务文件存在判通过。
  - 交付与修改范围：修改 `__main__.py`及 `skill/README.md`；新增 `skill/tests/test_v2_cutover.py`；产物 `docs/development/reviews/semantic-facts/非DDD重构交付核验.md`。
  - 输入/输出接口：默认profile切换到semantic-entity-model-2，--model-profile显式选择兼容读取；切换前备份读回验证，保存v2、v1及M1边界及回滚步骤。
  - 公开验证断言：test_default_writes_v2_only、test_legacy_reads_still_available、test_rollback_restores_readable_backup；运行全仓、Skill、契约、严格OpenSpec及原件校验，公开CI结果与私有验收状态分别列示。
  - 执行步骤：先新增上述失败测试并运行取得真实失败；再实现所列最小接口；运行定向命令并检查退出码；补齐对应文档与产物，自审差异后提交。不得仅新增与实现逐行同构的断言。
  - 定向命令：`npm test && npm run validate && npm run check:artifacts`。
  - 通过/失败与证据：另运行PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -v；仅全部前置有证据才切换，失败维持旧默认；不自动发行、归档或删除兼容数据。 每项绑定提交、输入版本、命令与实跑结果，失败保留未完成，不用历史测试数代替新测试。

## 11. 用户决定移除V1（2026-11-09）

本节替代此前保留兼容接口的要求，第10节作为历史交付证据保留。

- [x] 11.1 **删除公开V1运行接口**（7项唯一接口/旧档案不变/显式V2备份测试通过；原先21项失败断言已转绿；当前Skill176项及npm133项均通过）。依据用户明确删除决定及2026-11-09设计。先新增test_v2_only.py：CLI拒绝旧profile、旧查询/仓储/缓存/转换/包导出不存在、纯旧档案拒绝且摘要不变；实跑RED。修改__main__/query/store/semantic_store/entity_construction/semantic_entity_query，删除semantic_entity_migration及过时脚本；提取内部共用校验。V2公开API、实体/来源/算法及显式备份不退化。定向命令：PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -p 'test_v2_only.py' -v。通过后提交。
- [x] 11.2 **同步规格、测试和文档**（25个含旧接口的活动提案文件已标明ADR-0014替代，Skill184/184、npm133/133、严格23/23及原件4项通过，修正后Click/regex最终配置逐项回读均valid）。修订现行正式/变更规格及README、领域说明；历史报告保留并明确被替代。退休仅验证已移除接口的测试，列清去向；不得用放宽当前期望掩盖失败。运行npm test、npm run validate、npm run check:artifacts、Skill全套及固定Click/regex逐项回读，输出移除V1交付核验。通过后提交。
- [x] 11.3 **独立代码审核与交付**（新上下文完整项目只读审核完成，0Critical/6Important/0Minor；六项真实RED→GREEN修复，重跑全套及固定真实项目通过；审核原结论与修复证明分开记录，不冒称二次批准）。新上下文审核者仅读最终项目，不继承实施会话、不派子代理；检查整个V2路径、公开接口残留、数据安全与覆盖，不仅看删除diff。记录具体问题及等级，实质问题以RED→GREEN修复并重跑受影响全集。所有检查通过后main推送和远程读回，不称私有盲验收，不自动归档。
