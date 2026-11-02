# Independent DDD Delivery Implementation Plan

> **For agentic workers:** 后续获批执行时使用superpowers:subagent-driven-development或superpowers:executing-plans，并遵守本设计五角色隔离；默认编码者写测试的示例不适用。本文件只拥有交付治理任务，各产品任务仍唯一归属原change。

**Goal:** 固化独立交付约束与里程碑，准备有证据的连续执行门禁。

**Architecture:** 公开DDD契约指导独立实现及私有验收；受控工件交接，由独立验证者裁决。

**Tech Stack:** 现有OpenSpec/Superpowers；自维护脚本Python 3。隔离运行器尚未部署，本轮只写Markdown/JSON/YAML规划。

**Spec:** 本change两份specs、design.md及ADR-0008。

## Global Constraints

本轮仅1组规划；2组为未来前置任务，不在本轮执行。产品实施另批、不归档、不安装依赖、不改CI/凭据、不写实际测试，不改变既有语义基线。五角色独立，编码者不写/读suite；当前0.b.c，无版本修改。

## Review Focus

共享token与candidate间接读取suite；公开契约不足却靠泄露隐藏断言修复；旧candidate/suite运行证据被复用；Issue事件或里程碑通过绕过开发门禁；按Token指标省略语义。分别由2.1契约核对、2.2访问反证、2.3证据绑定及各原产品任务独立验收覆盖；本轮不编写这些用例。

## 1. 本轮规划交付

- [x] 1.1 固化需求、流程设计与里程碑索引。依据：本能力四项Requirement、版本约束及ADR-0008。交付：本change proposal/specs/design、两份主规格、ADR-0008、`docs/planning/program-2026-11-01/milestones.md`、既有tasks角色修订及协作规则。验证：真实双方两轮Battle及新reviewer，逐要求/里程碑/任务引用自审。通过：用户确认/代理设计/候选清楚，既有产品待办均未勾选，索引无第二套产品计划；失败：越界实现、角色冒充权限或重开已确认需求。

- [x] 1.2 核验并发布规划证据。依赖：1.1。依据：verification-before-completion及#4/#13整体一致性。交付：本评审目录`validation.md`、`tool-evidence.json`、更新集合manifest及Issue #4/#13回复。验证：`npm run validate`全库严格校验、`npm run check:artifacts`、`git diff --check`、摘要重算及路径/任务状态审计；发布后读回main及回复。通过：实际证据对应版本，设计not-frozen、implementation_approved=false、isolation_ready=false；失败：未检查即声称完成、过期摘要或把规格校验当运行测试。

## 2. 后续就绪门禁（本轮不执行）

- [ ] 2.1 完成M0公开契约与任务绑定的就绪审查。依据：五角色独立/真实项目验收、既有语义主规格及design §4–6。交付：原#3/#6/#7/#8/#9/#10/#5/#11/#12各design/tasks中的精确输入输出类型、边界、交付路径和受控验收入口；`docs/planning/program-2026-11-01/readiness.md`只登记绑定的版本/任务引用，不复制待办。验证：交叉契约消费/产出一致、真实项目固定源可追溯、host/target和非功能计量方案齐全；显式整体审查后冻结新集合摘要。通过：原任务不再依赖未定义接口、发布载体/版本映射明确，可供独立角色执行；失败：TBD接口、旧单Issue令牌或文件存在代替开发批准。此任务是后续技术规划，不执行产品代码；冻结后仍须用户单独批准实施。

- [ ] 2.2 在另行批准实施后建立并验证独立执行环境。依据：测试不可见和五角色独立，design §2–3。交付：`docs/development/reviews/independent-delivery/isolation-readiness.md`公开脱敏就绪结论；私有环境留存实际身份/权限/设施/运行命令与访问检查证据，不把凭据或suite路径暴露产品库。验证：编码身份及candidate身份对suite、日志、历史/API、挂载、进程和管理接口的读写被拒，合法交接可执行；runner及最终验证身份不同。通过：具体私有suite根、制品交接接口和runner命令已绑定且证据可复核；失败：仅分支/目录/角色提示隔离、共享全权token或candidate进程可读suite。未通过不得编写隐藏用例，当前blocked；本任务不自行授权开设施/凭据/CI。

- [ ] 2.3 在另行批准实施及2.1/2.2通过后接通连续交接和版本门禁。依据：授权内持续推进、product-versioning及design §3/5/6。交付：`docs/development/reviews/independent-delivery/handoff-verification.md`公开脱敏结论；私有run/verdict/制品清单由各独立角色所有。验证：用真实candidate/suite/源/环境版本执行交接并核查失效/重验，失配拒绝推进；失败反馈仅公开契约诊断，版本0.b.c对应被接受candidate。通过：独立角色无越权改写、可续同一批准范围且不触发新Issue、不自动归档；失败：旧证据沿用、runner兼最终验证、隐藏内容泄漏或未部署却声称后台持续运行。各产品验收只勾选原任务，本任务不重复实现它们。

## Workflow follow-up

- 本轮规划提交后等待整体技术规划审核和独立实施批准，不自动apply/archive。未来运行环境缺证持续blocked。
