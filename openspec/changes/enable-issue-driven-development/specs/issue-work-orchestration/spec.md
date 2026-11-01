# Spec Delta

## Purpose

为c2s提供受维护者授权、可恢复并有实际验证记录的Issue自动工作能力，协调OpenSpec与Superpowers完成讨论、规划及实施，明确自动执行与用户批准的边界，并直接提交合格结果到main。

## ADDED Requirements

### Requirement: 持久待办与事件补扫
系统 SHALL 在Issue新建、编辑、重开、标签及有效人工命令后唤醒，并通过定时与手动补扫处理已有未完成Issue；原始事件只作为唤醒信号。

#### Scenario: 持久待办与事件补扫的验收
- **WHEN** 多个事件被合并或既有Issue没有新事件
- **THEN** 扫描未完成事项，不以单次事件丢失作为完成。

### Requirement: 维护者授权与输入隔离
系统 MUST 仅处理仓库owner或具有write/maintain/admin权限的人员创建的Issue；批准和重试命令也必须检查权限；PR评论、机器人评论和陌生用户不能授权执行。

#### Scenario: 维护者授权与输入隔离的验收
- **WHEN** 公共仓库出现未授权Issue或机器人反馈
- **THEN** 跳过模型和main写入，不由Issue正文扩大权限。

### Requirement: 工作类型分流
系统 SHALL 区分discuss、feature、implement、bug、smoke；未知类型按discuss处理。discuss形成报告，feature/implement先规划，bug执行明确修复；smoke仅验证控制链路。

#### Scenario: 工作类型分流的验收
- **WHEN** 示例Issue声明为smoke
- **THEN** 运行确定性验证并明确标记未调用模型，不伪称Battle或产品修复。

### Requirement: 独立Battle与批准边界
系统 SHALL 对讨论和功能规划通过独立Codex会话执行双方首轮、交叉第二轮、独立评审，再形成报告/工件；规划不能直接变更产品实现。

#### Scenario: 独立Battle与批准边界的验收
- **WHEN** 功能规划完成但尚未批准
- **THEN** 保留awaiting-decision和与当前输入及规划工件哈希关联的批准令牌。

### Requirement: 批准绑定当前工件
系统 MUST 仅在维护者评论/c2s approve加当前令牌且输入、规划工件未变化时开始实施；旧批准不得复用。

#### Scenario: 批准绑定当前工件的验收
- **WHEN** Issue正文或规划文件发生变化
- **THEN** 使旧批准失效并重新规划，不执行旧计划。

### Requirement: 幂等与恢复
系统 SHALL 使用内容指纹而非机器人引起的updated_at判重；完成指纹不重复执行；显式retry可恢复失败；取消前未发布的工作可重扫。

#### Scenario: 幂等与恢复的验收
- **WHEN** 同一Issue重复label事件或机器人评论
- **THEN** 不重复模型调用与提交。

### Requirement: 验证与发布
系统 MUST 在执行环境验证生成结果，检查输出边界和补丁；发布job只使用可信基线代码处理补丁，直接提交main且不force，不创建分支或PR，不自动archive。

#### Scenario: 验证与发布的验收
- **WHEN** 远程main变化、Issue输入变化或验证失败
- **THEN** 不把旧补丁发布为完成，记录阻塞并允许恢复。

### Requirement: 缺少凭据的可观察阻塞
系统 SHALL 在模型密钥缺失时保留blocked原因和Issue反馈，且不启动模型；控制链路测试与模型测试结果必须分开。

#### Scenario: 缺少凭据的可观察阻塞的验收
- **WHEN** OPENAI_API_KEY没有配置
- **THEN** 任务为blocked/missing-model-key，不能报告已完成真实模型工作。

#### Scenario: 主分支拒绝发布
- **WHEN** main保护或推送错误拒绝状态提交但Issue仍可写
- **THEN** 以受信任机器人评论保存当前指纹的publication-failed守卫，阻止自动重复模型消费并要求retry；双重写入均失败时以Actions失败明确报告持久化限制
