# c2s语义事实查询Skill

当前默认使用`semantic-entity-model-2`及统一请求/结果协议。可按需查询Python/Rust项目的来源目录、嵌套清单、源码模块、声明、语义实体候选、属性与关系、实现引用、测试关联、算法及伪代码。JSON和Markdown来自同一规范结果；`sourceRecords`保存来源组织，`items`保存请求目标，主张、证据、覆盖、缺口和持久化状态分别返回。

按目标和描述面补缺，重复查询复用同一输入/分析配置下的覆盖；解析器、工具矩阵或产品源码改变后缓存失效。源码组织不依赖实体映射；实体解释保持有证据的暂定主张。数据属性不被递归深度省略，枚举值域仅在同文件词法作用域内有唯一类型引用时采用，未知绑定不按裸名称跨模块猜测。算法/伪代码仍为部分静态投影，不证明运行时行为或等价性；宏展开、动态调用、完整类型绑定等未解析项保留缺口。

目录盘点涵盖隐藏、忽略、测试及示例路径，实际语法前端覆盖`.py`与`.rs`。基础组合为Python AST、Rust Tree-sitter及TOML/Cargo，图后端只在显式请求与能力验证后使用；CodeGraph保持候选。未执行关系取得时不会将声明解析冒充relations完整覆盖。完整性只针对本次请求与已支持类别，不声称穷尽项目所有语义。

旧`semantic-entity-model-1`、`semantic-fact-model-1`及M1继续提供显式兼容接口。旧源码查询协议中的fact/subject ID、subject_id、claim_mode、顶层条目和原文投影规则只适用于v1；默认v2使用独立来源记录与实体身份。默认写入、备份及回滚见文末。

## 历史M1与旧完整档案兼容契约

仓库根目录的 `contracts/semantic-model/` 与 `src/c2s_semantic_contract/` 保留版本 `1.0.0` 的M1身份/事实契约及旧扩展profile `semantic-fact-model-1`。M1仍为独立的项目/workspace发现入口；旧扩展profile只可读取、校验和导出兼容数据，不再接受产品默认写入。扩展profile另有封闭谓词/类型目录，覆盖当前获取器事实类别，并为工程边界、构建目标/recipe/alias/output、E2签名/访问、E3契约及E4调用/绑定/捕获/控制数据流提供类型化表达；其中不少关系目前只有模型/校验规则，尚无源码获取器。安装使用 `python3 -m pip install -r requirements-semantic-model.txt`；语义模型验证使用 `PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s tests/semantic_model -v`。`project_query_to_semantic_model`将查询返回的每一项已支持事实映射为扩展profile，并保留源种类、层、owner、原文与展示状态；`project_algorithm_to_semantic_model`另将Python/Rust算法文档映射成实现/body/region/step/control-edge/data-edge事实，核对lowering记录的源文件摘要并为不透明步骤保留gap；算法局部实现身份不与独立查询中的声明身份自动合并。固定版本Click与regex实测回归遍历所有已获取查询事实并检查映射和显式缺口。该映射不扩大获取能力，不推断类型/调用绑定或项目归属；Cargo缺失仍作为workspace获取缺口保留。M1项目发现接口和既有M1契约保持独立兼容。

条件求解器位于`src/c2s_semantic_contract/conditions.py`：支持有限Boolean/Enum域上的`true/false/eq/neq/all/any/not`；`evaluate_condition`在部分赋值下按true/false/unknown三值求值，`condition_satisfiability`最多穷举4096种赋值，超过限额、域未知或表达式不支持时返回`undetermined`。`semantic-fact-model-1`现已集成Context/Condition、引用上下文、依赖需求/解析记录和单值声明重叠检查；`validate_model`还会按配置报告显式依赖图的条件环分析，并保留原图；`m1-project-discovery-1`拒绝这些扩展记录。依赖记录当前为显式输入，不会从项目自动推断。求解范围限于显式有限域及已注册M1谓词，不能据此声称项目完整语义分析完成。

