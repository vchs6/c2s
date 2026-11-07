# Tasks

## 现行范围说明

现行范围说明：就绪审核须复核本次全提案矩阵并确认无未处理模型冲突，严格校验只验证OpenSpec结构，不替代跨提案一致性审阅。

仅审核规划工作，非产品实施；不重复维护各子变更产品清单。

## 1. 一致性审核

- [x] 1.1 依据Issue#13和全部子工件，交付`docs/planning/program-2026-11-01/acceptance-matrix.md`、`overall-review.md`及本Issue Battle。检查：逐Requirement/Scenario与唯一tasks、独立双方两轮及新reviewer。通过：功能/非功能/语言平台/Token/恢复有归属，重大未决不伪批准；失败：缺引用、矛盾未列或候选当确认。

## 2. 候选清单与验证

- [x] 2.1 依据审核修订，交付`docs/planning/program-2026-11-01/bundle-manifest.json`、`verification.md`和台账。检查：逐文件SHA-256/集合摘要、全库严格validate、check:artifacts、git diff --check及正式基线/产品代码路径审计。通过：摘要可重算、未决列明、不冻结/不实施状态准确；失败：校验失败、摘要漂移或越界变更。

- [x] 2.2 按ADR-0012复核全部非归档提案与领域模型影响。交付：`docs/development/reviews/semantic-facts/semantic-entity-proposal-alignment.md`；验证：文件系统16项非归档提案全部各有且仅有一行结论，14项受影响项与实际改动一致，2项无影响项保留其原范围。此补充不将当前旧profile切换状态视为完成。
