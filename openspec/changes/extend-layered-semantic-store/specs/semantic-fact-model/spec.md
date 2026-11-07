## ADDED Requirements

### Requirement: 全层存储保留完整语义模型

语义仓库 SHALL 保留`semantic-fact-model-1`所有顶层记录集合（registrations、assessments、facts、evidence、coverage、dependencies、dependencyResolutions、semanticStates、diagnostics、contextDomains、contexts），不得只保存M1子集或将整次查询JSON作为唯一记录。规范化与去重 MUST 保持事实主张、层级谓词、主体身份、条件、证据角色、派生前提、覆盖、上下文和所有内部引用；不同层关联不得被转换为隐式包含关系。

#### Scenario: 持久化算法事实

- **WHEN** 一个有效全量bundle包含AlgorithmDescription、BehaviorBody、BehaviorRegion和BehaviorStep事实
- **THEN** 仓库保留各类型身份、算法步骤关系、证据引用及覆盖状态，读回后通过同版本语义契约校验

#### Scenario: 保留补证与冲突

- **WHEN** 相同语义主张获得新独立证据，或同条件出现不兼容主张
- **THEN** 新证据关联到规范主张而不复制主体；不兼容主张双方均保留并保留诊断
