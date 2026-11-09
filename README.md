# c2s — Code to Semantics

当前产品仅提供V2公开接口，V1兼容路径已按ADR-0014移除。首次使用所需工具、其他Skill与代理安装责任见[使用说明](skill/使用说明.md)，CLI/API索引见[Skill说明](skill/README.md)，实施与独立审核见[移除V1交付核验](docs/development/reviews/semantic-facts/移除V1交付核验.md)。下面早期准备与规划文字保留为历史记录，不恢复旧接口。

按规格驱动开发的上游软件项目语义事实提取Skill项目。当前模型决策见[ADR-0013](docs/decisions/0013-非DDD语义事实模型.md)：语义实体、源码实现参考和证据构成事实模型，不采用DDD建模约束。已取得连续开发授权（ADR-0009）；依据ADR-0011，未验证的双向盲编写和私有验收隔离不再阻塞开发。隔离现状与报告边界见[readiness](docs/planning/program-2026-11-01/readiness.md)。

现行实体模型依据ADR-0012及ADR-0013，E0–E4仅作为可选事实观察视角；历史五视角决定见[ADR-0001](docs/decisions/0001-five-semantic-layers.md)。已确认主规格见[事实模型](openspec/specs/semantic-fact-model/spec.md)和[查询响应](openspec/specs/semantic-fact-query/spec.md)，批准范围见[ADR-0002](docs/decisions/0002-confirmed-specification-baseline.md)。完整候选定义、证据和旧稿见[会话资料索引](docs/session/README.md)，不能将其全部视为已生效规格。

当前确认的查询需求见[ADR-0007](docs/decisions/0007-confirmed-system-query-requirements.md)：返回符合请求的顶层完整事实、不递归展开、如实报告缺口，同时提供报告与结构数据。另见[分析范围](openspec/specs/semantic-analysis-scope/spec.md)、[按需补充](openspec/specs/lazy-semantic-fact-construction/spec.md)和[评价边界](openspec/specs/semantic-analysis-quality/spec.md)。系统需求确认不等于产品实施批准。

独立交付要求见[ADR-0008](docs/decisions/0008-independent-delivery-and-milestones.md)及[里程碑索引](docs/planning/program-2026-11-01/milestones.md)：编码、审核、用例编写、测试和最终验证独立；基于真实项目的私有测试不向编码者开放。已授权准备后连续开发；托管公开边界探针已通过，真实双向编写入口及交接仍待验证。产品版本政策为0.b.c，未发布产品版本。

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

当前初始化变更是工具/文档工作，明确skip_specs，不虚构产品能力，也不自动archive。继续现有define-layered-semantic-fact-model；已确认需求先固化为主规格，候选公共定义经必要确认后另行实施，再开展获取器开发。

## 目录

- `openspec/`：正式规格和活动变更。
- `docs/domain/`：原始草案与候选领域定义。
- `docs/decisions/`：已确认决策及准确批准范围。
- `docs/development/reviews/`：Battle结果和固定来源证据。
- `docs/workflow/`：使用方式、Battle协议和历史配置包。
- `docs/development/setup/`：初始化命令与验证记录。
- `tools/superpowers/`：官方Superpowers源子模块，不在此实现产品。

仓库许可证为Apache-2.0；Superpowers子模块沿用其MIT许可证。

## 规划议题与手动启动

Issue仅登记议题；创建、编辑、评论、标签及定时任务不触发工作。请在会话显式指定规划目标，或在Actions手动选择单个Issue的plan/smoke；当前维护工具不提供apply，不根据评论令牌实施。见[持续规划模式](docs/workflow/planning-mode.md)与[手动工具](docs/workflow/issue-worker.md)。

先完成架构、功能与非功能（含查询性能、跨语言/跨平台）的讨论、规格和整体审核，再另行明确批准产品开发。方案A已选择，但不是实施批准；Issue #3相关领域模型仍沿用现有变更，不另建重复模型。

规划议题见[总计划 #4](https://github.com/vchs6/c2s/issues/4)与[仓库台账](docs/planning/agenda.md)；本次只创建事项，不自动启动讨论。

当前规范按需阅读：领域基础见docs/domain/foundation.md，项目约束见docs/project/constraints.md，代理治理/决策/任务/仓库管理/CI分别在docs/workflow下；AGENTS仅作入口。

## 平级公开开发准备（2026-11-03接续）

当前会话使用原生子代理推进公开基础设施；不在受限宿主另启Codex CLI，不把Docker作为公开协作前提。完成既有`npm ci`后可运行：

```bash
python3 scripts/check_public_environment.py
```

这是不联网、不安装、不调用模型/容器的公开工具自检；输出JSON和退出码只说明Python/Node/npm/Git/本地OpenSpec是否可用。Docker/Podman仅列命令存在性，缺失不使公开工具检查失败。原生模型可用性须由实际分派和返回另证；本脚本永远不宣布完整开发门禁通过。当前已验证宿主仅Linux，其他平台须另验。

私有用例作者、测试执行、最终验证及候选进程仍须具备独立有效权限和受控交接；共享会话、worktree或不同模型不能替代。现有runner可直接隔离候选程序，无需在其内再运行Codex。主规格/现有tasks保持权威；不要克隆私有suite到共享编码工作区。公开准备通过不授权绕过2.2/2.3，也不要求用户迁移仓库、升级GitLab或重复配置密钥。

## 主代理准备角色独立Git仓库（公开实验）

```bash
mkdir -p .local
python3 scripts/prepare_role_repositories.py \
  --source . --ref main --destination .local/my-role-repositories
```

目标必须尚不存在。该入口不联网、不创建远端项目，从ref一次解析固定提交，仅同步角色白名单文件；创建coding/review/author/runner/verifier五个独立Git仓库，独立main/root commit、无源remote或对象共享，MANIFEST与ROLE_INPUT记录源SHA和内容摘要。不带入未提交工作区内容或源历史；author不接收candidate示例。输入只含公开契约和公开基础设施示例，生成仓库不提交回主仓库。

它只负责主代理内容准备，不能收窄原生子代理现有文件、终端或连接器权限。首次使用须按本轮公开marker验证角色是否只能读取自身仓库；实际测试报告见`docs/development/reviews/independent-delivery/role-repositories-2026-11-03/`。权限未通过前，不在这些共享可读仓库创建隐藏用例/凭据，不放行产品编码。这里的本地仓库不冒充独立账号控制的远端私有项目或长期角色启动设施。

## CI角色仓库边界演练

现有`Source token and public role boundary diagnostic`工作流新增五角色matrix job，各自使用GitHub托管Ubuntu24.04。可信准备按该run提交创建公开角色快照，仅将所选仓库挂到受限worker的/repo；公开probe测试合法自身读写、其他role/宿主路径不可读写、socket/凭据不继承。脚本为`ci/acceptance/role_repository_probe.py`，只在配置齐全的可信CI宿主运行；它不是模型代理或任意candidate入口。

该工作流仅显式dispatch或相关基础设施文件push触发，不因Issue/评论/定时启动开发。源token只在独立检查step访问GitHub API，不传worker；不调用模型、不创建实际隐藏suite、不授予worker Docker权限。阶段通过只说明本次CI边界，不会改变当前聊天原生子代理工具权限，也不放行完整五角色门禁。

当前开发环境按[双向独立编写说明](docs/workflow/blind-development.md)组织：AI负责需判断的工作，CI固定执行构建与测试，普通检查不调用模型。正式角色入口与公开探针的验证范围分别报告。
