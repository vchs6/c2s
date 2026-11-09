# c2s上游事实查询Skill

当前仅公开V2协议：semantic-entity-model-2、semantic-fact-request-2及semantic-fact-result-2。按用户2026-11-09决定，V1、旧完整事实和M1运行接口、缓存接口及导入导出均已撤销，不提供兼容别名。历史Schema和报告仅供追溯。

## 当前能力

Python AST、Rust Tree-sitter提取来源目录、嵌套清单、模块、声明、实现机制、语义实体候选及属性关系；Cargo metadata提供原生工作空间成员；指定函数可查询算法、伪代码和静态缺口。来源组织与实体独立，无映射的来源模块仍可查询。推导主张有premiseIds/method及暂定状态，不将代码分析等同业务真值。

请求按目标和facets补缺，不默认降低全仓算法。self详情包含自身已取得属性；expandDepth为0–8。JSON和Markdown来自同一结果；items是请求目标，sourceRecords、claims、evidence、coverage、diagnostics及persistence分别返回。调用关系、测试绑定、宏展开、动态行为或类型解析未取得时保留缺口。枚举只在同文件词法作用域唯一引用时提供有限值域，不按裸名称跨模块猜测。

## 安装及自检

开发环境为Linux、Python3.12.14、Node22.13+/24+。Python包来自公开包索引，Rust工具链来自官方rust-lang.org；项目本地安装目录不随仓库提交。

```bash
uv venv .local/analysis-venv
uv pip install --python .local/analysis-venv/bin/python jsonschema==4.26.0 tree-sitter==0.26.0 tree-sitter-rust==0.24.2
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -v
npm test
npm run validate
npm run check:artifacts
```

基础依赖：Python AST标准库、jsonschema 4.26.0、tree-sitter 0.26.0、tree-sitter-rust 0.24.2及TOML标准库。开发工具为OpenSpec1.16.0、Codex0.166.0、Superpowers7.0.1，不是产品运行依赖。Rust/Cargo1.99.1用于本环境原生工作空间取证，安装和版本自检：

```bash
RUSTUP_HOME="$PWD/.local/rustup" CARGO_HOME="$PWD/.local/cargo" .local/cargo/bin/cargo --version
```

对仓库本地安装的Cargo，执行工作空间查询时还需将CARGO指向实际二进制；示例：

```bash
CARGO="$PWD/.local/cargo/bin/cargo" RUSTUP_HOME="$PWD/.local/rustup" CARGO_HOME="$PWD/.local/cargo" PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m c2s_skill query --root .local/real-projects/regex --select workspace-members --store /tmp/regex-v2.sqlite --format json
```

Cargo使用--no-deps --offline，不证明构建通过。Code Review Graph2.3.9可选，通过--graph-output导入其结构化响应，保留原始输出及新鲜度缺口。CodeGraph1.6.2（Apache-2.0、npm开源项目）已验证files/query/callers/callees解析，但尚无净覆盖收益证明，保持candidate；均非默认依赖。工具矩阵与专用解析器决定可执行能力，不把导航Skill短文本当事实。

## 查询

数据库、缓存、工具输出及报告应在分析项目目录之外：

```bash
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m c2s_skill query --root /path/to/project --select modules --store /tmp/project-v2.sqlite --format json
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m c2s_skill query --root /path/to/project --select function:Owner.run --store /tmp/project-v2.sqlite --format markdown
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m c2s_skill entities --root /path/to/project --request '{"target":{"kind":"DataEntity","name":"Record"},"detail":"self"}' --store /tmp/project-v2.sqlite --format json
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python -m c2s_skill algorithm --root /path/to/project --source src/parser.py --function parse --format json
```

固定中文表单如“有哪些类”规范化为V2请求。entity:<localId>和expand:<localId>查询当前scope中已发布标识，歧义返回候选。--model-profile只接受semantic-entity-model-2，不能选择旧协议。--semantic-facts选择算法的实体视图，不生成旧semantic_fact_bundle。

API：execute_fact_query/query_project_v2执行查询；query_entity_store_v2只投影当前档案，需提供scope、输入指纹与配置摘要；validate_semantic_entity_model_v2为公开模型校验器。旧query_project、SemanticFactStore、read/write旧实体API及semantic_entity_migration模块均已删除。

## 持久化与备份

同scope+固定输入+配置的事实原子补证，注册身份、证据、引用、覆盖及回执同事务保存；重复操作幂等，冲突拒绝。配置含实际产品源码与解析器/工具摘要，改变后不复用旧结果。缓存不能代替请求的事实存储，失败或retryable结果不缓存。纯旧档案返回UNSUPPORTED_ARCHIVE_PROFILE且文件不变；混合库仅访问V2，旧表不提供查询或改写。不会自动迁移、备份或删除V1。

显式备份当前V2档案：

```python
from pathlib import Path
from c2s_skill.semantic_store import SemanticEntityStore
from c2s_skill.archive_backup import backup_entity_archive
receipt = backup_entity_archive(SemanticEntityStore('/tmp/project-v2.sqlite'), Path('/tmp/project-v2-backup.sqlite'))
```

备份源必须存在、目标必须不存在；SQLite完整性和逐表回读一致后返回verified及摘要。恢复时先停写并保存当前库，将独立完整备份作为V2档案路径重新查询。Git历史和独立备份可用于运维回退；产品不提供V1恢复/转换接口。

退出码0为本请求完整，2为存在事实缺口或保存失败，64为执行阶段无效请求；argparse非法参数返回2。查询不主动联网；显式缓存/档案/结果和备份写磁盘；原生Cargo仅离线元数据。

## 验证边界

固定Click和regex的逐项来源/实体/证据回读及先定向→全量→定向一致性由scripts/verify_source_fact_refactor.py执行，脚本从固定Git版本创建隔离副本并检查源树不变。最新结果见[移除V1交付核验](../docs/development/reviews/semantic-facts/移除V1交付核验.md)。全部已发布记录遍历不等于穷尽全部语义真值，未请求算法不展开。

只验证了Linux的Python/Rust静态支持；其他语言、host/target、上游运行时等价及词元节省未验证。独立上下文只读代码审核与共享公开测试不是私有盲验收。
