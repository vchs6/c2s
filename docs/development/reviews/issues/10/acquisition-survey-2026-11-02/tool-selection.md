# 工具与项目分析 Skill 选型（按事实覆盖）

调研范围是首期已确认的 Rust/Python 项目事实需求 N01–N09。选择原则是用最少的工具组合，覆盖越多所需事实越好；语言数、图节点数、Skill 名称和 README 声明都不等于语义覆盖或完整性。文档、接口源码、真实项目试验分别标记，不把未知支持说成已验证。

## 当前运行环境与可用 Skill

本会话可调用的 Skill 清单包括云环境配置和 Superpowers 开发流程 Skill，没有可直接调用的仓库分析 Skill。ast-grep、Semgrep、CodeQL、Serena、GitNexus、CodeGraph 在当前执行环境均未安装；`/usr/bin/sg` 是系统 `sg` 命令，不是 ast-grep。Code Review Graph 2.3.9 与 Python/Rust 核心解析器有固定项目的先前公开试验记录；本轮另将 CRG 安装到忽略的 `.local/analysis-venv`，在 Click 的只读副本上实际构建图并执行 `callees_of`，随后通过本仓库 CLI 解析其真实 JSON 输出。

Code Review Graph 仓库附有 `build-graph`、`explore-codebase` Skill。调研报告记录其实际文件和接口，但有限检索预算不能替代全量事实枚举。本实现选择它的结构化 query API 作为**可选关系线索来源**，没有把自然语言 Skill 摘要当事实源，也没有把上游 Skill 注册为当前会话 Skill。其查询输出由 `c2s_skill.graph_tool_adapter` 解析。

## 候选覆盖对照

| 工具或 Skill | 多语言支持 | 轻量化 | 语言自有信息 | 重型项目分析 | 对 N01–N09 的有效覆盖及限制 | 决定 |
| --- | --- | --- | --- | --- | --- | --- |
| Python `ast` + `tomllib` | Python | 是，标准库 | 强：Python 声明/语法、pyproject 声明读取 | 否 | N01/02 仅已实现的静态 pyproject/Flit规则；N03/04 强；N05弱；N06局部语法；N07/09依赖本地全目录清单和 gap，而不是工具默认文件集 | 必需，现有路径保留 |
| Tree-sitter + Python/Rust grammar | 多语言语法框架，逐语言 grammar | 是 | 否 | 否 | N03/04强、N06局部语法、N07/09本地逐文件遍历；不提供类型绑定、跨模块调用解析、项目构建真值 | 必需的结构前端；Python 重复部分留给原生 `ast` |
| Cargo metadata | Rust 项目 | 是，原生 Cargo 接口 | 强：Cargo package/workspace/target 声明 | 否 | N01/02的Rust原生声明与workspace成员；不等于 Project 归属、依赖完整解析、构建产物或 target 语义 | Rust 工程信息必需 |
| Code Review Graph 2.3.9 query API | 实测固定 click/Python 与 regex/Rust | 中等；需建关系索引 | 否 | 是，项目级图查询 | N03–05、N06提供跨文件调用/引用候选；查询有 `result_count`/`results_omitted`，可见返回可截断；以 Git 跟踪范围建图，不能代表 N09 全目录；查询响应未绑定当前源摘要，故新鲜度未知 | 选作可选关系补充；当前事实标记 `static_may`，保留完整 JSON 工具证据和 freshness gap |
| Code Review Graph `explore-codebase` / `build-graph` Skills | 跟随其底层图支持 | 上游 Skill 有短输出预算 | 无额外语言语义 | 以图工具为后端 | 可导航和组织查询，但有限文本输出、默认索引范围和图截断不足以证明全体；当前工具上下文不能直接调用这些外部 Skills | 不作为语义事实来源；可供人工探索 |
| ast-grep | Tree-sitter 语法匹配，多语言 | 是，CLI/并行结构搜索 | 否 | 否 | 对已确认 Python/Rust 可查指定语法模式；不自然地产生完整声明目录、符号绑定、工程边界或跨文件调用；规则要按谓词维护，且与已有 Tree-sitter 遍历高度重叠 | 不选入必需栈；重复现有语法覆盖 |
| Semgrep CE | 官方 README 声明支持 30+ 语言 | 中等，规则引擎 | 否 | 中等；规则/局部数据流，不是完整项目图 | 可补指定模式和部分数据流候选；规则命中不等完整枚举，官方 README 也说明 Community Edition 跨文件/单函数边界限制；不能替代 N01–05 工程与符号信息 | 暂不选；当前需求下会增加规则和输出适配面 |
| rust-analyzer | Rust | 中等，需 Cargo 项目索引 | 强：Rust 名称解析、类型/引用候选 | 中等，语言服务器/项目索引 | 有望补 N04/05 的 Rust 绑定；需要配置和 Cargo target/features；不能解决 Python，亦不能单独满足 N01–03/06–09 | 作为遇到 Rust 精确绑定需求时的按需后端，不默认启动 |
| Serena 项目分析 Skill/MCP | 多个 LSP 后端，逐语言 | 中等至重，启动后端/索引 | 间接复用语言服务器 | 是 | 符号/定义/引用输出可补 N04/05；按文件调用与响应字符限额不证明全项目枚举；本会话不可调用，输出形态需单独适配 | 不选入当前运行依赖；不为覆盖本来已由 CRG 候选覆盖的能力叠加另一个图层 |
| GitNexus、CodeGraph Skills/API | 多语言项目图，版本/语言分别验证 | 重：索引、缓存与默认过滤 | 否 | 是 | 有 N03–06候选；Skill/查询示例有 top-k、忽略和文本协议风险；当前无实测覆盖收益，也会与 CRG 重叠 | 不选入首选组合 |
| CodeQL CLI / 自定义 QL | 多种语言前端，具体语言矩阵须按版本核 | 重：需要 CodeQL 数据库、CLI 和查询包 | 否 | 是，静态程序分析 | 有望对局部数据流/安全语义提供深度查询，但产品化需要每种语言的 QL 查询及 BQRS/SARIF 到本模型的适配；并非 N01/02 构造事实源。官方开源库 README 指 CLI 单独分发并单独许可；当前未安装/未测试 | 暂不选；成本和接入复杂度高，尚未证明对本次事实清单有净覆盖收益 |

