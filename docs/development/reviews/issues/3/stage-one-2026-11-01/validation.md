# 阶段一实际验证记录

状态：规划验证通过，awaiting-decision；不是产品验收通过。

## 已执行命令

先读取仓库规则、两份正式主规格、ADR、现有变更与研究资料。实际执行：git fetch origin main；确认本地与18370af文件树相同后git reset --soft origin/main以对齐此前等价提交；npm run openspec -- context --json、list --json、status --change define-layered-semantic-fact-model --json、show <两份能力> --type spec --json --no-scenarios，并读取完整主规格；逐项执行instructions proposal/specs/design/tasks --change define-layered-semantic-fact-model --json。返回的root为本仓库，按具体artifactPaths与模板修订。

本轮没有运行OpenSpec apply/archive或产品测试，也没有安装候选依赖。已读取using-superpowers（本会话开始）、brainstorming、dispatching-parallel-agents、writing-plans及verification-before-completion，并按brainstorming的builder-check-prompt实际独立审阅。所有自行维护的临时检查使用Python3，不向仓库添加执行脚本。

### `npm run validate`

退出码：0。

```text
> c2s@1.0.0 validate
> openspec validate --all --strict --no-interactive

✓ change/define-layered-semantic-fact-model
✓ change/enable-issue-driven-development
✓ change/initialize-sdd-ddd-workspace
✓ spec/semantic-fact-model
✓ spec/semantic-fact-query
Totals: 5 passed, 0 failed (5 items)
```

### `npm run check:artifacts`

退出码：0。

```text
> c2s@1.0.0 check:artifacts
> python3 scripts/verify_artifacts.py

PASS: 4 artifact hashes; workflow files; Superpowers 7.0.1.
```

### `git diff --check`

退出码：0。

```text
(无输出)
```

## 静态一致性与范围审计

- 两份正式主规格与基点字节一致；4份导入原件哈希由check:artifacts通过。
- 本轮没有contracts/semantic-model、src/c2s_semantic_contract、tests/semantic-model或requirements-semantic-model.txt产品交付；脚本、规则、配置及依赖文件无修改。
- 22项模型/算法Requirement均有映射和计划中的测试名；这不表示测试已实现或运行。查询主规格仅约束模型形状，不计作查询实现验收。
- 双方首轮及第二轮、独立reviewer均有实际输出，第二轮每方完整回答C01–C07；user_decision保持null。
- builder-check的一项重要目录自校验缺口已落实到design §6.1、模型目录Requirement和tasks1.2；修订后的元Schema/固定包/未知规则反例均为候选。
- 初次严格校验拒绝delta中的Review Status节（该节不能参与规格同步）。已按诊断移除，将状态保留在proposal/design/report；重新严格校验通过，未为通过校验削改需求。
- 方案A/B、4096预算、封闭首版目录和校验依赖是代理提议；user_decision=null、implementation_approved=false，不能将Battle当作用户批准。

## 批准绑定规则

使用现有core.fingerprint、pipeline.plan_digest及core.approval_token复算；plan_paths包括整个既有变更、评审输入/论证/报告及验证记录、正式基线和治理/核心来源材料。approval.json与state.json本身排除，避免循环哈希。未批准时choose_work不进入apply；输入或规划摘要变化时令牌不同。

重要限制：现有plan_digest仅自动枚举issue-*变更目录，故手动批准前还必须对approval.json的inventory_scopes重新枚举全部文件（排除approval.json），与inventory_paths逐项比较；任何新增/删除文件均使此候选批准过期，不能只调用旧digest。当前自动Runner不能路由该既有变更，未修改其脚本/权限，不能通过评论令牌期待自动实施。

本轮GitHub读取确认Issue正文和远程main未变；发布时仍使用基点期望值检查，若冲突则停止发布并重核。最终状态与token见approval.json和docs/development/issues/3/state.json，不在本文件内嵌token，避免循环。
