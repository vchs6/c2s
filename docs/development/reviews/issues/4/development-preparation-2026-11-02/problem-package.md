# 开发准备与实施授权：中立问题包

用户最新明确授权：“可以。先完成所有的准备工作。然后开始开发。无需要人为决策时，不用停止。”前序允许代理自行安装必要工具/Skill，须在最终Skill README说明。此前要求各类领域/约束/治理/任务/仓库规范分开，不堆AGENTS。仍保留五角色独立、隐藏测试编码不可见、真实项目验收、0.b.c和不自动归档；Issue不自动触发。

任务：把旧planning-only入口更新为准备后连续实施的条件授权，不重复索取同一开发批准，不把条件授权当准备/验收已通过。复用现有OpenSpec tasks，先执行#10试验及交付2组前置。

实际环境证据：Codex CLI登录可用；Python3.12.14/Node24.22.1/uv可用，Rust工具链未安装；项目.local/analysis-venv已安装tree-sitter0.26.0、Python grammar0.25.0、Rust grammar0.24.2、jsonschema4.26.0及CRG2.3.9。真实regex/click固定commit检出正在准备，不冒已分析。

隔离检查：uid_map仅0->0一个用户；setpriv切19101失败Invalid argument；unshare映射失败Operation not permitted；bwrap报namespace路径不存在；Landlock ABI syscall返回ENOSYS。当前Docker/Podman不可用。原生子代理继承同一文件系统及工具权限；分目录/分支/只读提示不能证明隐藏测试隔离。GitHub连接器可写仓库/读日志，但没有创建私有仓库、管理密钥或部署独立运行器的接口；shell无GH/OPENAI API凭据。不要探查或输出凭据。

比较本地OS角色隔离、独立CI/私有验收区、仅提示约束。需识别哪些准备可继续，哪些必须blocked，不能让“自动持续”覆盖已确认独立性。补领域基础/项目约束/治理/决策/任务/仓库文档的范围；不改变模型A，不重开已确认语义。不要写产品或隐藏测试。本轮文档/准备须有实际证据，不虚报CI运行器已部署。

按Battle协议只读首轮，允许读取文件和必要一手文档；不写文件/不派生代理。输出role round position claims(id statement evidence_refs assumptions falsifier) responses unknowns，500字左右。
