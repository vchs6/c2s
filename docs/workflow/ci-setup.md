# CI账户配置与验证

用户已授权配置；此处不再要求重复开发批准。现有GitHub连接器能写工作流并读回CI，不能创建私有仓库或操作Secrets；备用GitHub CLI已安装，但必须经账户所有者完成官方登录，不能从ChatGPT登录推导GitHub权限，不能制造模型API密钥。

## 仓库侧准备

`.github/workflows/isolation-readiness.yml`运行标准Ubuntu VM，以公开合成标记检查受限Docker容器只可读挂载的公共目录，不可读宿主标记。它不调用AI、不读私有suite，不是产品验收，也不能证明五角色或GitHub私有资产全部隔离。报告始终`development_ready=false`。

入口仅手动运行，或该workflow本身变更后的push基础设施诊断；不因Issue、评论、标签、定时开始开发。镜像先拉取，记录并按实际RepoDigest执行；容器禁网、非root、只读、drop all caps、no-new-privileges，无凭据或Docker socket挂载。公开artifact只含probe结果，不上传宿主文件或环境。

## 账户配置入口

`scripts/configure_ci.py`默认只列计划，不联网修改：

```bash
python3 scripts/configure_ci.py
```

有已认证GitHub CLI的可信终端才能实际应用：

```bash
gh auth login --hostname github.com --git-protocol https --web --scopes repo,workflow
python3 scripts/configure_ci.py --apply
```

默认源仓库`vchs6/c2s`，私有验收仓库`vchs6/c2s-acceptance`。脚本核实或新建验收仓库并拒绝同名公开仓库，设置源仓库`ACCEPTANCE_REPOSITORY`及验收仓库`SOURCE_REPOSITORY`变量；使用最小Actions默认权限并核对。它不创建宽权限跨仓库token、不自动改源仓库可见性、不改变组织Actions允许策略。

若需要配置新的模型API密钥，使用可信终端的安全交互输入：

```bash
python3 scripts/configure_ci.py --apply --set-model-key
```

值经getpass及stdin传给gh，不进入argv、计划、日志或Git。该选项会设置两仓库的`OPENAI_API_KEY`；不使用该选项则保留已有配置，不冒称已设置或已验证。GitHub不能读回Secret明文，所以不能自动把源仓库现有值复制到验收仓库；不要把密钥贴进聊天。

当前云端备用CLI在`.local/gh-cli/gh_2.103.3_linux_amd64/bin/gh`，独立配置目录`.local/gh-config`，均不提交；若在此环境调用需设置PATH与GH_CONFIG_DIR，而不是复制/输出认证文件。安装源GitHub cli/cli官方release v2.103.3，归档SHA256为4c806978ffce1cec70853302a56d70ac6da4f19bae7adca4e1a8ab00633dd91d，已核验。

## 不能混同的状态

账户bootstrap、公开容器probe、完整私有角色隔离、模型凭据可用、产品编排及验收分别验证。账户配置脚本成功也不等于开发已就绪。

完整3.2还需要：编码job处于没有验收仓库/日志/制品/管理API权限的上下文；可信私有harness与candidate进程分离；suite仅独立作者可写、执行者只执行、验证者只裁决；受控结果按版本交接。不能把私有suite作为编码job可下载的同运行artifact。配置/验证未实际完成不更新2.2/2.3为通过，不开始共享区隐藏测试。

## 设备授权成功但CLI未登录时

2026-11-02用户报告GitHub网页显示“Congratulations, you're all set!”；恢复登录进程时，执行工具实际返回`Network access to "https://api.github.com:443" was blocked by policy.`，随后独立`gh auth status`仍未登录。网页授权和当前CLI凭据保存不是同一结果；不能继续把阻塞只归因于用户未授权。

先恢复执行环境对`api.github.com:443`的合规网络访问，并保留设备登录所需`github.com:443`；不通过替代域名、代理或关闭限制绕过策略。在网络未修复前不继续生成设备码。当前工具不提供网络策略修改接口；用户也可在能访问GitHub的可信本地终端按上文登录并执行已提交的bootstrap脚本。不要发送/提交令牌、设备授权状态或密钥，不能从已结束进程回收认证秘密。

