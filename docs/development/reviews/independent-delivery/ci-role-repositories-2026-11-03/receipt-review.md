# 新增公开 CI 回执有限复核

日期：2026-11-03。结论：**PASS，仅限 task 2.2.4 的公开固定 CI 边界证据**；未发现阻断该有限任务完成的回执不一致。不能据此完成父任务 2.2、2.3、3.2，不能启动依赖完整隔离的产品实现或隐藏 suite。

本轮 taskType=有限公开CI证据核对；角色=独立回执复核；modelRequested=sol；reasoningEffort=high；modelReturned=unknown；usage=null。原独立源码审核已通过，补核续轮曾遇到 model at capacity；本轮只接续机械证据核查，不重做源码审核。

## 范围和方法

只读根 AGENTS、README、相关治理/仓库/CI 文档、原 `.local/ci-role-repositories-2026-11-03/review.md`、本地公开 `ci-receipt.json`、本轮公开 `evidence.json`/`report.md`，以及既有公开 native 反例。通过一次本地 Python JSON 解析及字段/类型/一致性断言核对回执，退出码 0；通过 Git 只读对象逐字节比较确认原 role-repositories 反例目录的已跟踪文件与 HEAD 一致。

没有访问连接器、凭据或私有数据，没有网络请求，没有发起 CI、Docker、Codex、模型子请求或其他测试；没有修改实现、原始证据或任务状态。没有重复 AST/help、缺 Docker、OpenSpec、维护测试或源码权限审查。所核对的是已经提供的公开 JSON 快照，本轮未重新向远端证明其当前状态或重放容器。

## 回执核对结果

- Run `41565989028` 为 completed/success，head 为 `1b2dfa06f3dcac3868c2707570c2a80d9c17d98a`。回执与公开 evidence 的 run id/head/url/status/conclusion 相同。
- 7 个 job 的 id 唯一，全部 completed/success；两个公共 job 与 coding/review/author/runner/verifier 五个角色 job 齐全。每个角色唯一且与其 job 名称/id 对应，公开 evidence 的 5 个 role_reports 与回执逐字段相同。
- 每个角色 worker_checks 恰为指定 15 项，值类型均为 bool，全部严格为 true；合计 75/75。三个宿主字段 host_controls_passed、host_output_control_passed、host_repositories_unchanged 每角色均严格为 true，合计 15/15。
- 每角色 source_commit 均等于 run head；image_digest 均符合 `python@sha256:[0-9a-f]{64}`，且五角色及两份 JSON 值一致：`python@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30`。
- 每角色 container_repo_boundary_passed=true、synthetic_only=true、job_workspace_scope=separate-ci-job、status=synthetic_probe_passed。
- private_api 与公开 evidence 完全相同：source_status=200、source_read_allowed=true；repository/commits/workflows/runs/artifacts 五项实际状态全部 404，passed/private_reads_denied=true，synthetic_only=true。本轮没有 403，因此不触发原源码审核对 403 原因不明的证据限制。目标存在且 private 的既有协调者元数据记录仅作为原记录读取，本轮未重新访问或验证它。
- 每角色 native_subagent_scoping_verified/full_role_delivery_ready/development_ready 均为 false；evidence 顶层这些字段以及 readiness_complete/isolation_ready/implementation_started 均为 false；private_api.development_ready=false。report.md 同样明确保留完整门禁。

## 保留的反例与证据边界

原 `role-repositories-2026-11-03/` 已跟踪公开文件逐字节等于 HEAD；native_access_probe 中自身、相对 author、绝对 author、Git author marker 读取仍为 allowed，role_repository_isolation_passed=false。新增受限 CI worker 通过没有改写当前云端原生子代理共享权限的失败反例。

沿用原源码审核的范围限制：resource_limits=true 只覆盖 pids/memory/cpu 实读；memory-swap 仅为配置，不扩展成逐项实测。可信准备宿主的权限不等于角色 worker 权限；固定公开 probe 通过不证明模型身份隔离、模型工具 broker、真实私有 suite 交接、run/verdict 输出所有权、受控反馈或版本失效重验。

因此只支持将有限 task 2.2.4 的公开 CI 证据记为完成；父 2.2/2.3/3.2 及完整门禁继续未通过。本复核不执行任务勾选、提交或发布。

Skill 记录：读取 using-superpowers，其 SUBAGENT-STOP 明确允许已分派子代理忽略一般流程；按有限委托执行。实际应用 verification-before-completion 的“先读实际核对输出再作结论”，核查命令退出 0。未把 Skill 读取或既有测试记录冒充新测试执行。
