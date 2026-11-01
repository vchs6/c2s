# c2s 初始化与验证记录

日期：2026-11-01。原始仓库HEAD：8dbef1a9bf62e9f52062b461b7fd474f30b18d41。当前目标分支：main。最初创建临时分支后，用户明确要求不建分支、不创建PR；已在提交前切回main并删除无提交的临时分支。

## 范围与用户授权

用户要求新仓库c2s使用OpenSpec与Superpowers、按DDD初始化并提交本会话资料；后续要求评审记录放入docs下的开发文档目录。本次只初始化工具/文档，不开发事实提取器；不自动archive。

## 实际执行的关键命令

以下为已执行命令摘要；不是虚构的superpowers init，也不把Skill入口当终端命令。

| 命令 | 结果 |
| --- | --- |
| git clone https://github.com/vchs6/c2s.git c2s | 成功，确认原仓库仅README、LICENSE、.gitignore |
| git switch -c chore/initialize-sdd-ddd | 最初成功创建；后按用户指令切回main并删除临时分支 |
| npm init -y | 生成开发工具包；随后纠正许可证、私有标记并删除失败测试占位 |
| npm install --save-dev --save-exact @fission-ai/openspec@1.16.0 | 成功，锁定OpenSpec |
| npm install --save-dev --save-exact @openai/codex@0.166.0 | 成功，锁定CodexCLI；此前宿主工具目录也安装相同版本以验证命令 |
| ./node_modules/.bin/openspec init --tools codex --language zh --no-animation --no-copilot-cloud | 成功生成OpenSpec结构和6个Codex Skill；copilot标志被正常忽略 |
| openspec new change initialize-sdd-ddd-workspace | 实际通过本地CLI执行，成功创建变更 |
| openspec status --change initialize-sdd-ddd-workspace --json | 多次成功检查工件依赖，未把存在状态当作实施验证 |
| openspec instructions proposal/design/tasks --change initialize-sdd-ddd-workspace --json | 三次分别取得模板与指令，再撰写对应工件 |
| openspec instructions apply --change initialize-sdd-ddd-workspace --json | 返回ready与4项任务，按其上下文执行 |
| openspec list --specs | 初始No specs found；工具/文档变更skip_specs，不虚构规格 |
| openspec update | 成功更新Codex集成；固定CLI1.16.0 |
| git submodule add https://github.com/obra/superpowers.git tools/superpowers | 成功，固定提交2ce8aa15d05bd57213e6f746f953aafb7ded7a8b、插件7.0.1 |
| codex plugin marketplace add openai/plugins --json | 失败：openai-curated为保留市场名；没有伪称成功 |
| codex plugin add superpowers@openai-curated --json | 失败：该市场未找到插件；后续list确认托管源名为openai-curated-remote |
| codex plugin marketplace add . --json | 成功注册项目本地c2s-tools，引用官方上游子模块 |
| codex plugin add superpowers@c2s-tools --json | 成功安装Superpowers7.0.1 |
| codex plugin list --json | 确认本地源installed/enabled；托管远程源也可见，不声称本机新会话已完成自动发现或去重验证 |
| npm run check:artifacts | 四原件SHA-256及工作流/插件源检查通过 |
| npm run validate | 严格校验1通过、0失败；skip_specs为预期INFO |

OpenSpec命令实际使用仓库node_modules/.bin/openspec；校验和后续调用设置OPENSPEC_TELEMETRY=0。npm的环境http-proxy弃用提示不是安装或校验失败。所有产品测试均未运行，因为本次没有产品实现或测试套件。

## Superpowers 的真实使用

本会话实际调用/读取using-superpowers、brainstorming、using-git-worktrees、writing-plans、executing-plans、verification-before-completion、requesting-code-review等Skill，应用于范围澄清、新检出分支、唯一任务清单、连续执行和交付核验。它是插件/Skill框架，不存在独立superpowers init CLI。

初始化Skill与OpenSpec生成指令已读取；用户明确授权完成初始化与提交，因此在此授权范围持续执行，不把工具内部规划提示误解成需要再确认已授权的同一任务。

## 工件位置与状态

四份原件哈希登记在docs/session/artifact-manifest.json，内容保持不变。评审和Battle结果位于docs/development/reviews/2026-11-01/；原始模型位于docs/domain/drafts，案例定义位于docs/domain/proposals，原始配置包位于docs/workflow/archives。未提交外部案例源码、node_modules、认证或宿主插件缓存。

用户确认的五层方向单独记录ADR-0001；其余模型定义仍是候选。本变更保持active，skip_specs表示纯工具与资料变更，不表示五层公共规格已经完成。

## 验证边界

已验证本环境CLI安装、真实初始化、插件命令、上游Skill文件可读、原件哈希及OpenSpec严格校验。新机器需clone子模块、npm ci并按README安装/选择一个Superpowers来源。GitHub Actions仅提交配置，本地不能将其称作远程CI已通过。终端plugin/list的安装结果不能证明所有客户端下一个新会话自动触发Skill。

独立复核已通过，详见../reviews/2026-11-01/c2s-initialization-review.md。不运行archive；按用户最新指令直接更新main，不创建PR。

本地创建初始化提交后，git push origin main因无法读取GitHub用户名失败（命令行无凭据）。使用已连接GitHub接口创建同一文件树和提交，以远程原HEAD为父提交，expected_sha校验后直接更新main；不force、不绕过分支保护、不写入认证凭据。远程提交链接在会话交付结果提供，避免在提交自身中嵌入无法预知的自身哈希。

独立复核阶段已纠正两项Minor：OpenSpec上下文中的旧评审目录路径；Node支持范围按锁定依赖引擎收紧为22.13+的22.x或24+。
