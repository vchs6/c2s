# Semantic Analysis Scope

## Purpose

为语义事实分析明确用户已确认的首期源语言及平台定义，区分Skill宿主、与其平台一致的分析工具和依据项目构造编译环境确定的项目平台，使范围选择不被误读为全部版本和组合已经验证。

## ADDED Requirements

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
