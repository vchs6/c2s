# Design

## Context

动机见`proposal.md`。本轮将已确认需求选择性同步为主规格，产品仍未实现。确认边界以ADR-0002为准；下表和原设计中的候选均不得自动提升为基线。

| 状态 | 依据 | 可使用的结论 |
| --- | --- | --- |
| 已接受 | `docs/decisions/0001-five-semantic-layers.md` | E0–E4五层为组织尺度，主体单身份，跨层类型引用；DDD用于统一语言、身份与不变量 |
| 已观察的研究证据 | 候选定义§§1、13、17，R1–R6/C1–C5/P1–P9固定来源 | 读取20份文件并核对Git blob；包括根包/workspace、INTERFACE/ALIAS、配方/入口、状态效果及三项局部算法 |
| 候选与限制 | 首次Battle报告§§5–9；候选定义§§14–16 | 未执行全量获取、metadata、构建、安装、宏展开、测试或形式等价验证；多workspace、循环、复杂宏和Java注解缺真实验收 |
| 本变更提议 | 候选事实模型记录、候选算法delta及本设计 | 目录格式、交换记录、校验阶段、交付路径和反例集；不是ADR已批准全部细节的声明 |
| 本轮确认基线 | ADR-0002及两份正式主规格 | 用户已确认的模型组织与查询响应约束；尚未实现 |

本次能力边界包括事实模型、查询响应与候选算法描述。导入原件保持不变；主规格只包含ADR-0002确认矩阵映射的Requirement，不包含详细候选。规格生效与实现完成分开记录。

## Goals / Non-Goals

**Goals:** 本轮实现确认依据到正式规格的可追溯映射，并明确后续设计的约束。可交换机器定义、结构/跨事实校验与算法投影仍是下一阶段候选目标。

**Non-Goals:** 不预选聚合、限界上下文、仓储、数据库、获取器或产品语言；不造完整新编程语言；不证明任意语言/任意项目语义完备；不实现执行历史服务。Python3仅约束后续验证脚本，不据此决定产品实现语言。

## Decisions

### 0. 本轮选择性同步与候选隔离

用户已明确授权固化已有确认，采用同一活动变更中选择性同步的文档处理方式（代理执行选择，不是新增产品决策）。全量复制delta会越过确认边界；等待产品实现才写主规格又违背本轮授权。仅同步semantic-fact-model与semantic-fact-query的确认部分，保留algorithm-description候选。

唯一计划为tasks.md；本轮任务只产生规格、证据及必要规划，既有产品任务均保持未完成。无第二份Superpowers待办。

以下决策1–7全部是**拟议实现选择，待相关方案确认，不能作为用户批准凭据**。原事实模型候选Requirement正文已保留在`docs/development/discussions/2026-11-01-specification-baseline/semantic-fact-model-candidates.md`，其完整方案尚未批准。未决设计问题集中在同目录discussion.md；这些选择不阻塞本次已确认基线的文档同步。

### 1. 公共目录与事实载荷分离

提议以版本化JSON目录和JSON Schema承载公共定义，结构校验与跨事实规则分阶段运行。替代方案是无类型三元组或在每条事实自填层号；它们无法约束角色、跨层重复与同名关系歧义。JSON只是交换格式，不决定存储形态。

未来路径及职责：

| 交付路径 | 职责 |
| --- | --- |
| `contracts/semantic-model/types.json` | 主体/值类型、身份要素、可用上下文键及类型规则 |
| `contracts/semantic-model/predicates.json` | 语义和来源谓词的含义、角色类型、基数、不变量与主层 |
| `contracts/semantic-model/fact.schema.json` | SubjectRef、TypedValue、Condition、Fact、Evidence、Coverage结构 |
| `contracts/semantic-model/algorithm.schema.json` | OperationContract、AlgorithmDescription、BehaviorRegion、Step及类型边 |
| `contracts/semantic-model/rules.md` | 身份连续性、条件解释、模态比较、跨事实与投影规则 |
| `tests/semantic-model/fixtures/` | 正反例、固定来源定位与预期诊断，不提交外部源码副本 |
| `tests/semantic-model/test_contracts.py` | Python3结构、目录、引用及跨事实验收 |
| `tests/semantic-model/test_algorithms.py` | Python3算法与伪代码投影验收 |
| `docs/domain/semantic-model-contract.md` | 公共使用与覆盖边界，引用规格而不重写导入原件 |

这些文件目前未创建。验证脚本未来通过`python3 -m unittest discover -s tests/semantic-model -p 'test_*.py'`运行；本轮不能把该预定命令写成已通过。

### 2. DDD统一语言与身份规则

Project表示带边界依据的工程单元，PackageSpecification表示发行/解析规格，模块名属于程序结构。先定义可观察身份和不变量，不把每种记录都当实体或聚合根。替代的“仓库就是项目、目录就是成员”会误合并Click示例与CMake独立集成工程。

