# 两个 Python 函数的代码级语义事实示例

项目：Click 示例 `examples/naval/naval.py`。
固定提交：`2247b35ea1c47c727d7a06e51fa280e12a863ff6`。
查询：`all-supported-facts`，按共享 `subject_id` 投影目标函数。
分析器：C2S semantic facts 0.6.4。静态 AST 证据，不代表运行时验证。

## `ship_move`

- 主体 ID：`fe8b822ab1e371429b99a35dd8e96aaac9ccbeda7b5a86e54bf00f25bcf76778`
- 函数声明：E2，`examples/naval/naval.py:641-788`；fact ID `45eed60532150d3c6fb47cc0ecc8668345b635716f59b0268a167f7b0198ceac`。
- 源码文档：E3，"""Moves SHIP to the new location X,Y."""（fact ID `c46b35ff2fdd19cb1ce2fa23442715cc1b9d944eebb3080e1af5fddefe5fd6a0`）。
- 函数体代码事实：
  - E4 `Call`，第 34 行，fact ID `257e75b04b3bd00e5de5b660ae72385b1b73e78d820e654851b005c7e3242a86`：`click.echo(f"Moving ship {ship} to {x},{y} with speed {speed}")`
- 本函数共 3 条当前支持事实。

## `ship_shoot`

- 主体 ID：`4d7ff8ffb514c6b763d059f1b7d8c364f94d961a20c3fcf3d236ce73675beb80`
- 函数声明：E2，`examples/naval/naval.py:904-1013`；fact ID `c9fa1d589e563be4c2b7c3ba8ca1b2a5e77d168dfbfc61cc0090d2e9fef91d18`。
- 源码文档：E3，"""Makes SHIP fire to X,Y."""（fact ID `6b862b5ef76b4689d08fc84c941b0eb9056bc5289408e249d513657027700922`）。
- 函数体代码事实：
  - E4 `Call`，第 43 行，fact ID `59541a8776edcaa40059557b6ae8e4104f15573ae8dd5ad0ca5ec015195764c7`：`click.echo(f"Ship {ship} fires to {x},{y}")`
- 本函数共 3 条当前支持事实。

边界：调用目标解析、变量/类型绑定、跨函数数据流、异常传播和运行时效果尚未完成；本报告只陈述语法树与源码文档中直接可见的事实。
