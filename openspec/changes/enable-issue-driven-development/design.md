# Design

## Context

见proposal。仓库已有Node工具、OpenSpec与Superpowers固定源；使用GitHub Actions事件承载自动执行，网页会话不作为常驻Runner。当前存在初始化CI成功记录，未假定模型Secret存在。

## Goals / Non-Goals

**Goals:** 单仓库串行调度、内容级判重、维护者授权、两轮独立Battle、计划绑定批准、可信发布及smoke可行性测试。
**Non-Goals:** 不构建外部常驻服务、不转移网页OAuth令牌、不创建PR/开发分支、不为缺失密钥模拟AI成功。

## Decisions

- 定时15分钟补扫、事件与手动触发均读取全部open Issue，一次处理一个可执行项。GitHub concurrency可能合并pending唤醒，持久Issue列表及定时补扫避免任务依赖每个事件独立存活。
- Python 3确定性worker负责类型、授权、指纹、批准、输出边界及状态；模型不控制token权限和最终git ref。状态写入docs/development/issues/<number>/state.json，评审记录在docs/development/reviews/issues/<number>/。
- Battle使用5个独立Codex调用：首轮双方、第二轮双方、独立评审；它们是Actions独立会话，不依赖单次exec是否暴露子代理工具。第6个调用按评审形成报告或规划。调用通过Python编排多个独立`codex exec --ephemeral`进程，使用固定CLI、只读/工作区sandbox及独立提示上下文；不复用会话，不在单个会话模拟角色。采用CLI避免重复codex-action drop-sudo限制；进程共享检出与来源资料，不宣称操作系统级隔离。
- 模型只在contents:read的job运行；发布job不接收模型API Key、不执行补丁中的代码。发布采用基线SHA检查和普通git push；内容过时或分支保护失败均阻塞，不force。
- 主体Issue指纹来自number/title/body，规划批准令牌同时绑定生成工件摘要。命令仅接受维护者发布的精确/c2s approve <token>或/c2s retry。输入变化取消旧批准。
- 失败默认不无界重试；缺密钥后配置密钥可由补扫恢复，其他失败需retry或Issue输入变化。机器人反馈不进入输入指纹。
- smoke只运行仓库确定性验证并提交报告，状态明确smoke，不冒充AI/真实Battle。

## Risks / Trade-offs

- [Risk] 当前无Secret设置权限 → 配置与控制链路可测试；真实模型阶段必须按Runner结果报告未验证/阻塞。
- [Risk] 并行人工提交或Issue编辑 → 发布前重新检查main与输入，过时拒绝。
- [Risk] 模型改动代理/执行权限 → 发布边界拒绝自动修改workflow、脚本、代理规则和认证相关路径；此类维护需人工处理。
- [Risk] 计划状态与Issue呈现不同步 → 仓库状态是执行依据；main拒绝提交时，以github-actions[bot]评论中带指纹的publication-failed状态作为失败守卫，后续补扫要求retry。后续补扫同步标签，失败反馈不作为成功证据。main与Issue同时不可写时只能报告Actions失败，不能保证守卫已保存。

## 用户新增约束与执行记录
用户明确要求全部脚本使用Python 3。自维护worker、校验、插件安装和unittest采用Python标准库；第三方CLI继续由npm锁定。
执行调整：使用独立ephemeral Codex CLI进程而非每角色一个Action job，保持独立会话与首轮信息隔离，减少工作流复杂度；模型与可信发布仍分job。此为实现选择，不冒称用户指定。
