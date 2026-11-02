# Design

## M1项目发现适配端口（代理技术决定，m1-project-discovery-1）

ADR-0009已授权公开试验及准备；本节是接口规划，不把现有AST/CRG探索当本端口已验证。M1仅项目发现/列表、明确语言声明及原生workspace成员；其他谓词UNSUPPORTED_PREDICATE，未支持工程格式保留UNSUPPORTED_SOURCE，不把未识别当不存在。采用原生声明读取加Cargo metadata；与整套代码图相比，无需为此切片构建类型/调用图；CRG/Serena等候选的全量试验不作本切片前置。

本节独占M1Entry={path:Path,kind:"file"|"directory"|"symlink"|"other",sizeBytes:int|null,state:"readable"|"unreadable"|"unfollowed",diagnostics:M1Diagnostic[]}；M1Acquired={bundle:M1Bundle,artifacts:M1Artifact[],inventory:M1Entry[],inventoryComplete:bool,diagnostics:M1Diagnostic[]}。输入M1Need/#8、M1Session/#12、已核验M1Read/#9（其中Registration/Artifact唯一归#3）；端口`acquire_m1(needs:list[M1Need], session:M1Session, prior:M1Read, current:M1Bundle)->M1Acquired`。不重复定义Fact/Evidence/Assessment/Artifact；经#3 register_m1登记身份后产生候选，#12负责校验/提交。current由#12 current_m1产生，prior保留完整历史/规范附件供定位和复用；每次Need可复用同session已有盘点/原生结果，不默认重新扫描全部目录。补证成功时#10产生新Assessment/Coverage的supersedes（指向current对应键叶）、非减少证据与已解决诊断键，#12验证后生效；原失败留历史/事件，新叶只列仍未解决项。不得自选最新记录或发无依据替代边。Cargo成员依据的原始stdout以M1Artifact留存，Evidence指向附件字节范围并保toolName/version；不可只引用Cargo.toml字节冒充解析结果证据。

范围盘点从root递归，含未跟踪、忽略、测试、示例、隐藏及嵌套目录，不使用Git/工具默认忽略缩小范围；所有目录项记录M1Entry，权限/特殊文件不读为普通源码。符号链接本切片不跟随，以SYMLINK_UNFOLLOWED及覆盖缺口披露，不静默排除；越界成员只留OUTSIDE_SCOPE缺口，不越界扫描或伪造内部Package。允许必要盘点，不提前解析所有程序语义。覆盖.complete仅在完整盘点、所需格式/声明处理均无已知缺口时true；不认识的工程声明/格式保留能力缺口，不能从可识别的Cargo/Python声明推出目录内只有这些项目。

所选Rust路径：Python3 TOML读取器（tomllib，运行期>=3.11）读取Cargo.toml，[package]/[workspace]分别登记SourceDeclaration；Cargo运行前以实际`cargo --version`绑定版本，`cargo metadata --format-version 1 --no-deps --offline --manifest-path <绝对Cargo.toml>`在外置副本、cwd明确执行，超时60秒；stdout按JSON格式1解析packages(id,name,manifest_path,targets.src_path)、workspace_members、workspace_root。opaque package id只映射PackageSpecification的sourceKey，不解析ID文本当领域身份；members必须实际在workspace_members，不能按目录或packages全集推导。无Cargo/非零/超时/未知格式为TOOL_FAILED，仍可报告已读声明，不能假装成员已解析。只消费当前请求需要字段，不取resolve依赖图、构建或宏展开。副本/缓存映射回root证据路径，原目录不得改写；复制范围与耗时/磁盘写入入#5，无法安全准备则缺口。

ProjectBoundaryAssessment规则（ruleId="m1-engineering-boundary-1"）是有来源的工程判定，不是manifest=Project：Rust须[package]独立包声明+metadata给出至少一个可回指范围内存在源码的target；Python须pyproject.toml的[project].name+[build-system].build-backend以及该backend明确绑定的范围内源码入口。M1只实现flit_core.buildapi规则：模块名取[tool.flit.module].name，否则[project].name按Flit规则连字符转下划线；检查<module>.py/<module>/__init__.py或src对应路径，恰一入口才resolved。同一声明多个可能工程边界记录候选Project且ambiguous，依据不足unresolved；没有依据不创建确定Project。SourceDeclaration/PackageSpecification/Project身份分开登记，用Assessment联系；workspace本身不升级Project。已登记Project后补证/收敛不得重键。其他Python backend、旧setup.py、影响当前所需字段或入口判定的动态module映射、非Rust/Python声明保留相应未决及UNSUPPORTED_SOURCE，后续扩展不作M1前置。动态version不属于M1三个选择项；如project.name和Flit源码入口已有充分依据，不因未解析version阻塞整个Project。仅当动态值实际影响本次所需名称/语言声明/入口映射时，按受影响项报告缺口；不新增版本查询，不静默忽略真正动态入口。

