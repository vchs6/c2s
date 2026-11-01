# Tasks

## 1. 工具初始化

- [x] 1.1 使用真实OpenSpec/Codex命令初始化并固定Superpowers源；验证 `npm run openspec -- --version`、`git submodule status` 及插件list。
  - 上游依据：proposal.md工具范围；design.md决策1、2。
  - 交付物：package.json、package-lock.json、.agents/skills、.agents/plugins/marketplace.json、tools/superpowers。
  - 检查方式：工具版本、插件安装输出、子模块提交匹配记录。
  - 通过条件：CLI初始化完成，插件注册/安装/list成功，Skill源可读。
  - 失败条件：伪造命令、未固定版本、插件不可读取。

## 2. 会话资料与批准范围

- [x] 2.1 将四个会话交付物及证据摘要置于分类目录；验证 `npm run check:artifacts`。
  - 上游依据：用户要求提交本次会话文件；design.md决策3、4。
  - 交付物：docs/domain、docs/development/reviews、docs/workflow/archives、docs/session/artifact-manifest.json、docs/decisions/0001-five-semantic-layers.md。
  - 检查方式：逐原件SHA-256、目录索引、决策范围复核。
  - 通过条件：四原件哈希一致，五层确认与其余候选细节清楚分开。
  - 失败条件：丢文件、改写原件、将完整草案误标为已批准。

## 3. 主代理与协作入口

- [x] 3.1 配置DDD/SDD/Superpowers主代理、Battle规则和复现说明；验证TOML及工作流文档。
  - 上游依据：用户指定DDD/OpenSpec/Superpowers；已存在Battle配置原件。
  - 交付物：AGENTS.md、.codex/config.toml、.codex/agents、docs/workflow、README.md。
  - 检查方式：解析TOML，核对实际Skill名与CLI帮助，核对相对路径。
  - 通过条件：命令可复现，不包含认证、宿主配置或产品实现。
  - 失败条件：无效角色配置、固定未知模型、绕开OpenSpec或提前编码。

## 4. 集成检查与提交

- [x] 4.1 执行 `npm run validate`、`npm run check:artifacts` 和 `git diff --check`，完成独立复核后提交并推送。
  - 上游依据：用户提交要求、verification-before-completion。
  - 交付物：docs/development/setup/2026-11-01-initialization.md、Git提交、远程提交链接。
  - 检查方式：严格校验、原件校验、子模块状态及远程HEAD比对。
  - 通过条件：检查成功、远程提交可读取、未运行archive。
  - 失败条件：检查失败、推送未完成或把状态工件存在误称实现已完成。

## Workflow follow-up

- 本初始化变更保持active，不自动archive。
- 下一产品变更为define-layered-semantic-fact-model；正式规格和机器可读公共定义不在本初始化中冒充完成。
