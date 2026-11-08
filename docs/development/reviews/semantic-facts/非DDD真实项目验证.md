# 非DDD重构真实项目集成验证

输入固定：Click `2247b35ea1c47c727d7a06e51fa280e12a863ff6`；regex `94ac45b2a6e7b1c30927feb5b66c5ded5b7ad447`。脚本从Git提交生成隔离副本，验证前后源树摘要相等；数据库和结果放在分析目录外。环境、输入/配置指纹、请求及冷热查询度量见同名前缀的两个JSON。

## 全集遍历与逐项回读

| 项目 | 来源记录查询 | 实体详情查询 | 主张核对 | 关系核对 | 实现映射核对 | 原生类型/函数盘点对照 | 显式算法 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| click | 4138 | 2610 | 2610 | 2668 | 4448 | 2078 | 1 |
| regex | 19041 | 4712 | 4712 | 4712 | 12698 | 4907 | 1 |

全部已发布集合均经v2契约和引用检查；每个来源记录按ref查询逐字比较，每个实体的属性、主张、关系、映射逐项比较，所有路径证据的SHA-256及字节边界核对。另用Python AST及直接Rust语法节点盘点类型和可调用定义，未用构造器自身计数充当外部真值。诊断全部遍历并保留；源码覆盖不等于业务解释或语义真值完整。

算法选样是Click `src/click/parser.py::_unpack_args`及regex `regex-syntax/src/hir/interval.rs::canonicalize`，结构契约、步骤证据引用及伪代码静态不完整标记均通过。未请求的其他函数算法保持未展开；本报告不声称项目全部行为语义或所有算法已获得。regex原生workspace查询返回7包并保存Cargo metadata原始输出，未当作7个语义模块；只执行--no-deps --offline，不声称完整依赖解析或构建通过。

## 成本与范围

两个项目每一条初次/重复请求的items、sourceRecords和diagnostics完全一致，重复请求解析0文件。各请求第一次执行可能复用前一请求的声明索引，不能把它称作整个项目的独立冷启动。耗时、解析次数、算法函数数、数据库体量及配置均在JSON中列出；两项目并行运行，耗时仅为该环境观察，不声明数值SLO或跨产品性能胜负。没有运行LLM，记录未使用，不宣称词元节省；平台实际为Linux，未测其他host/target组合。

## 发现的失败与修正

首轮Click全集构造发现无类型字段写入implementationType:null而违反封闭契约；用新失败用例复现后改为省略未知实现类型。随后验证增加了单实体查询不得携带其他实体诊断、opaque来源复用、来源路径消歧及仅存档案不得伪造算法覆盖的红绿回归。早期中断/失败运行保留在执行账本，不计通过结果。

## 复现

使用仓库本地Rust工具链时设置CARGO、RUSTUP_HOME、CARGO_HOME（见skill/README.md）；数据库路径必须不存在。以下命令分别为两项目执行，脚本提供--algorithm可重复选样，默认不降低未请求的全部函数：

```bash
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python scripts/verify_source_fact_refactor.py --project .local/real-projects/click --expected-commit 2247b35ea1c47c727d7a06e51fa280e12a863ff6 --store /tmp/c2s-v2-click-fresh.sqlite --output /tmp/c2s-v2-click-result.json --algorithm src/click/parser.py::_unpack_args
PYTHONPATH=src:skill/src .local/analysis-venv/bin/python scripts/verify_source_fact_refactor.py --project .local/real-projects/regex --expected-commit 94ac45b2a6e7b1c30927feb5b66c5ded5b7ad447 --store /tmp/c2s-v2-regex-fresh.sqlite --output /tmp/c2s-v2-regex-result.json --algorithm regex-syntax/src/hir/interval.rs::canonicalize
```

验证器6项测试包含故意删除来源记录、改动输入、破坏证据跨度、模拟查询丢主张，以及索引/普通投影等价；必须能发现这些错误。结果属于公开开发与集成证据，不是私有盲验收。默认切换及最终候选版本核验由任务10.10负责。