project.name来自对应明确元数据；project.language_declared仅Rust的Cargo包/target声明和Python的明确Python classifiers或requires-python声明支持，证据列出原字段；无明确语言声明保留缺口，不从文件扩展名推语言全集。workspace.member来源Cargo metadata的原生成员；Python无统一原生workspace接口，本切片不造workspace，也不能据此宣称Python不存在workspace。盘点中发现其他workspace声明时报告未支持。所有输出claimMode=declaration，工程判定Assessment另带ruleId，不生成运行观测/否定。

sourceKey采用规范JSON字符串{adapter:"cargo-v1"|"pyproject-flit-v1",kind:主体kind,manifest:根相对清单路径,section:"package"|"workspace"|"project",slot:string}；Cargo的包/声明取package、workspace取workspace，Python取project；slot通常空串，Project候选为边界源码入口的根相对路径（多个Rust targets按已确认同一包边界共享空slot，不按target复制Project）。SourceDeclaration/PackageSpecification/Project的kind不同故键不同；metadata不透明package id仅作为本次输出→该注册键的映射，不解析文本。路径用于登记查找而不替代随机身份；已存登记表才是同次身份依据。规则收敛只补评估/证据，不改变既有sourceKey对应的身份；无法判明两个声明是否同一工程时保留未决，不按同名合并。

实际可用性仍须#10 3.1/3.2的M1子切片在固定regex 94ac45b2a6e7b1c30927feb5b66c5ded5b7ad447、click 2247b35ea1c47c727d7a06e51fa280e12a863ff6核对metadata/API、Flit绑定、盘点/副本副作用与成本；未测工具/host组合标unknown。host工具与Skill同平台；项目target在#12单列，metadata无target参数不证明其他构造配置。此处不捏造命令运行结果，不要求所有候选先安装。


当前执行授权接续：ADR-0009已允许必要准备/安装/工具试验及准备通过后的连续开发；下文旧“不实施/另批”描述历史阶段，不撤销当前授权。真实就绪/隔离仍未通过，见readiness.md，不冒已完成。

## Context

已确认：共享context、ADR-0001/0002和两份主规格；模型A由用户选择但未批准实施。当前无产品实现或性能实测。新设计是候选；细节由授权范围内代理提出，不成为用户确认。讨论、异议及独立复核见本Issue评审目录。

## Goals / Non-Goals

逐需求明确能取得什么、还需转换什么和不能证明什么，减少交给模型的工作。非目标：安装/执行获取器、首期全面支持、从AST推出动态行为完整。

## Approaches

候选按需求比较原生工具、项目分析Skill及底层接口并共用中间成果，再对必要缺口局部模型补足；替代统一语法解析工具适配成本低但绑定/构建语义不足；每次模型直接分析可作质量/成本对照但重复上下文昂贵。不能以统一抽象掩盖能力不同，工具组合未执行前只为候选。

## Decisions

### 本轮工具与Skill先行调研

权威需求不变；用户确认补全此变更的调研，未选择具体产品。新增24份固定提交的一手资料见`docs/development/reviews/issues/10/acquisition-survey-2026-11-02/sources.json`；需求N01–N09、八组能力候选、接口及局限见同目录report.md/capability-matrix.json。本轮不安装/运行任何候选，不能据源码签名或上游实测宣布本项目能力已验证。下面原五份T证据保留为历史，不冒充本轮最新工具版本。

新增候选：Code Review Graph的build/explore Skill及图查询；GitNexus的exploring/guide Skill与图接口；Serena MCP符号能力；明确仓库身份的colbymchenry/codegraph。后两者不能仅凭“MCP/代码图谱”名称就宣称是通用项目分析Skill。CRG/GitNexus实际Skill文件已读，未执行。

比较完整复用上游Skill流程、仅复用接口、自有契约封装二者组合。代理建议组合：有稳定结构接口优先直接映射，Skill用于其有证能力并可提供导航/文本分析成果；符合公共契约的Skill可直接作为来源，不固定工具→Skill→LLM顺序。上游输出只有线索时仍需必要来源及转换，不把第三方社区/UID/边置信度当DDD边界/主体身份/语义真值。

枚举与检索分开：CRG minimal额外最多五项、GitNexus示例limit=3、Serena超字符限额无内容，均不能当所需顶层完整；按工具能力明确分页/分片/补取和终止依据，无法补全报告原因。工具默认忽略不缩小用户目录范围；覆盖清单记录未跟踪/忽略/不支持/失败内容，必要时换来源。不能从工具计数推未索引项不存在。

