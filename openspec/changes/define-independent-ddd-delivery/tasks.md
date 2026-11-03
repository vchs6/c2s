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

- [x] 2.1.1 完成M1所消费的公共契约设计切片细化与独立交叉审查（2.1的有限子步，不勾父门禁）。依据：原2.1、已确认语义基线和ADR-0009；交付：九个原change的M1 design/tasks、26单owner记录/25稳定子ID及docs/development/reviews/independent-delivery/m1-contract-readiness-2026-11-02证据。验证：独立审查F1–F4修正后PASS；所选Cargo/Flit声明成功路径公开运行与源不变实证已补。通过范围：项目发现/列表、语言声明、原生workspace成员的字段/端口闭合，M2–M4未消费内容不作本切片前置；未创建Schema/产品/私有suite。父2.1还需真实运行入口/交付版本绑定及准备范围实证，不以此设计审查冒整体技术就绪。

- [ ] 2.2 按ADR-0009既有授权建立并验证独立执行环境。依据：测试不可见和五角色独立，design §2–3。交付：`docs/development/reviews/independent-delivery/isolation-readiness.md`公开脱敏就绪结论；私有环境留存实际身份/权限/设施/运行命令与访问检查证据，不把凭据或suite路径暴露产品库。验证：编码身份及candidate身份对suite、日志、历史/API、挂载、进程和管理接口的读写被拒，合法交接可执行；runner及最终验证身份不同。通过：具体私有suite根、制品交接接口和runner命令已绑定且证据可复核；失败：仅分支/目录/角色提示隔离、共享全权token或candidate进程可读suite。未通过不得编写隐藏用例，当前因执行环境能力blocked；必要设施准备已获用户授权，但不得捏造当前未具备的部署管理能力或泄漏凭据。

- [x] 2.2.2 验证原生平级公开协作准备（2.2有限子步）。依据：用户2026-11-03要求尝试平级方案、design“平级执行准备接续”、ADR-0009及independent-delivery。交付：`scripts/check_public_environment.py`、README公开启动步骤、维护CI调用、自检与原生分派/独立审阅脱敏记录。角色：原生公开基础设施探测、实现、审阅由不同上下文承担，不冒正式权限隔离。接口：自检stdout JSON，Python>=3.11、Node ^22.13.0 || >=24、npm/Git/本地OpenSpec可用，每次外部调用<=10秒；只探测Docker/Podman命令存在性，不启动CLI模型/容器、不安装依赖、不读认证、不改策略。验证：实际自检、不同cwd执行、失败分类与门禁false、原生代理返回、独立源码审核、严格OpenSpec及适用维护检查；通过：无嵌套Codex即可运行公开准备流程，Docker缺失不误报必需工具失败，报告准确区分公开工具和真实角色权限；失败：创建隐藏suite、继承管理权限冒编码隔离、把旧CI证据记成本次通过。父2.2/2.3/3.2保持未完成。

- [x] 2.2.3 搭建独立角色Git仓库并实测访问边界（公开实验，不放行父门禁）。依据：用户明确选择主代理白名单同步、角色只可访问自身仓库，design“主代理同步独立角色仓库”及independent-delivery。交付：`scripts/prepare_role_repositories.py`、README用法及`docs/development/reviews/independent-delivery/role-repositories-2026-11-03/`公开报告；运行生成仓库只留本地。接口：主代理指定source/ref/new destination，ref一次解析固定SHA，白名单regular blobs快照到五个独立main/root commit仓库，无remote/alternates/源历史；ROLE_INPUT及MANIFEST绑定源SHA、内容摘要、角色提交，author无candidate。验证：独立仓库/白名单/摘要/工作区未提交内容排除/目标拒绝覆盖，实际原生coding探针合法读取自身及尝试公开合成author marker的相对路径/绝对路径/Git读取，记录实际允许/拒绝、独立审核及严格校验。通过范围：实验搭建和可信证据齐全，能回答是否达到权限要求；若越权读取成功，必须明确权限验收failed并保持父2.2/2.3/3.2未完成，不创建真实隐藏suite或产品，不以提示词/分仓库冒权限隔离。不得读取认证、真实私有用例或原始日志，不提权、不修改安全策略、不启动嵌套Codex。

