# 已确认规格基线验证记录

日期：2026-11-01。读取基点：`bb1b44d04e8254b9174a6ac365ffce942b5e5cb1`。变更：`define-layered-semantic-fact-model`，schema：spec-driven。

## 结果与边界

本轮固化两份主规格：semantic-fact-model 3项Requirement、semantic-fact-query 4项Requirement，每项均有Scenario及ADR-0002确认依据。两份主规格与确认delta仅标题和Requirements标头不同；algorithm-description没有主规格。候选事实模型原文从Git基点精确保留，导入原件未改。

本轮仅完成规格与必要规划，不实现公共目录、Schema、校验器、获取器、查询Skill或存储。原10项产品任务保持未完成。新增0组3项任务仅表示确认整理、规格同步及规划验证。CLI planning complete或apply ready不等于实施批准或产品完成；未执行archive。

## 实际工作流

使用已安装的OpenSpec更新/规格同步Skill；实际读取Superpowers using-superpowers、brainstorming、writing-plans、executing-plans、verification-before-completion。出现格式校验失败时读取并按systematic-debugging定位。没有第二份执行清单，全部任务归tasks.md。

brainstorming围绕已有候选整理固定约束、比较身份/关系/状态/算法/格式选项及反例，未选定新产品方案；讨论记录明确awaiting-decision。已确认需求不重新提问。没有开展新的Battle，也没有把既有Battle当用户确认。

## 实际命令及结果

所有OpenSpec命令均在仓库根目录通过`npm run openspec -- ...`执行，设置`OPENSPEC_TELEMETRY=0`。

| 命令/检查 | 实际结果 |
| --- | --- |
| `git clone https://github.com/vchs6/c2s.git` | 成功，起点为上述提交 |
| `npm ci --no-audit --no-fund` | 成功，安装固定开发依赖 |
| `git submodule update --init --depth 1` | 成功，Superpowers固定提交2ce8aa15d05bd57213e6f746f953aafb7ded7a8b |
| `npm run openspec -- list --json` | 成功，root为本仓库，3个活动变更 |
| `npm run openspec -- list --specs` | 修改前No specs found；本轮创建两份确认主规格 |
| `npm run openspec -- status --change define-layered-semantic-fact-model --json` | 成功，按artifactPaths读取/选择delta，不使用glob作文件名 |
| `npm run openspec -- context --change define-layered-semantic-fact-model --json` | 首次失败：context不接受--change；读取帮助后改用下一行 |
| `npm run openspec -- context --json` | 成功，repo-local上下文 |
| `npm run openspec -- instructions <artifact> --change define-layered-semantic-fact-model --json` | proposal、specs、design、tasks分别成功；写工件前实际取得模板、依赖及规则 |
| `npm run openspec -- instructions apply --change define-layered-semantic-fact-model --json` | 实际读取，确认原10项未完成；仅执行本轮0组文档任务，未继续产品任务 |
| `npm run openspec -- validate --specs --strict --no-interactive` | 2 passed，0 failed |
| `npm run validate` | 最终5 passed，0 failed：3个活动变更及2份主规格 |
| `npm run check:artifacts` | PASS：4原件哈希、工作流必需文件及Superpowers 7.0.1 |
| `git diff --check` | 最终通过 |
| 临时Python只读审计 | 两份主规格逐项来源/Scenario、delta同步等价、候选原文保留、算法未同步、10项产品任务未完成全部通过 |

首次全量严格校验因algorithm-description delta首节之前的候选状态文字而失败；复现JSON诊断后，移除该新增首节外文字，候选状态保留在proposal/design/ADR。未改变算法候选需求正文。之后diff检查发现tasks末尾多余空行，已清除。最终重跑严格校验及工件检查通过。npm的环境http-proxy弃用警告不影响退出码；未为此修改宿主配置。

## 独立复核与处理

按executing-plans的最终复核要求启动一个只读独立子代理，检查确认依据、候选隔离、主规格/delta一致性及未完成状态；这不是Battle，也不是用户批准。复核确认候选原文保留、主规格7项映射、算法未同步和10项产品任务未完成。

复核指出两处规划歧义，已修订并自行复查：design不再写“主体查询收集所有相关事实”，明确内部检索未定、响应受最小查询边界约束；tasks 5.1限定为届时批准的模型/算法契约验收，查询实现另行规划。修订不改变确认主规格。

## 尚未完成

Q01–Q05等候选设计仍待必要确认；公共模型/算法机器可读契约及查询流程均未实施，产品测试未新增也未运行。不将仓库工具检查当作产品行为验证，不归档活动变更，不改变Issue自动状态或审批令牌。