## 选定的最小组合

1. **目录与语法：** 本地清单遍历 + Python `ast` + Tree-sitter Rust grammar。保留所有范围内文件、parse error、未支持格式和未跟随链接的诊断；不让图工具的 Git 忽略规则缩小范围。
2. **原生工程声明：** Python `tomllib` 读取 pyproject；Rust 调用 `cargo metadata --format-version 1 --no-deps --offline`。只对文档和实测支持的工程声明产生事实，其他 backend/动态字段留下 gap。
3. **跨文件关系按需补充：** Code Review Graph `query_graph("callees_of", target, detail_level="standard", max_results=...)` 是可选来源。解析器检查 query pattern、结果计数/遗漏、返回路径、调用行、direct/unresolved 标签，把候选映射到本地源码声明和算法步骤；原始 JSON 作为 `tool_output` artifact 保存。由于工具响应没有提供可验证的完整索引源摘要，即使零遗漏也保留 `GRAPH_INDEX_FRESHNESS_UNVERIFIED`，不能据此宣布该函数调用事实完整。
4. **Skill 使用：** 不把项目分析 Skill 置于每次查询的固定链条。当前可调用 Skills 无项目分析器；Code Review Graph 的 Skill 是可选导航说明，底层 query API 才是能解析的结构化来源。这样不引入另一个模型摘要层，也不会把有限文本遗漏当不存在。

ast-grep/Semgrep 在需要一次性语法规则或局部数据流规则时可以按需试用；当其能补充具体 N01–N09 事实且给出可定位、可补齐输出证据时再加适配器。rust-analyzer 仅在 Rust 名称/类型解析成为本次请求必要项时启动；CodeQL 等重型分析器在现有事实组合无法覆盖、且其实际输出和资源成本已测量后再评估。以上不改变用户确认的 Rust/Python 首期范围。

**CRG 输出适配验证：** 解析器核对 query/status、结果数、遗漏数、edge 对齐、项目内路径、调用点和 direct/unresolved 标签。真实 CRG 响应会省略调用者路径；对 `callees_of` 查询，适配器从被查询函数的限定名恢复该路径。Click `Command.make_parser` 的真实查询返回 3 个调用点，其中 1 个映射到本地声明并生成 `behavior.calls` 候选，另 2 个 unresolved 作为缺口保留。即使结果没有截断，适配器仍报告图索引新鲜度未知，不会把关系覆盖标成 complete。

## 新增官方资料及试验边界

- ast-grep README，固定 commit `1e9830c8d038e728d98a5675cf48ca1c4c569136`：结构化 AST 搜索、lint 和 rewrite，语法由 Tree-sitter grammar 产生。
- Semgrep README，固定 commit `692bfae4ca1bf070f7e8b603037a19886fa36b4f`：声明支持 30+ 语言；README 对 Community Edition 的跨函数/文件能力边界有说明。
- CodeQL README，固定 commit `682545fdc03e8414d99a469c1f741c157b569740`：CodeQL 用于执行安全产品的标准库/查询；CLI/engine 单独分发，CLI 许可另行约束闭源项目使用。CodeQL 未安装，语言支持矩阵与项目覆盖尚未核验，故仅保留重型候选，不宣称受支持。
- Code Review Graph 实际固定项目试验、原始来源与版本见同目录 `experiment-results.json`、`sources.json`、`report.md`。此前公开试验在 click 和 regex 建图及查询，不能外推到其他 host/target，也没有测得端到端 Token 节省。
