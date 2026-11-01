# Tasks

这是唯一权威任务清单，Superpowers writing-plans/executing-plans共用本文件，不另设执行计划。规格见`openspec/specs/semantic-fact-model/spec.md`与`openspec/specs/semantic-fact-query/spec.md`，确认映射见ADR-0002，方案见design.md，未决问题见discussion.md。

全局约束：本轮仅执行0组文档任务；不进行产品实现，不自动归档，不因未实施重开确认需求。1–5组保留既有候选计划，全部未完成，相关设计未批准且超出本次授权，禁止顺序继续apply。执行0组前已取得实际apply指令；CLI ready只说明工件齐备，不是产品实施授权。

## 0. 已确认规格固化（本次授权）

- [x] 0.1 核对确认记录并隔离候选。上游依据：用户本轮条目1–2、ADR-0001及历史上下文用户约束。交付：`docs/decisions/0002-confirmed-specification-baseline.md`及`docs/development/discussions/2026-11-01-specification-baseline/`。验证：逐项核对B01–B06来源、证据等级及候选/代理分类。通过：每项确认有定位且Battle未当批准；失败：候选无依据升格或伪造原话。

- [x] 0.2 整理确认delta并选择性同步主规格。依赖：0.1。上游依据：用户条目3、B01–B06及实际specs instructions。交付：本变更`specs/semantic-fact-model/spec.md`、`specs/semantic-fact-query/spec.md`和对应`openspec/specs/`主规格。验证：逐Requirement比较delta与主规格，运行`npm run openspec -- validate --specs --strict --no-interactive`。通过：主规格3项模型+4项查询要求均有Scenario和确认映射，algorithm-description未同步；失败：混入候选或主规格含delta操作头。

- [x] 0.3 协调规划与验证记录。依赖：0.2。上游依据：用户条目4–6，B01–B06与两份主规格全部Requirement。交付：proposal.md、design.md、tasks.md、README/会话索引及`docs/development/reviews/2026-11-01/specification-baseline-verification.md`。验证：`npm run validate`、`npm run check:artifacts`、`git diff --check`，比较原10项产品任务均未完成，检查无产品代码/导入原件变动。通过：工件一致且实际校验有证据，文档任务与产品任务状态明确；失败：虚报验证、两套冲突计划、越界实施或归档。

## 后续产品候选计划的适用条件

以下原10项是待设计确认后重审的候选任务，不是已批准的可执行实施计划。上游细节来自discussion目录的`semantic-fact-model-candidates.md`、候选algorithm-description delta及design.md拟议选择；均受两份主规格的确认约束。开始任何一项前，先完成对应讨论问题、用户确认、规格增量和任务更新，再获取新的apply instructions。本轮没有制定查询Skill实现计划。

公共测试命令`python3 -m unittest discover -s tests/semantic-model -p 'test_*.py'`仍是未来目标，测试文件尚不存在，未执行。自维护脚本使用Python3，不据此指定产品语言。

## 1. 类型身份与公共目录

- [ ] 1.1 建立类型、身份与上下文目录并验证隔离和连续性。依据：`docs/development/discussions/2026-11-01-specification-baseline/semantic-fact-model-candidates.md`“五层组织与单一主体身份”“稳定身份与上下文保持引用”；`design.md`决策1–2；ADR-0001。交付：`contracts/semantic-model/types.json`、`contracts/semantic-model/rules.md`身份/上下文章节、`tests/semantic-model/fixtures/identity.json`、`tests/semantic-model/test_contracts.py`及`docs/domain/semantic-model-contract.md`身份说明。验证：公共测试命令中包含`test_project_identity_isolated`、`test_revision_is_evidence_not_identity`、`test_context_preserving_reference`、`test_ambiguous_rename`、`test_anonymous_and_overload_identity`。通过：同名跨项目隔离、来源换提交不自动换项目、T1/T2异型引用唯一、连续性缺证报歧义；失败：身份仅靠路径/名称/提交或引用丢失上下文。

