# Proposal

## Why

当前SQLite公开入口只接受`m1-project-discovery-1`，函数、算法、行为契约、证据引用及上下文事实不能写入或从语义仓库查询。这与已定义的E0–E4全量模型及按需复用查询要求不符，查询只能重新运行分析器。

## What Changes

- 让语义仓库读写`semantic-fact-model-1`全量bundle，并保存全部顶层记录、证据、附件、注册身份及引用关系。
- 为全量事实定义稳定规范化键，补证合并不复制主体/主张，冲突保留，提交原子化并规范回读。
- 让`query --store`按请求从已存覆盖和语义状态读取事实；缺项时按需构造、提交、回读后再返回。
- 让`algorithm --semantic-facts --store`持久化E4算法事实并供后续查询读取。
- 保留M1读写接口和历史数据兼容；M1只作为全量语义模型的受限profile，不再限制公开`--store`入口。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `semantic-fact-query`: 查询需复用持久化的各层事实并限定返回范围。
- `semantic-fact-model`: 全量顶层记录在存储与规范化后仍保持五层语义、身份及引用语义。
- `lazy-semantic-fact-construction`: 查询按请求从仓库复用已取得部分，只构造缺少部分。

## Impact

影响`skill/src/c2s_skill/semantic_store.py`、CLI查询和算法入口、`project_query_to_semantic_model`调用、契约schema与Skill测试。使用现有`semantic-fact-model-1`目录和校验器，不新增运行时依赖。共享工作区测试不构成私有验收。
