# 工具与Skill获取能力调研：中立问题包

用户确认：沿用survey-semantic-acquisition-capabilities；先由语义事实需求驱动工具/项目分析Skill调研，再收敛架构、构造和Token方案，不另建重复提案。本轮仅文档调研，不安装/运行候选，不实现产品、不编写测试、不归档。各类资料分开按需读取，不扩写AGENTS。

约束：Rust/Python；指定目录全部内容在分析范围；单次项目不变；请求相对顶层完整且不递归；缺口如实说明；报告/结构数据同源；减少实际LLM Token而不删所需事实。主体身份、领域关系不由第三方图节点/社区/置信度决定。既有需求不重开。

证据：sources.json记录24份固定提交的官方文档、Skill及部分接口源码。候选code-review-graph包含build-graph/explore-codebase Skill及图工具，GitNexus含探索Skill/图工具，Serena为MCP符号能力（不冒独立领域Skill），CodeGraph此轮定位为图工具，其仓库内两份Skill是维护/评估用途，未取得通用项目分析Skill的充分证据。旧Cargo metadata/Python AST/Tree-sitter/rust-analyzer文档证据仍为候选。

具体观察：CRG minimal模式返回最多五项且有省略计数，Skill有约800Token目标；GitNexus探索Skill建议limit=3，而文档有分页和省略；Serena符号接口输出str形式JSON，超字符限额可无内容；CodeGraph默认自动同步并有忽略规则，CLI部分接口支持JSON。部分安装/索引命令会写AGENTS/CLAUDE/插件/缓存，不能原样运行于不变输入。第三方Token宣传不是本项目实测。

待讨论：完整复用高层Skill流程、直接复用底层接口、或二者组合，如何避免有限检索冒顶层完整、默认忽略冒全目录覆盖、全仓图索引冒按需构造；工具/Skill内部LLM成本和宿主/target适用如何记账；首期实际验证候选顺序及阻塞界限。

输出要求：只读、勿写文件/派生代理，首轮独立提出可证伪主张和替代；明确研究结论不是用户确认/工具已验证。不要构造实际隐藏测试用例。首轮600中文字左右。
