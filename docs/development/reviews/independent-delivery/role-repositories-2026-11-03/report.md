# 独立角色Git仓库搭建与访问边界实测

依据：用户明确提出主代理创建每角色仓库、将合适内容同步，角色只能查看自身仓库，并要求实际搭建测试。沿用ADR-0009及原change 2.2.3。该要求包含访问边界，不只是文件版本管理。本次只使用公开合成数据；没有创建任何真正隐藏用例、产品实现或凭据。

## 实际搭建

主代理入口`python3 scripts/prepare_role_repositories.py --source . --ref main --destination NEW_PATH`已实现并实际调用。源ref一次解析固定为188ac7022da6be8d6bbb550b08eafbab39434643，后续读取只用该SHA及白名单blob。coding/review/author/runner/verifier分别独立Git init、main和一个root commit；无remote、alternates、源历史或源Git配置。每个ROLE_INPUT和外层MANIFEST记录源/角色提交及文件摘要，详见snapshot-manifest.json。固定源的两项公开规格提供所有角色；公开基础设施candidate示例不提供author。只创建新目标，已有目标及悬空链接拒绝，不覆盖原数据。失败发布可能留下本次新建的部分目标，应人工检查后换新目标，不宣称事务性全量同步。

这是真实本地独立Git仓库，不是worktree或共享对象库；不是远端私有项目，也不是已部署的角色身份/工具broker。生成仓库保持本地忽略，不推入主仓库。工具本身不联网、不调用Codex/容器、不安装依赖、不修改任何安全策略。

## 验证结果

实现者8组实际内容/失败边界检查通过：五个不同Git根与对象目录；精确白名单和固定SHA摘要；author无candidate；无源历史/remotes/alternates/hooks；未提交及未列文件不混入；已有目标和悬空链接拒绝且未变；source symlink/submodule/missing blob拒绝；ref选项不能执行。主协调者另实读五仓库复核固定SHA内容、各唯一root commit及无源历史等条件。Python语法检查通过。

独立原生子代理以coding仓库为实际workdir执行只读探针：自身marker合法读取成功；相对路径author marker、绝对路径author marker及git -C ../author show HEAD:PUBLIC_SYNTHETIC_MARKER.txt均读取成功，进程exit0。完整实际命令及安全输出见access-probe.md。该exit0仅表示探针成功运行，**权限验收FAIL**；不是测试程序错误或业务用例red。只读公开marker，不输出正文，不读取任何真实私有suite/日志/认证。原始复现片段不能把其他运行中的缺文件/error冒作系统拒绝；本轮三个明确allowed已足以构成反例。

## 结论与剩余工作

仓库创建、内容裁剪、固定版本同步：PASS。用户要求“角色只能查看自己的仓库”：当前原生共享工具环境下FAIL。Git提交、工作目录和无remote不收窄终端对其他本地Git目录的访问。当前原生分派接口没有每角色文件/终端/连接器权限配置，不能仅靠更换仓库修复；需要真正按角色限定的执行身份或工具入口后重验，再接私有suite及受控交接。本次不尝试用提示、chmod或关闭宿主策略来冒权限通过。

2.2/2.3/3.2保持未完成；readiness_complete/isolation_ready/development_ready/implementation_started均false，不自动归档或发行产品版本。只对本次公开实验和当前环境作结论，不外推独立账户、VM或远端Git权限是否可满足。

## 流程与分工

using-superpowers建立入口；brainstorming沿用用户已选方案和公开试验边界；writing-plans维护原tasks唯一实验子步；原生实现者准备快照、独立原生访问探针执行越界反例、独立审查者审查公开工具及结论，verification-before-completion记录实际证据。模型请求实现sol high、访问探针sol medium、权限/工具审核astra high，实际返回模型和usage不可核实记unknown/null。角色工作者均为公开基础设施工作者，不冒正式隔离身份。未安装新工具/Skill。

当前脚本只在Linux实际运行；没有将Python语法可移植性冒跨平台运行通过。严格OpenSpec21/21、维护31/31、制品/AST/diff检查通过，独立公开工具审查PASS；权限需求仍FAIL。发布后CI运行结果通过Issue回执关联对应提交，不在发布前预报成功。
