# c2s语义事实查询Skill

状态：原型实现中。当前可对Python与Rust源文件进行全目录语法遍历，提取类/结构体、字段、函数、导入、常量、源码文档行为说明及常见控制流/调用/运算步骤，并按selector或有限自然语言请求查询，返回JSON或Markdown。每条记录带项目根命名空间内的稳定fact ID、主体ID、源路径和UTF-8字节范围；同一函数的声明、文档契约和算法步骤共享`subject_id`。`evidence_included`标明本次请求是否附带源码片段。`claim_mode`区分语法、声明、Cargo元数据和文档陈述，不代表已验证运行时行为。fact/subject ID绑定分析根路径，移动检出目录后会改变。

目前还不具备完整E0–E4领域模型、类型/调用绑定、完整源码到结构化算法的提取、来源覆盖验证或完整工程语义。算法描述契约结构校验切片位于`contracts/semantic-algorithm.schema.json`和`c2s_skill.algorithm.validate_algorithms`；它要求输入/输出、前提、正常/错误/终止结果、效果和顺序约束分别记录证据覆盖状态；校验器检查步骤身份、区域/控制/数据引用、计算语义字段及opaque边界。`c2s_skill.algorithm.extract_python_algorithm(...)`和`extract_rust_algorithm(...)`可从指定Python函数或Rust函数生成带源码字节跨度、控制区域和显式缺口的初步算法描述。`algorithm --all-functions`会遍历项目中发现的Python/Rust函数，逐个生成结构化算法结果，并报告解析失败与未处理路径；该模式仍不等于全项目语义完整，也没有接入通用`function:`查询结果；生成物不等于行为完整或源码等价证明。宏展开、条件编译、多态/动态调用、反射、运行时行为和工程配置语义没有完整覆盖；所以当前结果的`complete=true`仅表示所选事实类别的获取没有已知缺口，并不表示项目的所有语义事实均已取得。结果会附带全目录清单和未处理路径；源文件解析目前只覆盖`.py`与`.rs`。`classes`、`functions`和`all-declarations`只返回顶层条目，不附带类型体/函数体；须请求`definitions`、指定`function:名称`或`all-supported-facts`才会附带相应源码体。SQLite结果缓存绑定项目树摘要及分析配置摘要（分析器、Python/平台、Tree-sitter和Cargo版本）；缓存写入失败时事实仍返回，并通过独立持久化状态报告，逐项构造事务恢复和supersedes lineage尚未实现。机器输出契约位于`contracts/semantic-fact-query.schema.json`。请把本原型用于开发与明确范围查询，不作为完整语义验收结论。

## 公共语义模型契约（M1）

仓库根目录的 `contracts/semantic-model/` 与 `src/c2s_semantic_contract/` 提供版本 `1.0.0`、profile `m1-project-discovery-1` 的初始M1身份、事实包及封闭谓词目录契约，含`project.name`、`project.language_declared`和`workspace.member`。开发环境安装使用 `python3 -m pip install -r requirements-semantic-model.txt`；验证使用 `PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s tests/semantic_model -v`。`register_m1`按identity domain和sourceKey复用身份并合并证据；`validate_model`检查M1结构、身份/证据引用、assessment基数与lineage、目录闭包、事实角色、来源观察和coverage关系。`scripts/query_m1.py`可按项目根目录运行`project`或`workspace-members`并输出M1 bundle、附件、来源观察和校验结果。Click名称/语言与regex workspace真实查询均已通过投影和校验。Cargo workspace适配器捕获`metadata --no-deps --offline` JSON附件，校验成员清单一致后才标记verified；Cargo缺失或输出不一致时保留unchecked gap。附件持久化、评估判定和完整跨事实规则仍在后续工作中；共享工作区开发测试不是独立验收。

条件求解器位于`src/c2s_semantic_contract/conditions.py`：支持有限Boolean/Enum域上的`true/false/eq/neq/all/any/not`，最多枚举4096种赋值；超过限额、域未知或表达式不支持时返回`undetermined`。`semantic-fact-model-1`现已集成Context/Condition、引用上下文、依赖需求/解析记录和单值声明重叠检查；`validate_model`还会按配置报告显式依赖图的条件环分析，并保留原图；`m1-project-discovery-1`拒绝这些扩展记录。依赖记录当前为显式输入，不会从项目自动推断。求解范围限于显式有限域及已注册M1谓词，不能据此声称项目完整语义分析完成。

完整语义profile也提供六种互不排序的claimMode、带Supports/Refutes/Limits角色的evidenceRefs，以及带前提引用的derivation；缺失前提或推导循环会报错。这些模态/推导目前由调用方提供，分析器不会自动推断运行观测，也不能由此宣称真值已证明。

