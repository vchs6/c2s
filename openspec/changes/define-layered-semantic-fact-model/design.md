# Design

## Context

动机见`proposal.md`。当前只有开发工具、导入研究与工作流，未实现公共Schema、事实校验或提取Skill；本轮补齐规划，不创建这些实现。

| 状态 | 依据 | 可使用的结论 |
| --- | --- | --- |
| 已接受 | `docs/decisions/0001-five-semantic-layers.md` | E0–E4五层为组织尺度，主体单身份，跨层类型引用；DDD用于统一语言、身份与不变量 |
| 已观察的研究证据 | 候选定义§§1、13、17，R1–R6/C1–C5/P1–P9固定来源 | 读取20份文件并核对Git blob；包括根包/workspace、INTERFACE/ALIAS、配方/入口、状态效果及三项局部算法 |
| 候选与限制 | 首次Battle报告§§5–9；候选定义§§14–16 | 未执行全量获取、metadata、构建、安装、宏展开、测试或形式等价验证；多workspace、循环、复杂宏和Java注解缺真实验收 |
| 本变更提议 | 两份delta spec及本设计 | 目录格式、交换记录、校验阶段、交付路径和反例集；不是ADR已批准全部细节的声明 |

本次能力边界按公共行为分成事实模型与算法描述。导入原件保持不变；详细需求处于活动变更，不提升为已归档主规格。

## Goals / Non-Goals

**Goals:** 让下一阶段能够实现可交换的机器定义、定位清楚的结构/跨事实错误、来源覆盖报告及结构化算法投影，并由反例验证身份和引用约束。

**Non-Goals:** 不预选聚合、限界上下文、仓储、数据库、获取器或产品语言；不造完整新编程语言；不证明任意语言/任意项目语义完备；不实现执行历史服务。Python3仅约束后续验证脚本，不据此决定产品实现语言。

## Decisions

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

跨层关系仍只有一条事实；层查询取目录主层，主体查询收集所有相关事实。未定义语义保留关系时不提供通用refines。

### 6. 契约、算法和伪代码单源投影

OperationContract记录输入域、前置、outcome、effect、交互、资源/时序/并发约束及观察边界。AlgorithmDescription包含描述目的、上下文、契约引用、body、实现关联、证据和抽象边界。body由BehaviorRegion与局部唯一Step构成；每Step记录种类、类型化参数、嵌套区域、控制/数据引用及来源。绑定与赋值、异常与结果错误、条件分支与循环出口、资源操作与普通调用分开。并发保留偏序。

伪代码由body投影并返回步骤到输出段落的映射；投影规则只改变可读性，不增加未证行为。未展开子过程显示引用，UNKNOWN显示原因，省略资源/外部效果必须显式列出。替代的独立维护自由文本伪代码会与body漂移，不采用。验收以R5栈遍历、C5 SAX结束处理、P7参数分配为固定源码摘要，核对回调错误传播、parse_error结果、零规格及多通配行为；不执行上游源码也不声称等价。

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

当前无主产品规格或已部署载荷，不需要数据迁移。本轮先完成活动变更并严格校验；后续另行取得apply指令，按`tasks.md`生成公共定义与反例验收，完成证据记录后再按明确请求处理主规格同步/归档。契约格式引入版本标识，若后续修改字段含义必须保留版本差异及转换说明；回退可停止发布新公共定义，不重写导入研究或伪造已有提取结果。

## Open Questions

- 全局ID的具体字符串编码和内部存储可在实现公共身份规则时选择；不得改变本规格的稳定性与上下文保持行为。
- 真正的workspace独立目标、宏展开、注解处理和条件循环真实来源尚缺；在补证前保持缺口和合成用例标记，不宣称获取能力或普遍性。