- [ ] 1.2 建立首批谓词目录及层查询规则并验证类型边界。依据：候选事实模型“可查询的类型与谓词目录”“五层组织与单一主体身份”；`design.md`决策5的全部条目。交付：`contracts/semantic-model/predicates.json`、`tests/semantic-model/fixtures/predicates.json`，扩展`test_contracts.py`和公共文档的目录章节。验证：运行公共测试命令，检查每个限定名均有含义/角色/类型/基数/约束，所有Semantic恰有一个E0–E4主层，Provenance无主层，未注册谓词、错误主层、错误角色和任意Record扩展被拒绝。通过：同一操作跨E2/E3/E4只登记一次，跨层事实不复制，无默认refines；失败：省略任何首批条目、无类型requires或成员/包含/实现混用。

## 2. 事实语法与工程关系

- [ ] 2.1 实现事实载荷Schema与结构/引用/条件校验契约。依赖：1.1–1.2。依据：候选事实模型“类型化事实与条件语法”；`design.md`决策4。交付：`contracts/semantic-model/fact.schema.json`，`rules.md`的校验与三值条件章节，`tests/semantic-model/fixtures/facts-valid.json`、`facts-invalid.json`、`conditions.json`，对应`test_contracts.py`断言及文档示例。验证：公共测试命令覆盖Fact必填项、全部TypedValue/Condition分支、角色类型/基数、断引用、无效上下文和未知来源条件；覆盖空All/Any及Unknown传播。通过：合法载荷通过，非法载荷定位记录/字段/规则，未知条件保持缺口；失败：JSON可解析便通过语义校验，或Unknown默认为False/True。

- [ ] 2.2 落地工程组织、构建与交付反例集。依赖：2.1。依据：候选事实模型“显式工程边界与组织关系”“目标配方别名与交付边界”；候选定义A01–A10、R1/C1/C4/P2。交付：`tests/semantic-model/fixtures/engineering.json`、`build-delivery.json`及`test_contracts.py`工程断言，`rules.md`工程不变量和公共文档工程说明。验证：公共测试命令覆盖根包兼workspace、无workspace项目、多独立项目/多workspace规则、包到项目映射、同workspace无依赖、CMake INTERFACE/ALIAS、嵌入独立工程、测试选择器、Python无原生目标、声明输出未构建及未安装入口。通过：组织/所有权/任务/目标/入口/产物分别表达且无虚构对象；失败：目录嵌套推出成员、成员推出依赖、ALIAS复制实现或声明推出观测。多workspacefixture标明synthetic，不能标为真实抽取结果。

- [ ] 2.3 落地依赖、范围、多配置与条件循环校验。依赖：2.1–2.2。依据：候选事实模型“需求解析与范围位置正交”；首次Battle C08与候选定义A08/A14–A16。交付：`tests/semantic-model/fixtures/dependencies.json`，`test_contracts.py`依赖断言，`rules.md`需求/解析/范围章节及公共文档例子。验证：公共测试命令覆盖resolved+outside切换inside、同需求多配置解析、path+version同时保留、仅`click>=8.1`未证本地解析、局部解析可见范围及歧义、可满足/互斥/未知条件循环、项目汇总环与目标环差异。通过：身份不随查询范围变化，结果按配置保留，未知不当不存在，循环不删边；失败：outside降级unresolved、无依据绑定本地项目或循环判定忽略条件/粒度。真实循环缺证须保留synthetic标识。

## 3. 模态来源与覆盖

- [ ] 3.1 建立证据、推导及覆盖契约并验证未知与否定边界。依赖：2.1–2.3。依据：候选事实模型“主张模态证据与推导可追溯”“覆盖与否定的边界”；候选定义§§10、13–14、17。交付：补齐`fact.schema.json`的Evidence/Coverage定义，`rules.md`来源及模态规则，`tests/semantic-model/fixtures/evidence-coverage.json`，`test_contracts.py`对应断言和公共文档覆盖报告示例。验证：公共测试命令覆盖六种claimMode、方法独立、Supports/Refutes/Limits、推导规则与缺前提、内容标识不匹配/不可取得、冲突并存、五种空缺状态及20文件选样范围。通过：声明不变观测、来源失效影响明确、未获取/不支持/不适用/否定/冲突可区分，static_must有充分前提；失败：靠工具名/置信度裁真、空字段当不存在、五层有事实即报全覆盖，或把历史源码阅读当构建/测试已运行。

