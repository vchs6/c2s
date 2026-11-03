# CI与连续执行边界

当前`.github/workflows/validate.yml`在push/PR运行维护测试、导入原件/工具检查、OpenSpec严格校验及diff检查。它不是产品验收或持续开发调度器；手动Issue worker仍只plan/smoke。

目标分三部分：公开CI跑确定性检查；独立私有验收区保存suite并经可信harness调用隔离candidate；协调器依原tasks和实际证据推进，不允许角色自批。candidate/suite/源/环境必须绑定，失败反馈脱敏。编码令牌不能读原始日志/制品、改私有验收workflow或管理权限。

当前本地身份/namespace/强制读取隔离检查未通过，连接器没有私有验收密钥/运行器的部署接口，不能只写一份YAML即宣称可用。需要具备实际隔离的执行设施及分别授权的角色入口后，验证跨角色拒绝访问和合法交接，才放行隐藏suite及产品流水线。

不把ChatGPT会话/网页登录自动当CI模型凭据；无密钥或权限时明确blocked，不复制或输出认证。用户已批准必要安装及准备后开发，无需再次请求相同批准；此处缺的是执行能力，不是重新确认需求。

账户bootstrap及公开容器探针接续见[ci-setup.md](ci-setup.md)。该探针不调用模型、不触发产品开发，始终报告development_ready=false；账户配置与完整五角色隔离分别验证。

当前接续：用户账户bootstrap成功回执已收录，连接器可向现有私有验收仓库部署workflow；旧无建仓/Secrets接口的限制不再阻塞此部署。私有credential诊断已实跑通过，Secret可见/API认证200；仍未证明推理/账单、完整角色工具入口或产品验收。原就绪任务继续，正式编码上下文不能使用协调者的admin连接器。

执行入口备选：当前直接Responses API诊断因credit_balance_exhausted受阻；并非项目要求只能使用API余额。可保留CI确定性校验，另用以ChatGPT登录的Codex本地/受信执行环境承担模型任务；官方也有仅适用受信私有runner的进阶账号认证方案。该备选当前未部署，认证来源/维护/隔离交接需实证，不复制当前宿主登录文件来冒已具备授权。依据https://learn.chatgpt.com/docs/auth与https://learn.chatgpt.com/docs/non-interactive-mode。符合资格的Pro/Business还可领取组织API赠送额度，但资格/支持用途须按官方说明核验，不承诺用户账户符合；该赠送额度不增加已登录Codex订阅限额，也不支持Codex API-key用量。https://developers.openai.com/api/docs/guides/chatgpt-api-credits。

平级接续（2026-11-03）：维护CI在`npm ci`后运行`python3 scripts/check_public_environment.py`，不调用嵌套Codex或模型，也不以Docker存在作为公开工具通过条件。原生代理用于公开基础设施协作；角色私有权限和candidate执行仍在独立设施验证。此入口的public_tools_ready不是完整开发门禁，不触发Issue开发、不创建suite、不自动归档。

角色仓库实验接续（2026-11-03）：维护CI用该运行的GITHUB_SHA调用`prepare_role_repositories.py`，在RUNNER_TEMP内创建五个公开Git快照，不访问私有测试项目、不调用模型、不授予角色身份。步骤成功只证明准备入口运行，不是“角色只能看自己仓库”的权限通过；当前原生访问实测FAIL见role-repositories报告。当前仅Linux实际验证，其他宿主平台未外推。

CI边界实测接续（2026-11-03）：private-access-check工作流保留源token私有API拒绝检查及既有六容器诊断，另加五个独立Ubuntu24.04角色job（最多并行3）。每job可信宿主生成公开快照，仅所选role仓库挂入非root worker；role_repository_probe.py使用固定image digest与有界只读/写公开marker检查，凭据和Docker socket不进入worker。模型认证、模型工具broker、实际私有role交接不属于此probe，完整门禁始终不因基础设施success自动通过。

## ADR-0010当前执行模式

双向独立编写＋确定性CI是当前模式，入口与输入矩阵见[blind-development.md](blind-development.md)。不要求所有五角色彼此互盲，也不要求AI参与每次构建/测试。历史完整五角色诊断不再扩大解释为用户硬性需求；实际coding/author权限、candidate拒读suite、受控反馈和真实版本交接仍需通过。模型调用只属于编写/判断入口，不能以API额度不足阻塞无模型CI。
