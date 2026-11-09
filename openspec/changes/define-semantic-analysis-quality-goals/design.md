# Design

现行接口接续（2026-11-09，ADR-0014）：本文件M1/V1及旧完整事实运行接口为历史规划/交付记录，当前公开运行协议仅V2，不再提供兼容查询、仓储或转换。通用能力要求继续适用；新实施不得恢复旧API。唯一删除与审核任务见`openspec/changes/redesign-semantic-entity-domain-model/tasks.md`第11节。

## 当前领域模型基准

当前领域模型基准：质量评价以本次请求所需实体、属性、关系、源码实现映射、测试验证映射、证据与覆盖缺口为对象。E0–E4可作结果观察/分组维度，不作为实体类别或完整度标准。

## M1公开测量记录（代理技术决定，m1-project-discovery-1）

本节独占计量记录，其他change只消费；ADR-0009授权及独立门禁继续适用，M2–M4优化不作开始M1前置。记法/基础类型沿用#3；不含源码/提示正文。
- M1Event={eventId:Id,requestId:Id,attemptId:Id,needId:Id|null,operationId:Id|null,stage:"normalize"|"read"|"plan"|"inventory"|"acquire"|"validate"|"commit"|"project",clockId:Id,startNs:int,endNs:int,outcome:"complete"|"partial"|"failed"|"reused"|"unsupported",toolMs:number|null,peakRssBytes:int|null,readBytes:int|null,writtenBytes:int|null,llmCallIds:Id[],diagnostics:M1Diagnostic[]}；单调时钟同clockId才相减，未知资源为null，endNs>=startNs。
- M1Usage={callId:Id,requestIds:Id[],provider:string,model:string,inputTokens:int|null,outputTokens:int|null,contextBytes:int|null,status:"measured"|"unknown",source:string}；actual物理调用/重试各一callId，source注明供应商usage/本地计数或缺证原因，不把估算当实际；无调用列表=[]，不能将未计量调用记零。
- M1Profile={profileId:Id,requestId:Id,query:M1Query|null,session:M1Session|null,inputStatus:"invalid"|"accepted",scenario:"cold"|"reuse"|"supplement"|"retry",strategyId:Id,receivedNs:int,acceptedNs:int|null,firstResultNs:int|null,terminatedNs:int,clockId:Id,events:M1Event[],usage:M1Usage[],semantic:string,persistence:string,factSummary:[{factId:Id,key:string}],gaps:[{selector:string,subject:M1SubjectRef|null,path:Path|null,code:Id,message:string}],inventory:{analysisId:Id|null,state:"complete"|"partial"|"unknown",origin:"acquired"|"reused"|"none"},fileCount:int|null,sourceBytes:int|null,storeBytes:int|null,diagnostics:M1Diagnostic[]}；semantic/persistence枚举严格引用#7/#9。key由#9 fact_key_m1生成，保存实际投影事实的完整规范等价键而非仅ID；gaps逐当前请求项保留缺口，非项级诊断selector="*"。不保留源码/提示全文。

端口`profile_m1(request_id:str, query:M1Query|None, session:M1Session|None, delivery:M1Delivery, scenario:str, strategy_id:str, received_ns:int, accepted_ns:int|None, first_result_ns:int|None, terminated_ns:int, clock_id:str, events:list[M1Event], usage:list[M1Usage], inventory:{analysisId:str|None,state:str,origin:str,entries:list[M1Entry]}, store_bytes:int|None)->M1Profile`；inventory枚举精确沿用M1Profile字段。#6在收到命令输入后、正常化前分配失败路径的备用requestId并记录receivedNs；正常化成功改用Query.requestId关联已缓冲的阶段事件，失败保留备用ID，profile的request_id始终等于delivery.data.requestId（query非null时也等于query.requestId）。结构有效请求acceptedNs非null，其他为null/query=null/inputStatus=invalid；open失败允许query非null/session=null/inputStatus=accepted。失败M1Delivery使用#7的空结果/诊断，不落原始非法输入。firstResultNs只在已有经校验可投影事实时给值，不是字节前缀；所有CLI请求尝试（含非法/打开失败）入总体，未送达进程的启动失败不计。#12供合法请求事件，#6供正常化/打开失败事件，#5产Profile供#11比较。

盘点输入由#10 M1Acquired的inventory/inventoryComplete转换：同analysisId、完整且已核验时state=complete；部分为partial；未盘点、复用但无已验证盘点、session=null时unknown/none/entries=[]。复用已有盘点时origin=reused并保留其analysisId/完成性，不能仅凭空entries推0。只有state=complete且归属当前session才fileCount=完整file数（可0）；sourceBytes还要求每个file.sizeBytes已知才求和，否则null；其他总体均null，storeBytes取实测参数。received<=accepted（若有）<=firstResult（若有）<=terminated，均同clockId；前置失败也保留received→terminated时长与失败事件。

