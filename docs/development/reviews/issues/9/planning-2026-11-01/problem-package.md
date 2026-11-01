# 中立问题包

problem/scope: Issue#9只保存未存内容、身份去重、幂等、部分写失败与来源变化；不是数据库选型任务。constraints/evidence:共享context/upstream、主规格、已选模型A身份/条件/证据、Issue原文。unknowns:同主体来源变化时是否允许更新/失效重建，用户未决定；不得默认为upsert、摘要重键或历史服务。acceptance:相同提交不重复；变化不被already-exists隐藏；补证/配置/平台条件不误去重；引用一致且失败可重试。比较至少两个更新政策选项与存储方案，建议待用户决定，不改变基线。
