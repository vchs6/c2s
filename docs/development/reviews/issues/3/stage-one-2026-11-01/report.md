# Issue #3阶段一评审与候选规划报告

日期：2026-11-01。状态：**awaiting-decision**；user_decision=null；implementation_approved=false。基点：18370af506d2153d0dae66a4d9536499a2b08114。

后续更新：用户已选择方案A，准确范围见scheme-decision.md；实施未批准。下文为阶段一提交时的报告快照，原始Battle的user_decision=null保留原貌，不改写历史评审。

## 工作结果

继续既有define-layered-semantic-fact-model，完善proposal、两份领域/算法delta、design、唯一tasks及review-map。模型delta共14项Requirement（含原3项已确认约束），算法delta8项；新增具体方案均待用户选择。两份正式主规格及ADR保持原文，未把代理意见提升为基线。22项领域/算法Requirement均有上游与任务/候选验收映射。

已实际使用brainstorming：核对需求与固定约束，比较A/B方案，先独立Battle再整合反例，形成候选设计，并用独立builder-check审查可实施性。writing-plans仅用于条件化候选计划，未越过方案/实施门槛。待用户确认前不运行产品实施技能。

本轮3个独立Battle角色：双方首轮各自读取中立包，首轮结束后互传意见与C01–C07争议，第二轮逐项交叉质询，再由新上下文独立reviewer综合。builder-check是额外独立审阅，不冒充Battle第四票。参与者只读、主代理单点写记录；记录为真实答复的结构化整理，不是逐字转储，不含宿主会话数据或OS隔离宣称。

## 推荐与替代

推荐A：版本化JSON类型/谓词目录、结构Schema与Python分阶段校验；受限算法结构+opaque，body单源伪代码投影。B：逐谓词判别联合Schema、人工文本+步骤/来源映射；静态工具约束更直接，但扩展与漂移审查成本不同。A只是代理推荐，用户尚未选择；如选择B，重写相应候选并重算批准令牌。

## 争议的处理与残余风险

| 争议 | 候选处理 | 证据限制 |
| --- | --- | --- |
| C01 身份与配置 | 保留D身份；歧义、合法多值、同时适用的冲突分开；零匹配不证明不存在 | 身份连续性仍靠显式依据，未承诺任意源码变动自动识别 |
| C02 工程边界未决 | 身份域与项目映射分开；来源声明可交换，不冒充Project/确认所有权 | 项目边界和映射反例是阶段二候选验证 |
| C03 组成/内嵌边界 | 有限内嵌白名单、独立主体/body/区域/步骤引用；完整包不等于响应整包 | 静态形状支撑不等于查询Skill运行验证 |
| C04 三值与SAT | 明确有限Boolean/Enum片段和4096组合预算，sat/unsat/undetermined；违规另判 | 不解决一般条件可满足性，循环例标synthetic |
| C05 来源到body与文本 | 人工审定行为清单与程序投影分别验；删失败出口需被独立清单发现 | 清单可能遗漏，需独立审查；不证明全项目或等价 |
| C06 状态/覆盖/否定 | 呈现、获取、结论分开；两类有限闭合依据，不以空/哈希裁真 | 校验只检查依据一致，不能自行证明来源实际穷尽 |
| C07 目录/校验接口 | 固定首版发行包，元目录Schema与manifest、已知规则注册表；阶段错误后续not_run | 产品尚未实现；jsonschema依赖只核对官方发行，未安装/测试 |

保留少数意见：受限构造加opaque、人工文本+映射、逐谓词联合Schema。拒绝把“多种不同值”一概视为歧义。独立builder-check另发现目录可替换性未定义，候选A已补固定包/元Schema/目录引用/规则/版本及摘要检查与对应反例；该修订也未冒充用户批准。

## 工件入口

- 方案及全部公开接口/边界：openspec/changes/define-layered-semantic-fact-model/design.md。
- 唯一候选实施任务：同目录tasks.md；原10项产品任务保持未完成。
- Issue—Requirement—任务—测试映射：同目录review-map.md与本目录requirements-map.json。
- 中立输入：issue-input.json、authorization.md、problem-package.md。
- 实际论证：双方round1/round2记录、disputes.json、reviewer.json、battle-result.json、builder-check.json。
- 实际校验与批准：validation.md、approval.json及docs/development/issues/3/state.json。

## 继续方式与边界

方案确认与阶段二实施批准是两件事。用户可以仅确认A而不实施；若要实施，必须明确批准approval.json所列当前令牌及手动Work阶段二范围。输入、规划内容或规划目录文件清单变化，旧令牌失效。

现有自动Runner的允许路径/完整规划检查只识别issue-3-*，不能直接承接本既有变更；本轮在用户明确授权的人工Work会话完成规划，未改自动权限/脚本，也未另建重复模型。不要把本轮完成视为原Actions模型链路已恢复。后续若要求Runner自动实施，需另行授权修复路由；当前令牌不会自动扩大Runner权限。

本轮没有产品实现、获取器、存储、查询执行流程、产品依赖安装或产品测试；无新增上游构建/运行证据。没有归档或关闭Issue。