完整语义profile也提供六种互不排序的claimMode、带Supports/Refutes/Limits角色的evidenceRefs，以及带前提引用的derivation；缺失前提或推导循环会报错。这些模态/推导目前由调用方提供，分析器不会自动推断运行观测，也不能由此宣称真值已证明。

完整profile的negative claim必须引用受限输入闭合集、逐项无匹配、条件相同、人工审定且无未解决缺口；校验器只能核对闭合记录结构，不能证明调用方提供的输入集合客观穷尽。

`semanticStates`分别记录`ref_only/expanded`展示状态和`obtained/not_acquired/unsupported/not_applicable`获取状态，并与事实主张分离；缺口和不适用状态须附理由/证据。由此可以表达“已获取但未展开”，不会把空结果自动解释为不存在。

```bash
python3 scripts/query_m1.py --root .local/real-projects/click --select project
python3 scripts/query_m1.py --root .local/real-projects/regex --select workspace-members
```

## 当前实现与测试

实现位于`src/c2s_skill/`，测试位于`tests/`。在仓库根目录运行：

```bash
PYTHONPATH=skill/src .local/analysis-venv/bin/python -m c2s_skill query \
  --root .local/real-projects/click --select all-supported-facts --format json
PYTHONPATH=skill/src .local/analysis-venv/bin/python -m c2s_skill algorithm \
  --root .local/real-projects/click --all-functions
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m c2s_skill algorithm \
  --root .local/real-projects/click --source src/click/core.py --function Command.parse_args \
  --semantic-facts --graph-output /tmp/click-callees.json --graph-version 2.3.9
PYTHONPATH=skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -v
```

`--graph-output`读取已由 Code Review Graph `query_graph("callees_of", target, detail_level="standard", max_results=...)`生成并存放在项目目录之外的JSON对象；其target必须与请求算法的限定名称相同。图输出应保留`result_count`、`results_omitted`、每行`call_site`和完整`results`。若当前项目没有相符的外置图索引，先按Code Review Graph文档在隔离的数据目录建立索引，再查询；不可将默认Git跟踪文件范围冒充Skill全目录。解析器会拒绝不安全路径、保留遗漏和不匹配诊断。当前响应不能证明索引对应最新源码摘要，所以即使查询零遗漏也会报告freshness gap并以部分状态返回。JSON只支持结构化工具响应，不接受Skill自由文本摘要作为关系事实。

支持的查询：`project`、`workspace-members`、`classes`、`members:类型名`、`functions`、`function:名称`、`local-bindings`、`definitions`、`imports`、`constants`、`behavior-contracts`、`algorithm-structure`、`all-declarations`、`all-supported-facts`。自然语言暂支持“有哪些类”“Command 的成员有哪些”“函数 run”等明确形式；不能识别的请求会作为gap返回。`function:名称`返回所选函数声明、源码文档、算法步骤、局部绑定和来源可追溯的伪代码视图；伪代码标记为不完整静态投影，保留步骤证据引用及算法缺口。不支持的步骤会标注为未解析，不构成行为等价证明。嵌套函数是独立主体，需单独查询，避免把内层函数的执行步骤误归到外层函数。`local-bindings`目前返回函数内简单名称的赋值目标（Python支持简单/解构赋值、循环目标、with别名及异常别名；Rust支持元组、结构体、元组结构体、切片、or、引用及`@`捕获`let`模式中的标识符）；事实以源码片段为证据，不表示调用解析、类型确认或完整数据流。`workspace-members`通过Cargo metadata解析，不需要依赖下载；Cargo不可用或元数据失败会明确报告gap。对Cargo项目使用`query --store --select workspace-members`或`all-supported-facts`时，成员包名和manifest路径还会作为Project实体的E1观察主张及覆盖写入实体档案；包本身不会被升级为语义模块。查询工具从`skill/contracts/tool-capabilities.json`选择满足请求的已点亮工具组合，点亮项必须在矩阵中有解析器、测试、证据文件，并在当前环境通过运行时检查；未覆盖能力会作为gap报告。未知selector以退出码2返回；`algorithm --all-functions`对部分静态分析返回退出码2，即使所有函数均已遍历成功；结构错误或读取失败使用退出码64。JSON和Markdown包含相同事实ID，并标明源码片段是否因本次请求省略。`--cache /path/outside/project/query-cache.sqlite`只缓存查询投影；`--store /path/outside/project/semantic-facts.sqlite`用于写入`semantic-entity-model-1`实体档案：普通`query --store`构造并回读项目实体；`algorithm --semantic-facts --store`还将本次算法投影关联到对应计算实体的实现映射，保留算法步骤、控制/数据边、语义事实证据及外部图工具原始响应（若有）。算法响应中的`semantic_fact_bundle`仍是本次请求的内存兼容投影，不另行写入旧profile。旧`semantic-fact-model-1`完整档案可读但写入明确拒绝，M1入口保持独立。遍历包含测试、示例、隐藏及忽略文件中的`.py`/`.rs`源；`.git`对象库和非源文件不作为程序语法解析，并在结果覆盖中列为未处理路径。

