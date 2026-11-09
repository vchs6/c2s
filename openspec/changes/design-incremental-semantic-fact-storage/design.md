# Design

现行接口接续（2026-11-09，ADR-0014）：本文件M1/V1及旧完整事实运行接口为历史规划/交付记录，当前公开运行协议仅V2，不再提供兼容查询、仓储或转换。通用能力要求继续适用；新实施不得恢复旧API。唯一删除与审核任务见`openspec/changes/redesign-semantic-entity-domain-model/tasks.md`第11节。

## 当前领域模型基准

当前领域模型基准：本提案定义的M1增量写入继续服务于`m1-project-discovery-1`，其identity不替代语义实体identity。实体档案增量依据语义实体注册身份及其主张、证据、适用条件和覆盖处理，详见`redesign-semantic-entity-domain-model`；本提案的旧M1实现记录不表示实体档案已切换。

## M1读取与引用自洽提交（代理技术决定，m1-project-discovery-1）

本节固定M1端口和最小后端，不改变原全量任务；ADR-0009授权准备及门禁通过后实施，M2–M4细节不作M1新增前置。记录沿用#3封闭JSON记法，本节独占：
- M1Receipt={operationId:Id|null,state:"stored"|"already_stored"|"not_required"|"failed"|"unknown",generation:int|null,addedIds:Id[],existingIds:Id[],diagnostics:M1Diagnostic[]}；generation非负，未读到有效存储为null。未需提交时not_required；语义取得不由state决定。
- M1Read={analysisId:Id,session:M1Session|null,generation:int,bundle:M1Bundle,artifacts:M1Artifact[],receipts:M1Receipt[],diagnostics:M1Diagnostic[]}；session唯一引用#12、Artifact引用#3；不存在的合法新分析返回session=null/generation=0空包；损坏/不可读仍返回诊断，不把空包当有效命中。
- M1Commit={session:M1Session,operationId:Id,expectedGeneration:int,bundle:M1Bundle,artifacts:M1Artifact[]}；session唯一引用#12、Artifact引用#3；operationId绑定session.analysisId、profile和规范提交内容（不含operationId）SHA256；同ID异内容拒绝CONTRACT_INVALID。会话的tools/target属于已观测元数据，提交时须与已有session的输入/身份域/根范围一致，可追加观测，不能变换inputId。

端口：`read_m1(store:str, analysis_id:str)->M1Read`；`commit_m1(store:str, candidate:M1Commit)->M1Receipt`；`lookup_m1(store:str, analysis_id:str, operation_id:str)->M1Receipt`；没有回执返回state=unknown及COMMIT_UNKNOWN，不先重做获取。未触发提交的#7结果使用operationId=null/state=not_required/空ID数组；读取失败用failed，不伪装not_required。

M1采用外置SQLite（Python3标准库sqlite3）单写事务；数据库承载session登记（#12 M1Session原值）、注册表、bundle记录及回执，提交一个M1Bundle为本切片最小自洽单元，含全部新增主体、证据、事实、评估、覆盖与回执，同事务可见。#12 session登记与registry首次写入须同事务；未完成记录对读取不可见。generation乐观比较失配返回failed/INPUT_MISMATCH，由#12重读后重新差量，不吞掉已得候选；事务失败无半包可见。M1串行协调，跨进程并发/取消代际留M4；SQLite原子性/基本崩溃后重读不得延期。

规范比较端口（本#9所有）`fact_key_m1(fact:M1Fact)->str`返回规范JSON对象{predicate:fact.predicate,subject:fact.subject.identity,value:规范值,claimMode:fact.claimMode,condition:fact.condition}；引用值规范为{identity,kind}，字符串保原值，identity三元组完整保留。不含factId/evidenceIds；#5保存此key，不能自行重定义或跨身份域按名称匹配。等价主张合并新增证据并选最先已存factId（全新同批等价项选字典序最小ID），所有引用回写该规范ID。

