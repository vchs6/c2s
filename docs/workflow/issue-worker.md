# 手动规划维护工具

当前Issue只登记议题。创建、编辑、重开、标签、评论（含旧/c2s approve、retry）和定时任务均不触发工作；不扫描待办队列。推送仍可触发普通CI检查，CI不调用模型、不处理Issue。

## 显式启动

推荐在Work/Codex会话明确指定总计划或某个Issue，授权会话按规划议题依赖持续推进。若使用Actions维护工具，在Actions → Issue worker → Run workflow中输入：

- issue_number：一个正整数Issue编号，必填，不能all或留空。
- operation：plan或smoke，默认plan；没有apply选项。
- change_name：可选，复用已有OpenSpec变更的精确标识；否则使用该Issue既有state.change_name，最后才使用issue-N-planning。

调用者及Issue作者须有write/maintain/admin权限；PR、机器人或非open Issue不进入工作。工具仅访问指定Issue，不因评论或旧令牌授权而实施。再次手动plan表示明确重新规划，不自动恢复旧apply。OPENAI_API_KEY仅为手动plan的模型凭据，网页登录不能替代；缺密钥明确blocked，smoke不调用模型。

## 当前范围

手动plan先实际读取并使用brainstorming形成中立问题包，再进行独立双方首轮、交叉质询及独立综合；写工件会话读取实际OpenSpec instructions，产出提案/规格/设计及适用任务，保持产品任务未实施。缺少重大决定时列明确决策请求；不拿代理共识冒充用户确认。跨语言/跨平台及非功能指标须纳入规划。

当前Runner仅处理一次明确指定的Issue；它不是跨Issue无人值守调度器。会话内主代理可在用户授权范围连续推进，详见planning-mode.md。真实模型调用本轮未验证；本地入口/路径/门禁测试不能替代模型验证。

模型只可修改本Issue的docs/development/reviews/issues/N/及精确选定的openspec/changes/<change_name>/。不改产品src/tests/contracts、主规格、规则、workflow、发布脚本、认证或上游工具。复用变更不能改其他变更；维护者明确授权的工具修正另行处理，不由模型规划补丁自行扩权。

model入口拒绝非plan；publish入口拒绝apply，均在相关副作用前失败。方案确认、整体规划审核和开发批准分离，单Issue令牌只是规划指纹；当前Runner不接受其作为产品实施入口。包括此前Issue #3在内的方案选择继续保留，但旧令牌不能绕过当前“整体规划完成后另批开发”的门禁。

## 验证与发布

Python3测试、原件哈希、OpenSpec严格校验和diff检查通过后才可发布；发布检查当前Issue与main基点、精确补丁范围及文件模式，不force，不自动关闭Issue或archive。缺模型/失败明确blocked；移除自动事件后，修复问题必须再显式手动启动，不由评论或补扫自动恢复。

## 历史资料

旧Issue事件/15分钟补扫/approve→apply的说明和运行记录是历史行为。本次修正替代该入口；不改写旧报告假装它们验证了当前模式。参考docs/development/reviews/manual-planning-switch.md。

当前Actions的plan用于实质性领域/架构议题，保守执行完整Battle，不声称已实现自动争议识别或最省Token路由。机械性文档修订在显式授权会话内直接处理，不反复启动Runner plan；具体讨论预算与代理调用策略纳入非功能指标议题后再优化。

## 状态与检查环境

维护评论使用末尾唯一的`c2s-state-v1`编码载荷，读取时校验完整状态字段、时间与运行地址。旧明文状态标记不再作为恢复依据；模型原因只作为转义后的展示文本，不能注入控制标记。只接受可信Actions Bot的有效载荷，评论仍不能启动工作或授权实施。

确定性检查同时运行顶层和Skill测试；子进程仅继承PATH、HOME、语言/时区/临时目录及明确的Cargo/集成测试配置，PYTHONPATH由仓库路径构造，遥测关闭。环境白名单不等于文件系统隔离或私有盲验收。
