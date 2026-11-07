# 语义实体模型重构验证记录

日期：2026-11-07。工作树：`main`。验证范围：OpenSpec change `redesign-semantic-entity-domain-model`，共享开发容器。

## 实现与真实项目遍历

- Click 固定提交 `2247b35ea1c47c727d7a06e51fa280e12a863ff6`：逐实体构造、契约校验、SQLite往返和逐实体查询比对共 2610/2610；283 个属性、2668 条关系、17226 条证据、15464 条源码映射。缺口清单有 74 条未映射源码构造、556 个测试目标未解析、2 项边界缺口。
- regex 固定提交 `94ac45b2a6e7b1c30927feb5b66c5ded5b7ad447`：逐实体构造、契约校验、SQLite往返和逐实体查询比对共 4712/4712；1034 个属性、4712 条关系、41392 条证据、36445 条源码映射。缺口清单有 6081 条未映射源码构造、9 个测试目标未解析、2 项边界缺口。
- 每个档案的JSON清单、查询往返和成本口径分别见同目录`entity-model-click-inventory.json`、`entity-model-regex-inventory.json`、`entity-model-cost-comparison.md`。未内嵌源码文本的映射记录仍带固定提交、路径、摘要和字节区间。
- 新增命令 `c2s_skill entities` 在固定Click检出上运行成功并生成实体清单。单命令CLI回归 13/13 通过。`entities`档案与旧M1/完整语义事实档案使用隔离仓储。

## 自动验证

- `npm test`：125/125通过。
- OpenSpec全库严格校验：23/23通过；当前change严格校验通过。
- `npm run check:artifacts`：4项工件摘要、工作流文件及Superpowers版本校验通过。
- Skill完整回归（包含CLI新增命令）：164/164通过。CLI定向回归：13/13通过。

## 尚未声称完成的检查

`entities`已可独立构造和查询；旧`query`仍是默认源码事实入口并可写`semantic-fact-model-1`，尚未切换为新模型的默认写入路径，故OpenSpec任务6.2与6.3保持未完成。切换要求的旧档案只读拒绝、备份回滚、M1入口不变和切换后全套验证尚未执行。不要把新入口可用误报成迁移切换完成。

regex的Tree-sitter全源码遍历及Cargo.toml静态workspace核对已完成；Cargo metadata未运行，因为当前Cargo shim无默认Rust toolchain。此记录不是私有隔离验收或盲验收；私有角色隔离门禁未执行。模型候选是带证据的暂定解释，不代表经过人工确认的业务语义真值。
