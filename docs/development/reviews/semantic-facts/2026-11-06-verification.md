# 语义事实原型验证记录

日期：2026-11-06。分析器：`c2s-semantic-facts/0.6.5`。

## 测试与检查

| 检查 | 命令/范围 | 结果 |
| --- | --- | --- |
| 产品测试 | `PYTHONPATH=skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -v` | 45/45通过；包括真实regex/Click全源解析、穷举验证所有真实函数的按需查询投影、局部绑定选择器以及Rust元组/结构体/枚举/切片/or/引用/捕获模式绑定提取 |
| 仓库维护测试 | `npm test` | 35/35通过 |
| M1契约和集成测试 | `npm test`，当前仓库 | 67/67通过，含32个语义模型契约/投影测试 |
| OpenSpec严格校验 | `npm run validate` | 21/21通过 |
| 制品完整性 | `npm run check:artifacts` | 通过：4个制品哈希、workflow文件和Superpowers版本 |
| Click上游测试 | 在`.local/real-projects/click`目录执行`PYTHONPATH=src /workspace/c2s/.local/analysis-venv/bin/python -m pytest -q .` | 2262通过、24跳过、31,000 deselected、1 xfailed |
| 全量真实项目事实遍历 | `PYTHONPATH=skill/src .local/analysis-venv/bin/python scripts/generate_semantic_fact_inventory.py` | regex：227/227源文件、54,315条事实、4,342个函数声明/3,395种查询目标；Click：91/91源文件、23,779条事实、1,897个函数声明/1,797种查询目标；批量按主体ID比对函数查询返回集合，全部匹配预期且事实ID唯一，输入检出干净；详情见同目录`2026-11-06-exhaustive-inventory.json` |
| Rust workspace元数据 | Cargo `metadata --no-deps --offline`，regex | 7个workspace成员成功解析 |
| Rust依赖测试 | `cargo test --workspace --offline`，regex workspace | 1,405通过、6跳过，稳定工具链；输出含上游deprecation/ABI warnings。未包含bench targets |
| Rust bench target | `cargo test --workspace --all-targets --offline`，regex | 依赖下载并完成常规编译后，在`regex-syntax/benches/bench.rs`因`#![feature(test)]`要求nightly而失败；不算全目标通过 |
| M1真实项目投影 | Click `project` 与 regex `workspace-members` 查询→M1投影→`validate_model` | Click 2项E0事实有效、无诊断；regex 7个成员、1个Cargo metadata附件、摘要verified、coverage complete、模型有效 |
| 隔离私有验收 | 当前环境 | 未运行；没有独立私有验收身份/用例环境 |

Click上游测试的一次初始尝试从monorepo根目录启动，导致依赖当前工作目录的glob测试失败；从Click检出目录重跑后得到表中通过结果。regex最初的`--all-targets`尝试在bench的nightly-only feature处失败；稳定可支持的`--workspace --offline`重跑通过。原始Click和regex检出在遍历和测试后均保持干净。

## 结论边界

E2声明、E3源码文档及部分E4语法事实可以按需查询。E4现包含部分赋值和局部绑定语句，但仍是静态语法证据。类型与调用绑定、跨函数数据流、完整控制流/异常传播、宏和条件编译语义、构建交付语义、运行时行为验证及完整E0–E4覆盖仍未完成。以上测试通过不证明项目全部语义事实已获取；查询响应中的`whole_project_semantics_complete`保持`false`。
