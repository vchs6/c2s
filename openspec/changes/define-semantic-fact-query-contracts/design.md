# Design

## M1请求与同源结果（代理技术决定，m1-project-discovery-1）

本节补足交付2.1接口，后文历史“另批/类型待定”不阻塞此切片细化；当前ADR-0009已授权准备及门禁通过后实施。只承诺项目发现/列表、语言声明、原生workspace成员的本次顶层结果，不称完整项目语义。结构化入口使用JSON，人类可用三种固定短语“列出项目”“列出项目语言声明”“列出原生workspace成员”（可用中文顿号连接）；其他自然语言在M1返回INVALID_REQUEST并说明支持项，不猜意图；后续扩展自由语言不作M1前置。

本节独占M1Query/M1Result/M1Delivery；模型记录精确引用#3 design“ M1项目发现切片契约”，不复制事实类型。记法沿用#3的必填/可空/封闭记录；JSON UTF-8、无NaN、重复键拒绝，Id/Path别名沿用#3。

- M1Query = {contract:"m1-project-discovery-1", requestId:Id, analysisId:Id|null, root:string, store:string, select:string[]}；root/store是host绝对目录路径，store必须在root之外以保持项目不变；select是非空、非空字符串、不得重复的有序数组，结构有效时保留全部字符串，含未知项也仍是合法M1Query。能力检查唯一归#8：仅"project.list"/"project.language_declared"/"workspace.member"可产生Need，其余逐项诊断，不在正常化阶段拒绝整个请求。analysisId=null创建分析；非null只能打开已登记同root的分析。store不可用仍可取得并报告保存失败。
- M1Result = {contract:"m1-project-discovery-1", requestId:Id, analysisId:Id|null, requested:string[], bundle:M1Bundle, semantic:"complete"|"partial"|"unavailable", persistence:M1Receipt, diagnostics:M1Diagnostic[]}；M1Receipt唯一归#9。无有效session时analysisId=null、bundle空且保留诊断。complete仅当前所有requested已取得且无已知获取/定位缺口；有任意所需项缺口且有事实/评估为partial，无可用所需事实/评估为unavailable。保存失败独立，不强制降semantic；非法输入无需读取项目/存储。
- M1Delivery = {data:M1Result, report:string}；report为确定性Markdown，逐项列请求、Project列表/语言声明/workspace成员、未决声明、覆盖及原因、持久化结果。空列表必须附覆盖结论，不能写“没有项目”或“没有成员”的全称否定。两输出身份、事实集合、缺口原因与持久化状态相同，不再调用模型。

端口：`normalize_m1(input:dict|str, root:str|None=None, store:str|None=None)->M1Query|M1Diagnostic`（字符串模式root/store须给定，requestId由入口分配UUID，analysisId默认null）；`project_m1(query:M1Query, bundle:M1Bundle, receipt:M1Receipt, analysis_id:str, request_diagnostics:list[M1Diagnostic])->M1Result`；`present_m1(result:M1Result)->M1Delivery`。request_diagnostics由#12传递#8 M1Plan.diagnostics及本次端口错误，#7不重做能力判定。非结构/未知字段/重复选择/空select/空字符串为INVALID_REQUEST，未知contract为UNSUPPORTED_CONTRACT，才返回单个Diagnostic；未知select保留在Query并交#8。正常化失败由#6产生analysisId=null/semantic=unavailable/空M1Bundle/current诊断及not_required回执的M1Result，requested只保留可安全解析的select字符串，否则[]。

结构有效的混合select：requested保持完整原数组，#8每个未知项产生一条UNSUPPORTED_PREDICATE（recordId=该selector，path=null，message含原值），支持项继续；有已得所需事实/评估时semantic=partial，无可用所需内容时unavailable，退出2；全为未知则不读源码/不获取，空结果、unavailable、persistence=not_required、退出2。#12可仅做内存session登记，不为全未知请求创建存储事务。结构/contract错误才退出64；报告/JSON都保留每个未知请求项，不让诊断以外内容递归扩展响应。

投影输入bundle必须由#12 current_m1给出（成功提交/lookup确认后先#9重读规范包；失败为已校验暂存合并的当前包）。project.list选有效resolved评估的Project及project.name；语言项另选project.language_declared，成员项只选workspace.member。project.*保留相关有效未决/冲突评估，成员项不夹带无关Project评估；两者都保当前相关缺口和request_diagnostics，已被合法替代的旧失败不再投影。登记/证据只留选中内容所需引用闭包，supersedes仅外部历史ID，不递归附旧记录。PackageSpecification只作成员引用，不能展开包。取得所需名称/声明未知使对应coverage.complete=false；#7不能挑某个complete吞掉其他有效缺口，#8/#7使用同一当前视图。没有语言声明不推出不存在语言；#7不做获取/提交或自行重写规范ID。