已对固定真实项目做全源遍历：regex commit `94ac45b2a6e7b1c30927feb5b66c5ded5b7ad447`：227/227 Rust文件解析，54,315条当前支持事实（含7条Cargo工作区成员）；click commit `2247b35ea1c47c727d7a06e51fa280e12a863ff6`：91/91 Python文件解析，23,779条当前支持事实。函数声明归E2，函数体算法步骤和已支持的局部绑定归E4；当前还覆盖部分控制结构、运算、调用及返回/异常语法。Python装饰器不会计入函数体算法步骤。另已批量按需查询所有函数：regex 4,342个函数声明、3,395种查询目标；click 1,897个声明、1,797种目标，返回事实均与全量扫描中的主体事实一致。两项目事实ID均无重复，并列出224/155个非源或未处理路径。全量selector返回所有当前支持事实。完整仓库测试也将Click的23,779项和regex的54,313项投影写入SQLite，再按`all-supported-facts`读回并逐项比较`factId`。这些仍不是完整语义真值。逐文件、逐事实ID清单见`../docs/development/reviews/semantic-facts/2026-11-06-exhaustive-inventory.json`；验证记录见`../docs/development/reviews/semantic-facts/2026-11-06-verification.md`；两个函数的具体示例见`../docs/development/reviews/semantic-facts/2026-11-06-two-function-facts.md`。使用`PYTHONPATH=skill/src .local/analysis-venv/bin/python scripts/generate_semantic_fact_inventory.py`可重建清单和函数示例。

## 开发依赖与来源

| 工具/能力 | 实际版本 | 用途及当前边界 |
| --- | --- | --- |
| Python | 3.12.14 | Linux实现与AST；其他Python版本未测试 |
| tree-sitter / Python grammar / Rust grammar | 0.26.0 / 0.25.0 / 0.24.2 | Rust结构解析依赖；Python使用标准库AST |
| jsonschema | 4.26.0 | 校验JSON Schema 2020-12查询输出契约 |
| Code Review Graph | 2.3.9（可选） | 已在固定Click/regex项目建图/查询；仅为按需跨文件调用/引用补充，不作为项目全量清单；外置索引、无模型嵌入。当前会话本地venv未安装，重建开发环境命令会安装 |
| Rust工具链 | rustc 1.99.1，Cargo 1.99.1 | 已安装至`.local`；Cargo workspace metadata可离线取得，Rust依赖测试仍未通过下载阶段 |
| GitHub CLI | 2.103.3 | 备用账户配置工具，官方归档摘要核验；仅CI开发准备，需独立GitHub授权 |
| OpenSpec / Codex / Superpowers | 1.16.0 / 0.166.0 / 7.0.1 | 开发流程工具，不当产品运行依赖；Superpowers在当前环境可读 |

