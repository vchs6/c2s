# Independent DDD Delivery Implementation Plan

> **For agentic workers:** 后续获批执行时使用superpowers:subagent-driven-development或superpowers:executing-plans，并遵守本设计五角色隔离；默认编码者写测试的示例不适用。本文件只拥有交付治理任务，各产品任务仍唯一归属原change。

**Goal:** 固化独立交付约束与里程碑，准备有证据的连续执行门禁。

**Architecture:** 公开DDD契约指导独立实现及私有验收；受控工件交接，由独立验证者裁决。

**Tech Stack:** 现有OpenSpec/Superpowers；自维护脚本Python 3。隔离运行器尚未部署；当前允许公开CI配置及Python账户bootstrap准备，不实现产品。

**Spec:** 本change两份specs、design.md及ADR-0008。

## Global Constraints

当前按ADR-0009执行：必要安装、工具试验和准备已获授权，准备门禁通过后连续开发，不重复索批。当前隔离未通过，不写隐藏suite或依赖其门禁的产品代码；不改变既有语义基线，不自动归档，不泄漏凭据。五角色独立；当前产品0.b.c，未发布版本。

## Review Focus

共享token与candidate间接读取suite；公开契约不足却靠泄露隐藏断言修复；旧candidate/suite运行证据被复用；Issue事件或里程碑通过绕过开发门禁；按Token指标省略语义。分别由2.1契约核对、2.2访问反证、2.3证据绑定及各原产品任务独立验收覆盖；本轮不编写这些用例。

## 1. 本轮规划交付

- [x] 1.1 固化需求、流程设计与里程碑索引。依据：本能力四项Requirement、版本约束及ADR-0008。交付：本change proposal/specs/design、两份主规格、ADR-0008、`docs/planning/program-2026-11-01/milestones.md`、既有tasks角色修订及协作规则。验证：真实双方两轮Battle及新reviewer，逐要求/里程碑/任务引用自审。通过：用户确认/代理设计/候选清楚，既有产品待办均未勾选，索引无第二套产品计划；失败：越界实现、角色冒充权限或重开已确认需求。

- [x] 1.2 核验并发布规划证据。依赖：1.1。依据：verification-before-completion及#4/#13整体一致性。交付：本评审目录`validation.md`、`tool-evidence.json`、更新集合manifest及Issue #4/#13回复。验证：`npm run validate`全库严格校验、`npm run check:artifacts`、`git diff --check`、摘要重算及路径/任务状态审计；发布后读回main及回复。通过：实际证据对应版本，设计not-frozen、implementation_approved=false、isolation_ready=false；失败：未检查即声称完成、过期摘要或把规格校验当运行测试。

## 当前授权接续（ADR-0009）

用户已授权先完成准备然后连续开发，无需再次索取同一实施批准。旧“本轮仅规划/另取批准”仅描述历史阶段；本轮可执行准备、必要安装和工具试验，未通过就绪/隔离门禁不放行产品开发。状态见readiness.md。

- [x] 1.3 完成当前授权与分离治理文档、环境准备和就绪诊断。依据：ADR-0009及用户分文档按需读取要求。交付：docs/domain/foundation.md、docs/project/constraints.md、docs/workflow/{agent-governance,decision-policy,task-decomposition,repository-management,ci}.md，缩减AGENTS入口，skill/README.md依赖说明，readiness.md及本轮environment/validation记录。验证：独立双方两轮及新reviewer、严格校验、维护测试、实际安装/固定源试验记录及隔离诊断。通过：授权/就绪分开、无隐藏suite/产品完成虚报，CI实际能力与目标分开；失败：保留“尚未授权”作为当前状态、按角色名假隔离或文档互相复制冲突。此项不重复#10试验任务；2.1–2.3仍按真实条件留未完成。

## 2. 当前就绪门禁（已授权，未通过项不勾选）

- [ ] 2.1 完成M0公开契约与任务绑定的就绪审查。依据：五角色独立/真实项目验收、既有语义主规格及design §4–6。交付：原#3/#6/#7/#8/#9/#10/#5/#11/#12各design/tasks中的精确输入输出类型、边界、交付路径和受控验收入口；`docs/planning/program-2026-11-01/readiness.md`只登记绑定的版本/任务引用，不复制待办。验证：交叉契约消费/产出一致、真实项目固定源可追溯、host/target和非功能计量方案齐全；按当前授权完成整体审查后冻结新集合摘要。通过：原任务不再依赖未定义接口、发布载体/版本映射明确，可供独立角色执行；失败：TBD接口、旧单Issue令牌或文件存在代替实际就绪。此任务是技术准备；ADR-0009授权已成立，技术准备及隔离门禁通过后直接接续，不再重复请求实施批准。