## 4. 契约算法与语言机制

- [ ] 4.1 实现契约和结构化算法公共定义与引用校验。依赖：1.1–3.1。依据：`specs/algorithm-description/spec.md`前四项Requirement；`design.md`决策6。交付：`contracts/semantic-model/algorithm.schema.json`，`rules.md`契约/算法章节，`tests/semantic-model/fixtures/algorithms.json`，`tests/semantic-model/test_algorithms.py`及公共文档算法章节。验证：公共测试命令覆盖所有行为构造、重复stepId、悬空控制/数据边、循环出口目标、UNKNOWN调用、错误返回/异常差异、求值/数值规则缺口、资源效果及并发偏序；覆盖parse(&self)状态效果、SAX回调结果、单算法跨项目实现及归属未决。通过：类型与引用有效、目的/观察边界/省略项齐全、机制未知不被默认成功补全；失败：implemented_by当等价证明、算法强制单项目或缺少资源/并发语义便静默串行化。

- [ ] 4.2 实现语言机制映射反例并验证来源与身份。依赖：4.1。依据：算法规格“宏生成与注解的分阶段来源”“匿名操作闭包与绑定语义”；候选定义§11、A10/A15。交付：`tests/semantic-model/fixtures/language-mechanisms.json`，扩展`test_algorithms.py`、`rules.md`映射规则及公共文档语言支持/缺口矩阵。验证：公共测试命令覆盖未展开宏、重复展开多绑定、cfg条件、未支持注解处理、Click返回Command/callback、lambda捕获方式未知、let/if let模式/作用域/路径和绑定≠赋值。通过：原函数/包装/运行对象/生成绑定可区分且多对多来源可追溯，缺证标UNKNOWN；失败：伪造展开AST、把装饰器当静态注解、匿名主体合并、捕获方式猜测。真实宏展开/Java注解尚无证据，fixture必须明确synthetic，公共文档不得声称获取器已支持。

- [ ] 4.3 实现单源伪代码投影定义并核对三语言局部算法。依赖：4.1–4.2。依据：算法规格“伪代码是可追溯投影”；候选定义§12的R5:205–251、C5:161–222/565–572、P7:51–108。交付：`rules.md`投影规则，`tests/semantic-model/fixtures/pseudocode/`的三项结构化body/预期投影/步骤映射，扩展`test_algorithms.py`及公共文档投影示例。验证：公共测试命令检查Rust两层循环/回调传播/未展开子过程、C++ strict/EOF/parse_error真实结果、Python零规格/双端消费/通配余项/尾段逆序/第二通配TypeError；每段映射有效Step且省略/UNKNOWN显示。通过：投影由body规则生成且保留行为差异；失败：维护独立文本造成漂移、静默省略外部效果、局部摘要宣称完整等价或读测试断言宣称运行通过。

## 5. 集成证据

- [ ] 5.1 执行跨能力集成验收并发布准确边界说明。依赖：1.1–4.3。依据：两份正式主规格的约束及届时批准的模型/算法候选需求；`openspec/config.yaml`与AGENTS验证规则。交付：`docs/development/reviews/semantic-model-contract-verification.md`（实际命令、输出摘要、来源/合成标记、覆盖矩阵和剩余缺口），完善`docs/domain/semantic-model-contract.md`链接与使用说明；仅在逐项证据通过后更新本清单。验证：运行公共测试命令、`OPENSPEC_TELEMETRY=0 node_modules/.bin/openspec validate define-layered-semantic-fact-model --strict`及仓库适用检查；逐项映射届时已批准的模型/算法Requirement与fixture/test，核对所有计划路径真实存在且无获取器实现冒充；查询响应实现另行规划，本任务不声称覆盖完整查询Skill。通过：结构/跨事实/算法/投影验收通过、每项需求有可定位证据、缺口如实列出；失败：只凭status/artifact存在标完成、任何断言失败、无证完整性或省略真实证据限制。

## Workflow follow-up

- 本轮完成确认基线的选择性同步；公共契约、算法描述、查询Skill及1–5组实施仍未完成。后续不得把0组勾选或CLI planning complete当作产品完成。
- 未获明确请求不archive；外部真实案例补证不能抹去synthetic/未获取记录。