提议的身份要素由类型目录约束：Project使用显式项目标识及边界依据；原生workspace使用其声明身份与所属工程上下文；目标使用项目域和目标定义身份；声明使用项目域、声明种类及工具可确认的声明身份；算法有独立描述身份，管理归属可未决。名称/位置是定位线索，不能单独证明身份连续性。匿名和生成主体使用引入/变换应用身份及局部区分符；重载需要签名/声明区分信息。此处不固定全局URI编码或散列算法。

移动、重命名或版本变化不自动改身份，也不自动合并：只有规则和来源支持连续性才关联，否则保留歧义记录。来源版本与内容标识只固定证据。上下文键需有类型，至少包括平台、目标、构建选项、特性、语言模式、解释阶段及外部约束。指称不同用限定引用；值不同用带条件事实；无法唯一指称必须报歧义。

### 3. 工程关系及依赖图不混用

项目可独立存在；NativeWorkspace按工具规则记录原始成员及包→项目映射；CoordinationGroup表示分析者指定协作。AnalysisScope只是本次选取。目标保留项目管理归属，workspace命令若只是选择器不变成目标。真正无法按现有规则归属的独立定义单元先报告缺口，不伪造项目，也不在缺证时扩展所有权联合类型。

DependencyRequirement持有消费方、需求类型、阶段、约束与条件；DependencyResolution持有需求引用、提供方/候选、解析配置、可见范围、状态与证据。查询位置独立计算，不进入需求身份。保留path与version；CMake ALIAS归一不制造第二条库边；测试先后不是链接；调用不自动成为构建依赖。循环保留原图，判定需同时满足边条件与对应工程规则。替代的单一resolved/outside/unknown枚举会丢失已知范围外提供方。

### 4. 抽象事实语法与校验

以下是拟实现的公共语法，而非声称已有Schema：

```text
SubjectRef = {id, kind, ownershipScope, interpretationContext?}
TypedValue = Scalar | Enum | SubjectRef | Sequence | DefinedRecord | Expression
Condition = True | False | Unknown(reasonRef) | Compare(operator, typedOperands)
          | All(Condition*) | Any(Condition*) | Not(Condition)
          | SourceCondition(sourceRef, interpretationGapRef)
Fact = {factId, predicateId, arguments:[{role,value:TypedValue}]+,
        applicability:Condition, claimMode, evidenceRefs:[EvidenceId]+, derivation?}
Predicate = {predicateId, catalog:Semantic|Provenance, meaning,
             argumentRoles, argumentTypes, cardinalityRules, constraints, primaryLayer?}
Evidence = {evidenceId, sourceRef, contentIdentity, locator, method,
            role:Supports|Refutes|Limits, premiseFactRefs?}
Coverage = {scopeRef, subjectKinds, predicateFamilies, contextRef,
            inspectedInputs, excludedInputs, acquisitionState, gaps}
```

`?`为可选，`+`至少一项，`*`零或多项。DefinedRecord必须由目录定义字段。claimMode为declaration/specification/static_may/static_must/observation/interpretation；它不是可信度排序。SourceCondition不能变成静默True；True/False仅在前提充分时使用，Unknown不等于False。条件求值采用三值语义：Not Unknown仍未知，All有False则False、全True才True，其余未知；Any有True则True、全False才False，其余未知；空All=True，空Any=False。比较操作必须有定义过的操作符及兼容类型，无法解释时产出缺口。

校验顺序为：载荷结构→目录存在及版本→角色和值类型/基数→主体与上下文引用→跨事实不变量→来源内容有效性和推导前提→覆盖/模态诊断。错误至少定位记录、角色/字段、规则及原因；对结构合法但未知语义保留缺口。校验通过只证明契约一致性，不证明来源真值。若来源不可取得，报告未核验而不是伪称内容匹配。

### 5. 首批谓词目录及层查询

正式目录应把下表每个谓词展开为独立条目，表内`A/B`是多个条目的简写，不能作为字面predicateId。参数名称引用types目录中的主体或值类型；来源定位与推导属于横贯元数据。

