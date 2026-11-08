# Design

## 当前领域模型基准

当前领域模型基准：工作合并、复用和响应投影按语义实体引用、请求描述面、条件、输入和覆盖适用性判断；E层和源码节点不作身份键。M1接口保留其独立profile。

## M1分析归属与串行恢复（代理技术决定，m1-project-discovery-1）

本节固定M1执行切片；旧“另批/接口未定”不覆盖本节，ADR-0009及交付隔离门禁仍适用。M1不实现订阅并发/代际取消；单进程同一analysis串行，每个请求独立投影，不允许以未实现M4替代M1基本保存失败/断连诚实性。

本节独占M1Session={analysisId:Id,inputId:Id,root:string,store:string,identityDomain:Id,sourceCommit:string|null,inputDigest:string|null,host:{os:string,arch:string,pythonVersion:string},target:{value:string|null,basisEvidenceIds:Id[],status:"declared"|"unknown"},tools:[{name:string,version:string,status:"verified"|"unknown"|"unavailable"}],profile:"m1-project-discovery-1"}。root/store为host绝对路径；analysisId/inputId/identityDomain均显式UUID登记，inputId只限定输入归属，不作主体身份；实际固定源commit/digest有证才填，不要求通用项目有Git。target未知必须null+unknown，不能从host补。tools记录实际版本；目标配置不是源码语言或宿主。首次请求建立session并在外置#9 SQLite登记，后续analysisId精确核root/store/profile/inputId；不同输入不盲复用，无跨次刷新/监控。

端口：`open_m1(query:M1Query)->M1Session|M1Diagnostic`；`verify_m1(session:M1Session, stored:M1Read)->M1Read`；`current_m1(session:M1Session, read:M1Read)->M1Bundle`；`run_m1(query:M1Query)->M1Result`（供#6装配，#7拥有返回类型）；`observe_m1(event:M1Event)->None`（#5拥有事件）。open仅登记，不构造项目语义；verify核存储session/inputId、profile、工具规则适用，保留全部历史，不能因命中而推来源/语义有效；损坏/输入失配报INPUT_MISMATCH/CONTRACT_INVALID，不把不可核验项供复用。同次固定输入不每查询全量校验，重启须核已存session的输入归属，无法核验则缺口，不自动等同新分析。

current_m1为当前视图唯一owner，#9 read返回规范化完整历史，#8/#7只消费本端口的有效包：

1. Assessment按(declaration.identity,ruleId)分组，Coverage按(selector,subject完整身份或null)分组。只承认同键/同输入、无环、目标存在且证据集合不减少的supersedes边。Assessment允许unresolved→ambiguous/resolved、ambiguous→其候选子集或其一resolved、resolved→同一Project补证；resolved换Project/不可兼容分支不得覆盖，保留各叶并产生CONFLICTING_CLAIMS，不能以“最新”裁真。
2. Coverage替代要求checkedPaths/证据不减少，消失的旧诊断键必须显式列于resolvedDiagnosticKeys，且新的checkedPaths/实际证据涵盖该诊断path（path=null须有对应新评估/盘点依据）。仍未支持/未决的项不能宣称解决；冲突诊断不能靠替代清除。complete→不完整不作有效替代；无新增需求的冗余失败探测只进M1Event，不推翻仍适用的完整覆盖。违反替代条件保留旧叶/新分支并报CONTRACT_INVALID，不丢失败内容。
3. 每组只取未被合法替代的叶；旧失败/未决诊断保留在历史及事件，不再混入当前包。多叶一律保留，覆盖按所有相关叶均complete且无当前缺口/冲突才有效；没有Coverage、存在有效未决/矛盾Assessment或对应项缺口均不得视完整。project.*关联项目评估，workspace.member不要求Project评估先resolved。事实自身不因评估收敛删除，#7只按有效resolved评估选Project；相关冲突事实仍随结果和诊断披露。
4. 返回包只含有效Assessment/Coverage、所需登记/证据及全部当前可用事实；bundle.diagnostics只列当前全局问题和有效叶/矛盾诊断。supersedes历史ID不递归展开；独立阶段失败只在事件/历史中，不当当前缺口。#8规划与#7投影调用同一视图，不各自挑“任一complete”。