证据等价键为(source,path,来源附件sha256,sha256,startByte,endByte,method,toolName,toolVersion)，不删定位/方法；附件按原始字节判等（摘要加速，碰撞时比较原文），与证据同事务提交。Registration按sourceKey/完整ref绑定，其evidenceIds并集追加合法；仅ref/kind/sourceKey变化拒绝，不能把合法补证当“同ID异载荷”。Assessment按(declaration.identity,ruleId,status,projects完整引用集合,evidenceIds集合,supersedes集合,diagnostics规范JSON)判等，Coverage按全部非ID字段判等；同内容不同ID选已存规范ID并重写supersedes/诊断recordId。新进展记录按#3增加ID/替代边，保留旧记录；不在存储端擅选当前真值。单值不兼容主张仍保留双方和CONFLICTING_CLAIMS。#12 current_m1对#9读出的完整历史给唯一当前视图。

纯数据端口`canonicalize_m1(session:M1Session, stored:M1Read, pending:M1Bundle, artifacts:list[M1Artifact])->M1Read`与commit使用同一规范化规则：在已核输入下合并历史/新记录、证据并集、规范ID/所有引用重写，返回generation不变的暂存读形状（不写盘、不增加成功回执）。全新分析可用session=null/generation=0的空M1Read作为stored。#12先canonicalize再校验其合并包；#5可直接以fact_key_m1生成包含未保存结果的比较摘要，无隐式全局缓存。

commit_m1仍仅返回M1Receipt；stored/already_stored或lookup确认成功后，#12必须read_m1取得generation>=回执generation且同session的规范历史，再current_m1后供#7投影；不得直接把提交前ID包当已存结果。read失败/归属不符时本次返回unknown/COMMIT_UNKNOWN，暂存事实可报告但规范持久化身份未确认，下次显式查询可继续；不伪装stored。无需提交路径使用已有核验规范包；failed/unknown路径用canonicalize得到的已校验暂存+已存合并包并明确回执状态。相同内容不同operationId仍去重；同operationId同内容回原回执。M1后端只为此切片，不冻结全产品数据库/跨次更新政策。


## Context

历史背景：原提案以共享context、ADR-0001/0002及当时五视角主规格为约束，并记录用户对模型A的历史选择。当前领域主轴按ADR-0012更新为语义实体；本段未实现的模型细节/性能候选不因本次对齐自动成为用户确认。讨论、异议及独立复核仍见本Issue评审目录。

## Goals / Non-Goals

固定项目输入内重复构造/重试不重复存储，新增内容不遗漏，保存原语义及证据。非目标：数据库实现、快照查询、全版本历史、自动重命名识别。

## Approaches

候选后端端口+确定性规范比较，支持原子发布语义。单文件原子替换实现简单但并发/大集合写放大；事务存储支持细粒度去重但增加依赖和平台成本；不可变分块清单有复用优势但需垃圾回收与引用校验。后端按契约与平台兼容性比较，负载实际测试后确定适用范围，不要求用户预先给定规模；这些物理手段不决定跨次分析的更新政策。

## Decisions

复用#3主体身份与主张条件/模式；主体、主张、证据、覆盖分别比较，不用同名、路径、层号或源码摘要当主体身份。候选内容指纹仅加速规范化等价比较，需处理哈希碰撞并保留原始语义，不能作为跨语义身份。顺序有语义的参数/算法不能排序抹平；证据位置、条件和主张模式不能删除求同。

| 候选与已存比较 | 操作含义 |
| --- | --- |
| 同主体、相同规范主张和相同证据 | already-stored，不再写重复内容 |
| 主张相同，新增独立证据 | 只新增证据及关联，不复制主体/主张 |
| 同主体、不同适用条件/模式 | 按模型A可比较性校验后保存新增内容，不擅自覆盖 |
| 同适用条件且不兼容主张 | 冲突保留并标诊断，不最后写入者裁真 |
| 当前输入归属或适用条件未确认的已有内容 | 不盲作同次有效成果，不因此自动实施跨次更新 |

