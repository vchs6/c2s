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
