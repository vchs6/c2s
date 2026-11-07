# 语义实体模型重构验证记录

日期：2026-11-07。工作树：`main`。验证范围：OpenSpec change `redesign-semantic-entity-domain-model`，共享开发容器。

## 实现与真实项目遍历

- Click 固定提交 `2247b35ea1c47c727d7a06e51fa280e12a863ff6`：逐实体构造、契约校验、SQLite往返和逐实体查询比对共 2610/2610；283 个属性、2668 条关系、14921 条证据、15464 条源码映射。缺口清单有 74 条未映射源码构造、556 个测试目标未解析、2 项边界缺口。
- regex 固定提交 `94ac45b2a6e7b1c30927feb5b66c5ded5b7ad447`：逐实体构造、契约校验、SQLite往返和逐实体查询比对共 4712/4712；1034 个属性、4712 条关系、35227 条证据、36445 条源码映射。缺口清单有 6081 条未映射源码构造、9 个测试目标未解析、2 项边界缺口。
- 上述JSON清单由本次切换复核重新生成于全新SQLite档案，只包含当前分析指纹；原先合并过的历史档案快照已从清单排除，避免将多版本证据计数误作当前全量。
- 每个档案的JSON清单、查询往返和成本口径分别见同目录`entity-model-click-inventory.json`、`entity-model-regex-inventory.json`、`entity-model-cost-comparison.md`。未内嵌源码文本的映射记录仍带固定提交、路径、摘要和字节区间。
- 新增命令 `c2s_skill entities` 在固定Click检出上运行成功并生成实体清单。单命令CLI回归 13/13 通过。`entities`档案与旧M1/完整语义事实档案使用隔离仓储。

## 自动验证

- `npm test`：125/125通过。
- OpenSpec全库严格校验：23/23通过；当前change严格校验通过。
- `npm run check:artifacts`：4项工件摘要、工作流文件及Superpowers版本校验通过。
- Skill完整回归（包含新旧档案切换、共享实体档案和只读旧档案测试）：167/167通过。模型契约：90/90通过。实体/迁移/CLI定向回归：51/51通过。

## 切换与兼容边界

2026-11-07已切换默认模型档案写入：`query --store`与`algorithm --semantic-facts --store`均通过`SemanticEntityStore`写入`semantic-entity-model-1`；旧完整档案`commit_bundle`接口拒绝新写入，`read_bundle`/`query_bundle`保留读取能力，`commit_m1`保持独立。CLI测试验证新旧profile可在同一SQLite文件的独立表中共存，原有旧档案数据回读不变；切换前使用SQLite在线备份API生成快照，切换后逐项验证快照与原旧档案一致。切换只新增实体档案表而不改写旧表，回退到前一代码版本时原表及数据文件仍保留。实体命令与普通查询的相同项目范围共用档案，覆盖命中时不重复构造。OpenSpec任务6.2/6.3已完成。

regex的Tree-sitter全源码遍历及Cargo.toml静态workspace核对已完成；Cargo metadata未运行，因为当前Cargo shim无默认Rust toolchain。此记录不是私有隔离验收或盲验收；私有角色隔离门禁未执行。模型候选是带证据的暂定解释，不代表经过人工确认的业务语义真值。