Python包来自包索引；Rust安装来源为官方https://rust-lang.org/tools/install/，使用项目本地RUSTUP_HOME/CARGO_HOME且不改shell profile。当前安装路径`.local/analysis-venv`、`.local/rustup`、`.local/cargo`均为开发临时目录，不随Skill发行。

Code Review Graph `build-graph`/`explore-codebase` Skills只作为工具导航资料，不是本会话已注册的可调用Skill，也不把其短文本结果当语义事实；确定性API结果由专用解析器消费。ast-grep、Semgrep、Serena、GitNexus和CodeQL CLI不作为必需运行依赖；CodeGraph 1.6.2（Apache-2.0、npm开源项目）已临时安装并验证files/query/callers/callees输出解析，但覆盖收益尚未达到点亮条件，保持candidate；按覆盖矩阵暂不进入必需组合。具体比较见`../docs/development/reviews/issues/10/acquisition-survey-2026-11-02/tool-selection.md`。

## 重建当前开发环境

```bash
uv venv .local/analysis-venv
uv pip install --python .local/analysis-venv/bin/python tree-sitter==0.26.0 tree-sitter-python==0.25.0 tree-sitter-rust==0.24.2 jsonschema==4.26.0 code-review-graph==2.3.9
```

依赖安装在被忽略的`.local/analysis-venv`，不随Skill发行。Python查询运行需Python 3.12+及`tree-sitter`、`tree-sitter-rust`固定版本。Windows/macOS及其他Python/Rust版本尚未验证。

运行上面的真实项目测试命令可验证安装和遍历。

本轮Rust安装在项目本地，Linux自检必须显式指定两处home（不能直接调用默认home的rustup代理）：

```bash
RUSTUP_HOME="$PWD/.local/rustup" CARGO_HOME="$PWD/.local/cargo" .local/cargo/bin/cargo --version
RUSTUP_HOME="$PWD/.local/rustup" CARGO_HOME="$PWD/.local/cargo" .local/cargo/bin/rustc --version
```

## 索引、写入与联网

CRG建图使用`--data-dir`外置图数据库及`--skip-postprocess`，未启用嵌入、watch或自动配置安装；工具仍可能维护宿主的图目录注册信息，不能把这些命令称为完全无副作用。源项目跟踪文件与固定提交blob核对无变化。索引是语法/关系候选，不是完整领域事实。

安装及克隆需要联网；本轮解析/图查询没有调用LLM，不据此宣称未来端到端零Token。最终模型参与的凭据只通过环境/宿主安全配置提供，不写入Skill、日志或仓库。必要依赖不可用或工具无法覆盖时必须报告原因，不伪造结果。

## 尚未完成的能力与验证限制

真实五角色权限隔离未就绪，私有独立验收未运行。依据ADR-0011，这不阻止开发，但本原型不能宣称通过盲编写或私有验收。E3行为契约验证、E4算法语义、Python workspace/打包边界、类型/调用解析、逐项懒构造和崩溃后事务恢复仍未完成；产品版本未发布。Click上游测试套件已运行。Rust workspace元数据及7成员M1投影已在真实regex项目验证；稳定工具链下`cargo test --workspace --offline`通过1,405项、忽略6项。`--all-targets`因regex-syntax基准使用nightly-only `#![feature(test)]`而失败，未把基准算作通过。

CI账户配置与公开容器探针的命令、最小权限、安装来源及安全输入方法见`../docs/workflow/ci-setup.md`；gh不是产品运行依赖。Docker仅供GitHub托管Ubuntu探针使用，本地未安装或验证。

私有验收准备增加credential-check模板：使用托管Ubuntu预装Python 3标准库，一次GET /v1/models校验Secret可见和API认证，不执行生成请求、不证明推理或完整角色隔离。无需新增产品依赖；部署/状态见交付change tasks 3.2.1。