完整profile的negative claim必须引用受限输入闭合集、逐项无匹配、条件相同、人工审定且无未解决缺口；校验器只能核对闭合记录结构，不能证明调用方提供的输入集合客观穷尽。

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
PYTHONPATH=skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -v
```

支持的查询：`project`、`workspace-members`、`classes`、`members:类型名`、`functions`、`function:名称`、`local-bindings`、`definitions`、`imports`、`constants`、`behavior-contracts`、`algorithm-structure`、`all-declarations`、`all-supported-facts`。自然语言暂支持“有哪些类”“Command 的成员有哪些”“函数 run”等明确形式；不能识别的请求会作为gap返回。`function:名称`返回所选函数声明、源码文档、算法步骤及局部绑定事实；嵌套函数是独立主体，需单独查询，避免把内层函数的执行步骤误归到外层函数。`local-bindings`目前返回函数内简单名称的赋值目标（Python支持简单/解构赋值、循环目标、with别名及异常别名；Rust支持元组、结构体、元组结构体、切片、or、引用及`@`捕获`let`模式中的标识符）；事实以源码片段为证据，不表示调用解析、类型确认或完整数据流。`workspace-members`通过Cargo metadata解析，不需要依赖下载；Cargo不可用或元数据失败会明确报告gap。未知selector以退出码2返回；`algorithm --all-functions`对部分静态分析返回退出码2，即使所有函数均已遍历成功；结构错误或读取失败使用退出码64。JSON和Markdown包含相同事实ID，并标明源码片段是否因本次请求省略。可用`--store /path/outside/project/facts.sqlite`启用SQLite缓存，缓存键绑定项目树摘要、分析配置摘要和请求。输出及缓存目录在读取或创建前必须位于分析项目之外。遍历包含测试、示例、隐藏及忽略文件中的`.py`/`.rs`源；`.git`对象库和非源文件不作为程序语法解析，并在结果覆盖中列为未处理路径。

已对固定真实项目做全源遍历：regex commit `94ac45b2a6e7b1c30927feb5b66c5ded5b7ad447`：227/227 Rust文件解析，54,315条当前支持事实（含7条Cargo工作区成员）；click commit `2247b35ea1c47c727d7a06e51fa280e12a863ff6`：91/91 Python文件解析，23,779条当前支持事实。函数声明归E2，函数体算法步骤和已支持的局部绑定归E4；当前还覆盖部分控制结构、运算、调用及返回/异常语法。Python装饰器不会计入函数体算法步骤。另已批量按需查询所有函数：regex 4,342个函数声明、3,395种查询目标；click 1,897个声明、1,797种目标，返回事实均与全量扫描中的主体事实一致。两项目事实ID均无重复，并列出224/155个非源或未处理路径。全量selector返回所有当前支持事实。这些仍不是完整语义真值。逐文件、逐事实ID清单见`../docs/development/reviews/semantic-facts/2026-11-06-exhaustive-inventory.json`；验证记录见`../docs/development/reviews/semantic-facts/2026-11-06-verification.md`；两个函数的具体示例见`../docs/development/reviews/semantic-facts/2026-11-06-two-function-facts.md`。使用`PYTHONPATH=skill/src .local/analysis-venv/bin/python scripts/generate_semantic_fact_inventory.py`可重建清单和函数示例。

## 开发依赖与来源

| 工具/能力 | 实际版本 | 用途及当前边界 |
| --- | --- | --- |
| Python | 3.12.14 | Linux实现与AST；其他Python版本未测试 |
| tree-sitter / Python grammar / Rust grammar | 0.26.0 / 0.25.0 / 0.24.2 | Rust结构解析依赖；Python使用标准库AST |
| jsonschema | 4.26.0 | 校验JSON Schema 2020-12查询输出契约 |
| Code Review Graph | 2.3.9 | 已实际建图/查询，默认覆盖不能当全目录完整；外置图缓存，无模型嵌入 |
| Rust工具链 | rustc 1.99.1，Cargo 1.99.1 | 已安装至`.local`；Cargo workspace metadata可离线取得，Rust依赖测试仍未通过下载阶段 |
| GitHub CLI | 2.103.3 | 备用账户配置工具，官方归档摘要核验；仅CI开发准备，需独立GitHub授权 |
| OpenSpec / Codex / Superpowers | 1.16.0 / 0.166.0 / 7.0.1 | 开发流程工具，不当产品运行依赖；Superpowers在当前环境可读 |

Python包来自包索引；Rust安装来源为官方https://rust-lang.org/tools/install/，使用项目本地RUSTUP_HOME/CARGO_HOME且不改shell profile。当前安装路径`.local/analysis-venv`、`.local/rustup`、`.local/cargo`均为开发临时目录，不随Skill发行。

CRG包自带build-graph/explore-codebase等Skill文件可读取，但本轮没有执行自动install去覆盖客户端MCP/AGENTS/hooks，也未把这些文件注册为新的个人Skill。Serena、GitNexus、CodeGraph仍是调查候选，未安装，不声称已支持。

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

## 初步算法描述请求

可用`PYTHONPATH=skill/src .local/analysis-venv/bin/python -m c2s_skill algorithm --root .local/real-projects/click --source examples/naval/naval.py --function ship_move`或将根目录换成regex、源文件换成`.rs`路径，按需获得单个Python/Rust函数的JSON算法描述。请求只读取根目录内的一个常规源码文件，拒绝越界路径和符号链接；响应带源码摘要、结构校验、`complete=false`及来源/类型/调用/数据流等显式缺口。该输出是静态语法投影，不能当作完整CFG、类型检查结果、测试结论或行为等价证明。
