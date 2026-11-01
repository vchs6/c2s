# 多代理 Battle 协议

## 输入
主代理先整理 problem、scope、user_constraints、evidence、unknowns、acceptance_criteria。证据是引用和具体事实，不是主代理结论。用户已给出的信息不重复询问；非阻塞缺口用明确假设推进。

## 角色
- battle_proposer：提出可行方案、至少一个替代方案、取舍及可证伪条件。
- battle_challenger：独立识别歧义、反例、遗漏和替代方案，承认可成立部分，不为反对而反对。
- battle_reviewer：检查双方证据与约束，形成建议，不按票数裁决；用户有最终决定权。

## 调度
1. 为任务创建唯一记录标识，冻结中立问题包和证据引用。
2. 并行启动 proposer 和 challenger，使用各自角色说明。每人首轮只接收问题包；建议各不超过 800 中文字，证据另计。
3. 全部完成后主代理分配 C01 等争议编号，保留双方原义，不删除少数意见。
4. 将对方意见与争议列表分别传回原代理；逐项回答接受、反驳、修订或缺证，并引用争议编号。建议每人不超过 600 中文字。
5. 新建 reviewer 独立上下文，输入完整问题包、双方两轮意见和证据，要求逐项提出建议及未决事项。若运行时不能回收已完成线程，先结束立论线程再启动评审；不要超出并发上限。
6. 有决定性新证据时可追加一轮，并重新评审；否则终止，不能循环追求全票一致。
7. 主代理输出建议、证据、解决和未决争议，保存机器可读记录。除已有明确授权外，等待用户裁决后再改变权威工件。

## 输出
每个参与者返回：role、round、position、claims、responses、unknowns。claims 含 id、statement、evidence_refs、assumptions、falsifier；responses 含争议编号、action、reason。
最终记录包含 battle_id、problem、constraints、participants、rounds、disputes、recommendation、unresolved、decision_status、user_decision。decision_status 只能是 proposed、accepted、rejected、deferred；没有用户决定时 user_decision=null。
共识只描述参与者立场，不能替代用户批准。纯事实结论与需要用户选择的决策分开报告。

## 证据、失败与成本
引用源码路径和符号、规格条目、工具结果或一手来源。区分事实、推断和假设，不能捏造已读内容。缺少证据时保留 unknown。
某个角色失败时主代理可针对明确原因重试一次；仍失败则记录角色缺席及受影响结论，不伪造输出。不得将未完成或超时标成共识。
默认继承主代理模型，不配置未经验证的模型 ID；决策型讨论宜在可用的强推理主模型会话中启动。不同上下文不等于统计独立或必然意见多样。
三个子角色只读（行为规则，不是操作系统权限隔离）；主代理是记录工件唯一写入者。权限和沙箱继承运行环境，不削弱现有保护。

## SDD 接续
问题讨论 → 用户决策 → 必要的 OpenSpec 变更/规格/设计/任务 → 验证。记录中保留正式工件引用，不能把 Battle 建议自动视为已生效规格。
