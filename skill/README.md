# c2s语义事实查询Skill

状态：开发准备说明，产品尚未实现，当前没有可用的SKILL.md或查询入口。本文件是最终Skill README的维护位置；依赖是否进入发行包以实际实现及验证结果为准，不把试验工具全部当必需运行依赖。

## 当前已安装与用途

| 工具/能力 | 实际版本 | 用途及当前边界 |
| --- | --- | --- |
| Python | 3.12.14 | 本轮Linux宿主、AST与自维护脚本；未测试其他Python版本 |
| tree-sitter / Python grammar / Rust grammar | 0.26.0 / 0.25.0 / 0.24.2 | 结构解析候选，不证明类型绑定或完整行为语义 |
| jsonschema | 4.26.0 | 已安装的公共契约验证依赖候选；产品契约尚未实施 |
| Code Review Graph | 2.3.9 | 已实际建图/查询，默认覆盖不能当全目录完整；外置图缓存，无模型嵌入 |
| Rust工具链 | rustc 1.99.1，Cargo实际版本见环境档案 | 已安装，实际运行no-deps/offline metadata；不是依赖全解析或构建验证 |
| GitHub CLI | 2.103.3 | 备用账户配置工具，官方归档摘要核验；仅CI开发准备，需独立GitHub授权 |
| OpenSpec / Codex / Superpowers | 1.16.0 / 0.166.0 / 7.0.1 | 开发流程工具，不当产品运行依赖；Superpowers在当前环境可读 |

Python包来自包索引；Rust安装来源为官方https://rust-lang.org/tools/install/，使用项目本地RUSTUP_HOME/CARGO_HOME且不改shell profile。当前安装路径`.local/analysis-venv`、`.local/rustup`、`.local/cargo`均为开发临时目录，不随Skill发行。

CRG包自带build-graph/explore-codebase等Skill文件可读取，但本轮没有执行自动install去覆盖客户端MCP/AGENTS/hooks，也未把这些文件注册为新的个人Skill。Serena、GitNexus、CodeGraph仍是调查候选，未安装，不声称已支持。

## 复现本轮开发环境

```bash
uv venv .local/analysis-venv
uv pip install --python .local/analysis-venv/bin/python tree-sitter==0.26.0 tree-sitter-python==0.25.0 tree-sitter-rust==0.24.2 jsonschema==4.26.0 code-review-graph==2.3.9
```

这不是最终产品安装命令。Windows解释器路径及Rust前置工具按官方平台方式配置；当前只在Linux x86_64实际验证，不外推Windows/macOS或项目交叉target。

自检可读取包版本、CRG `--help`及Rust `--version`。本轮真实输入为固定regex/click提交，工具试验记录在`../docs/development/reviews/issues/10/acquisition-survey-2026-11-02/experiment-results.json`。没有产品查询示例或验收命令可供运行。

本轮Rust安装在项目本地，Linux自检必须显式指定两处home（不能直接调用默认home的rustup代理）：

```bash
RUSTUP_HOME="$PWD/.local/rustup" CARGO_HOME="$PWD/.local/cargo" .local/cargo/bin/cargo --version
RUSTUP_HOME="$PWD/.local/rustup" CARGO_HOME="$PWD/.local/cargo" .local/cargo/bin/rustc --version
```

## 索引、写入与联网

CRG建图使用`--data-dir`外置图数据库及`--skip-postprocess`，未启用嵌入、watch或自动配置安装；工具仍可能维护宿主的图目录注册信息，不能把这些命令称为完全无副作用。源项目跟踪文件与固定提交blob核对无变化。索引是语法/关系候选，不是完整领域事实。

安装及克隆需要联网；本轮解析/图查询没有调用LLM，不据此宣称未来端到端零Token。最终模型参与的凭据只通过环境/宿主安全配置提供，不写入Skill、日志或仓库。必要依赖不可用或工具无法覆盖时必须报告原因，不伪造结果。

## 当前限制

真实五角色权限隔离未就绪，隐藏用例和产品流水线尚未运行。用户已授权准备后连续开发，环境阻塞消除后可继续，无需重新批准同一范围；当前不声明产品版本发布、不自动归档。

CI账户配置与公开容器探针的命令、最小权限、安装来源及安全输入方法见`../docs/workflow/ci-setup.md`；gh不是产品运行依赖。Docker仅供GitHub托管Ubuntu探针使用，本地未安装或验证。

私有验收准备增加credential-check模板：使用托管Ubuntu预装Python 3标准库，一次GET /v1/models校验Secret可见和API认证，不执行生成请求、不证明推理或完整角色隔离。无需新增产品依赖；部署/状态见交付change tasks 3.2.1。

托管角色边界检查使用Docker与python:3.12-slim镜像；每次先解析并记录实际RepoDigest，按摘要执行，非root、禁网、只读根及限定挂载。源/私有runner合成诊断已通过；本地没有Docker能力，未验证其他host。该封装不是完整模型编排器，不能把当前原生代理全权工具当作正式编码工具入口。

开发健康检查另有一次公开输入的gpt-5-mini Responses请求（最大256输出Token、store=false、不重试）；它不是产品语义后端选择。当前实际返回credit_balance_exhausted，推理未通过，usage未知。开发按任务选模型、按需选专用Skill及实际使用回报见../docs/workflow/agent-governance.md和本轮skill-usage.md。

开发环境采用ADR-0010双向独立编写与确定性CI，见`../docs/workflow/blind-development.md`。GitHub托管Linux probe的Docker仅为可信CI准备依赖，不是最终Skill或所有开发宿主必装依赖；普通测试执行不消耗模型Token。正式AI编写工具入口尚未部署验证。
