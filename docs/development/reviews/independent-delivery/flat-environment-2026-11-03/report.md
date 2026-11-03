# 平级公开开发环境准备记录

用户确认依据：2026-11-03明确要求尝试平级方案；沿用ADR-0009授权及原交付change 2.2.2。正式语义规格、五角色独立、测试对编码者不可见不变。未要求迁移仓库、升级GitLab、重复登录、API充值或放宽系统策略。

## 本次实际完成

原生任务分派、公开能力探测、独立边界分析及公开自检实现均已在当前会话工作，无嵌套Codex，无bwrap/unshare尝试，无Docker安装或执行。公开入口：`python3 scripts/check_public_environment.py`。它只检查Python>=3.11、Node ^22.13.0 || >=24、npm、Git、本地OpenSpec版本；命令固定、shell=False、每次10秒超时，不读取认证和宿主会话。可选运行器只检查命令存在性，不因缺Docker阻塞公开工具。维护CI在npm ci后复用该入口，不调用模型或自动扫描Issue。

实际工具：Python3.12.14、Node24.22.1、npm11.9.0、Git2.51.1、OpenSpec1.16.0；Docker/Podman命令不存在，public_tools_ready仍true。跨cwd=/tmp真实成功；仅子进程PATH=/nonexistent的真实故障注入返回missing和exit1，所有完整门禁flags保持false。实现者还检查了10秒超时参数和超时分类（模拟异常，不冒实际挂起计时）。严格OpenSpec21/21、维护测试31/31、四项原件摘要/workflow/Superpowers检查、脚本AST通过；diff及集合摘要另在发布前核验。只验证当前Linux，不外推Windows/macOS。

## 仍未完成

原生子代理仍共享文件和连接器权限，本轮工作者是公开基础设施角色，不是正式隔离编码者。独立作者/runner/verifier身份、候选进程拒读suite、受控反馈、不可变工件交接及失效重验尚未接通。原有Docker六角色合成底座可在受信runner直接复用，但本轮未重新运行该容器probe，不把历史成功记为本次通过。当前工具没有workflow_dispatch接口；不通过修改无关workflow强迫其运行。

2.2/2.3/3.2保持未完成。没有产品代码、Schema、隐藏suite、私有原始日志、发行版本或归档；development_ready/readiness_complete/isolation_ready/implementation_started均false。原生分派返回只证明当前公开模型协作路径能运行，不替代有效权限证据。

## Skill与角色记录

using-superpowers建立入口纪律；brainstorming沿用用户选择的平级方向并限定公开spike；writing-plans维护原tasks唯一子步；dispatching-parallel-agents分别探测运行时与审查边界；subagent-driven-development分离公开自检实现及独立审查；verification-before-completion按实际命令记录通过范围。模型请求按任务配置：公开探测/实现sol medium，权限边界及整体审核astra high；实际返回模型/Token不可核实，记unknown/null。没有安装新Skill或依赖。独立审查报告随本目录保存，不能把公共基础设施审核当产品最终验证。
