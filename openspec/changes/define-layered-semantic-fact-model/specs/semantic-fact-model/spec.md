# Spec Delta

## Purpose

为软件项目语义事实提供语言无关、类型化且可追溯的公共交换与校验契约，使工程组织、构建、程序结构、操作契约和算法能够分别查询并通过稳定引用关联，保留未知、条件、冲突及实际获取范围。

## ADDED Requirements

### Requirement: 五层组织与单一主体身份

系统SHALL以E0工程组织与协作、E1构建装配与交付、E2程序结构与接口、E3操作行为契约、E4实现算法与局部语义组织事实。层号MUST由语义谓词目录确定，SHALL NOT进入主体身份或自动产生包含、细化关系；同一主体可由多层事实引用。

#### Scenario: 同一操作的接口与效果
- **WHEN** 同一操作具有签名、状态效果和算法实现事实
- **THEN** 三项事实分别归入E2、E3、E4并引用同一操作身份，不复制操作或自动添加refines边

#### Scenario: 没有工作空间的项目
- **WHEN** 来源支持一个独立项目且没有原生workspace声明
- **THEN** E0仍保留项目事实，不为填满层次创建workspace

### Requirement: 显式工程边界与组织关系

系统SHALL分别表达Project、项目边界评估、NativeWorkspace、CoordinationGroup、AnalysisScope及成员关系。项目边界MUST有来源和解释依据；仓库、目录、清单、包坐标与项目SHALL NOT仅凭名称或路径相等合并。原生成员种类及其工程映射MUST保留，成员关系不转移所有权或推出依赖。

#### Scenario: 根包兼任工作空间
- **WHEN** Cargo根清单同时声明包和workspace且根包未列于显式members条目
- **THEN** 保留两种角色和各自来源，不从条目行数声称完整成员数已经解析确认

#### Scenario: 多个独立项目与多个工作空间
- **WHEN** 两个工作空间显式引用若干项目，另一个项目独立存在，或工具禁止某种重叠成员关系
- **THEN** 各项目身份独立，按原生规则保留各成员声明与合法性；不制造共同父项目、不假设所有工具都允许多重成员

#### Scenario: 分析者选择项目集合
- **WHEN** 用户把两个无原生协作声明的项目纳入一次分析
- **THEN** 使用AnalysisScope或显式CoordinationGroup表达选择，不把集合宣称为原生workspace或治理自治证明

### Requirement: 目标配方别名与交付边界

系统SHALL区分原生BuildTarget、BuildRecipe、PackageSpecification、TargetAlias、ExecutionTask、OutputSpecification、EntrypointBinding与ArtifactObservation。原生目标SHALL保留明确项目归属，别名解引用到原目标；非原生派生目标MUST标识派生依据。输出声明、接口能力或入口映射SHALL NOT自动成为产物观测。

#### Scenario: 接口目标与目标别名
- **WHEN** CMake声明INTERFACE目标及指向它的ALIAS
- **THEN** 保留接口使用要求和别名身份，但只有一个目标实现且不捏造二进制产物

#### Scenario: Python项目没有显式原生目标
- **WHEN** 来源只有打包配方、发行声明与脚本入口
- **THEN** 保留对应配方、发行规格和入口绑定，不伪造原生BuildTarget；未执行安装时不声称入口已安装

#### Scenario: 聚合测试命令
- **WHEN** workspace命令仅选择成员目标执行测试
- **THEN** 将选择器或任务编排与独立目标定义区分，不仅凭命令名称建立workspace所有的目标

### Requirement: 需求解析与范围位置正交

系统SHALL把消费方到提供方的依赖需求与解析结果分开，保留用途、阶段、条件、版本及路径约束。解析MUST包含解释配置、可见范围、证据和resolved/unresolved/ambiguous状态；相对查询范围的inside/outside/unknown位置SHALL独立表达且不改变需求身份。调用、成员、测试先后与构建依赖SHALL NOT互相推导。

#### Scenario: 范围外已解析提供方
- **WHEN** 已解析依赖的查询范围从仅消费项目改成包含提供项目
- **THEN** 同一需求及提供方身份保持不变，位置由outside变为inside，解析状态仍为resolved

#### Scenario: 多配置与未证本地解析
- **WHEN** 同一需求在两种配置下解析到不同提供方，或仅有`click>=8.1`而无本地绑定证据
- **THEN** 前者保留两项带条件结果，后者保留需求与解析缺口，不自动指向当前检出项目

#### Scenario: 路径版本与条件循环
- **WHEN** 依赖同时声明本地路径和版本约束，或声明图存在环
- **THEN** 同时保留两种约束及原图；只在相应粒度下条件可同时满足时报告可发生的环，并依据明确工程规则判断违规，不删边或把项目汇总环当目标构建环