- [ ] 2.2 按ADR-0009既有授权建立并验证独立执行环境。依据：测试不可见和五角色独立，design §2–3。交付：`docs/development/reviews/independent-delivery/isolation-readiness.md`公开脱敏就绪结论；私有环境留存实际身份/权限/设施/运行命令与访问检查证据，不把凭据或suite路径暴露产品库。验证：编码身份及candidate身份对suite、日志、历史/API、挂载、进程和管理接口的读写被拒，合法交接可执行；runner及最终验证身份不同。通过：具体私有suite根、制品交接接口和runner命令已绑定且证据可复核；失败：仅分支/目录/角色提示隔离、共享全权token或candidate进程可读suite。未通过不得编写隐藏用例，当前因执行环境能力blocked；必要设施准备已获用户授权，但不得捏造当前未具备的部署管理能力或泄漏凭据。

- [ ] 2.3 在ADR-0009授权下且2.1/2.2通过后接通连续交接和版本门禁。依据：授权内持续推进、product-versioning及design §3/5/6。交付：`docs/development/reviews/independent-delivery/handoff-verification.md`公开脱敏结论；私有run/verdict/制品清单由各独立角色所有。验证：用真实candidate/suite/源/环境版本执行交接并核查失效/重验，失配拒绝推进；失败反馈仅公开契约诊断，版本0.b.c对应被接受candidate。通过：独立角色无越权改写、可续同一批准范围且不触发新Issue、不自动归档；失败：旧证据沿用、runner兼最终验证、隐藏内容泄漏或未部署却声称后台持续运行。各产品验收只勾选原任务，本任务不重复实现它们。

## 3. CI配置接续（用户已明确要求配置，账户能力不足时如实阻塞）

- [x] 3.1 交付仓库侧CI容器边界检查和安全账户配置入口。依据：用户要求完成GitHub托管Runner/私有验收仓库/凭据配置，ADR-0008/0009及本设计隔离约束。交付：`.github/workflows/isolation-readiness.yml`、`scripts/configure_ci.py`、`docs/workflow/ci-setup.md`。接口：脚本默认dry-run，--apply需本地gh已认证；创建/核实私有验收仓库、设置仓库变量和最小Actions默认权限，API密钥只通过安全输入及stdin交gh，不输出/提交凭据。CI仅执行公开合成标记的容器访问检查（非隐藏验收），不加载私有suite/调用模型；允许push仅在该workflow变更时运行此基础设施诊断，不触发产品开发或Issue扫描。验证：独立实现/代码审阅、脚本help/dry-run/无凭据拒绝、既有维护检查及实际GitHub托管CI结果。通过：候选容器只挂公共目录、无网络/凭据/Docker管理接口，宿主私有标记不可读，宿主可合法读取；报告镜像摘要及探测结果且development_ready=false。失败：把标记诊断冒完整五角色就绪、账户配置未执行却称完成、泄漏密钥或默认live修改。实际证据：`docs/development/reviews/independent-delivery/ci-setup-2026-11-02/validation.json`，候选6283a23的托管probe及维护CI均success；3.2及整体就绪仍未完成。

- [ ] 3.2 完成账户端配置及完整角色边界验证。依赖：3.1及有权限的GitHub账户管理入口、实际模型凭据。交付：私有验收仓库、Secrets/变量/权限、受控交接入口和本地脱敏配置回执。验证：私有性确证，编码身份不能读验收仓库/日志/制品或改验收workflow，candidate进程不能读suite，五角色及独立运行证据对应。通过：实际运行的合法交接及访问拒绝证据齐全才更新2.2；失败：仅脚本/YAML存在或只通过公开容器probe即放行。当前连接器不提供建仓/Secrets操作，未有实际账户入口时保持blocked；不得将用户开发授权误报为缺批准。

- 整体技术准备及真实隔离检查通过后按既有授权持续实施；当前运行能力缺证持续blocked。不重复索批，不自动archive。