执行顺序：open/read/verify→#8 plan_m1（调用current_m1）→#10 acquire_m1→#9 canonicalize_m1合并已存/暂存→#3 validate_model合并包→#9 commit_m1→成功read_m1/verify/current_m1→#7 project_m1。open的新session先留本进程，首次commit连同M1Bundle原子登记；有新增session/记录才提交，无变化not_required并用已有current视图。成功或lookup确认成功都须读到同session且generation不早于回执的规范历史，再投影，不直接用候选ID；重读失败则回执unknown/COMMIT_UNKNOWN，已校验暂存可报告但不承诺规范ID已存。

failed或仍unknown：将prior已存与pending经canonicalize_m1合并/校验/current_m1，保留本次已得事实，回执如实failed/unknown；暂存不冒已发布。下次同进程优先重用已校验暂存，unknown先lookup/read，确认成功转上面的统一规范回流。进程重启只复用已发布且适用内容，不保证未发布暂存/零Token；临时结果仅当前进程session存活期，close/进程结束释放。#9回执addedIds/existingIds只作提交说明，不充当投影ID映射。

每次received/accepted（若有效）/firstResult（若有）/terminated单调时间和M1Event/#5 M1Usage送#5；#6补正常化/打开失败事件，Profile允许query/session=null。盘点完成性、analysisId与acquired/reused/none来源一起传profile_m1，无已核盘点就unknown，不能把[]解释成完整空目录。失败也入总体，必要盘点/副本准备计inventory/acquire，未知成本null。M1Result/#9回执分别拥有语义/持久化状态。M1每次获取失败至多一次本请求重试；未知提交至多一次lookup/规范重读后仍未知即报告，下一显式查询可继续，不挂后台。


## Context

历史背景：原提案以共享context、ADR-0001/0002及当时五视角主规格为约束，并记录用户对模型A的历史选择。当前领域主轴按ADR-0012更新为语义实体；本段未实现的模型细节/性能候选不因本次对齐自动成为用户确认。讨论、异议及独立复核仍见本Issue评审目录。

## Goals / Non-Goals

固定项目输入下不混用不适用成果、相同需求少重复、恢复有边界，结果和持久化状态分开。非目标：历史快照服务、分布式exactly-once保证、实现数据库锁或后台监控。

## Approaches

候选同一有效性条件下共享等价需求，逐查询独立订阅/投影；替代逐请求隔离执行实现简单、取消清楚但重复工具与模型成本；重叠查询只共享相同且充分适用子需求，不为合并扩大分析/响应。是否跨进程共享待负载决定，不能只因相似名称合并。

## Decisions

职责：#8产需求计划和缺口；本能力调度/来源观察/工作合并/取消/恢复，#10执行许可获取；#3校验语义；#9消费期望基点原子发布；#7逐项投影；#5/#11消费观测。存储不自行核验来源或裁真。

一次分析期间项目保持不变（ADR-0006）。成果记录本次分析输入归属、适用配置、host/项目平台、工具能力/规则版本与覆盖。复用检查这些条件和公共契约，不要求每次查询重复全仓源码核验或持续监控；同一输入稳定也不证明工具输出完整或模型主张正确。

分析输入标识仅限定内部成果归属，不作为主体身份，不提供用户历史快照API，也不强制文件锁/快照实现。后续查询带来事实增加，不是项目变化；原分析内TOCTOU/热更新/跨源原子来源观察设计不再作为本期功能要求。跨次输入如何复用、更新或清理另留讨论，不由此决定。

共享键包含规范需求、主体/条件、观察基点、能力/规则版本及覆盖，不同target/配置不能合并。相同子需求可订阅共享工作，响应仍独立范围。共享执行并非共享所有模型对话：输入必要上下文仍按#11，有额外来源/权限差异不能自动合流。

| 事件 | 行为与恢复 |
| --- | --- |
| 一订阅取消 | 退订并停止其独有新工作，其他订阅继续 |
| 最后订阅取消 | 停止新调度，尽力取消在途工作；晚到结果隔离，只有满足核验/发布条件方可共享，不强制提交 |
| 获取/模型失败 | 保留已验证部分和失败缺口，按获准重试策略局部重试；不重做仍有效阶段 |
| 构造成功但保存失败 | 可返回带证据的本次已核验事实并明确未持久化/保存失败；操作汇总partial（非全部成功），语义维度仍可semantic_complete，不对未来复用作已存承诺 |
| 提交结果未知/断连 | 先以幂等标识重读提交结果/语义内容，再补未发布单元；不立即全量重构 |
| 进程中断 | 已发布单元重读校验；未发布候选不可见；仍存在且有效的中间成果可重用，不保证全部临时成果跨进程存活 |
| 已知输入归属/适用条件不符 | 不盲复用并保留缺口；不将异常扩大为本期项目热更新支持 |
| 工具不可用/环境失配 | 报对应组合能力缺口或许可内等质量替代，不偷偷改target |

