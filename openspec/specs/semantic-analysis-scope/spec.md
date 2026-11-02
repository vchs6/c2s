# semantic-analysis-scope Specification

## Purpose

为语义事实分析明确已获用户确认的首期源代码语言范围，使后续能力和验收规划据此选择对象，同时将语言选择与版本、混合语言桥接、运行及目标平台、实测支持状态分开。

## Requirements

### Requirement: 首期源代码语言范围
系统 SHALL 将首期语义事实分析的源代码语言范围确定为Rust和Python。确认依据：用户2026-11-02原文“首期针对Rust和Python”，见docs/decisions/0003-initial-source-languages.md；此范围选择不表示具体版本、混合语言桥接或平台组合已经确认或验证。

#### Scenario: 首期语言范围进入规划
- **WHEN** 为首期选择分析对象和能力验收语言
- **THEN** 以Rust和Python为已确认语言范围，版本、混合边界及平台组合仍按各自确认与验证记录确定