索引分别记录扫描、解析、结构索引、具体语义构造和查询成本；结构索引的必要性/范围由本次需求及工具前置能力证明，不一概豁免。依赖提前全仓具体E3/E4事实的候选不作为按需方案；同次项目固定，不启用不必要的watch/定时构造。默认安装或analyze可能改AGENTS/CLAUDE/hooks/缓存，未来试验必须在副本/外置状态中明确写入；本轮不运行，禁写证明未知，不给出未经验证的“安全命令”。

报告与结构数据由公共结果同源产生，不将第三方自然语言摘要直接充作权威事实。文本承载JSON、纯文本诊断、结构字段需按接口版本区分；必要模型转换只处理不可确定解析部分，保来源/缺口。Skill正文、内部模型/嵌入、分页补取及失败重试成本均入实际Token/资源账，未知成本记unknown，不采信宣传节省率为本项目收益。

先以Cargo metadata/Python AST为原生对照，验证CRG/Serena互补能力，再比较GitNexus/CodeGraph；此顺序是可调整试验建议，不是能力排名或依赖锁定。真实项目固定regex/click，host工具版本与项目target分列；新增实际试验须另行明确授权，隐藏测试编写/执行仍遵循ADR-0008隔离。当前公共语义基线不改，受影响技术设计不得先冻结已验证组合再补证据。

实际本次通过GitHub读取五份官方文档，证据路径及blob标识在本Issue`tool-evidence.json`，均documented_not_executed。查询失败的旧文档路径已改为官方当前路径，不把404当能力否定。

| 需求 | 候选来源/工具证据 | 确定性转换 | 尚不能证明 |
| --- | --- | --- | --- |
| E0成员声明/E1依赖解析 | T4 Cargo metadata JSON | 原生成员/包/依赖到模型A声明和解析关系 | 工程Project归属、构建产物观测，其他语言工程 |
| E2声明/局部结构 | T1 Tree-sitter具体语法树；T3 Python AST | 节点定位、结构声明与白名单值 | 类型绑定、跨文件/动态调用和行为契约完整 |
| Rust定义/引用线索 | T2 rust-analyzer README能力 | 经版本与配置核对的定义/引用映射 | 本Skill接口可用性、宏/生成/FFI全覆盖 |
| C/C++编译上下文分析 | T5 Clang LibTooling与CompilationDatabase | 前端结构和证据映射需专门适配 | host/target工具链完备、缺参数仍正确 |
| E3契约/E4局部语义 | 源码、声明/工具主张、必要模型解释 | 可确定条件/控制结构先转换 | 动态运行结果、形式等价、所有外部效果 |
| 混合语言桥接 | 显式FFI声明/生成绑定/构建链接依据，工具待定 | 记录桥接证据和候选引用 | 不能因各语言分别成功就声称跨语言调用已解析 |

T1/T3只能对其语法和版本断言；语法错误恢复节点不当成完整声明。T4格式版本固定并容忍新增字段/枚举，opaque原生ID不解析猜身份。T3列偏移是UTF-8字节，不能当Unicode字符索引。宏、注解、生成代码保留原始/展开来源映射、配置与方法；未运行展开器不声称展开后语义。

| 矩阵字段 | 状态及验证要求 |
| --- | --- |
| 源语言版本及混合边界 | 首期源语言Rust和Python已由用户确认；C/C++仅保留历史文档调查，非首期支持承诺；语言版本和混合边界仍待定 |
| Skill host | Windows/Linux/macOS、WSL/容器分别列版本/架构/可执行依赖；均未验证 |
| 项目target | triple/ABI、编译开关/特性/依赖环境与host分列；缺失不默认host |
| 工具版本/语法版本/能力 | documented、verified、unsupported、unknown分别记录，不从文档直接升级 |

每个组合保留输入案例、版本、命令/允许操作、输出定位、期望事实/局限与结果证据；跨语言边界单独验证。路径、大小写、Unicode、行尾、权限、符号链接和容器挂载映射保存原始定位及转换依据，不创建新主体。能力不可用时可选等质量替代，否则部分/不支持/未获取，不悄悄使用模型猜完整。

执行边界（用户第6点已确认）：为取得请求所需事实，必要分析操作可由设计选择执行；不把每次构建、宏展开、插件或依赖获取都重新要求用户批准作为需求前置。单次分析项目保持不变仍成立：可能改写项目的工具应由设计安排临时工作区/工作副本等方式，派生产物不改被分析项目；具体隔离方式属于代理设计决定。实际环境权限或工具能力不允许执行时，如实报告无法取得及原因，不假称执行成功。本轮仅规划，未运行这些操作。

