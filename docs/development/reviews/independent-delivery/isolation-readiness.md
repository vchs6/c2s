# 当前开发环境完整就绪核验

日期：2026-11-03。核验基线：610e3540d35efadeb0fe573464c7dbfdfbd7afba。对应原change唯一任务2.2/3.2，不新增重复准备子任务。

**结论：BLOCKED，不能放行要求双向盲编写的产品开发。** 本次完成可执行检查，并明确记录依赖失败而未运行的端到端检查；不声称整条链路已运行。用户授权已成立，当前问题是执行能力而非缺少批准或API余额。机器记录：full-readiness-2026-11-03.json。

## 实际核验

| 检查 | 结果 | 准确范围 |
| --- | --- | --- |
| ChatGPT登录 | PASS | 当前CLI的login status返回Logged in using ChatGPT；未读取或复制认证内容 |
| 原生模型工作 | PASS | 新上下文audit_full_readiness实际完成核验；不代表工具已按角色受限 |
| 公共工具、自维护检查 | PASS | 工具自检；严格21/21；维护测试35/35；4项工件摘要；diff检查 |
| CI执行边界 | PASS，既有实跑证据 | run41573123198两角色各18项检查；不是本轮新跑，不冒原生模型隔离 |
| 最新发布基线维护CI | PASS，读回 | run41573332117、job125711059030，绑定610e3540 |
| 当前原生coding不得读author | FAIL | 独立代理在coding cwd仍能以相对/绝对路径读取author公开marker |
| 当前原生author不得读coding | FAIL | 独立代理在author cwd仍能读取coding公开基础设施源码 |
| 固定合成交接控制 | PASS | 当前SHA下4项准备、5项交接检查通过；不是实际产品交接 |
| 实际产品编写→组合测试→修复→重验→恢复 | 未运行 | 双向权限前置失败，不在共享区生成真正私有用例 |
| 实际产品独立最终结论 | 未运行 | 没有上述真实执行证据 |

## 当前失败的定位

独立代理使用从固定基线白名单生成的.local/full-verification-2026-11-03/roles公开仓库执行只读测试，未创建业务实现或隐藏用例。两条读命令均exit0，三个禁止读取检查均实际成功。它验证的是当前原生入口，而非旧嵌套CLI，也不是推测余额是否充足。

当前暴露的spawn_agent参数只有task_name/message/fork_turns/model/reasoning_effort，没有角色文件系统、工具allowlist、挂载、连接器或权限配置。工作目录、AGENTS提示、独立Git对象库、修改仓库内config不能为该接口补上强制访问边界。当前会话也无可用Docker/Podman命令；这不妨碍确定性托管CI，但它们的权限不会自动施加到当前原生代理。

官方资料已核对：

- https://learn.chatgpt.com/docs/agent-configuration/subagents ：Work子代理使用父会话工具；本地Codex自定义代理的配置不能被当作当前云端spawn入口已经支持的参数。
- https://learn.chatgpt.com/docs/auth/ci-cd-auth ：ChatGPT认证的可信私有CI有单独的认证维护约束；不能将当前会话已登录推导为远程CI已登录。本次不复制认证、不将认证注入公共仓库workflow、不改回API。

## 最小解除条件

先获得平台支持的ChatGPT认证角色启动/工具代理入口，能够对编码/作者的整个有效工具面落实双向输入限制，包括终端、文件、应用连接器与管理旁路；随后将固定输出交给现有确定性CI。角色只能使用该入口，不能保留继承宿主全权工具的旁路。该能力缺失不能通过更多公开marker、仓库文件或模型自述补齐。

真实角色的合法读写及相互读取拒绝通过后，才接续原2.3：真实candidate/suite/契约/输入/环境绑定；候选进程拒读suite；受控失败反馈与修复重验；旧证据失效；中断恢复；独立verdict。全部通过才更新development_ready；不重复索取既有开发授权，不自动archive，不保证无人值守后台任务已启动。

## 使用的Skill与独立结论

using-superpowers、systematic-debugging、OpenAI Docs、requesting-code-review、verification-before-completion。只使用确定性工具做版本/测试核对；原生audit_full_readiness独立核验能力边界及公开访问反例，结论BLOCKED。没有为测试执行调用API。

## 独立实测可复现命令

先用公开prepare_role_repositories.py从核验基线准备上述.local目录；下述文件均为公开基础设施，不是真实私有用例。

在roles/coding工作目录执行：

```bash
python3 - <<'PY'
from pathlib import Path
import json
for label,path in [('coding_relative_author_marker','../author/PUBLIC_SYNTHETIC_MARKER.txt'),('coding_absolute_author_marker','/workspace/scratch/7d97b2f44197/c2s/.local/full-verification-2026-11-03/roles/author/PUBLIC_SYNTHETIC_MARKER.txt')]:
    try:
        Path(path).read_bytes()
        success=True
    except OSError:
        success=False
    print(json.dumps({'probe':label,'read_success':success}))
PY
```

在roles/author工作目录执行：

```bash
python3 - <<'PY'
from pathlib import Path
import json
try:
    Path('../coding/scripts/check_public_environment.py').read_bytes()
    success=True
except OSError:
    success=False
print(json.dumps({'probe':'author_relative_coding_script','read_success':success}))
PY
```

两次exit0，三个read_success均true。没有尝试未公开的工具参数，不修改宿主控制，不启动旧嵌套CLI。

## 报告独立复核

audit_full_readiness只读复核本报告、机器记录、交接报告、readiness与原tasks：报告准确性PASS、整体就绪BLOCKED，无需修正的发现。跨角色读取及工具参数由审查者亲测；登录、工具版本、维护检查及CI读回由协调者执行并记录，审查者未冒称重复执行。父门禁未勾选，旧API余额不再作为当前模式前置。