只有实际`gh auth status`通过后再执行--apply及API读回；bootstrap成功仍不等于完整角色隔离或模型可用。

## 用户本地bootstrap完成后的接续

用户已提供status=account_bootstrap_applied、bootstrap_configured=true回执，连接器已独立读回私有验收仓库。此前云端CLI网络阻塞仅保留为历史诊断；不能再要求用户重做已完成的账户基础配置。使用现有连接器部署不含suite的认证workflow，并读取实际托管结果；模板见ci/acceptance/credential-check.yml。model_key_set=false只表示该次脚本未写Secret，不是不存在的证据。认证GET成功也不证明生成模型/账单可用或完整隔离；后续仍按原门禁验证。

短推理健康检查已实际返回HTTP429/credit_balance_exhausted，证明密钥可认证不等于有推理额度。当前需账户所有者在该密钥所属OpenAI组织恢复可用API余额；不重建密钥、不自动改预算或反复重试。细分code依据官方https://developers.openai.com/api/docs/guides/error-codes。恢复后重跑inference-check，再继续模型角色工具/交接门禁，不重复基础账户配置。开发模型按docs/workflow/agent-governance.md路由，探针固定模型不是全任务模型选择。

恢复不只有充值一路：当前API路径余额不足属实；Codex的ChatGPT订阅认证是可选执行入口。API余额恢复、符合资格时领取API赠送额度、或重新部署订阅认证的受信执行入口，均需各自验证；不能将“需恢复API余额”误写成所有开发方式的硬要求。当前没有替用户选择付款/改计费或迁移订阅认证。

## Codex以ChatGPT订阅登录

在实际执行模型任务的可信终端先运行`codex login status`。若已显示Logged in using ChatGPT，不重复登录；若未登录，运行`codex login`并在浏览器选择ChatGPT账户登录。若现为API-key登录且明确要切换，先logout再login。对无人值守设备，官方另支持设备码登录，但应先核网络/账户权限，不循环生成设备码。登录配置只作用于该执行环境，不自动迁移到GitHub托管runner；已有OPENAI_API_KEY Secret不变成ChatGPT密码或订阅认证。

当前云端CLI0.166.0实际login status为Logged in using ChatGPT；移除仅子进程的API-key环境并以read-only/ephemeral运行仅回复OK的60秒健康检查超时，故只证明已登录，不证明可完成推理或已建立角色隔离。证据subscription-login-check.json；不修改/导出认证文件，不将宿主会话复制进CI。

本项目建议的备选是Codex订阅登录承担模型工作、GitHub CI继续做确定性检查；若确需私有CI账户认证，须按官方受信私有环境指南管理安全凭据与刷新，并实际验证角色边界，不能向公开/开源workflow放账户认证缓存。当前该迁移未部署。官方依据https://learn.chatgpt.com/docs/auth及https://learn.chatgpt.com/docs/non-interactive-mode。

## 订阅CLI超时诊断接续

2026-11-02已使用systematic-debugging及OpenAI Docs做有界复现。早期--ignore-user-config探针会忽略当前受管服务入口，不作为唯一网络判断；后续保留配置、read-only/ephemeral、明确输入EOF/模型，且仅为无工具健康检查禁用缺令牌的可选cua_repl及apps、关闭无界连接重试，仍未输出CLI thread.started。受管代理下模型目录实际HTTP200、Responses WS握手101；本地DNS失败不能据此推导代理转发失败。INFO启动轨迹停留thread/start/session_init，尚未定位具体未返回子步骤，未观察到生成请求；不是已证明的模型生成慢或订阅额度不足。

当前resolved=false。未增加超时掩盖问题，未修改全局配置/代理/证书/安全策略，未重登/导出认证、未继续无界重试。应在实际独立受信执行端先运行`codex doctor --network-only --summary`及最小`codex exec --json --sandbox read-only "只回复OK，不读取文件或执行命令"`，按其真实日志核对；若成功才采用该端，若同样卡初始化再交平台维护方核查。不要将当前云端特有cua_repl警告套用到用户本地，也不把订阅登录成功当完整流水线通过。脱敏证据见subscription-timeout-diagnosis.json，原始运行日志/认证不提交。
