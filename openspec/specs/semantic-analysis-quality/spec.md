# semantic-analysis-quality Specification

## Purpose

为分层语义事实分析明确当前采用如实报告结果与缺口的评价边界，并由代理通过优化前后实际测试比较性能和Token消耗，避免依赖未经定义的严格语义正确性证明或编造收益。

## Requirements

### Requirement: 结果如实报告而不虚报严格正确性
系统 SHALL 如实报告取得的语义事实、获取边界和已知缺口，不要求当前先严格定义或证明语义结果正确性；用户要求但获取不到事实时须明确告知。此边界不取消结构/引用检查，也不允许编造事实、来源或验证结论。确认依据：ADR-0007，见docs/decisions/0007-confirmed-system-query-requirements.md。

#### Scenario: 无法证明完整行为语义
- **WHEN** 已取得部分静态事实但无法取得用户所需的完整行为内容
- **THEN** 报告实际取得内容和无法取得原因，不宣称严格正确或已完整获得，也不要求用户先给出完备语义金标才能查询

### Requirement: 性能与Token由优化前后对照评价
系统 SHALL 允许代理自行比较优化前后的性能及实际LLM输入输出Token消耗，记录输入、请求顶层范围、环境、结果及缺口变化；不预设当前必须由用户给定数值目标或严格正确率门槛，未测量不得宣称收益。确认依据：ADR-0007，见docs/decisions/0007-confirmed-system-query-requirements.md。

#### Scenario: 比较优化前后同一查询
- **WHEN** 对同一项目输入和查询开展优化前后测试
- **THEN** 报告耗时、实际Token及取得内容/缺口的差异，不将省掉所需事实或隐瞒缺口当作优化收益
