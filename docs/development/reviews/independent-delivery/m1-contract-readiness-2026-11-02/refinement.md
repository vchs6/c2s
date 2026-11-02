# M1公共契约细化报告

2026-11-02；交付2.1的规划子工作，未宣告2.1通过/集合冻结/产品可实施。范围严格为项目发现/列表、明确语言声明、原生workspace成员，不是完整所有项目事实。具体记录、JSON、函数签名、SQLite与Python3.11+选择均为代理技术决定，不是新增用户确认。

## 精确修改范围

下列九个原change各修改design.md和tasks.md，共18个规划文件；只追加M1节及父任务的稳定子ID，25个子任务均未勾选，原父任务状态不变。

| openspec/changes/下的change | design新增内容 | 原tasks的M1子ID |
| --- | --- | --- |
| define-layered-semantic-fact-model | 模型/身份登记/证据附件/来源观察/校验；三个封闭谓词与字段、基数、诊断 | 1.1.1、1.2.1、2.1.1、2.2.1、3.1.1 |
| define-semantic-fact-query-contracts | M1Query/Result/Delivery，规范化、投影、Markdown/JSON、退出0/2/64 | 1.1.1、2.1.1、3.1.1 |
| design-lazy-semantic-fact-construction | M1Need/Plan、plan_m1、同次复用/补缺 | 1.1.1、2.1.1 |
| design-incremental-semantic-fact-storage | M1Read/Commit/Receipt、读/幂等查询/SQLite事务、规范主张及补证去重 | 1.1.1、2.1.1 |
| survey-semantic-acquisition-capabilities | M1Entry/Acquired、全目录盘点、Cargo/Flit选定路径、显式工程边界评估及试验切片 | 3.1.1、3.2.1、1.1.1、2.1.1 |
| define-semantic-analysis-quality-goals | M1Event/Usage/Profile、全链计时/未知计量、compare_m1 | 1.1.1、2.1.1 |
| minimize-semantic-extraction-tokens | M1ModelDecision，确定性直转/无法取得不猜，消费唯一计量口径 | 1.1.1、2.1.1 |
| design-semantic-fact-coordination | M1Session、open/verify/run/observe端口、输入归属与串行基本恢复 | 1.1.1、2.1.1、3.1.1 |
| design-semantic-fact-skill-architecture | 精确生产者/消费者表、引用层/公开命令/Skill归档、产品与模型版本分列 | 1.1.1、2.1.1 |

公共类型共26个，各仅一个owner；其他design引用精确名。模型身份仍为authority/domainId/localId，登记源键只查已有身份；Cargo原生成员指向PackageSpecification，Project由独立Assessment有据判定。原生工具stdout作为来源附件随候选原子保存，结果只返回依据引用；不经诊断/原生JSON偷递归展开。语义完成与保存结果分列，unknown先重读再补未存；M1暂存仅本进程生命期，不承诺崩溃零Token。

## 剩余实质问题与门禁

- 所选Cargo metadata命令、Flit入口绑定和工程评估规则仍需获取3.1.1/3.2.1实际接口/覆盖/副作用证据；既有AST/CRG公开探索不能替代。未知格式、backend、symlink、不可读及未决工程边界保留缺口，不声称所有Project都已找到。
- M1未发现需重开用户领域基线的矛盾。工程判定规则是可拒绝的技术设计，需跨模块审查；不能因为写出精确记录就把它升级为实测支持或严格真值。
- 历史design/tasks里仍保留“另批/全量依赖”阶段说明，本轮M1节明确按ADR-0009接续，并只依赖实际消费的子契约；它们不应重新成为M2–M4全量冻结的前置。里程碑/交付/readiness/集合摘要由协调者统一绑定，不能把此最小切片当整项M1或整个原任务验收通过。
- 真实五角色隔离及制品/运行入口合法交接仍需交付2.2/2.3验证；本轮不访问私有仓库/秘密/日志，不创建隐藏suite、产品Schema、产品代码或测试，不提交git。未修改交付change、readiness、主规格或manifest；工作区这些文件的其他改动归协调者。

