# Issue Worker 验证记录

2026-11-01。用户授权配置并测试，直接提交main，无分支/PR，所有自维护脚本Python 3。

## 本地证据

Python unittest 22项通过；包含内容指纹、维护者授权、旧批准、新增/删除/编辑计划文件、缺密钥恢复、显式重试、路径穿越/符号链接/禁止源重命名、独立审查门槛、真实临时bare远程普通推送及拒绝推送反馈守卫。
`python3 scripts/verify_artifacts.py`：4份导入原件哈希与固定Superpowers源通过；`npm run validate`：3项活动变更严格校验通过；workflow YAML解析及工件/凭据边界检查通过。

## 独立复核

独立reviewer只读复核后发现重命名越界、缺密钥恢复批准、隐藏工件上传、新增规划文件及发布失败重复执行问题。已补回归测试并修复；暂存区空白检查更正为--cached。独立进程会话共享检出资料，不声称系统级隔离。

## 远程验证

- 配置提交：`36ba4050f96f2e31dc83a84bbfc4ab30bc06223e`，直接main。
- 基线CI：[41268550468](https://github.com/vchs6/c2s/actions/runs/41268550468)，success。
- smoke [Issue #1](https://github.com/vchs6/c2s/issues/1)触发[41268564276](https://github.com/vchs6/c2s/actions/runs/41268564276)，prepare/publish成功，model跳过。四项校验全部code=0；smoke.json明确model_called=false；状态completed，机器人标签/反馈成功。
- smoke自动提交：`0faf2d016ca81fb16b87693250db352fd8e73074`，main写入状态和报告。
- 模型探针[Issue #2](https://github.com/vchs6/c2s/issues/2)触发[41268598288](https://github.com/vchs6/c2s/actions/runs/41268598288)，工作流success，任务明确blocked/missing-model-key，model跳过；未发生真实模型调用。
- 阻塞记录自动提交：`b7dadacb196cd551e2d61ae1d10b602804a43991`。第二次扫描没有重做已完成的smoke，证明完成指纹跳过。
- 公开main远程树及Issue机器人评论已重新读取核对，不以本地测试代替远程验证。

结论：Issue事件→队列→工件→验证→直接main提交→反馈的控制链路实际可行。仓库缺少OPENAI_API_KEY，真实Battle/规划/批准/apply端到端尚未验证。需仓库维护者在Actions Secrets中配置API密钥，之后Issue #2可由补扫恢复；不能通过网页OAuth替代。若不再需要探针，可手动关闭该Issue。

## 领域模型工件

`openspec/changes/define-layered-semantic-fact-model/`已补齐proposal/design/tasks和semantic-fact-model、algorithm-description两项delta specs。16项需求、35个场景，10项实施任务未完成。不将规划完整误报为提取Skill已实现。未同步主规格或归档。
