# semantic-analysis-scope Specification

## Purpose

为语义事实分析明确用户已确认的首期源语言及平台定义，区分Skill宿主、与其平台一致的分析工具和依据项目构造编译环境确定的项目平台，使范围选择不被误读为全部版本和组合已经验证。

## Requirements

### Requirement: 首期源代码语言范围
系统 SHALL 将首期语义事实分析的源代码语言范围确定为Rust和Python。确认依据：用户2026-11-02原文“首期针对Rust和Python”，见docs/decisions/0003-initial-source-languages.md；此范围选择不表示具体版本、混合语言桥接或平台组合已经确认或验证。

#### Scenario: 首期语言范围进入规划
- **WHEN** 为首期选择分析对象和能力验收语言
- **THEN** 以Rust和Python为已确认语言范围，版本、混合边界及平台组合仍按各自确认与验证记录确定

### Requirement: Skill宿主与分析工具运行平台一致
系统 SHALL 将host解释为Skill宿主运行的平台；宿主可能运行于Windows、Linux、macOS等操作系统，分析工具的运行平台 SHALL 与Skill运行期平台一致。确认依据：用户2026-11-02明确说明，见docs/decisions/0004-host-and-project-platforms.md；这不是所有平台组合已验证的声明。

#### Scenario: 在不同宿主平台选择分析工具
- **WHEN** Skill运行于Windows、Linux或macOS宿主之一
- **THEN** 选择与该Skill运行期平台一致的分析工具，不能把其他平台的工具默认视为本机可运行

### Requirement: 项目平台依据构造编译环境
系统 SHALL 依据被分析项目设定的构造／编译环境确定并解释项目平台，不得仅由Skill宿主平台推定。确认依据：用户2026-11-02明确说明，见docs/decisions/0004-host-and-project-platforms.md。

#### Scenario: 宿主与项目设定平台不同
- **WHEN** Skill在Linux宿主运行，而被分析项目的构造／编译环境设定面向Windows
- **THEN** 分析工具运行平台仍与Linux宿主一致，项目语义按其Windows构造／编译环境解释，不因host为Linux而改作Linux项目

### Requirement: 负载范围依据实际测试确定
系统 SHALL 允许当前规划不预先固定负载范围，并在实际项目分析阶段依据实际测试结果确定和记录适用范围；负载范围尚未确定不得单独作为当前规划冻结前置阻塞。确认依据：用户2026-11-02明确说明，见docs/decisions/0005-defer-workload-scope-to-measurements.md。

#### Scenario: 当前尚无实际负载测试
- **WHEN** 当前只有规划且尚未取得实际项目分析测试结果
- **THEN** 负载范围保持延期，不猜定规模且不因此单独阻塞当前规划；实际分析测试后再据结果记录适用范围

### Requirement: 单次分析期间项目保持不变
系统 SHALL 以一次分析期间项目输入保持不变为分析前提；在该前提下按查询补充尚未取得的事实，不将分析内的事实增量取得解释为项目源码持续变化。确认依据：用户2026-11-02原文“每次分析过程中，项目不会发生任何变更”，见docs/decisions/0006-stable-project-during-analysis.md；此确认不决定跨次分析的更新政策。

#### Scenario: 固定项目输入上的后续查询
- **WHEN** 同一次分析中项目保持不变，后续查询需要此前尚未构造的内容
- **THEN** 在该分析输入下复用适用成果并补充所需内容，不要求通过项目热更新流程才能取得新增事实

### Requirement: 指定目录内内容纳入分析范围
系统 SHALL 将用户指定存储目录中的内容纳入待分析范围，不仅限于主项目或主src目录；具体语义按用户查询触发取得，不因范围包含全部内容而预先构造全目录事实。目录成员与Project工程身份仍按领域模型分别判断。确认依据：ADR-0007，见docs/decisions/0007-confirmed-system-query-requirements.md。

#### Scenario: 目录包含多个及嵌套项目
- **WHEN** 指定目录同时包含主项目、嵌套项目、测试、示例或基准相关内容
- **THEN** 这些内容均在分析范围内，按本次请求取得必要事实；不能静默排除某类目录，不能取得的事实报告原因

### Requirement: 必要分析操作由设计选择执行
系统 SHALL 允许由设计选择并执行取得请求所需语义事实的必要分析操作，不以固定只读或逐操作重新批准作为用户需求前置；执行仍须保持被分析项目在本次分析期间不变，并遵守实际执行环境权限。此项授权指产品分析能力，不启动本轮产品开发。确认依据：ADR-0007，见docs/decisions/0007-confirmed-system-query-requirements.md。

#### Scenario: 获取事实需要构建或宏相关操作
- **WHEN** 为取得本次所需事实，所选工具需要执行构建、宏展开或其他必要分析步骤
- **THEN** 可按设计执行并保持被分析项目不变；环境或工具不能执行时明确报告获取不到及原因，不假称已执行或已取得
