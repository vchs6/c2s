# Issue #5中立问题包

battle_id: issue-5-planning-2026-11-01。读共享context.md、upstream.md及本目录issue-input.json，按需核对正式主规格；不反复通读全部源码或历史。

目标：建立查询工作负载、性能/扩展/存储/质量指标、语言/host/target支持矩阵及实际LLM Token最小化的评价依据，不运行基准、不猜目标数值、不承诺全部平台。

问题：什么最小负载集合可区分首次构造/已有复用/局部变更/失败？如何界定首结果/完整响应/正确性与延迟/Token统计，防止缓存复用或缺口结果伪装快且省Token？跨语言/混合语言、host/target如何分列？哪些目标必须人工裁决、哪些技术性度量定义可由代理在授权内形成规格？比较至少一个替代，不引入超出Issue范围的服务。

验收：可用于下游架构的确定性口径与参数边界，明确重要未知不阻断无依赖规划；实际测量证据为未执行。首轮独立、第二轮交叉、新reviewer，不多数票裁决。子代理只读，输出role/round/claims/evidence_refs/assumptions/falsifier/unknowns，控制300中文字左右，证据另计。
