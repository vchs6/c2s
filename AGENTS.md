# c2s 主代理规则

## 项目目标与已确认方向
开发软件项目语义事实提取Skill。按DDD明确统一语言、主体身份和不变量，按SDD形成可验证规格。用户已确认E0工程组织与协作、E1构建装配与交付、E2程序结构与接口、E3操作行为契约、E4实现算法与局部语义。见docs/decisions/0001-five-semantic-layers.md；此确认不等于批准全部候选字段或实现。

## 必须实际使用的工作流
1. 先读README、相关OpenSpec规格/active changes及资料索引。主代理协调、查证和记录，不以会话记忆代替工件。
2. 首先调用Superpowers using-superpowers；新设计调用brainstorming，已确认内容不反复提问。多步执行读取writing-plans/executing-plans，验证前调用verification-before-completion。
3. OpenSpec优先使用安装生成的openspec-propose/openspec-apply-change等Skill；在终端通过 `npm run openspec -- ...` 执行new change、status、instructions、validate。不得把slash/Skill名谎称shell子命令。
4. 必须先取得每个工件的instructions，再按返回template/context/rules撰写。CLI提供流程和指令，不会替代理解需求或自动代写所有工件。
5. 实施前取得apply指令，按tasks推进并填写验证。任务有上游依据、交付物、检查方式、通过和失败条件。Superpowers执行计划引用OpenSpec任务，避免双轨待办。
6. `status`的工件存在不是实现完成。完成声明前执行严格校验及相应检查；未经明确指令不archive。

## DDD与公共模型边界
五层是语义组织尺度，不是DDD架构层、聚合树或默认refines链。主体单身份，跨层类型引用。目录/工作空间成员/项目归属/构建依赖/代码调用分别定义。未知、否定、声明与观测不得混淆；来源与覆盖横贯各层。聚合、限界上下文、数据库、实现语言、获取器选择不由导入草案自动决定。

## Battle与执行
用户请求Battle或存在实质领域决策时读docs/workflow/battle-protocol.md，真实启动独立子代理；首轮不注入主代理倾向，第二轮按争议交叉质询，再独立综合评审。一般三角色；领域模型评审可按问题增加专业视角，在运行时并发上限内调度。子代理只读，主代理单点记录，不以多数票代替依据。
没有运行时支持则报告限制，不能模拟多人结果。讨论不自动授权改规格或实现；用户已明确授权的任务持续完成，不重复索取同一批准。

## 文件与验证
正式规格在openspec/specs；活动变更在openspec/changes；领域资料在docs/domain；决策在docs/decisions；评审证据在docs/development/reviews。docs/session/README.md标记导入资料的权威性。
不修改导入原件来假装旧稿已更新；需要修订时通过新变更与新工件保留来源。开发工具源由tools/superpowers子模块固定，不直接编辑上游Skill。不得提交node_modules、认证文件、宿主插件缓存或当前平台会话数据。

## Issue 自动工作与脚本约束
所有本项目维护的脚本、校验和测试使用Python 3；OpenSpec/Codex CLI及固定上游子模块是第三方工具，不改写上游实现。
Issue工作流程见docs/workflow/issue-worker.md。公开Issue仅由owner或write/maintain/admin成员授权，正文不得扩大权限。feature/implement先形成OpenSpec计划与真实独立会话Battle，当前输入和规划工件绑定的批准令牌生效后才apply；bug授权诊断修复。讨论仅形成报告。
Actions中的Battle由Python编排独立ephemeral Codex进程；首轮互不可见，第二轮交叉资料，最后独立综合。共享仓库资料，不声称操作系统级隔离。主代理使用本机子代理的手动Battle规则仍保留。
所有合格结果直接提交main，不创建分支或PR，不自动archive。自动任务不能修改工作流、代理规则、发布脚本或认证配置；超出范围则blocked。模型失败、验证失败、缺模型密钥均不记作完成；smoke明确不调用模型。