用户已确认单次分析期间项目不变（ADR-0006）。本期增量写入围绕同次查询新增内容，不要求处理同主体来源热更新，因此原D03的分析内A/B/C选择不再是前置条件。先前方案讨论保留在原Battle/历史提交中；本决定不选A/B/C，不承诺不同分析之间自动复用或更新。

提交消费经公共校验候选、读取观察和期望有效性/内容基点，产出新增/已存/冲突/输入不适用/失败逐项结果。幂等标识绑定规范提交内容及政策/契约版本；重试同标识同内容复用提交结果，同标识异内容报冲突。语义去重还跨不同操作标识生效。

发布边界为保证引用自洽的最小单元，不等于全仓事务。内部引用目标/必需证据与主张一起可见，外部引用按模型A明确标记；部分失败可报告已发布单元与未完成单元，不能暴露悬空主张。中断后已发布结果可核验重读，未发布部分重试；不要求exactly-once网络传递。项目在构造与提交之间不变；#12确认成果属于本分析输入与适用上下文，#9仍保证并发事实写入的引用自洽，不要求监控项目源码变化。

路径大小写/分隔符/Unicode/行尾只影响证据定位与适配，不按host统一lowercase重键；语义内容去重/索引和差量比较应确定性完成，禁止调用模型判同。主张与来源核验观察分开记录，不把全量重写或长期历史默认为“增量”。
补证只指独立新依据追加；旧依据撤回或失效属于变化，不当纯补证掩盖不适用内容；跨次撤证政策另议。幂等结果保留窗口待负载和恢复要求冻结；窗口过期后仍用语义去重防重复。批内循环引用允许共同发布，失败时该自洽单元整体不可见，不要求全仓事务。

补证合并候选规则：以模型A证据身份/原始来源及方法区分独立依据；同证据重复转换不是独立新证据。同证据标识不同载荷报契约冲突。追加不同证据关联不删除既有支持/反驳/限制角色；来源或方法配置/能力版本不同须保留，覆盖单独比较，不能简单合并声明完整性。该规则和原子单元未冻结时相关提交实现阻塞。幂等结果过期后可不返回原操作报告，但仍核已发布语义内容；恢复不要求永久日志服务。

验证反例：同操作ID提交内容A后用内容B重试→拒绝；两并发操作写同一规范内容→至多一份语义记录，另一得已存；循环A↔B中B证据写失败→整个自洽单元不对查询可见，重试只发布完整单元。


## Risks / Trade-offs

去重误抹配置/顺序/新证据会丢语义；读查再写并发须原子去重或等价约束；原子发布失败窗口由#12故障注入验证；写放大/元数据成本按#5计入，不宣称节省比例。

## Migration Plan

只规划；不改正式主规格、不apply、不archive。先冻结公共定义和未决重大选择，再整体审核，最后取得明确开发批准。唯一任务清单为本变更tasks.md，不维护第二套Superpowers计划。语言/混合边界、host和target按#5/#10矩阵取证；#5定义质量、端到端延迟/吞吐/资源及Token评价，数值未定不得宣称达标。

## Open Questions

本期分析内无D03更新前置裁决；跨次政策另留讨论，后端、原子单元和索引由代理按公共契约及实际能力设计；负载和成本随测试如实报告；不承诺历史查询。

## ADR-0013 当前约束（2026-11-08）

保留幂等、补证、冲突和原子提交要求；按稳定实体身份及来源适用性复用。M1独立、旧完整档案只读兼容；存储组织不由DDD聚合或事务模型决定。 依据：`docs/decisions/0013-非DDD语义事实模型.md`。历史执行记录中的DDD或旧模型表述不构成现行约束。本轮只进行文档修订，产品重构完成状态不变。
