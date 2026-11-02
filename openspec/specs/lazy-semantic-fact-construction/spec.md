# lazy-semantic-fact-construction Specification

## Purpose

为用户查询驱动的分层语义事实分析固定首次按需启动和同主体后续补充行为，避免预先全目录构造或重复已完成工作，并以明确缺口报告代替无法取得内容的猜测。

## Requirements

### Requirement: 查询触发按需分析
系统 SHALL 在用户查询指定目录中项目的语义事实时，若所需内容尚未分析，直接针对该查询开始必要分析，不要求用户先执行全目录完整分析；响应仍只返回符合本次请求的顶层事实。确认依据：ADR-0007，见docs/decisions/0007-confirmed-system-query-requirements.md。

#### Scenario: 首次查询尚未分析的函数
- **WHEN** 指定目录中的函数尚未分析，用户请求其定义或实现事实
- **THEN** 针对该请求开始分析并返回已取得的所需顶层事实；无法取得的部分明确告知原因

### Requirement: 同主体后续查询仅补未完成内容
系统 SHALL 对同一主体的多次查询复用已完成且适用的分析内容，仅补充当次请求尚未完成的部分；不因已有部分结果而省略本次仍需取得的顶层事实，不把此前未取得当成不存在。确认依据：ADR-0007，见docs/decisions/0007-confirmed-system-query-requirements.md。

#### Scenario: 函数结构已分析而实现尚未分析
- **WHEN** 同次固定项目输入下已取得某函数结构事实，后续请求还需要其实现语义
- **THEN** 复用已得结构与适用证据，仅补本次尚未完成内容，不重复全量分析或要求源码发生变化
