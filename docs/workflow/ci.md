# CI与连续执行边界

当前`.github/workflows/validate.yml`在push/PR运行维护测试、导入原件/工具检查、OpenSpec严格校验及diff检查。它不是产品验收或持续开发调度器；手动Issue worker仍只plan/smoke。

目标分三部分：公开CI跑确定性检查；独立私有验收区保存suite并经可信harness调用隔离candidate；协调器依原tasks和实际证据推进，不允许角色自批。candidate/suite/源/环境必须绑定，失败反馈脱敏。编码令牌不能读原始日志/制品、改私有验收workflow或管理权限。

当前本地身份/namespace/强制读取隔离检查未通过，连接器没有私有验收密钥/运行器的部署接口，不能只写一份YAML即宣称可用。需要具备实际隔离的执行设施及分别授权的角色入口后，验证跨角色拒绝访问和合法交接，才放行隐藏suite及产品流水线。

不把ChatGPT会话/网页登录自动当CI模型凭据；无密钥或权限时明确blocked，不复制或输出认证。用户已批准必要安装及准备后开发，无需再次请求相同批准；此处缺的是执行能力，不是重新确认需求。

账户bootstrap及公开容器探针接续见[ci-setup.md](ci-setup.md)。该探针不调用模型、不触发产品开发，始终报告development_ready=false；账户配置与完整五角色隔离分别验证。
