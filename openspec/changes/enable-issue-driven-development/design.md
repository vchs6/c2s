# Design

## Context

现有Issue worker有issues/issue_comment/schedule入口、全队列扫描及批准令牌到apply分支。用户明确要求关闭Issue自动工作，先修正仓库再创建规划事项。旧自动化验证只作为历史记录。

## Goals / Non-Goals

**Goals:** 手动指定一个Issue，维护者校验后仅规划或无模型检查；当前Runner不执行产品开发。工作方式支持在显式启动的会话内持续规划、分开方案与开发批准，并涵盖性能/成本等非功能指标。

**Non-Goals:** 不创建新的无人值守规划平台，不恢复API凭据或调用模型验证，不实施语义事实产品，不根据单Issue评论进入开发，不归档。

## Decisions

1. 保留workflow_dispatch而非删除整个维护工具；输入为正整数issue_number、plan/smoke操作及可选change_name。移除Issue/评论/定时入口；prepare在访问GitHub前拒绝非手动事件、非法编号或apply操作。当前用户授权的是工作流修正，非产品开发。
2. 仅读取指定Issue，调用方及Issue作者须具备write/maintain/admin；PR、机器人或非open Issue拒绝。不读评论批准，不扫描/反馈其他Issue；再次手动plan表示明确重新规划，不自动续跑旧apply。
3. 规划目标由手动输入或该Issue已有state.change_name确定；无既有变更时使用issue-N-planning。变更名只接受小写字母数字连字符，拒绝路径穿越。允许路径精确为该变更及本Issue评审目录；原受信脚本、规则、主规格和产品目录不可由模型规划补丁改动。
4. model入口只接受plan，publish拒绝apply上下文且在网络/提交前失败；方案/整体规划/实施批准分别记录。保留旧纯函数及历史回归用例以验证旧输入，但入口不再使用旧自动队列/approve分流；不能将旧函数中的apply分支视为可用入口。
5. 目录摘要检查扩展到任意已选OpenSpec变更的全部文件，新增规划文件使旧摘要失效。讨论和plan均可形成提案/规格，重大设计未定时明确阻塞，不凭空填实现任务。
6. AGENTS与planning-mode.md规定委托决策、人工例外、议题清单、功能/非功能指标及统一开发门禁。此为会话治理，不声称当前Runner实现跨Issue自动调度；显式启动后的主代理可在授权范围连续推进。无人值守扩展若需要，另提案。

## Risks / Trade-offs

- [Risk] 已排队的旧版本Actions仍可能运行 → 发布前读取工作流运行状态；如果存在进行中的旧Issue worker，先停止/报告，不创建会触发旧自动入口的新Issue。
- [Risk] 只删事件仍可因旧批准进入实现 → 手动选择器忽略评论令牌，model/publish双入口拒绝apply。
- [Risk] 新规误作已完成自动平台 → 明确只有手动入口和会话治理；远程模型可用性未重新验证。
- [Risk] 旧工件与当前授权冲突 → 保留历史说明并以当前AGENTS/新用户决定为准，不静默重写产品基线。

## Migration Plan

先添加并观察失败的入口/触发/范围回归，再实现控制修改，更新规格/规则/文档并严格验证。直接提交main，核对远程workflow只包含手动入口，确认无旧运行后才创建后续规划Issue。后续产品开发必须另行获得整体规划及实施授权；当前Runner没有apply选项。不自动archive。

## ADR-0013 当前约束（2026-11-08）

手动启动、Issue不自动执行及授权边界继续有效；治理工作不引入DDD模型要求。产品工作量按本次请求的上游事实及证据衡量。 依据：`docs/decisions/0013-非DDD语义事实模型.md`。历史执行记录中的DDD或旧模型表述不构成现行约束。本轮只进行文档修订，产品重构完成状态不变。
