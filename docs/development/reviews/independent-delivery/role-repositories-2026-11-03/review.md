# 公开角色仓库准备及访问边界独立审查

日期：2026-11-03。taskType：公开同步工具/权限审查。角色：独立审阅者；委托的modelRequested=gpt-6-astra、reasoningEffort=high；modelReturned、Token usage未由工具回报，记unknown。审阅仅覆盖公开管理工具、公开契约、公开合成实验及其证据；不代表已部署的受限正式角色。

## 结论

| 审查维度 | 结论 | 可接受范围 |
| --- | --- | --- |
| 公开准备工具规格符合性 | PASS（限定brief范围） | 五仓库、固定源SHA、regular blob白名单、独立初始历史、安全调用及如实状态符合本次管理工具约定。 |
| 公开准备工具代码质量 | PASS，无需阻塞当前工具合入的源码发现 | 不是权限broker；保留已经声明的发布中断限制，不要求它承担不存在的运行隔离承诺。 |
| 仓库输入数据范围 | PASS（本次公开快照） | 八组既有执行证据支持Git内容边界；author不含candidate，其他四角色仅多一份公开基础设施示例。 |
| 用户“角色只能看自己的仓库”要求 | FAIL，实质阻塞 | coding工作目录中的原生子代理通过相对路径、绝对路径和Git均读到author公开marker。 |
| 五角色正式交付与开发就绪 | BLOCKED | 2.2、2.3、3.2不可因此完成；隐藏suite编写及依赖该门禁的产品开发不得启动。 |

这不是待补一份说明文档的问题：当前实际工具权限已允许跨仓库读取。独立Git根、独立上下文、角色名、工作目录和不同模型均不消除此反例。用户授权仍成立；失败的是实际权限条件。

## 审阅基线和范围

已读AGENTS、README、agent-governance、ADR-0009、正式independent-delivery规格，以及本任务brief、review-package.diff、implementer.md、implementation-verification.json、access-probe.md。独立核对实际脚本全部源码、一次性公开验证脚本和落盘MANIFEST。未扫描其他临时目录，未访问连接器、真实私有仓库、认证、隐藏suite，未运行Docker/Codex/bwrap，未修改源码、任务状态或创建提交；唯一写入是本审阅报告。

被审源码：`scripts/prepare_role_repositories.py`，SHA256 `106c1c39a7044305e50b4498f4e487e7b9b17cf09b5789795115f27be7178cdd`。实验固定源：`188ac7022da6be8d6bbb550b08eafbab39434643`。生成目标：`.local/role-repositories-2026-11-03/repositories`。审阅未重新执行八组已有运行测试或重新运行访问probe，避免把同次证据冒充第二次独立执行；下述运行结果归属于相应原始回执，本审阅是源码和证据一致性复核。

## 公开准备工具规格和质量

- 固定源读取：115–159行以`rev-parse --verify --end-of-options <ref>^{commit}`解析一次，验证40位小写hex；之后用该提交的精确`ls-tree -z`记录和blob ID读取。明确拒绝非100644/100755、非blob、路径不精确、缺失和超限输入；不使用工作区文件或未经校验的归档解压。
- 内容边界：24–30、166–198行固定五角色和输入列表。author只有两份公开规格，其他角色另有`check_public_environment.py`。生成的ROLE_INPUT含源SHA、逐文件SHA256和synthetic_only；marker明确公开合成。没有复制源.git/config、历史、hooks、remote或alternate的路径。
- Git行为：55–112、190–194行使用固定argv、shell=False、stdin=DEVNULL、20秒timeout；重新构建环境、禁止全局/系统Git配置、签名、hook、fsmonitor及传输，空template初始化独立SHA1/main。错误路径输出固定分类JSON，没有透传Git stderr或原始异常正文。
- 既有目标：201–249行用lexists识别既有路径和悬空链接，在父目录自建临时目录，发布前mkdir独占保留新目标；不会用整体rename覆盖并发出现的既有空目录，失败仅清理本次临时目录。不删除旧目标。
- 发布限制：逐项移动不是整体原子发布；中断可留下本次新目标部分内容，随后调用拒绝覆盖。实现者和脚本文档已明示该行为。此可信本地准备工具不宣称防同身份恶意并发，不据此要求增加生产权限broker。消费者仍须结合退出状态和完整性检查，不能把残留目录或单独存在的MANIFEST当成发布成功。
- 状态语义：233–235行只将repository_setup_passed置true，permission_isolation_verified和development_ready固定false。README、design和新增2.2.3文字均明确内容准备与权限验证分离；维护CI调用仅证明准备入口能运行，不自动获得角色隔离证据。

在上述限定范围未发现需要修正后才能接受的代码缺陷。这里的PASS不授予更宽的数据复制权限，也不证明不可信源配置或恶意同身份进程下的生产安全性。

