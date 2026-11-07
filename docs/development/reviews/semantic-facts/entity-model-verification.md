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
- Skill完整回归（包含新旧档案切换、共享实体档案、只读旧档案、算法投影和Cargo E1观察持久化）：170/170通过。模型契约：90/90通过。实体/迁移/CLI定向回归：原51项及新增Cargo集成检查通过。
- 切换复核发现算法 `--store` 曾只重扫源码构造档案，未保存本次请求的算法图或外部图响应。修正后，算法结构、语义事实投影、来源观察、投影工件和外部图JSON以`implementationView`关联到对应计算实体映射；算法证据对象提升到实体档案的可查询证据集合，外部工具版本和证据引用一并保存。CLI回读测试覆盖首次写入、同一源码下外部图结果变化后双版本保留，以及通过`entities`详情查询取回完整投影和证据。该回归测试加入完整Skill测试集，旧档案仍不双写。
- Cargo元数据复核补充：显式`workspace-members`请求的E1结果现在持久化为Project实体上的`workspaceMemberPackage`观察主张，配套Cargo.toml来源证据和`workspace-members`覆盖；Cargo不可用时覆盖为`not_acquired`并保留gap。真实regex的7条workspace事实写入并从同一SQLite Project详情读回7条，Cargo虚拟workspace不会把package自动变成语义实体；缺工具及虚拟workspace均有正反集成测试。

## 切换与兼容边界

2026-11-07已切换默认模型档案写入：`query --store`与`algorithm --semantic-facts --store`均通过`SemanticEntityStore`写入`semantic-entity-model-1`；旧完整档案`commit_bundle`接口拒绝新写入，`read_bundle`/`query_bundle`保留读取能力，`commit_m1`保持独立。CLI测试验证新旧profile可在同一SQLite文件的独立表中共存，原有旧档案数据回读不变；切换前使用SQLite在线备份API生成快照，切换后逐项验证快照与原旧档案一致。切换只新增实体档案表而不改写旧表，回退到前一代码版本时原表及数据文件仍保留。实体命令与普通查询的相同项目范围共用档案，覆盖命中时不重复构造。OpenSpec任务6.2/6.3已完成。

regex的Tree-sitter全源码遍历、Cargo.toml静态workspace核对和Cargo metadata均已完成。最初未给Cargo shim设置仓库本地`RUSTUP_HOME`/`CARGO_HOME`，导致先前报告误记为未运行；修正环境后离线执行`cargo metadata --no-deps --format-version 1`返回根包及6个workspace members共7个包，Skill的`workspace-members`查询返回7条事实且无gap。实体清单已重跑并记录`cargoToolStatus: available`；随后将真实regex的`workspace-members`结果通过`query --store`写入实体档案，并从同一SQLite库的Project详情中读回7条E1主张、工具证据和coverage；未将包实体化。该构造器不把Cargo packages直接转换为语义模块/实体，避免把构建包边界误认成业务边界。此记录不是私有隔离验收或盲验收；私有角色隔离门禁未执行。模型候选通过结构、类型、身份、证据引用、源码摘要/范围及SQLite逐实体回读校验；主张仍为暂定，因为这些检查不能证明业务解释符合项目真实意图，尚无权威领域文档或领域负责人确认结果。当前产品没有交互式业务确认/候选提升流程，未声称任何主张已被业务负责人确认。