未来公开调用入口由#6装配`python3 -m c2s_skill query --request REQUEST.json`，stdout仅一个M1Delivery JSON对象；退出0为semantic complete且persistence stored/already_stored/not_required，2为partial/unavailable/保存失败/未知提交，64为非法请求/契约版本。stderr仅安全运行诊断，不输出源码/秘密；candidate不接触suite。产品包装见#6，不在本轮创建入口。


## Context

用户确认见docs/decisions/0007-confirmed-system-query-requirements.md；“当前一层”仅指符合本次请求要求的顶层语义事实。 首期Rust/Python，host和项目平台遵循ADR-0003/0004；项目在单次分析中不变（ADR-0006），负载范围实际测试后定（ADR-0005）。必要分析操作和优化对照方法由代理设计，不再等待用户逐项选工具或定义严格语义金标。其他实现细节仍是候选，不假称已验证。

## Goals / Non-Goals

目标是每次请求的顶层完整事实、诚实缺口和人机双输出；不把当前一层当固定E编号/目录层数，不递归返回完整对象图。完整限定于所需事实；无法取得须说明原因，不要求严格证明语义正确。

## Approaches

代理设计选择统一公共结果再投影为报告/结构数据，替代分别生成两种独立结果。统一结果减少双重分析与事实/缺口漂移；代价是需共同结果契约。候选输出Markdown报告与JSON数据，格式属于设计安排，不是用户额外逐项批准。用户正常提出语义查询，内部规范请求可由其他Skill复用，不要求用户先手写Schema。

## Decisions

内部规范请求包含指定目录、项目/主体选择、所需事实及适用上下文。目录内全部内容是分析范围；本次选择只限定取得/返回所需事实，不把嵌套项目、测试/示例等先排除。目录不是Project身份；原生workspace、Project及目录关系按模型A分别判定。

当前顶层的解析以本次语义问题为准：项目类清单、类成员清单、指定成员定义、函数定义或实现描述可以各自成为目标。E0–E4仍是语义组织尺度，不把类型/函数层次机械映射成固定E编号。

投影规则从所需顶层事实建立取得清单，完整取得已知所需内容；不得用“最小字段白名单”只返标识符而漏掉用户要求的定义/实现。更深对象仅保留必要引用，不从证据、诊断或内嵌值夹带递归定义。用于定位目标和内部必要证据的遍历不等于递归响应；旧根0/每边加1、多深度结果示例被本次请求相对顶层定义取代，不成为对外深度参数承诺。

| 用户请求 | 本次顶层结果 | 不自动返回 |
| --- | --- | --- |
| 项目中有哪些类 | 本次范围内取得的完整类清单及必要标识/定位，覆盖缺口及原因 | 每个类全部成员和函数实现 |
| 类C有哪些成员 | C的所需成员清单和顶层事实、缺口原因 | 各成员的递归实现/引用类型定义 |
| C的成员m如何定义 | m的所需定义事实及来源/局限 | 整个C或其关联对象图 |
| 函数f如何定义/实现 | 符合本请求的顶层定义/实现语义及无法取得部分 | 被调用函数或无关对象的递归展开 |

不能唯一定位时如实列候选与歧义原因；不猜共同项目/配置。已唯一且独立的项可取得结果，相关歧义项保留缺口；不把空结果作不存在。

逐项获取/呈现/适用/覆盖/诊断保持独立；“完整”表示本次所需项已取得且没有已知获取缺口，不声称严格语义正确性证明。保存失败独立于语义取得：已得事实仍可报告，持久化失败不能隐瞒。报告与机器数据由同一公共结果投影，事实身份/范围/缺口及原因一致。后续查询先询问#8已完成项与缺口，不重新全量分析同主体。

## Risks / Trade-offs

请求解释可能遗漏用户所需顶层项：用用户给出的四类典型问题作验收例，并把不能取得/不能定位如实报告。未知类数量/解析失败不能称全目录已完整覆盖。双输出若独立生成容易漂移，统一结果对照检查。

## Migration Plan

只维护规格/设计及唯一tasks.md；不实现产品、不安装依赖、不运行实际项目分析、不apply/归档。系统需求确认不等于整体设计冻结或开发批准。

## Open Questions

代理需细化请求/结果公共类型、目录到项目定位、顶层投影规则及报告编码，并提交整体设计审核。这些是技术设计事项，不再列作等待用户补充基本需求的阻塞。跨次输入变更策略未由本次选择。