托管角色边界检查使用Docker与python:3.12-slim镜像；每次先解析并记录实际RepoDigest，按摘要执行，非root、禁网、只读根及限定挂载。源/私有runner合成诊断已通过；本地没有Docker能力，未验证其他host。该封装不是完整模型编排器，不能把当前原生代理全权工具当作正式编码工具入口。

开发健康检查另有一次公开输入的gpt-5-mini Responses请求（最大256输出Token、store=false、不重试）；它不是产品语义后端选择。当前实际返回credit_balance_exhausted，推理未通过，usage未知。开发按任务选模型、按需选专用Skill及实际使用回报见../docs/workflow/agent-governance.md和本轮skill-usage.md。

工作授权与访问现状见`../docs/decisions/0011-development-without-isolation-gate.md`及`../docs/workflow/blind-development.md`。公开维护测试不消耗模型Token；实际语义理解/模型调用流程尚未实现。

## 语义实体模型与查询（开发中的隔离档案）

领域模型档案使用`semantic-entity-model-1`，独立保存在与旧M1/`semantic-fact-model-1`隔离的SQLite表中。项目、模块、能力、数据实体、计算实体和测试实体均由证据提出暂定候选；仅当文档明确列出模块/能力时才生成相应候选，不从目录、Cargo package或函数名推断业务边界。源码类/结构体字段可生成数据实体属性，成员函数生成计算候选；裸实现类型不会被当作语义类型，值域默认未知，枚举成员只有在可定位的类型引用证据下才提供有限值域。

档案保存身份、属性、关系、主张状态、来源证据、`SourceConstruct`及`sourceMappings`。源码映射保留语言、语法种类、父构造、解析器版本、相对路径、SHA-256和UTF-8字节区间；映射未解决时不丢弃构造，而是保留定位与缺口。宏、泛型、闭包、枚举等记录为语言实现参考，不会因此自动变成领域实体。测试实体与测试函数入口分开，只有唯一解析到本地计算实体的调用才会形成暂定验证关系。

查询使用项目范围和结构化选择器。`project`返回项目实体的直接子实体引用和摘要；`entity:<localId>`返回单体全部属性、主张、关系、证据、来源映射及覆盖状态；`expand:<localId>`显式逐层展开并受最大深度限制。中文名称可解析，未知目标和歧义目标分别返回缺口状态。Markdown和JSON从同一查询结果投影。重复输入与相同解析配置复用覆盖；源码、解析器或工具矩阵指纹变化后旧覆盖标为需复核。本段描述显式v1兼容入口的全项目扫描行为；默认v2按下文的目标与描述面补缺。

显式`--model-profile semantic-entity-model-1`时，命令行中的`entities`与`query --store`保持既有v1实体档案兼容行为；`query`原有的classes/functions等选择器仍返回源码事实视图，同时构造并存储同一项目范围的实体档案。`algorithm --semantic-facts --store`也写实体档案；其`semantic_fact_bundle`字段仅为向现有调用方提供的内存兼容投影，不会写入旧档案。旧完整profile的`commit_bundle`写入接口已拒绝新写入，`read_bundle`/`query_bundle`仍可读取旧档案。示例：

```bash
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python3 -m c2s_skill entities --root /path/to/project --select entities --store /tmp/project-entities.sqlite --format json
```

`--select project`查询已能由证据构造的项目实体；项目元信息不足时会返回`not_found`及缺口，`--select entities`可列出档案中已有的全部候选。`--select entity:<localId>`查询单个实体，`--select expand:<localId>`展开子实体。实体查询会检查源码与分析器指纹，覆盖未命中时扫描并写入实体档案；相同项目根路径的`entities`与`query --store`可共用同一SQLite文件和实体档案。数据库仍须位于项目根目录之外。旧完整档案以独立表保留并只读，不会与实体档案混写。

