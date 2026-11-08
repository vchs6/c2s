# OpenSpec与Superpowers协作

OpenSpec实际命令：`npm run openspec -- new change <name>`，随后status、逐工件instructions、instructions apply及validate。Slash命令或`$openspec-propose`是代理Skill入口，不是终端子命令。CLI返回的指令仍需代理按模板撰写工件。

Superpowers没有独立的init终端命令。当前上游为Codex插件，使用using-superpowers、brainstorming、writing-plans、executing-plans、verification-before-completion等Skill。所需Skill已在本会话真实读取；新客户端需通过插件发现它们。

## 插件复现

```bash
git submodule update --init --recursive
npm ci
npm run setup:codex
npm run codex -- plugin list --json
```

项目本地marketplace名为c2s-tools，源指向tools/superpowers官方固定子模块。当前云端也存在superpowers@openai-curated-remote；官方市场名称随环境不同。选择一种有效来源，避免重复启用；不要把openai-curated和openai-curated-remote混同。本项目配置声明c2s-tools入口；当前托管环境的list仍显示远程安装，两者安装可见性不等于新会话技能去重已验证。不更改全局提供商或认证。

初始化安装命令成功，只证明插件注册/安装和Skill可读；不证明每个客户端会自动加载。新检出需在项目目录启动受支持Codex会话，检查using-superpowers与OpenSpec Skills被发现。不存在的命令不能用文字报告成已执行。

## 分工与门槛

事实模型：依ADR-0013组织语义实体、属性、关系和证据，不采用DDD建模约束。OpenSpec：proposal/spec/design/tasks的权威工件及变更生命周期。Superpowers：需求澄清、计划、实施、调试和验证方法。

工具/文档初始化用skip_specs:true；产品行为变更必须有规格增量。Superpowers计划引用OpenSpec tasks，不维护另一份会漂移的清单。实现新功能时遵循适用的TDD和独立审查；仅归档资料用哈希验证，不虚构产品测试。

Battle协议见battle-protocol.md。历史ZIP仅供追溯，不应将其配置覆盖本项目。新增或修改产品Skill时再按skill-creator和writing-skills执行，此初始化不创建一个空壳产品Skill来冒充实现。

未经明确要求不archive，不发布产品。已经授权的初始化和提交持续完成。

## 当前启动与开发门禁

以planning-mode.md和issue-worker.md为准：Issue、评论及定时不启动工作；会话显式授权后持续规划，当前Actions只手动指定单项plan/smoke。功能、非功能及跨语言/跨平台都要规划，整体审核及单独实施批准前不开发产品。旧自动运行记录仅作历史证据。
