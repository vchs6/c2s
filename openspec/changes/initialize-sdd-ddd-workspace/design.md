# Design

## Context

仓库初始只有README、Apache-2.0许可证和Python忽略模板。OpenSpec 1.16.0通过本地npm开发依赖固定；Codex CLI 0.166.0在宿主工具目录安装用于插件注册。见proposal.md的初始化范围。

## Goals / Non-Goals

**Goals:** 使用真实CLI与已安装Skill；支持新检出复现；把已确认五层和未批准细节分开记录。

**Non-Goals:** 不实现事实提取Skill；不选实现语言、数据库、聚合或解析工具；不将资料归档视为产品规格发布。

## Decisions

1. OpenSpec使用官方init生成的Codex Skills，保留默认spec-driven schema；纯工具变更skip_specs，不为校验虚构产品需求。后续模型定义另开变更。
2. Superpowers采用官方obra/superpowers的固定git子模块，项目本地Codex marketplace只引用该源，不复制或修改上游技能。使用codex plugin marketplace/add/list命令验证，避免声称存在superpowers init。
3. docs/domain/drafts保留早期原件；docs/domain/proposals保留案例定义；docs/development/reviews存放Battle及证据；docs/workflow/archives存配置ZIP。原件字节不改，迁移清单记录SHA-256。
4. ADR-0001只确认五层组织方案及用户已明确的DDD方向，不把候选字段、谓词和完整语法一并批准。三/四层少数意见作为历史证据保留。
5. AGENTS.md协调OpenSpec的工件生命周期和Superpowers的分析、规划、执行、验证。约束、计划和任务互相引用，不维护两份矛盾待办。
6. Node包仅用于开发工具。许可证改为与仓库既有Apache-2.0一致，删除npm init生成的失败测试占位；node_modules不提交。

## Risks / Trade-offs

- [Risk] 客户端插件市场名字不同 → 记录实际失败与成功命令，提供项目本地源复现；不修改全局提供商或认证。
- [Risk] 原始文档含历史路径及proposed字样 → 索引明确原件性质，当前批准范围由ADR记录，不能将原件当作生效规格。
- [Risk] 插件安装不证明新会话自动触发 → 分别验证安装、Skill源可读和当前会话调用；本机客户端新会话仍需按说明验证。

## Migration Plan

按任务完成工具初始化、工件迁移、规则与决策、校验及提交。当前初始化变更保持active，不运行archive。工具源由git子模块回退，项目设置由本次提交回退；原件哈希用于确认迁移未改写。
