# Proposal

## Why

仓库目前只能在会话中手动启动工作。需要让已有与新建Issue自动进入可恢复、可验证的工作流程，并继续遵循DDD、OpenSpec、Superpowers及直接提交main的既定规则。

## What Changes

- 增加Issue/评论/手动/定时补扫触发与维护者授权检查。
- 增加分流、输入指纹、审批令牌、状态记录与安全重试；机器人评论不自激活。
- 讨论与功能规划使用独立Codex会话执行两轮Battle及综合评审，再产出报告或OpenSpec工件。
- 实施需匹配当前计划的明确批准；缺陷修复在授权范围内可自动推进。
- 完成后执行校验，经独立发布步骤将合格变更直接提交main，不创建分支/PR，不自动archive。
- 提供无模型smoke链路与缺少密钥的明确阻塞反馈，分别报告控制链路与真实模型验证结果。

## Capabilities

### New Capabilities

- `issue-work-orchestration`: Issue分流、授权、恢复、真实Battle、审批、验证及发布。

### Modified Capabilities

无现有产品规格。

## Impact

新增GitHub Actions、Issue表单、确定性worker及测试、开发记录。模型任务依赖仓库Secret OPENAI_API_KEY；它不是网页会话登录。当前账号无密钥设置接口时，仅能通过实际Runner确认可用性，不能伪称模型链路已验证。