factSummary精确遍历delivery.data.bundle.facts并调用#9 fact_key_m1，故保存失败仍有实际载荷的规范键；不靠事后重读补齐。gaps来自当前Coverage中severity=gap/error/conflict的诊断，使用该Coverage.selector/subject及诊断path/code/message；结果顶层诊断同样纳入，UNSUPPORTED_PREDICATE的selector取其recordId，其余无项关联用"*"/subject=null。相同(selector,subject身份或null,path,code)键去重，多个message按字典序连接保留原因。Profile.diagnostics保留结果顶层诊断及盘点/计量不可得原因，历史失败仍在events，不变成当前gaps。

`compare_m1(before:M1Profile, after:M1Profile)->dict`返回{comparable:bool,reasons:string[],strategies:{before:Id,after:Id},elapsedMs:{before:number,after:number},tokens:{before:int|null,after:int|null},addedFactIds:Id[],removedFactIds:Id[],gapChanges:{before:[{selector:string,subject:M1SubjectRef|null,path:Path|null,code:Id,message:string}],after:同形数组}}。仅消费Profile内摘要，不读store/全局缓存；elapsedMs=(terminatedNs-receivedNs)/1e6，无调用的usage=[]确为0，存在unknown用量则总量null。

可比性要求query/session非null、相同inputId与identityDomain、profile、root、select顺序及host/target/工具模型版本；策略由strategyId显式标明，允许前后不同以对照。不同分析新分配的inputId/identityDomain即不可比（reasons列明），不能按名称/路径重配身份；本切片不要求跨次身份连续性。非法/打开失败样本保留时长/成本，但不可比语义差异。可比时以factSummary.key集合差给added/removed的对应原factId，缺口以(selector,subject完整身份或null,path,code)键比较并保message；不可比时added/removed=[]、gapChanges仍分别原样列示，不把空差异当相等。少事实/多缺口不自动算收益；未测不得宣称收益/负载上限/全平台支持。


## Context

用户确认见docs/decisions/0007-confirmed-system-query-requirements.md；“当前一层”仅指符合本次请求要求的顶层语义事实。 首期Rust/Python，host和项目平台遵循ADR-0003/0004；项目在单次分析中不变（ADR-0006），负载范围实际测试后定（ADR-0005）。必要分析操作和优化对照方法由代理设计，不再等待用户逐项选工具或定义严格语义金标。其他实现细节仍是候选，不假称已验证。

## Goals / Non-Goals

评价实际取得的事实、缺口及原因、性能和Token。当前不以完备语义金标、形式证明、固定正确率或数值SLO作为查询/规划前置；仍保留结构、引用、契约及实际运行记录检查。

## Approaches

代理采用优化前/后同输入与同请求对照，必要时分解机制做额外实验；替代先固定硬数值目标和人工全量金标在当前缺少依据，用户已选择如实报告和自行对比。机制拆分是诊断方法，不是必须完成三组实验的业务门槛。

## Decisions

测试档案记录项目输入、请求顶层范围、实际项目/文件规模、并发/请求场景、host、项目构造环境、工具/模型版本与所用策略。负载适用范围据实际项目分析测试后确定，不要求用户先给规模。

比较首次构造、同次复用、后续查询补充和失败重试；相同主体后续只补未完成部分。不隐去失败、缺口、重复上下文或新增工具准备成本。输出同时列取得项和缺口变化；若优化后少取得了所需事实，必须列差异，不能只报Token下降为收益。

请求总体包括取得/部分/失败/不支持，语义完成、持久化结果和操作汇总分别统计；无已知获取缺口不等于严格正确。语义“成功率”若使用须明确其取得口径，不把它标为真实语义正确率。

计时从接受请求起，首个有效语义结果与终止分开；排队/获取/模型/核验/存储/投影及重试归原逻辑请求。记录实际输入输出Token、调用数、模型上下文量、重复分析、延迟分布/样本数、吞吐、内存、工具耗时和存储占用。共享物理调用只计一次，受益另列。预算/限额不是降耗机制。

期望档案可以验证已知示例、结构/引用/状态一致性与“缺口要有原因”，不把它冒充全量语义正确性金标。尚未运行的性能/Token数字保持未测。

## Risks / Trade-offs

不同输入、请求范围或缺口变化会影响可比性：明确记录，不将缺事实包装为更省。工具和模型仍可能错误，报告方法/来源/局限，不宣称严格正确。

## Migration Plan

只维护规格/设计及唯一tasks.md；不实现产品、不安装依赖、不运行实际项目分析、不apply/归档。系统需求确认不等于整体设计冻结或开发批准。

## Open Questions

代理需落实测量事件/报告格式和优化前版本选择；在未来实际分析中取得数据。系统评价方式已明确（D02不再等待人工严格正确性定义），不承诺未测收益。

## ADR-0013 当前约束（2026-11-08）

评价请求范围内的事实、来源、枚举覆盖和缺口；分开来源直接陈述、静态推导和暂定解释。结构合法、节点数量或遍历成功均不能证明需求解释为真。 依据：`docs/decisions/0013-非DDD语义事实模型.md`。历史执行记录中的DDD或旧模型表述不构成现行约束。本轮只进行文档修订，产品重构完成状态不变。
