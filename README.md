# c2s — Code to Semantics

按DDD和规格驱动开发的软件项目语义事实提取Skill项目。当前提交只完成开发工作区初始化和会话资料迁移，尚未实现提取Skill。

已确认五层方向见[ADR-0001](docs/decisions/0001-five-semantic-layers.md)。完整候选定义、证据和旧稿见[会话资料索引](docs/session/README.md)，不能将其全部视为已生效规格。

## 开发环境

Node.js 22.13+（22.x）或24+、npm、Git。固定工具：OpenSpec 1.16.0、Codex CLI 0.166.0、Superpowers 7.0.1（git子模块固定提交）。Node依赖仅为开发工具，不指定Skill的实现语言。

```bash
git clone --recurse-submodules https://github.com/vchs6/c2s.git
cd c2s
npm ci
npm run setup:codex
npm run check:artifacts
npm run validate
```

`setup:codex`通过Codex插件命令注册当前项目本地marketplace并安装官方上游Superpowers。它会在本机Codex用户配置中登记插件；不包含认证，不改变模型或提供商。已有托管/官方Superpowers时可使用该安装，避免重复启用多个来源；详见[工作流](docs/workflow/README.md)。初始化验证不能替代你本机新会话中的自动触发检查。

## 工作流程

在项目中启动Codex，遵循[AGENTS.md](AGENTS.md)。Superpowers负责分析、规划、执行与验证方法，OpenSpec管理变更和规格工件。终端示例：

```bash
npm run openspec -- list --specs
npm run openspec -- list
npm run openspec -- status --change initialize-sdd-ddd-workspace
```

当前初始化变更是工具/文档工作，明确skip_specs，不虚构产品能力，也不自动archive。下一产品变更建议define-layered-semantic-fact-model，将五层方向转为规格及机器可读公共定义，再开展获取器开发。

## 目录

- `openspec/`：正式规格和活动变更。
- `docs/domain/`：原始草案与候选领域定义。
- `docs/decisions/`：已确认决策及准确批准范围。
- `docs/development/reviews/`：Battle结果和固定来源证据。
- `docs/workflow/`：使用方式、Battle协议和历史配置包。
- `docs/development/setup/`：初始化命令与验证记录。
- `tools/superpowers/`：官方Superpowers源子模块，不在此实现产品。

仓库许可证为Apache-2.0；Superpowers子模块沿用其MIT许可证。

## Issue 自动工作
使用[工作事项表单](https://github.com/vchs6/c2s/issues/new?template=agent-work.yml)创建讨论、功能规划、实施或缺陷任务。详情见[Issue Worker](docs/workflow/issue-worker.md)。仓库脚本和测试统一采用Python 3，OpenSpec及Codex仍使用固定版本CLI。

Battle形成的语义模型计划位于`openspec/changes/define-layered-semantic-fact-model/`，包含proposal、design、delta specs和tasks；领域研究原件不等同于已生效的主规格。
