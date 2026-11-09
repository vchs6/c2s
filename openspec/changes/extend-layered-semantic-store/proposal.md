# Proposal

现行接口接续（2026-11-09，ADR-0014）：本文件M1/V1及旧完整事实运行接口为历史规划/交付记录，当前公开运行协议仅V2，不再提供兼容查询、仓储或转换。通用能力要求继续适用；新实施不得恢复旧API。唯一删除与审核任务见`openspec/changes/redesign-semantic-entity-domain-model/tasks.md`第11节。

## Why

本提案开始时SQLite公开入口只接受`m1-project-discovery-1`，函数、算法、行为契约、证据引用及上下文事实不能写入或从语义仓库查询。这与当时规划的全量旧模型记录和按需复用查询要求不符，查询只能重新运行分析器。

## What Changes

- 历史交付曾让语义仓库读写`semantic-fact-model-1`全量bundle；当前只读兼容，实体档案承接新写入，并保存全部顶层记录、证据、附件、注册身份及引用关系。
- 为全量事实定义稳定规范化键，补证合并不复制主体/主张，冲突保留，提交原子化并规范回读。
- 让`query --store`按请求从已存覆盖和语义状态读取事实；缺项时按需构造、提交、回读后再返回。
- 让`algorithm --semantic-facts --store`持久化E4算法事实并供后续查询读取。
- 保留M1读写接口和历史数据兼容；M1保留独立入口，公开`--store`当前使用实体档案。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `semantic-fact-query`: 查询需复用持久化的各层事实并限定返回范围。
- `semantic-fact-model`: 旧完整profile的顶层记录保留其历史观察视角、身份及引用语义，迁移不把观察视角推为实体组成关系。
- `lazy-semantic-fact-construction`: 查询按请求从仓库复用已取得部分，只构造缺少部分。

## Impact

影响`skill/src/c2s_skill/semantic_store.py`、CLI查询和算法入口、`project_query_to_semantic_model`调用、契约schema与Skill测试。使用现有`semantic-fact-model-1`目录和校验器，不新增运行时依赖。共享工作区测试不构成私有验收。

## 领域模型对齐复核（2026-11-07）

领域模型对齐及兼容状态：本提案交付的 `semantic-fact-model-1` 保留为旧完整档案的兼容读写实现/迁移输入，不再被解释为新领域模型的权威组织轴。新权威profile为 `semantic-entity-model-1`；默认入口切换、旧profile只读和回滚门槛只由 `redesign-semantic-entity-domain-model` 后续迁移任务管理。本注记不宣称切换已执行。

## ADR-0013 当前约束（2026-11-08）

该提案记录旧完整档案的历史交付。当前新写入使用实体档案，旧档案只读兼容；历史写入场景不重新授权旧profile写入，不能作为新模型的分层组织依据。 依据：`docs/decisions/0013-非DDD语义事实模型.md`。历史执行记录中的DDD或旧模型表述不构成现行约束。本轮只进行文档修订，产品重构完成状态不变。