- [x] 2.2.4 实跑CI平级角色仓库边界公开probe（有限证据，不放行完整门禁）。依据：用户选择测试CI方式、design“CI角色仓库执行边界实测”及五角色隔离需求。交付：`ci/acceptance/role_repository_probe.py`、现有private-access-check workflow五角色独立job及公开脱敏报告。验证：源token源repo200且指定私有验收元数据/历史/workflows/runs/artifacts拒绝；五role的独立job使用固定SHA公开快照和image digest，仅挂/repo，合法自身读写、相邻/容器绝对/宿主绝对禁止marker读取及其他目录写入被拒，Docker socket/凭据无继承，宿主标记不变；实际远端run及job结果与提交绑定，独立公开审核、严格校验。通过：所有该有限检查实际通过；失败/超时/缺文件正控/未运行不得勾；无模型请求或真实隐藏suite，native_subagent_scoping_verified/full_role_delivery_ready/development_ready始终false，父2.2/2.3/3.2保留。脚本是可信CI探针，不是开放的任意候选启动入口，不授予角色Docker权限。

- [ ] 2.3 在ADR-0009授权下且2.1/2.2通过后接通连续交接和版本门禁。依据：授权内持续推进、product-versioning及design §3/5/6。交付：`docs/development/reviews/independent-delivery/handoff-verification.md`公开脱敏结论；私有run/verdict/制品清单由各独立角色所有。验证：用真实candidate/suite/源/环境版本执行交接并核查失效/重验，失配拒绝推进；失败反馈仅公开契约诊断，版本0.b.c对应被接受candidate。通过：独立角色无越权改写、可续同一批准范围且不触发新Issue、不自动归档；失败：旧证据沿用、runner兼最终验证、隐藏内容泄漏或未部署却声称后台持续运行。各产品验收只勾选原任务，本任务不重复实现它们。

## 3. CI配置接续（用户已明确要求配置，账户能力不足时如实阻塞）

- [x] 3.1 交付仓库侧CI容器边界检查和安全账户配置入口。依据：用户要求完成GitHub托管Runner/私有验收仓库/凭据配置，ADR-0008/0009及本设计隔离约束。交付：`.github/workflows/isolation-readiness.yml`、`scripts/configure_ci.py`、`docs/workflow/ci-setup.md`。接口：脚本默认dry-run，--apply需本地gh已认证；创建/核实私有验收仓库、设置仓库变量和最小Actions默认权限，API密钥只通过安全输入及stdin交gh，不输出/提交凭据。CI仅执行公开合成标记的容器访问检查（非隐藏验收），不加载私有suite/调用模型；允许push仅在该workflow变更时运行此基础设施诊断，不触发产品开发或Issue扫描。验证：独立实现/代码审阅、脚本help/dry-run/无凭据拒绝、既有维护检查及实际GitHub托管CI结果。通过：候选容器只挂公共目录、无网络/凭据/Docker管理接口，宿主私有标记不可读，宿主可合法读取；报告镜像摘要及探测结果且development_ready=false。失败：把标记诊断冒完整五角色就绪、账户配置未执行却称完成、泄漏密钥或默认live修改。实际证据：`docs/development/reviews/independent-delivery/ci-setup-2026-11-02/validation.json`，候选6283a23的托管probe及维护CI均success；3.2及整体就绪仍未完成。

- [ ] 3.2 完成账户端配置及完整角色边界验证。依赖：3.1及有权限的GitHub账户管理入口、实际模型凭据。交付：私有验收仓库、Secrets/变量/权限、受控交接入口和本地脱敏配置回执。验证：私有性确证，编码身份不能读验收仓库/日志/制品或改验收workflow，candidate进程不能读suite，五角色及独立运行证据对应。通过：实际运行的合法交接及访问拒绝证据齐全才更新2.2；失败：仅脚本/YAML存在或只通过公开容器probe即放行。当前连接器不提供建仓/Secrets操作，未有实际账户入口时保持blocked；不得将用户开发授权误报为缺批准。

- [x] 3.2.1 收录账户回执并运行私有Secret/API认证诊断（3.2的有限子步，不代表父任务完成）。依据：用户成功JSON、正式independent-delivery及design私有仓库接续。负责：协调者记录，独立基础设施实现者/审阅者处理模板，GitHub托管runner执行。输入：私有验收仓库、现有OPENAI_API_KEY；输出：ci/acceptance/credential-check.yml公开模板、私有仓库.github/workflows/credential-check.yml、脱敏结果记录。接口：无workflow输入；一次GET固定OpenAI /v1/models，结构化输出仅credential_present/authentication_passed/http_status/error/inference_tested=false/role_boundary_verified=false/development_ready=false。权限为空，无checkout/action/artifact，禁输出Secret/响应正文/模型列表，30秒网络超时，workflow job最多2分钟；缺失/401/403/网络错误exit非零并用固定安全类别；拒绝跨域重定向。触发仅自身变更push或显式dispatch，不监听Issue/定时，不发生成请求，不写业务用例。验证：YAML及嵌入Python语法、独立审阅、严格OpenSpec及实际私有CI。通过：该次API认证HTTP200且认证结果true；若失败保留未完成并报告具体类别；只交付模板不算运行通过。保持3.2/2.1/2.2/2.3未完成，不能把协调者admin连接器当编码身份隔离。

