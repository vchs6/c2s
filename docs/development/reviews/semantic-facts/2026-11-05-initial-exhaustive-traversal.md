# 首次真实项目全源语法遍历

日期：2026-11-05。范围：当前Python/Rust语法、源码文档及显式工程声明原型，不代表全部E0–E4语义完成。

> 这是2026-11-05的历史基线。2026-11-06先修正了Python函数声明的E2分类及装饰器调用误计入函数体步骤的问题，随后补入Python赋值和Rust `let` 局部绑定的E4语法事实。最新click事实数为21,324（此前基线20,582）；最新完整结果及逐文件事实ID以[2026-11-06清单](2026-11-06-exhaustive-inventory.json)为准，两个函数的例子见[双函数事实示例](2026-11-06-two-function-facts.md)。

## 固定输入与执行

| 项目 | 固定提交 | 语法源文件 | 完整解析 | 当前支持事实 | 语法树节点 |
| --- | --- | ---: | ---: | ---: | ---: |
| rust-lang/regex | `94ac45b2a6e7b1c30927feb5b66c5ded5b7ad447` | 227 `.rs` | 227 | 45,077 | 1,178,011 |
| pallets/click | `2247b35ea1c47c727d7a06e51fa280e12a863ff6` | 91 `.py` | 91 | 20,582 | 128,806 |

支持类别数量：regex含33,439个algorithm_step、2,403个behavior_contract及9,233个程序声明；click含14,388个algorithm_step、628个behavior_contract及5,564个程序声明。两者各含显式项目名/语言声明2条。

执行器：Python 3.12.14；tree-sitter 0.26.0、tree-sitter-python 0.25.0、tree-sitter-rust 0.24.2。来源树在遍历后 `git status --short` 为空；两个HEAD均与表内固定提交一致。

Click上游测试另以锁文件pytest 9.0.2执行：`PYTHONPATH=/workspace/c2s/.local/real-projects/click/src /workspace/c2s/.local/analysis-venv/bin/python -m pytest -q`，结果为2262 passed、24 skipped、31,000 deselected、1 xfailed。Rust工具链现已安装；`cargo metadata --no-deps --offline` 成功解析regex的7个workspace包。`cargo test --workspace --all-targets`仍未能编译：HTTP请求连不上配置代理`proxy:8080`，offline缓存缺少`aho-corasick`。这不是Rust测试通过证据。

遍历命令：

```bash
PYTHONPATH=skill/src .local/analysis-venv/bin/python - <<'PY'
from pathlib import Path
from c2s_skill.acquisition import scan_project
from c2s_skill.query import query_from_scan
for project in ("regex", "click"):
    scan = scan_project(Path(".local/real-projects") / project)
    result = query_from_scan(scan, ["all-supported-facts"])
    print(project, scan.source_files, scan.parsed_files, scan.fact_count,
          scan.syntax_node_count, len(result.facts), result.complete)
PY
```

产品原型测试：

```bash
PYTHONPATH=skill/src .local/analysis-venv/bin/python -m unittest discover -s skill/tests -v
```

测试逐项核实Python UTF-8字节位置、Rust结构体/字段/实现/函数/源码文档、控制流和调用步骤、两项目全部可识别源文件解析、每个扫描事实及Cargo工作区成员均在`all-supported-facts`查询返回且ID唯一、跨层主体共享ID、JSON/Markdown事实ID与源码证据一致、查询输出符合JSON Schema、未知选择项保留gap、格式错误在扫描前拒绝、缓存配置变更失效、缓存写入失败保留事实并单独报告、项目内缓存路径不创建文件、隐藏/忽略/测试/嵌套文件纳入盘点以及符号链接不跟随。新增逐文件事实ID与未处理路径清单见`2026-11-05-exhaustive-inventory.json`。

## 后续覆盖清单

`2026-11-05-exhaustive-inventory.json` 固定记录了每个`.py`/`.rs`文件的SHA-256、解析状态、诊断、事实数与全部事实ID；另记录Cargo解析出的7个regex workspace成员、每个项目全量结果的唯一ID总数、跨层共享主体分组、源码摘要及所有未处理目录项。该文件及本报告中的click数量是修正前的历史结果。最新复跑数字和清单见上方2026-11-06报告链接；两个项目的`whole_project_semantics_complete`仍为false。

## 解释边界

每个被纳入解析的源文件均被解析，没有语法解析失败；所有解析器产生的支持类别事实均能被全量selector取回。这不证明语义事实真值完整。没有类型绑定、跨文件调用解析、宏展开、条件编译全部分支或运行时行为验证。E3目前只记录源码显式文档，不验证陈述真伪；E4只记录常见算法语法结构，不提供已验证的算法语义解释。Cargo workspace成员解析、Python打包边界、构建交付和工程协作语义仍待实现。`complete`只表示所选类别的语法遍历成功，JSON另有`whole_project_semantics_complete=false`。不能据本报告称“所有语义事实遍历完成”。私有独立验收未运行。