## 验证

使用brainstorming、writing-plans及verification-before-completion；已取得九个change的status/design/apply instructions并读取相关上下文，tasks规则复核沿用原唯一清单。实际运行：OPENSPEC_TELEMETRY=0 npm run validate，21 passed/0 failed；npm run check:artifacts，4 artifact hashes及workflow/Superpowers检查PASS；git diff --check通过。只读核对脚本确认26个M1记录定义均有唯一owner，25个稳定子ID无重复且未勾选；没有以这些文档检查冒实际产品验收。

## F1–F4限定修订（2026-11-02）

按m1-contract-review.md核对后，确认原文存在比较输入不足、有效视图未定义、未知select交接及规范ID回流四处接口缺口；上文首次“契约细化完成”的描述不代表这些缺口已经在首次版本解决。本轮使用receiving-code-review与verification-before-completion，只修九个change原M1节及已有子任务条件，26个记录owner与25个子ID不变，没有新增产品任务或改checkbox。

| 审查项 | 明确字段/签名及生产者→消费者 |
| --- | --- |
| F1 比较/失败档案 | #5 M1Profile新增factSummary[{factId,key}]、逐项gaps、strategyId、inventory完成性/来源，query/session可null，receivedNs与可空acceptedNs覆盖前置失败；profile_m1显式接盘点状态/来源/entries。#6/#12供请求/事件，#9 fact_key_m1生成完整规范键，#5保存自包含摘要→#11/compare_m1消费；不同inputId/identityDomain明确不可比，不读全局缓存补事实。 |
| F2 当前视图/补证 | #3 Assessment/Coverage增加supersedes，Coverage增加evidenceIds/resolvedDiagnosticKeys；Registration固定ref/kind/sourceKey，evidenceIds可并集。#10 acquire_m1显式接prior历史+current包并产进展，#9保历史及规范去重，#12 current_m1(session,read)->M1Bundle按合法替代边选叶、保冲突、区分旧失败/当前缺口；#8规划/#7投影共用同一视图。 |
| F3 未知select | #7结构有效Query保全部字符串，normalize_m1仅因结构/contract错误返回单Diagnostic；#8逐项UNSUPPORTED_PREDICATE，#12经project_m1的request_diagnostics参数传#7。混合请求继续支持项且partial/unavailable，全部未知不获取/不提交、unavailable、退出2；结构错误才64。 |
| F4 规范ID回流 | #9 canonicalize_m1(session,stored,pending,artifacts)->M1Read先合并暂存/历史并重写规范引用；commit/lookup成功后#12必须read_m1读到不早于回执generation的同session规范包，再current_m1→#7 project_m1。规范重读失败回unknown并披露；failed/unknown可报告已校验暂存合并视图，不冒规范ID已持久化。 |

同时依root指示修正动态version歧义：version不在M1需求内，不影响已取得project.name/Flit入口时不阻塞整个Project；真正影响当前所需字段/入口的动态module映射仍报相应缺口。root随后报告固定regex/click原生路径实证已取得，此为root工作，本轮未复制/运行其证据；固定click的version_dynamic=false，不能冒已测动态version反例。其他异常/未知backend/隔离证据仍分别按原任务处理。

修订专用diff：.superpowers/sdd/tasks/m1-contract-f1-f4.diff（18个规划文件，仅相对本轮开始的差异，供同reviewer限定复核）。本轮实际重新运行：OPENSPEC_TELEMETRY=0 npm run validate，21 passed/0 failed；npm run check:artifacts，PASS；git diff --check，退出0。只读字段/任务核对：26个记录唯一owner、25个M1子ID及全部既有checkbox ID/状态与修订前完全相同。未修改主规格/交付change/readiness/manifest，无领域基线变更、Schema/产品/测试/私有访问或git提交；本报告不宣布reviewer复核通过或交付就绪。

F3文字接续：已将架构M1末段的旧句“未知select由#7诊断”改为“由#8判定，并经#12交#7呈现”；仅更新该owner表述及本报告，未调整任务/checkbox，实际git diff --check通过。
