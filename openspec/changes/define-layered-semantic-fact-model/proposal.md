# Proposal

## Why

Battle与三语言案例已形成候选模型，ADR-0001已确认五层组织方向，但活动变更只有脚手架，缺少可评审的公共契约与验收任务。研究文档不能替代OpenSpec；本变更补齐从决策、证据到规格的可追溯链。

## What Changes

- 定义语言无关的类型化主体、事实、谓词目录、上下文、证据与覆盖公共模型；采用DDD统一语言、身份和不变量，不预设聚合或存储。
- 明确E0工程组织与协作、E1构建装配与交付、E2程序结构与接口、E3操作行为契约、E4实现算法与局部语义。五层不是包含树或默认细化链。
- 定义独立项目、原生工作空间、协作集合、目标、配方、依赖需求/解析与查询范围的边界，以及来源声明与实际观测的区别。
- 定义操作契约、结构化算法与伪代码投影，并保留宏、注解、闭包、let绑定及语言特有求值/错误/资源语义。
- 为机器可读目录、Schema、校验与案例验收登记后续任务；本轮只交付规划工件，不把候选细节当成已批准实现。

## Capabilities

### New Capabilities

- `semantic-fact-model`: 五层事实组织、工程关系、主体身份、类型化事实语法、谓词目录、条件、模态、来源和覆盖的公共契约。
- `algorithm-description`: 操作行为契约、结构化算法、语言机制映射和可追溯伪代码投影。

### Modified Capabilities

无。`openspec list --specs`当前返回No specs found；以上为新增能力，尚未同步到主规格。

## Impact

本轮修改仅位于此活动变更。未来实现将新增`contracts/semantic-model/`公共定义、`tests/semantic-model/`验收资料及相应文档；这些路径是设计建议，尚未创建或实现。未选择获取器、数据库、聚合、事务边界或产品实现语言；不新增构建历史、任意语言完备性或形式等价证明服务，不改写导入研究原件，不同步主规格、不归档。

依据：`docs/decisions/0001-five-semantic-layers.md`（已接受的组织方向）；`docs/domain/proposals/language-independent-layered-semantic-model.md` §§1–17及`docs/development/reviews/2026-11-01/semantic-model-battle-report.md`（候选定义、反例与证据限制）。详细字段及语义是本活动变更的提议，供后续评审与实施。
