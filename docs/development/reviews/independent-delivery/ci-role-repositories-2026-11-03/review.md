# CI角色仓库公开探针独立审核

日期：2026-11-03。角色：独立公开基础设施代码/权限边界审核；请求模型gpt-6-astra、high。未访问连接器、凭据、真实私有suite或其他临时目录；未运行Docker、嵌套Codex或重复实现者的AST/help/缺Docker检查，未编辑实现或提交。

结论：在“可信宿主执行固定公开有限probe”的明确范围内，未发现阻断进入真实CI实验的新增实质缺陷。该结论是源码审核通过，不是容器边界运行通过；2.2.4必须等待真实远端五角色job和源token检查结果，父2.2/2.3/3.2及三个总门禁继续未通过。

## 审核基线和方法

已读根AGENTS、README、brief、implementer、review-package.diff、agent-governance/repository-management/ci、independent-delivery主规格、原change相关design/tasks/proposal差异；逐段核对实际workflow、完整prepare_role_repositories.py及role_repository_probe.py。实际计算新脚本SHA256为`80cc4c05ef8288e7eeefe87af1e5953cdeded3978cc6e3f6278599a6b7cc5c92`，与实现记录一致。OpenSpec status返回4/4规划工件完成；apply instructions仍显示2.2.4及父任务未完成，规划工件完成不作实施证明。

Skill记录：读取superpowers:using-superpowers；其SUBAGENT-STOP明确指示已分派的子代理忽略该流程，故本次只按明确审核委托执行，不将读取说明冒充完成另一套Skill工作流。

## 已核对的关键边界

- workflow第108–125行采用五个matrix job、GitHub托管ubuntu-24.04、最多并行3；只有固定角色名进入CLI。checkout固定action提交且不持久化凭据；新job只继承source-access-boundary的成功依赖，不接收该step的SOURCE_TOKEN。
- probe第276–310行从自身路径定位源码，要求GITHUB_SHA为40hex且等于HEAD；本次RUNNER_TEMP子目录内调用既有白名单快照准备器。宿主正控核对MANIFEST、五个role输入、内容摘要、HEAD和公开marker后才运行worker。
- 第328–338行只把所选仓库bind到/repo；实际run使用先pull/inspect得到并校验格式的digest。无源码根、其他角色、宿主根、socket或凭据挂载/环境传递；非root UID/GID、network none、只读根、cap-drop ALL、no-new-privileges、pids/memory/swap/cpu及ipc none均显式设置。HOST_ENV已无HOME键；DOCKER_CONFIG隔离保留。
- 第70–96、119–140行对受控公开路径的读写拒绝明确区分ENOENT/EACCES与其他错误，socket存在即不通过；不把缺少Git命令当权限拒绝。env -i加严格允许列表防止敏感环境正文进入worker或报告。
- 第223–273、347–366行提供宿主正向控制及运行前后五仓库树比较，仅允许自己固定公开输出新增，并另外检查该输出确实存在于宿主且内容正确。任一worker非零、超时、JSON大小/结构/布尔类型不符或任何检查false均不通过。
- 第339–346行finally只按随机唯一容器名执行有界强制删除；TemporaryDirectory只删除本次目录。失败错误仅输出固定类别，没有输出命令stderr、环境正文或marker内容。
- 第371–397行三个总门禁固定false；late cleanup异常也会关闭有限容器门禁。脚本没有模型请求、实际suite或任意candidate入口；不会因单个job成功放行完整角色交接。
- source-access-boundary第66–87行要求明确的vchs6/c2s-acceptance、排除source等于private，source 200且五类私有API均403/404才通过；禁代理和重定向防止token转发。硬编码目标消除了任意不存在仓库变量造成的配置伪通过。

## 非阻断的证据范围提示

1. `ci/acceptance/role_repository_probe.py:153–159` 的resource_limits实读pids.max、memory.max、cpu.max，但没有实读memory.swap.max；第332行确实配置了memory-swap与memory相等。本次可以陈述“swap限制已配置”，不能单凭resource_limits=true扩展为“swap限制已逐项实测”。若要报告全套cgroup约束的逐项实测，可在后续有限补充中核对memory.swap.max为0；不应因此把整个实验扩为任意candidate压力harness。
2. `.github/workflows/private-access-check.yml:85–87` 延续既有公开任务明确允许403/404的规则，未区分403的授权拒绝与限流等原因。源200是必要正控，但不能排除随后五次调用遇到非授权原因的403。因此真实run若为403，应把它报告为观测到的HTTP拒绝，并在认定持久权限隔离前另行确认原因；不能只凭此状态宣布完整访问权限证明。本轮新增的固定目标校验解决的是目标误配置，未解决全部HTTP拒绝语义问题。此为既有检查的证据限制，不是新增worker逃逸或私有suite泄漏发现。

## 仍需真实CI提供的证据

本地没有Docker，审核没有容器运行成功证据。托管runner是否实际满足cgroup v2路径、非root bind写入、镜像拉取/RepoDigest格式以及所有worker检查，须以该次绑定提交的远端五job结果回答；出现不兼容即保留失败，不修改断言假装通过。汇总还须记录源API五个实际状态、各role source_commit/image_digest与worker_checks，不能仅引用workflow总绿色。无论结果如何，native_subagent_scoping_verified、full_role_delivery_ready、development_ready继续为false。