- [x] 3.2.2 运行六个受限容器身份及源token访问边界的公开合成诊断（3.2/2.2的证据子步，非产品验收）。依赖：账户回执、3.2.1模板；不依赖实际suite。负责：独立基础设施实现/审阅，托管runner执行。交付：ci/acceptance/role_sandbox.py、ci/acceptance/boundary-check.yml、.github/workflows/private-access-check.yml，脱敏结果。接口：run_role(root: Path, role: str, argv: list[str], image: str) -> CompletedProcess，受信协调者调用；--probe执行公开合成marker，无私有业务用例。角色coding、review、author、runner、verifier各唯一UID10001–10005，candidate UID10006；挂载矩阵写于design，无密钥/宿主配置/套接字挂载；禁网、只读根、drop all caps、no-new-privileges、pids32/memory128m/cpu1；镜像拉取后按实际RepoDigest执行、记录摘要。检查合法读取/独占输出写入、公用输入只读、各禁止文件读写、宿主路径/进程凭据/Docker socket不可达；host检查禁止区未被修改。源workflow用自身contents:read的GITHUB_TOKEN验证源repo200、私有验收repo及commits/workflows/runs/artifacts均403/404，仅输出状态和布尔值，容器不传token。私有workflow只下载并核验公开脚本的固定commit+SHA256，无checkout/第三方action/上传artifact；模版发布时显式替换两个公开占位符。验证：独立审阅、静态语法、实际两repo托管诊断；全部要求的访问拒绝和合法访问通过才勾本子步，报告仍development_ready=false、synthetic_only=true。完整模型角色编排、suite/handoff生产化未部署，不勾父任务/2.2/2.3，不把当前协调会话当受限编码身份。

- [ ] 3.2.3 运行一次有界模型推理健康检查（非产品/隐藏用例）。依赖：3.2.1通过。交付：ci/acceptance/inference-check.yml模板、私有.github/workflows/inference-check.yml、脱敏证据。技术选择：固定gpt-5-mini，POST https://api.openai.com/v1/responses一次，store=false、reasoning.effort=low、max_output_tokens=256，公开输入只要求返回OK；无重试、无工具、无仓库数据，网络超时45秒、job2分钟。权限为空、仅自身路径push/显式dispatch，Secret仅runner step环境；禁checkout/action/artifact、密钥/响应正文/原始异常输出。结果仅credential_present/http_status/response_status/answer_ok/error、usage(input_tokens/output_tokens/total_tokens可null)、inference_passed/role_boundary_verified=false/development_ready=false；固定模型名可记录。HTTP200 completed且输出去空白为OK才通过；401/403/429/余额不足/无模型权限/不完整输出分别安全分类，不冒称都缺密钥。验证：语法/独立审阅及实际私有CI；本次调用有实际API Token消耗，记录真实usage，不当语义提取Token指标；失败按类别报告，不自动改密钥/预算或持续重试。父任务/完整编排仍待验证。

- 整体技术准备及真实隔离检查通过后按既有授权持续实施；当前运行能力缺证持续blocked。不重复索批，不自动archive。

## 当前模式接续：ADR-0010

- [ ] 2.2.5 搭建双向盲开发的确定性CI环境并实跑公开验证。依据：ADR-0010 U01/U02、independent-delivery“测试作者对候选实现保持独立”“按信息边界分工执行”。依赖：已完成2.2.3/2.2.4；负责：公开基础设施实现、独立审阅、固定CI执行。输入：固定源SHA的公共快照/合成marker；输出：`ci/acceptance/blind_delivery_probe.py`及对应workflow、`docs/workflow/blind-development.md`、脱敏执行证据。步骤：定义双向输入矩阵；复用受限coding/author worker；以固定脚本验证同契约交接与失配拒绝；实跑CI并绑定SHA/结果；独立审查及严格校验。通过：双方合法输入正控和禁止读取负控、版本失配拒绝、确定性公开执行真实通过，报告synthetic_only且无模型调用；失败/未运行保持未完成。无产品/真实隐藏suite；本子步不自动勾2.2/2.3。

当前2.2/3.2的权限验收按ADR-0010聚焦coding与author双向不可见及必要管理旁路，其他角色按职责授权，不再要求五方全部互盲。2.3仍需真实产出的固定版本交接及独立结论；无需测试执行/安装job调用模型。API健康检查3.2.3仅阻塞该API模型入口，不阻塞无需AI的CI；不要求为已可用的其他合法编写入口恢复API余额。