### Requirement: 稳定身份与上下文保持引用

系统SHALL按主体种类、归属域和明确身份要素识别主体，名称、路径、行号、内容摘要或提交号SHALL NOT单独充当身份。上下文影响指称时引用MUST携带解释上下文；仅影响事实取值时SHALL保留条件化事实。匿名、重载、包装及重复展开主体MUST可区分；连续性未决时MUST报告歧义。

#### Scenario: 同名目标与来源变更
- **WHEN** 两独立项目拥有同名目标，或同一项目取得新提交证据
- **THEN** 前者保持隔离；后者不因提交变化自动成为新项目，来源版本与主体身份分离

#### Scenario: 相同声明在不同目标下类型不同
- **WHEN** 同一源码声明D在T1下为i32、T2下为i64且引用C需要其类型
- **THEN** C的引用保留对应解释上下文并唯一确定所用类型，不把两个无条件类型堆在D上供任意选择

### Requirement: 类型化事实与条件语法

系统SHALL交换带factId、predicateId、角色参数、applicability、claimMode、evidenceRefs及可选derivation的事实。参数MUST遵守目录类型；条件SHALL支持True、False、Unknown、类型化比较、All、Any、Not及携带解释缺口的SourceCondition。类型值SHALL区分标量、枚举、主体引用、序列、定义过的记录与表达式；任意字典SHALL NOT绕过类型约束。

#### Scenario: 语法正确但角色错误
- **WHEN** JSON可解析但build.alias_of的target参数指向算法，或角色、引用、基数、作用域非法
- **THEN** 公共校验报告对应事实、角色和违反规则，不将JSON可解析等同语义有效

#### Scenario: 不支持的条件表达式
- **WHEN** 来源条件暂时不能规范化
- **THEN** 保留来源条件引用与明确解释缺口，不默认True、False或成功解析

### Requirement: 可查询的类型与谓词目录

系统SHALL公开主体类型、值类型、上下文键及谓词目录。每个谓词MUST定义限定名称、含义、角色类型、基数与约束；Semantic谓词MUST恰有一个E0–E4主层，Provenance谓词MUST作为横贯元数据且不设置主层。contains、member、declares、alias、binds、implements等SHALL分别定义，不以无类型requires替代不同关系。

#### Scenario: 首批跨层谓词
- **WHEN** 使用engineering.workspace_member、build.entry_binds、program.has_signature、contract.effect、behavior.calls及provenance.generated_from
- **THEN** 前五项分别由目录归入E0、E1、E2、E3、E4，最后一项无主层；跨层参数仍接受有类型引用且不复制事实

#### Scenario: 目录扩展
- **WHEN** 新谓词未定义参数类型、主层或字段约束，或一项事实自行指定与目录不同的主层
- **THEN** 校验拒绝其作为符合公共契约的语义事实并报告缺失或冲突

### Requirement: 主张模态证据与推导可追溯

系统SHALL区分declaration、specification、static_may、static_must、observation、interpretation模态，并把获取方法与模态分开。证据MUST记录来源、版本/内容标识、定位、方法及Supports/Refutes/Limits角色；推导MUST关联规则与前提。支持、反驳、置信度或工具名称SHALL NOT自动裁真或消除冲突。

#### Scenario: 声明与运行观测不同
- **WHEN** 清单声明输出文件但未执行构建，或规范要求无副作用而静态分析发现可能写入
- **THEN** 前者只有声明而无ArtifactObservation；后者保留双方模态、条件及证据，不把静态可能冒充运行事实或自动覆盖规范

#### Scenario: 证据失效或推导缺前提
- **WHEN** 当前输入内容不再匹配记录的证据标识，或推导引用不存在的前提
- **THEN** 报告失效来源或缺失前提及受影响事实，不将其标为已核实；不要求因此实现历史查询服务

### Requirement: 覆盖与否定的边界

系统SHALL按scope、主体种类、谓词族、上下文、已检查/排除输入、获取状态及缺口报告覆盖。已确认不存在、未获取、不支持、不适用和冲突MUST可区分。只有来源和覆盖足以支持否定时SHALL报告不存在；五层均有事实或字段为空SHALL NOT成为完整性证明。

#### Scenario: 选样不能证明全项目完整
- **WHEN** 只检查固定提交的20份Rust/C++/Python文件且未运行构建、宏展开或完整解析
- **THEN** 覆盖报告限定选样，列出未检查输入和宏/注解/多workspace/循环等缺口，不声称全仓库或所有语言完备

#### Scenario: 没有提取到调用事实
- **WHEN** 调用获取器不支持某动态解析或输入未读取
- **THEN** 结果分别标记不支持或未获取，不把空调用集合解释为不存在调用