### 逐事实需求与转换边界（首批调查样本，非完整谓词目录）

| ID/需求 | 一手输出依据 | 转换与精度/覆盖边界 | 失败判据 |
| --- | --- | --- | --- |
| R01原生workspace成员 | T4 workspace_members中Package ID，packages | 映射NativeWorkspace成员声明，不推Project归属 | 引用ID不在所见包范围或格式未知则缺口 |
| R02目标声明/依赖解析 | T4 packages.targets及resolve.nodes | 候选构建目标声明、依赖解析；按filter-platform/配置记录，非运行产物 | 缺resolve/目标过滤不符，不编造解析 |
| R03 Python操作声明/签名 | T3 AST函数节点/字段和源码位置 | 版本化节点→操作/签名，UTF-8位置校验；只静态声明 | 节点版本未知、位置无法回指、动态改写不明保缺口 |
| R04 Rust定义引用 | T2仅README能力，无本次具体协议输出字段证据 | 仅能力调查，协议结果到SubjectRef的转换尚未知 | 未取得接口字段/配置实证则不输出确定绑定 |
| R05 C/C++结构 | T5 FrontendAction与编译参数前提，无本次具体提取字段 | 须另证AST访问及位置转换，当前未验证 | 无编译命令/头文件/target依据，不当完整结构 |
| R06 E3行为契约/E4局部含义 | 此轮无能证明完整行为语义的一手工具证据 | 静态结构线索可输入，行为解释仍需局部来源和方法，能力unknown | 仅语法/README或模型断言不足以升级完整契约/观测 |

T4本次还实际读取全文核对workspace_members、targets及resolve字段；原生ID视为不透明引用，禁止解析其文本推主体身份。

组合记录候选示例（不是支持声明）：Python/待选版本×Linux/待选架构host×待选Python target×AST，Rust/待选版本×Windows host×待选target×rust-analyzer，C/C++×容器Linux host×交叉编译target×Clang，以及Rust↔C桥接；语言选择现仅Rust/Python已确认，以上具体版本/host/target组合仍unknown/未运行；C/C++及Rust↔C保留为后续调查。

本地工具可用不代表远程工具可用；远程路径、版本、target和来源快照必须可对应，权限/网络/环境不可用则记录缺口，不自动上传源码或配置远端。WSL/容器不是Windows/Linux全组合替代。退化例：Windows路径无法映射容器原始文件→定位未核验，不伪造行列；远程rust-analyzer版本未知→能力unknown；FFI声明存在但链接依据缺失→保声明和桥接缺口，不确定调用绑定。


## Risks / Trade-offs

文档只能支持有限候选能力；缺目标配置或工具错误时确定性也会错。跨平台字符/路径定位偏差会破坏追溯。必要工具操作由设计选择且保持项目不变。工具维护成本、内存/耗时纳入#5，减少模型输入只是机制假设。

## Migration Plan

只规划；不改正式主规格、不apply、不archive。先冻结公共定义和未决重大选择，再整体审核，最后取得明确开发批准。唯一任务清单为本变更tasks.md，不维护第二套Superpowers计划。语言/混合边界、host和target按#5/#10矩阵取证；#5定义质量、端到端延迟/吞吐/资源及Token评价，数值未定不得宣称达标。

## Open Questions

首期Rust/Python及平台定义已确认；具体工具API、版本/混合边界及获取能力由代理结合实际项目环境调查和设计，无法取得须说明原因。负载范围实测后确定，不等待用户给数值目标；本轮不安装依赖。

## 2026-11-02 用户确认的平台约束

host为Skill宿主平台，分析工具的运行平台与Skill运行期平台一致；项目平台依据项目设定的构造/编译环境确定，不等于host。平台矩阵的工具运行维度因此跟随host，不是可任意混配的独立平台。此前本地/远程、容器等调查不授权异构工具运行或自动选择远端；相关候选仍须满足此确认。例：Linux上的工具可分析设定为Windows目标的Rust项目，但工具能否正确处理该构造/编译环境须有相应能力证据。具体组合未验证时保持unknown。确认依据ADR-0004。

目录范围包括用户指定目录全部内容，不把测试/示例/嵌套目录先排除；Rust/Python是首期语言目标，其他内容可作项目组织/构造证据，无法分析的语义如实报告。目录范围不等于每个请求必须通读全仓或预构造全部事实。工具/版本及混合边界能力由代理调查和设计，不能把尚未验证能力冒充已支持，也不将版本选择当作等待用户逐项裁决的前置。