| 主层 | 谓词及角色 | 关键不变量 |
| --- | --- | --- |
| E0 | `engineering.defines_project(declaration, project)`；`engineering.workspace_member(workspace, member, sourceMapping)`；`engineering.group_member(coordinationGroup, project)` | 边界依据明确；原生成员种类保留；成员不推出依赖 |
| E1 | `build.declares_target(project, target)`；`build.declares_recipe(project, recipe)`；`build.alias_of(alias, target)` | 目标归属明确；无目标不造目标；别名不造实现 |
| E1 | `build.requires(consumer, requirement)`；`build.resolves_to(requirement, provider, context)`；`build.provides_usage(target, usageRequirement)` | 用途/阶段/条件明确；解析附范围与依据 |
| E1 | `build.declares_output(producer, outputSpec)`；`build.observed_artifact(outputSpec, observation)`；`build.entry_binds(entryName, subjectOrResolver)`；`build.precedes(task, task, orchestrationContext)` | 声明不推出观察；入口目标和先后不混同 |
| E2 | `program.contains(container, declaration)`；`program.has_signature(operation, signature)`；`program.accessible_under(declaration, accessConstraint)` | 不任意传递；签名不推出效果 |
| E3 | `contract.precondition(operationOrAlgorithm, condition)`；`contract.outcome(operationOrAlgorithm, outcome)`；`contract.effect(operationOrAlgorithm, effect)`；`contract.ordering(participants, orderingConstraint)` | 前提/结果/效果/观察范围和模态明确；支持偏序 |
| E4 | `behavior.implemented_by(operationOrContract, body)`；`behavior.calls(callSite, callableOrCandidates)`；`behavior.binds(introduction, binding, initializer)`；`behavior.captures(closure, bindingOrLocation, mode)` | 实现关联不证明等价；绑定和运行对象区分 |
| E4 | `behavior.reads(step, location)`；`behavior.writes(step, location)`；`behavior.control_edge(step, step, edgeKind)`；`behavior.data_edge(step, step, edgeKind)` | 位置/别名和边种类明确；引用局部域有效 |
| E4 | `behavior.algorithm_described_by(implementationRefs, algorithmDescription)`；`behavior.projects_to_pseudocode(algorithmBody, pseudocodeView)` | 目的、步骤映射、省略项明确 |
| 无主层 | `provenance.generated_from(generatedSubject, application, sourceRefs)` | Provenance目录，多对多来源，不虚设“可信度层” |

候选方案中跨层关系仍只有一条事实，层查询拟取目录主层。主体可关联跨层事实；内部检索范围尚未确定，响应仅按semantic-fact-query主规格规定的请求及展开边界返回。通用refines的语义仍待定义。

### 6. 契约、算法和伪代码单源投影

OperationContract记录输入域、前置、outcome、effect、交互、资源/时序/并发约束及观察边界。AlgorithmDescription包含描述目的、上下文、契约引用、body、实现关联、证据和抽象边界。body由BehaviorRegion与局部唯一Step构成；每Step记录种类、类型化参数、嵌套区域、控制/数据引用及来源。绑定与赋值、异常与结果错误、条件分支与循环出口、资源操作与普通调用分开。并发保留偏序。

伪代码由body投影并返回步骤到输出段落的映射；投影规则只改变可读性，不增加未证行为。未展开子过程显示引用，UNKNOWN显示原因，省略资源/外部效果必须显式列出。独立维护自由文本伪代码存在与body漂移的风险，因此代理推荐body单源投影；该实现选择尚未裁决。验收以R5栈遍历、C5 SAX结束处理、P7参数分配为固定源码摘要，核对回调错误传播、parse_error结果、零规格及多通配行为；不执行上游源码也不声称等价。

### 7. 语言机制按语义拆分

宏记录TransformationApplication及输入/生成主体映射；无展开证据只记应用。元数据附着及已证处理效果分开，cfg条件不泛化为Java注解语义。闭包定义、可调用值、捕获对象/位置及方式分开；未知布局、生命周期不猜测。let表示绑定引入及作用域/路径可用性，不把关键字实体化。Click装饰器按调用→对象构造/返回替换→callback→名称绑定拆解，不与静态注解或原函数身份混合。

对尚无样本的复杂宏、Java注解、多workspace和条件循环建立“规则反例”fixture并明确synthetic；后续取得真实来源才能升级证据级别。合成用例能验证契约，不证明获取器已支持该语言机制。

## Risks / Trade-offs

- [五层目录被误当本体层级] → 层不进入身份；跨层引用和无workspace场景作为反例。
- [位置/提交被用作稳定身份] → 类型目录规定身份要素，移动/重载/多上下文例覆盖歧义诊断。
- [目录无限扩张或任意Record逃逸] → 每次扩展提供类型、角色和规则；不声称首批词汇已穷尽全部语言。
- [三值条件不足以证明可满足性] → 不能判定时报告未知；不把未知循环当不可发生。
- [规范、解释与运行观测混同] → 模态与方法分别记录，冲突保留，覆盖报告列明未运行事项。
- [伪代码丢失语言行为] → 求值/数值/错误/资源/并发规则有证据或UNKNOWN，投影断言与步骤映射同时验收。

## Migration Plan

本轮按tasks.md的0组完成确认分类、delta整理、选择性主规格同步及严格验证。未部署产品，不存在数据迁移。通过Git提交保留基线来源和候选正文，纠正错误须提出可追溯修订而非静默覆盖。后续实现先解决讨论记录中的设计问题、取得相应批准并重新读取apply指令；未获明确归档请求不archive。候选格式的版本化和兼容处理尚未确认，不据本段增加兼容义务。

## Open Questions

本轮规格固化的路径和执行方式已确定，无阻塞本轮的设计问题。可能改变未来公共契约或任务分解的问题不在此假装“可安全延后实施”：已移至`docs/development/discussions/2026-11-01-specification-baseline/discussion.md`，后续实施前必须解决。ID具体编码也留待后续实现设计，不改变本轮的单身份约束。
