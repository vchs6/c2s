# 本轮实际Skill使用与任务对应

用户允许自主选择适合任务的专用Skill，并要求报告其用途；此表只登记实际使用，不将候选、包内附带文件或CLI工具冒充Skill执行。当前Superpowers仓库版本7.0.1，云端Skill按会话提供包读取；本轮没有新安装个人Skill。

| Skill | 实际任务 | 产出/验证 |
| --- | --- | --- |
| superpowers:using-superpowers | 任务启动、选用适用流程并读规则 | 实际Skill读取及仓库授权边界检查 |
| superpowers:brainstorming | 已确认约束下比较私有runner/最小诊断、M1接口选择 | 交付design接续与九change的M1设计；不重开基线 |
| superpowers:writing-plans | 细化原tasks的准备子步/M1稳定子ID及精确端口 | 原OpenSpec唯一tasks，不建立第二计划 |
| superpowers:subagent-driven-development | 公开基础设施独立实现/审阅、M1契约交叉审查 | 独立代理报告、修订diff与本轮CI证据；不冒原生代理FS强隔离 |
| superpowers:verification-before-completion | 先校验/实跑再报告 | AST/YAML、严格OpenSpec、artifact/diff、实际GitHub run和读回 |
| superpowers:systematic-debugging | 设备登录网络阻塞及实际推理HTTP429分类 | 安全诊断及官方额度/限流code白名单修订；不反复重建密钥 |
| OpenAI Docs | 专用官方资料核对：模型/API认证、Responses与额度/限流错误 | 官方models/list、gpt-5-mini、error-codes页面；不将网页研究当实测 |

工具与Skill分列：OpenSpec是实际运行的CLI，不自动代写正文；Cargo/tomllib是本轮原生接口实验工具；Code Review Graph此前实际运行的是CLI，未将其附带Skill注册或调用为独立Skill。模型路由见docs/workflow/agent-governance.md；本轮局部实现/静态审阅用gpt-6.1-sol，关键边界/跨模块审查用gpt-6-astra，短API健康检查的gpt-5-mini不锁定开发任务模型。

追加专业资料核对：OpenAI Docs已用于核验Codex ChatGPT订阅认证、私有CI进阶认证、订阅API赠送额度条件及限流/余额分类。运行入口备选仅记录，不冒已迁移或已获订阅凭据。
