# Issue 自动工作

Python 3脚本编排GitHub Actions，以OpenSpec和Superpowers处理Issue，合格结果直接提交main。无需PR或开发分支。脚本只依赖Python标准库；Runner使用Python 3.12。Node 22仅用于运行固定版本OpenSpec与Codex第三方CLI。上游子模块不属于自行维护的脚本。

## 使用

1. 在仓库Settings → Secrets and variables → Actions中设置`OPENAI_API_KEY`。使用有API调用额度的项目密钥；网页登录不能替代API凭据。密钥只注入模型job。
2. 确认Actions开启，允许工作流的`contents:write`、`issues:write`；main分支策略允许该自动提交。脚本不会绕过保护或force push。
3. 使用工作事项表单。只有仓库owner或write/maintain/admin成员创建的Issue进入自动执行。已有Issue无需搬迁，无类型正文默认讨论。
4. feature/implement形成计划后，查看`docs/development/reviews/issues/<N>/`及本Issue OpenSpec change，按机器人反馈评论`/c2s approve <24位令牌>`。输入或计划变动使旧批准失效。
5. 失败修复后评论`/c2s retry`。缺密钥会在配置后由补扫自动恢复。讨论报告保持awaiting-decision，后续实施可新建implement Issue引用报告。

| 类型 | 行为 | 终态 |
| --- | --- | --- |
| discuss | 两轮双方独立分析＋独立评审＋综合报告 | awaiting-decision |
| feature / implement | 同上，并形成OpenSpec proposal/specs/design/tasks | awaiting-decision；批准后apply |
| bug | OpenSpec和Superpowers诊断、TDD修复、独立代码审查 | completed或blocked |
| smoke | 仅运行确定性仓库校验 | completed或blocked；明确未调用模型 |

## 调度与真实会话

Issue事件唤醒、手动Actions运行及每15分钟补扫读取全部open Issue，按编号处理一个可执行项。仓库级concurrency串行化main写入；GitHub可能合并pending唤醒，后续补扫继续消费持久Issue列表。定时运行由GitHub尽力调度，不承诺15分钟内必达；闲置仓库可能需要手动重新开启定时工作流。

Battle由Python依次运行5个独立`codex exec --ephemeral`进程：首轮双方互不可见，第二轮交换首轮输出，第五个独立评审；第六个会话综合并写工件。它们共享检出资料，但无对话延续；不是一个提示词自演六个角色。前五个使用read-only sandbox，写工件会话使用workspace-write。apply另外启动独立代码审查。真实模型可行性须由实际Runner记录证明，smoke不能证明模型执行成功。

模型job不持有GitHub写凭据；发布job不接收模型密钥，不执行生成代码，用可信基线脚本验证补丁路径/文件模式、当前main及Issue指纹，再普通push。运行校验发生在模型环境，发布环境只处理数据。Codex sandbox与进程隔离不等于整个Runner或容器安全边界。

## 状态与边界

权威状态：`docs/development/issues/<N>/state.json`。运行与讨论证据：`docs/development/reviews/issues/<N>/`；对应Issue标签为`agent:awaiting-decision`、`agent:blocked`、`agent:done`。运行中状态直接看Actions，不写入虚假的running提交；崩溃前未发布的任务可重扫。机器人反馈不进入内容指纹，发布后反馈失败由后续扫描协调。

自动修改范围是本Issue的评审目录和`openspec/changes/issue-<N>-*/`；apply额外允许`src/`、`tests/`、`contracts/`、`docs/domain/`。禁止脚本工作流及代理规则变更、符号链接/子模块/可执行模式、路径穿越和非Python脚本。需要工具链或公共规则更新时阻塞，转为人工维护。

main变更或Issue变更会丢弃旧候选，后续补扫重新计算。普通推送冲突/分支保护错误会使Actions失败，并在机器人Issue评论保存publication-failed守卫，后续扫描要求明确retry，避免重复模型消费。若main和Issue反馈同时不可写，无法持久保存守卫，只能依据失败的Actions日志人工处理；不声称这种双重写入故障已恢复。其他持久blocked错误需要明确retry。不会自动关闭用户Issue或archive变更。

## 本地检查

```text
python3 -m unittest discover -s tests -v
python3 scripts/verify_artifacts.py
npm run validate
```

远程验证记录见`docs/development/reviews/2026-11-01/issue-worker-verification.md`。测试结果必须分别报告控制链路与真实模型链路。
