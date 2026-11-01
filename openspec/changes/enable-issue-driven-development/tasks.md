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
- [x] 3.1 更新规则和使用说明，严格校验、独立复核，提交main并创建一次明确的smoke Issue验证实际触发/状态/提交；检查模型凭据可用性。
  - 上游依据：用户配置并测试可行性的要求。
  - 交付物：docs/development中的流程、测试记录和远程run/commit链接。
  - 验证：npm test、npm run validate、check:artifacts、git diff --check及真实Actions日志。
  - 通过：控制链路实际成功，模型阶段成功或明确阻塞且不误报；失败：未运行却称完整端到端成功。

## Workflow follow-up
- 缺少仓库OPENAI_API_KEY时，真实模型链路保持blocked，用户配置Secret后恢复验证；不能传输网页OAuth令牌。
- 不创建PR或开发分支，不自动archive。

## 4. 外部凭据恢复后的实际模型验收
- [ ] 4.1 配置仓库OPENAI_API_KEY后，验证真实独立Battle及计划批准/apply端到端。
  - 上游依据：真实模型可行性不能由smoke或纯规则测试证明。
  - 交付物：docs/development/reviews中的实际会话、计划与实施验收记录。
  - 验证：Issue #2恢复后检查实际模型会话及报告，再以明确测试任务验证批准与apply。
  - 通过：真实模型调用、当前令牌批准及验证提交均有证据；失败/当前阻塞：仓库缺OPENAI_API_KEY，暂未调用模型。

## 5. 用户授权切换为手动规划模式

本组覆盖当前维护工具修正；1–3组为旧版历史验收。4.1的无人值守模型/apply验收暂缓，当前模式不再承诺该自动链路，也不以本组完成将其勾选。唯一执行计划为本文件。

- [x] 5.1 关闭自动事件并实现指定Issue的规划入口。依据：新规格前3项；交付：issue-worker.yml、Python入口/选择器/模型与发布守卫、test_manual_planning.py。验证：先运行新回归观察失败，再运行全量npm test；通过：事件/无编号/越权/apply全部拒绝、旧令牌不转apply、既有变更精确范围和摘要有效；失败：扫描其他Issue、触发模型或产品写入。
- [x] 5.2 更新治理、OpenSpec规则、工作流说明及表单。依据：新规格持续规划/指标/门禁；交付：AGENTS、config、planning-mode/issue-worker说明、README和表单。验证：核对功能/非功能/跨语言跨平台、委托裁决、主规格与候选、整体批准与实施分离；通过：与运行入口一致，无产品实现或归档；失败：旧自动触发/评论实施说明仍作为当前用法。
- [x] 5.3 验证、独立复核并先发布入口修正，再顺序创建规划Issue。依据：用户当前顺序要求与新规格追溯；交付：docs/development/reviews/manual-planning-switch.md、Git提交与规划议题清单。验证：npm test、check:artifacts、严格validate、diff检查、远程workflow与旧运行状态；通过：关闭自动入口后才创建事项，Issue含依赖/交付/验收且不启动；失败：先建Issue、模型或产品未运行却称已验证。
