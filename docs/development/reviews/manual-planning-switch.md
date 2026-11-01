# 手动规划模式修正记录

日期：2026-11-01。用户明确要求先修正工作方式、关闭Issue自动触发，再依序创建规划Issue；补充要求包括非功能指标、跨语言/跨平台和Token消耗控制。本次只实施维护工具/治理例外，不实施语义事实产品。

## 修正

- workflow仅workflow_dispatch，必须提供一个正整数Issue编号，操作只有plan/smoke，可精确复用已有change；删除issues、issue_comment和schedule，不扫描队列。
- prepare在API前拒绝非手动事件/无效编号，校验调用者及Issue作者；comments/旧令牌/implement或bug类型均不转apply。
- model仅接受plan，publish拒绝apply并在副作用前报错；规划补丁只可到选定变更/本Issue评审目录。主规格、产品、规则、workflow及认证不由模型规划补丁修改。
- 摘要显式绑定所选变更全部文件（包括未修改的既有工件）；新增文件或改内容使其变化，不能仅依赖本次diff。
- 当前方案选择继续保留，但不复制实施批准。历史状态不再被提示成“已批准状态”；重试提示改为再次手动启动。
- 治理与OpenSpec context覆盖持续规划、委托决策及人工例外、功能/非功能、源语言与混合语言、运行host/目标target支持矩阵和Token成本；整体规划审核与开发批准独立。

## 实际过程与验证

读取AGENTS、config、既有工作流/脚本/测试和相关变更；实际执行list/status及proposal/specs/design/tasks/apply instructions，维护原enable-issue-driven-development。只执行其第5组维护任务；历史4.1自动模型/apply端到端任务仍未完成且本模式暂缓，不冒充通过。

遵循已读取的brainstorming（具体关闭行为已有用户授权）、writing-plans/executing-plans（唯一tasks）、test-driven-development及verification-before-completion；先观察新7组测试失败（首次13失败/1错误，旧入口在拒绝前先读取密钥；隔离测试凭据和模型后为14个明确失败），再实现；未调用模型、未访问凭据。独立只读reviewer指出报告单独变更时的摘要覆盖问题，补第8个回归，先观察失败再修正。没有启动新领域Battle或产品实现。

最终本地结果：npm test共30项通过；npm run validate共5项通过/0失败；npm run check:artifacts四原件哈希及Superpowers固定源通过；git diff --check通过。发布测试包含临时本地bare仓库真实push，不等于GitHub模型端到端。源码/产品contracts、语言获取器和产品测试未实现，两份语义主规格与研究原件不变。

## 独立复核

Important：所选已有change未必进入plan_digest，已通过planning_paths显式枚举和报告单独变更回归修正。Minor：旧backlog重扫提示与“当前已批准状态”措辞已修正。另一个Minor保留为明确边界：当前Actions plan是实质性领域讨论的保守完整Battle路径，未实现自动争议识别/省Token调度；机械修订在授权会话直接处理，预算与调用策略列入后续非功能Issue，不声称已实现最优Token消耗。

未调用真实模型、未重新配置密钥、未声称跨Issue无人值守规划。推送仍可执行无模型CI；Issue创建/评论不能调用模型。当前工作流中没有产品apply入口。

## 发布与Issue顺序检查

发布前通过GitHub读取issue-worker各状态in_progress/queued/waiting/pending/requested，均无活动运行；最近30个Actions记录中的7个旧Issue worker均已结束。先发布并核对远程workflow只保留手动入口，再创建新规划事项；完成后的实际链接和顺序见docs/planning/agenda.md。本文件首版提交时尚未创建后续Issue，不把计划动作写成已完成。