## 数据范围与运行证据

读取`implementation-verification.json`得到8项通过记录，源码审阅确认验证脚本确实断言：五个不同Git根/object路径/root commit、单提交main、无remotes/alternates/hooks、干净工作区、fsck、源提交对象不存在、精确Git树与固定源字节/摘要、author排除candidate、ROLE_INPUT及false门禁。其余组覆盖既有目标字节不变、悬空链接拒绝、未提交/未跟踪/未列已提交内容排除、symlink/gitlink/缺失路径拒绝及ref选项不执行。

落盘MANIFEST与回执源SHA、五个角色提交和公开文件矩阵一致。本次输入只有两份公开规格和一份公开基础设施示例，不含真实验收用例或产品实现；这不是完整生产角色输入分配方案。生成ROLE_INPUT和marker是本次额外公开元数据，不是从主仓库偷偷带入的内容。

## 实质阻塞：角色工具权限未收窄

依据：正式`independent-delivery`的“五类交付职责独立”“独立测试对编码角色不可见”，以及用户“角色只能查看自己的仓库”。`access-probe.md`给出实际独立原生probe、完整命令、cwd和安全JSON；不是仅凭推测判定。

cwd为`repositories/coding`，结果如下：

| 通道 | 精确公开目标/调用 | 实际结果 |
| --- | --- | --- |
| 合法控制 | `PUBLIC_SYNTHETIC_MARKER.txt` | allowed，非空 |
| 相对文件路径 | `../author/PUBLIC_SYNTHETIC_MARKER.txt` | allowed，非空 |
| 绝对文件路径 | `/workspace/scratch/7d97b2f44197/c2s/.local/role-repositories-2026-11-03/repositories/author/PUBLIC_SYNTHETIC_MARKER.txt` | allowed，非空 |
| Git工具 | `git -C ../author show HEAD:PUBLIC_SYNTHETIC_MARKER.txt` | allowed，exit_code=0，stdout非空 |

原probe进程退出0只说明探针正常报告；其`role_repository_isolation_passed=false`才是权限判定。复现入口为`access-probe.md`所列Python命令，保持同一原生入口及coding cwd即可对上述公开marker验证；本审阅没有另行读取其他目标。三个禁止访问通道中任意一条成功即足以否定“只能看自己的仓库”，不需要暴露真实suite来证明风险，也不能将未测写权限或连接器权限默认为安全。

解除此阻塞需要实际受限的角色执行身份或工具入口，并由独立实测证明合法输入可读、其他角色禁止目标不可读，同时覆盖正式门禁要求的历史、日志、制品、API、candidate进程和受控交接。当前工具与证据没有提供这些能力。增加Git目录、提示词或改cwd不是修复；本审阅不允许删改上游要求来使结果通过。

2.2.3可以按其明确的“公开实验与可信证据完成”范围记录实验完成，但必须在同一结果中突出权限验收FAIL，且不得把该子步完成改写为用户整体要求已达成；父2.2/2.3/3.2、整体readiness仍保持未完成。

## 本审阅执行与Skill记录

实际执行`npm run openspec -- status --change define-independent-ddd-delivery`及`npm run openspec -- instructions apply --change define-independent-ddd-delivery --json`，读取返回：规划工件4/4、任务8/14完成，2.2/2.2.3/2.3/3.2仍未完成。这里的ready只表示apply工件状态，不是产品就绪。

本审阅另以Python3对被审源码执行AST解析并重算SHA256，退出0、AST_PARSE=PASS；只证明语法及基线身份。既有八组测试和独立probe结果按原回执引用，不冒称本审阅重新执行。

已读取`superpowers:using-superpowers`（cloud c18），按其SUBAGENT-STOP适用专门委派子代理例外；采用`superpowers:verification-before-completion`的证据先于结论原则核对源码、回执及状态并区分未复跑证据。Skill工具未返回包版本，版本unknown。没有因为Skill另起代理、重复测试或要求用户重复授权。

## 公开报告补核

协调者后续提供的`docs/development/reviews/independent-delivery/role-repositories-2026-11-03/`中report.md、evidence.json、snapshot-manifest.json、access-probe.md已全部只读核对。独立Python比较确认：公开snapshot-manifest与实际落盘MANIFEST逐结构一致；公开access-probe与本任务原始公开回执字节一致；evidence中的8组内容检查与原implementation-verification逐结构一致，setup=true、permission_requirement=false。本次补核退出0。report.md准确区分准备PASS和权限FAIL，没有将八组公开工具验证冒充隐藏产品测试。严格21/21、维护31/31等是协调者另行报告的检查，不由本审阅重复执行或背书为自身运行结果。