一个直接调用示例：

```python
from pathlib import Path
from c2s_skill.entity_construction import construct_and_query_semantic_entities
from c2s_skill.semantic_store import SemanticEntityStore

store = SemanticEntityStore(Path("/tmp/c2s-entities.sqlite"))
result = construct_and_query_semantic_entities(Path("/path/to/project"), store, "project")
```

SQLite档案会写入磁盘，必须放在被分析项目目录之外；调用者需为分析输入建立稳定的`scopeId`身份域，仓储会由项目绝对根路径生成默认域。用户可复核的全量遍历产物位于`../docs/development/reviews/semantic-facts/`；清单固定上游提交并列出未映射源码和测试目标缺口。清单为控制体积省略内嵌源码文本，须用记录的提交、相对路径、SHA-256和字节区间复核原文。

运行仓库全套Skill测试的命令为：

```bash
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python3 -m unittest discover -s skill/tests -v
```

运行真实Click与regex全量实体遍历：

```bash
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python3 scripts/verify_semantic_entity_inventory.py .local/real-projects/click .local/entity-analysis/click.sqlite docs/development/reviews/semantic-facts/entity-model-click-inventory.json
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python3 scripts/verify_semantic_entity_inventory.py .local/real-projects/regex .local/entity-analysis/regex.sqlite docs/development/reviews/semantic-facts/entity-model-regex-inventory.json
```

这两项目的共享容器验证不是私有盲验收。regex项目的Cargo metadata已用仓库本地工具链离线执行：7个workspace packages完整返回（根包regex及6个workspace members），`workspace-members`查询无gap；执行时必须将`RUSTUP_HOME=.local/rustup`与`CARGO_HOME=.local/cargo`指向本地安装目录，否则Cargo shim找不到已安装工具链。Rust构建测试仍未运行。语义候选和引用通过契约、源码摘要/范围、证据引用及SQLite回读校验；它们仍是带证据的暂定业务解释，因为代码分析无法代替项目领域负责人或权威需求文档确认其业务含义，也不证明运行时行为正确。当前没有交互式业务确认/候选提升工作流，模型不自动将源码推导的主张改为`confirmed`。

## 初步算法描述请求

可用`PYTHONPATH=skill/src .local/analysis-venv/bin/python -m c2s_skill algorithm --root .local/real-projects/click --source examples/naval/naval.py --function ship_move`或将根目录换成regex、源文件换成`.rs`路径，按需获得单个Python/Rust函数的JSON算法描述。请求只读取根目录内的一个常规源码文件，拒绝越界路径和符号链接；响应带源码摘要、结构校验、`complete=false`及来源/类型/调用/数据流等显式缺口。该输出是静态语法投影，不能当作完整CFG、类型检查结果、测试结论或行为等价证明。

结构化算法source-to-body回归清单锁定regex/R5、Click/P7和nlohmann-json/C5 commit，位于`skill/tests/fixtures/algorithm-source-checklists.json`。R5/P7按自动lowering的step做映射；C5当前以人工审阅的opaque记录保留SAX错误回调结果和输入效果，C++自动lowering仍不支持。测试只证明固定来源片段与公开映射用例一致，不证明算法与完整运行时行为等价。

## v2来源组织实施切片

`collect_source_records(root, scan, request)`在没有语义实体映射时仍保留目录、清单、包、工作空间、源码模块及声明。来源记录和语义实体身份独立，重复取得复用来源键并追加证据；工具解释分歧保留为观察差异。`scan_project`可传`source_paths`限制实际解析文件，完整inventory仍保留，未解析/非源文件在来源覆盖中显式列出。现已接入默认v2统一查询及存储。

v2局部构造接口`construct_requested_entities`只对计划需要的实体和描述面构造解释，解释均为带premiseIds/method的暂定主张；不按实体类型固定分配E视角。仅algorithm描述面请求会调用算法lowerer，并将步骤证据纳入档案引用。实现视图保持partial_static_syntax_projection；宽泛实现类型仍不能推断业务类型或值域。

