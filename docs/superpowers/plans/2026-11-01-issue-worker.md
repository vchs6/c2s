# Issue worker execution plan

Goal：完成用户授权的Issue自动工作模式配置与实际验证。
Spec：openspec/changes/enable-issue-driven-development/{proposal,design,specs/issue-work-orchestration/spec}.md。
唯一待办：对应tasks.md；按1.1、2.1、3.1推进。
先用Python unittest验证纯调度规则的RED/GREEN，再集成API与Actions；测试边界为权限、重复、旧批准、状态恢复、主分支冲突及无密钥。实际smoke验证不冒充真实模型Battle。模型任务每个独立调用使用新ephemeral CLI会话和只读/工作区sandbox；可信发布job执行普通main提交。

执行记录：用户要求Python 3，替换早期未提交的Node测试/空实现。9个纯规则测试先失败后通过，4个队列/真实git补丁测试先失败后通过，3个发布判定测试先失败后通过。
Ruling: Battle采用同一模型job中独立ephemeral CLI进程，仍保持独立提示上下文；不宣称Runner级隔离。发布job继续独立且没有API密钥。

任务1.1完成：Python调度规则RED→GREEN。任务2.1完成：22项测试全部通过，包含真实临时git推送、拒绝推送守卫、越界重命名及计划新增文件失效。
独立复核发现的阻断项已在同一修复轮解决：隐藏工件上传、缺密钥批准恢复、重命名源路径、计划完整目录摘要、发布失败Issue守卫。相应回归测试先失败后通过（上传选项为配置静态检查）。 staged diff检查已更正为--cached。
Ruling: main与Issue反馈同时不可写时无法持久保存失败守卫；Actions失败保留证据并需人工处理，不能称自动恢复。