#9拥有原子提交和语义去重，本能力不另实现事务。项目输入虽固定，但并发新增事实仍可能重复或半写，引用自洽单元/幂等发布仍须保证；这是事实存储写入的一致性，不是项目源码TOCTOU。原子单元与后端契约仍需冻结，不要求项目来源更新政策。

观测只记录必要结构事件：逻辑请求/尝试/需求/提交关联、阶段开始终止原因、排队/工具/模型/核验/存储/投影耗时、模型输入输出Token/调用/上下文量、复用命中及有效/失效/未核验原因、重复工作、覆盖缺口及资源指标；复用#5计时端点与总体分母。不复制全文源码/提示到日志来求可观测，来源引用可回查；规划诊断、静态工具证据和真实运行观测标明类型。跨host时钟只对同计时域算时长，分布式关联不直接相减未校准时间戳。

可维护/扩展：获取器通过能力契约扩展，状态/诊断集中定义；增加适配不新建身份语义。负载增大时先测共享率、等待、内存、写竞争和失效成本，再决定并发/持久化方式。
共享执行按工作代际区分取消/新订阅竞态；旧代取消不得终止新代，预算/权限仍逐订阅判断。共享物理模型调用Token只在全局实际量计一次，分别记录各订阅受益或成本分摊，分摊不能重复累加成实际消耗；请求延迟仍各自测量。同次固定输入下复用与提交只需保持归属及适用性；不以重复全仓来源扫描换取表面一致性，也不宣称任何跨次结果自动有效。

临时构造候选保留、有效性失效与清理由#12负责，时长待负载/恢复要求冻结；#9只负责已发布单元与提交回执保留语义。晚到旧代结果隔离，不污染新代候选；中间成果无法保留时如实重取，不保证崩溃恢复零Token。

异常Scenario：已知成果输入归属不适用→不盲混为本分析有效结果，保留缺口；没有要求持续检测项目变更或实施跨次刷新。

语义完成（#7）与持久化成功（#9）分别汇总：完整事实而保存失败为语义完成/持久化失败/操作partial，#5的语义成功率与延迟仍计该完整回答，操作成功率另列，不用一布尔值冲突定义。未需写入的已有效存储复用视持久化not-required，不误记保存失败。


## Risks / Trade-offs

共享增加取消/等待复杂度，可能伤首结果延迟；项目来源保持不变不代表事实并发写入无竞争，仍需幂等/引用自洽；不增加全仓一致快照服务。保留临时成果有内存成本和生命周期边界，恢复不保证零Token。

## Migration Plan

只规划；不改正式主规格、不apply、不archive。先冻结公共定义和未决重大选择，再整体审核，最后取得明确开发批准。唯一任务清单为本变更tasks.md，不维护第二套Superpowers计划。语言/混合边界、host和target按#5/#10矩阵取证；#5定义质量、端到端延迟/吞吐/资源及Token评价，数值未定不得宣称达标。

## Open Questions

代理需细化事实写入原子单元/后端契约、临时成果保留时长和重试/并发数值，相关负载范围依实际分析测试后确定，不作为当前规划冻结前置；无运行证据。

ADR-0007后，“语义完成”仅表示本次所需顶层项已取得且无已知获取缺口，不是严格语义正确性证明。缺口和原因必须进入同一公共结果供#7生成可读/机器输出。范围内所有目录内容均可能成为查询目标；相同主体只补未完成部分。必要分析操作由#10设计安排，当前执行/恢复不以逐操作重复批准或人工完备语义金标为前置。

## ADR-0013 当前约束（2026-11-08）

协调固定输入上的事实获取、提交和恢复；共享工作依据目标、证据和适用覆盖，不依据DDD聚合或观察视角划分。取消、失败与存储状态分别报告。 依据：`docs/decisions/0013-非DDD语义事实模型.md`。历史执行记录中的DDD或旧模型表述不构成现行约束。本轮只进行文档修订，产品重构完成状态不变。
