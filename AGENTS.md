# c2s代理入口

开发软件项目语义事实提取Skill，遵循DDD、OpenSpec及Superpowers。先读README和本次任务相关规格、变更及下表所需文档，按需加载，不重复通读全部资料。

## 当前授权与工作边界

最新用户授权见`docs/decisions/0009-continuous-development-authorization.md`：先完成准备，门禁通过后连续开发；必要工具/Skill自行安装，不逐任务重复索批。用户确认优先于旧planning-only说明。Issue/评论/标签/定时仍不启动工作，不自动archive。

用户在2026-11-05明确要求放宽双向盲编写和私有验收隔离门禁，以保证开发可继续；详见ADR-0011。可以按原tasks继续产品开发、开发侧测试及公开CI，不再等待角色入口或私有验收隔离通过。必须如实标明当前共享工作区的权限限制，不得声称独立盲编写、私有suite隔离、私有验收或完整交接已通过；不可访问或不存在的私有suite不得伪称已运行。重大领域/范围决策仍按既有规则处理。M0证据与旧失败记录见`docs/planning/program-2026-11-01/readiness.md`。

当前工作模式与例外见`docs/decisions/0010-bidirectional-blind-development.md`及ADR-0011：双向盲编写是目标质量模式，不再是开始开发的先决条件；当工作区权限不支持隔离时，按透明、非盲模式推进并记录限制。审核/执行/验证按职责读取，固定CI不必调用模型。

## 按任务读取

| 任务 | 必读文档 |
| --- | --- |
| 领域/公共契约 | `docs/domain/foundation.md`、相关`openspec/specs/`、ADR-0001至0008及原模型变更 |
| 范围/架构/资源 | `docs/project/constraints.md`及相应design |
| 角色/执行/证据 | `docs/workflow/agent-governance.md` |
| 新取舍/反例/需求变更 | `docs/workflow/decision-policy.md`；实质领域争议再读`battle-protocol.md`并真实独立讨论 |
| 任务规划/分派 | `docs/workflow/task-decomposition.md`及原change唯一tasks |
| 提交/CI/发布 | `docs/workflow/repository-management.md`、`ci.md` |
| 手动维护工具 | `docs/workflow/issue-worker.md`，其Runner仍只plan/smoke |

## 必须实际执行

1. 先用using-superpowers；未决设计用brainstorming，多步计划用writing-plans，执行按适用执行Skill，完成声明前用verification-before-completion。用户双向独立验收要求优先于默认同上下文编写验收与实现流程。
2. 执行`npm run openspec -- status --change <name>`及适用逐工件instructions；实施前取得apply instructions并读返回contextFiles。CLI不自动代写正文，文件存在不等于产品完成。
3. 复用已有变更；公共契约单点归属，唯一tasks不复制为第二计划。已确认需求不重开；不能把代理共识冒用户确认。小型技术选择在委托内裁定并记录，重大变化给具体反例及影响。
4. 合格授权工件直接main，先实际严格校验及适用检查，读回发布结果。不提交认证、私有suite/日志、node_modules、.local或宿主会话；不改导入原件和tools/superpowers上游。
5. 自维护脚本/测试Python3。产品版本0.b.c（a固定0），工具/契约版本分开；最终Skill README必须列实际依赖、来源/版本、安装自检、平台范围及副作用。
