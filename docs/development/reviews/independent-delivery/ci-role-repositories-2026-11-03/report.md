# CI平级角色仓库边界公开试验

用户选择实际测试CI方式。复用现有GitHub托管Ubuntu24.04和private-access-check工作流，原change唯一tasks 2.2.4。没有请求用户迁移环境、重做登录或配置模型凭据；只测试公开基础设施，不调用模型或创建隐藏suite。

## 执行设计

源token job以contents:read检查源repo可读，以及明确配置的vchs6/c2s-acceptance元数据/历史/workflows/runs/artifacts不可读。协调者另通过连接器核实该目标仍private，只读元数据，不获取私有suite。源token不传入worker；目标配置若指向其他不存在项目则拒绝而非伪通过。

五个matrix job分别运行coding/review/author/runner/verifier公开probe，最多并行3。每个job的可信准备宿主仍能访问它自己创建的五份公开快照；被测角色worker只挂选定的一个仓库到/repo。worker非root、无网络、根只读、drop caps、no-new-privileges、限制进程/内存/CPU且不挂Docker socket、其他角色仓库或宿主root。宿主可读其他marker是正控制，worker合法自身读/写及三类跨路径读写、socket/env/网络/权限/资源检查分别记录。

这不是“整个CI job只能读取一份仓库”的承诺：可信准备属于协调设施。未来模型角色必须只能调用受限worker工具，不能获得准备宿主shell或管理token；当前脚本只接受固定role并执行固定有限probe，不是任意候选或模型工具服务。未启动嵌套Codex/嵌套VM，也未放宽本云端策略。

## 发布前本地检查

本地无Docker，仅执行host/worker AST、workflow YAML、help、缺少CI/非法参数/缺Docker的安全失败，未模拟容器成功。OpenSpec严格21/21、维护31/31、制品及diff检查已通过。实际run、各role的镜像digest与结果必须发布后读取，不预报通过；evidence.json记录当前状态。

## 验收范围

仅当所有五role的有限worker检查和源token检查实际通过，才记录container_repo_boundary_passed及有限2.2.4证据完成。该事实不改变本云端原生子代理共享权限的反例，不证明模型身份隔离、实际suite交接、受控反馈、版本失效重验或产品验收。native_subagent_scoping_verified/full_role_delivery_ready/development_ready/readiness_complete/isolation_ready/implementation_started仍false，父2.2/2.3/3.2不勾选。Git二进制不在该Python镜像内，本probe不把缺Git当读取拒绝；Git/API证据由快照结构及独立token步骤分别提供。memory-swap仅配置命令，worker资源实读覆盖pids/memory/cpu，不扩大其覆盖范围。

## 流程

using-superpowers/brainstorming沿用用户选择和公开试验边界；writing-plans维护原tasks；原生独立实现sol high与独立权限审查astra high分工，verification-before-completion依据真实输出确认范围。返回模型及usage不可核实记unknown/null。没有安装新Skill或依赖，不改产品规格、发行版本或自动归档。

## 实际远端结果

已实跑 https://github.com/vchs6/c2s/actions/runs/41565989028 ，head=1b2dfa06f3dcac3868c2707570c2a80d9c17d98a，工作流completed/success。source-access-boundary源repo200，明确私有验收repository/commits/workflows/runs/artifacts全部404；此轮未出现403语义歧义。此前协调者已核实该目标private且存在，不能用不存在目标冒权限拒绝。

coding/review/author/runner/verifier五个独立job全部success，分别输出15项worker检查true：合法输入/自身输出、UID/GID、相对/容器绝对/真实宿主路径跨读写拒绝、socket不提供、敏感env不继承、network none、权限限制、rootfs只读及pids/memory/cpu实读。五个宿主正控及输出正控通过、其他仓库树未变；source_commit均等于该run head。镜像digest均为python@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30。原有public-role-boundary六容器诊断job也success，本次角色明细以evidence.json的逐项安全JSON为准，不仅引用总绿色，不提交原始日志。

因此可完成有限2.2.4：CI受限执行进程的仓库文件/挂载/环境边界已得到真实正负控制。没有因此完成模型角色接入、私有suite传输、run/verdict所有权或跨角色反馈；当前聊天原生工具范围不变。所有总门禁仍false。该次源码/选定快照文件及镜像版本明确绑定，后续仅证据/任务状态更新不冒新一次容器运行。
