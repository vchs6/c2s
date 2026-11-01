# Tasks

## 1. 确定性调度与授权
- [x] 1.1 先编写并观察失败测试，再实现类型、指纹、当前工件批准、维护者授权、重试和补丁边界；运行 `npm test`。
  - 上游依据：spec中的授权、分流、批准、幂等需求。
  - 交付物：scripts/issue_worker/core.py、tests/test_issue_worker.py。
  - 验证：未授权、机器人、旧批准、输入变化、缺密钥、补丁越界、重复事件反例。
  - 通过：全部反例测试通过；失败：错误执行、错误完成或泄漏权限。

## 2. Runner与真实Battle
- [x] 2.1 实现API适配、上下文/状态、独立会话Battle、验证和可信发布；运行worker测试及workflow结构检查。
  - 上游依据：独立Battle、验证与发布、恢复需求。
  - 交付物：worker CLI、Issue表单、issue-worker工作流、输出Schema。
  - 验证：独立ephemeral Codex CLI会话调用；只读模型job与有写权限发布job分离。
  - 通过：类型化上下文、当前SHA校验、普通main提交；失败：force、PR、伪造Battle或运行补丁中的发布脚本。

## 3. 运行验证与记录
- [ ] 3.1 更新规则和使用说明，严格校验、独立复核，提交main并创建一次明确的smoke Issue验证实际触发/状态/提交；检查模型凭据可用性。
  - 上游依据：用户配置并测试可行性的要求。
  - 交付物：docs/development中的流程、测试记录和远程run/commit链接。
  - 验证：npm test、npm run validate、check:artifacts、git diff --check及真实Actions日志。
  - 通过：控制链路实际成功，模型阶段成功或明确阻塞且不误报；失败：未运行却称完整端到端成功。

## Workflow follow-up
- 缺少仓库OPENAI_API_KEY时，真实模型链路保持blocked，用户配置Secret后恢复验证；不能传输网页OAuth令牌。
- 不创建PR或开发分支，不自动archive。