v2存储接口`read_request`按scope、输入指纹与配置隔离快照，并按target/facets返回可复用覆盖；部分静态结果保留原缺口。`commit_request`在单事务中注册、合并补证、写覆盖和操作回执，同操作同载荷幂等、异载荷拒绝；取消/失败不发布完成覆盖。数据库仍须放在分析目录外；保存失败不能吞掉已取得事实，旧profile表保持独立。

## v2统一查询（当前默认）

默认profile为semantic-entity-model-2，显式选择参数仍可使用。以下v2命令已在固定Click检出实跑；部分静态覆盖返回退出码2，不能据此声称全部行为语义已取得。

```bash
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m c2s_skill query --root .local/real-projects/click --select modules --model-profile semantic-entity-model-2 --store /tmp/c2s-v2-cli.sqlite --format json
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m c2s_skill query --root .local/real-projects/click --select function:make_parser --model-profile semantic-entity-model-2 --store /tmp/c2s-v2-cli.sqlite --format json
```

这两次分别取得91个源码模块、1个函数；第二次复用来源索引，解析0文件、降低1函数。JSON/Markdown来自同一规范结果，原始工具工件、证据及缺口可回读。`query_project_v2`是公开执行入口，`query_entity_store_v2`只查询给定输入/配置下的已有档案，不重构来源。v2缓存以规范请求、协议版本、输入指纹及配置隔离；v1缓存不能命中v2。

sourceRecords表示来源组织，items是请求目标；实体self详情保留自身全部已取得属性，子实体按expandDepth展开（0至8），循环与歧义有独立诊断。`--request`可传请求JSON。显式`--graph-output`仍按已点亮CRG解析器导入，保存原始响应和新鲜度缺口；CodeGraph目前仍是候选，不会默认执行。


## 默认切换、备份和回滚

默认命令返回semantic-fact-result-2，并只向v2独立表写新事实。旧v1实体、旧完整profile和M1接口/档案保留；显式`--model-profile semantic-entity-model-1`仅用于既有协议兼容，不会迁移或覆盖v2表。新调用请使用`execute_fact_query`或`query_project_v2`，纯档案查询使用`query_entity_store_v2`。

首次向含v1实体档案的数据库写v2时，先用SQLite在线备份生成同目录`<档案名>.pre-v2-<唯一标识>.sqlite`，执行integrity_check和逐表回读比较；失败则不写v2，并返回persistence.failed。回执persistence.backup给出路径、摘要和验证状态；备份文件不会被覆盖。并发首次写入允许生成多个独立备份，后续已有v2数据时不重复备份。数据库、结果、缓存及备份均须位于分析项目外，正常查询不联网；Cargo metadata仅--no-deps --offline。

回滚时先停止写入并另存当前数据库和v2产物，然后用回执备份的完整SQLite文件恢复到独立路径，指定该路径和`--model-profile semantic-entity-model-1`验证旧实体查询；若需恢复历史默认行为，检出切换前版本。禁止把v2载荷直接覆盖v1表。Python API `backup_entity_archive`也可手动生成经验证的外置备份。

退出码0表示本请求范围完整，2表示有静态缺口或保存失败，64表示无效请求。部分算法和图关系会保留已取得内容并返回2。覆盖完整只针对本次请求，不承诺穷尽全部语义、类型、动态行为或运行时等价。当前验证平台Linux，Python/Rust静态提取；其他语言、host/target及词元收益未验证。

最终复现与验证证据见[非DDD重构交付核验](../docs/development/reviews/semantic-facts/非DDD重构交付核验.md)和[真实项目验证](../docs/development/reviews/semantic-facts/非DDD真实项目验证.md)。本次为共享工作区公开开发验证，私有盲验收未执行。
