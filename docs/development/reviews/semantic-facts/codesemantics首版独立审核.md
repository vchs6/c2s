# codesemantics 首版分发最终只读审核

审核范围：`c196bb7224377cee460ce4cf62dbd435b259db4d..baabc4116a7a3eb7989dcc4d8040ed924700b85d`，候选HEAD核对一致。已阅读AGENTS.md、code-reviewer.md、设计、导航计划、唯一tasks第13节、审核diff及ledger。未修改仓库、index或HEAD，未派生代理。使用共享工作区进行新上下文审核，不声称私有suite隔离或独立盲验收。

## Strengths

- 分发映射将产品源码、当前契约和必要入口收敛为42个登记文件；不携带开发记录、测试、上游或凭据。规范命名和当前契约独立性有可执行测试。
- ZIP先校验路径、数量、解压大小和文件类型，后展开到临时目录；文件摘要与未登记文件检查覆盖损坏和清单遗漏。
- 查询入口定位自身runtime，并禁止字节码写入污染清单。实际从`/tmp`、清空PYTHONPATH运行了独立分发包中的模块、实体及Python/Rust算法查询。
- 普通单次安装的已有目标拒绝、坏摘要拒绝和环境失败恢复已有测试；助手目录来源有明确记录，AtomCode/Qcode没有被猜测映射到其他产品，文档诚实限定真实IDE验证范围。

## Issues

### Critical

未发现。

### Important

1. **发布阶段无条件接管新出现的目标，绕过`--replace`和产品归属校验，造成用户文件丢失。**

   - 位置：`scripts/codesemantics_release.py:145`（以及147、157；初始检查位于131–134）。
   - `install_bundle`只在开始时检查目标是否存在及是否允许替换。复制和验证stage之后，只要目标这时存在，就无条件将其改名为backup；安装成功后无条件删除backup。此时没有再次检查`replace`，也没有验证新目标是本产品目录。
   - 触发：两个进程／代理同时使用同一目标，或用户在安装准备期间创建该目标。即使调用`install_bundle(..., replace=False)`，期间出现的普通目录及其用户文件也被移除。对已通过校验但随后改变的目标亦有同类窗口。
   - 验证：先以校验stage后的同步钩子确定性复现，再用真实线程观察stage目录出现后创建目标和`user-file.txt`；没有修改安装器或mock文件操作，连续10/10次返回安装成功、用户文件消失、backup不再存在。所有操作仅在临时目录。
   - 影响：违反“已有目录默认拒绝覆盖；显式替换也须确认目录由本产品管理”的数据保护承诺。需要修复后交付。因触发需要并发变化，按Important报告，而非一般安装必现的Critical。
   - 建议：对目标路径建立贯穿校验、发布、环境准备与回滚的安装互斥，提交时重核目标身份／内容，且不存在目标的发布操作必须保证不覆盖后来出现的路径。不能仅在145前加一次`exists()`判断，留下判断与rename之间的同类窗口；失败恢复也应只处理本次事务拥有的目标。补充无`--replace`并发创建及并发安装／替换回归测试。

真实并发复现主体（使用候选源码，安装器无需修改）：

```python
import sys, tempfile, threading, time
from pathlib import Path
sys.path.insert(0, '/workspace/c2s')
from scripts.codesemantics_release import build_bundle, install_bundle
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    source, target = root / 'source', root / 'target'
    build_bundle('/workspace/c2s', source)
    done = threading.Event()
    def create_user_target():
        while not done.is_set():
            if list(root.glob('.codesemantics-stage-*')):
                target.mkdir()
                (target / 'user-file.txt').write_text('must survive')
                return
            time.sleep(0.0001)
    worker = threading.Thread(target=create_user_target)
    worker.start()
    receipt = install_bundle(source, target, replace=False)
    done.set()
    worker.join()
    print(receipt['installed'], (target / 'user-file.txt').exists())
    # 实测 True False
```

### Minor

未发现需要单独列出的问题。

## 本次执行的验证

解释器`/tmp/c2s-public-venv-3125/bin/python`，设置`PYTHONDONTWRITEBYTECODE=1`。

- `PYTHONPATH=src:skill/src ... -m unittest discover -s tests -p test_codesemantics_distribution.py -v`：9/9通过。
- `PYTHONPATH=src:skill/src ... -m unittest discover -s skill/tests -p test_codesemantics_release.py -v`：3/3通过。
- 从候选构建42文件的分发目录及ZIP，在`/tmp`离线安装，清空PYTHONPATH，在其他cwd执行查询。Python/Rust模块查询退出0，返回两个模块；ComputationEntity返回一个实体，明确`SEMANTIC_INTERPRETATION_PROVISIONAL`；Python/Rust算法均返回一个结果及`ALGORITHM_STATIC_PARTIAL`，退出2符合文档的部分静态结果契约，不计为安装失败。
- 查询后完整性校验仍通过，分发根Markdown本地链接全部可解析。
- 上述并发目标保护反例：确定性钩子复现一次；无mock真实线程复现10/10。
- 本席未重复运行完整146+210测试，也未重新联网pip安装；这些记录仅见父任务提供的执行证据，不冒称本席已运行。

## Declined to judge

- 开发档案、导入原件、上游中的旧品牌／DDD文字：明确不属于产出包，且用户要求不改写原件；不以仓库全局匹配判失败。
- Codex、CodeArts、AtomCode、Qcode真实IDE发现／触发：本环境无完整助手应用；仅审核来源记录、目录策略和文件部署，不能作真实集成结论。
- Windows、macOS及其他架构的实际执行：声明支持验证范围为Linux x86_64；本席未具备其运行环境，不提升为跨平台承诺。
- 发行者签名／防恶意发布者：manifest明示仅完整性校验，本计划未承诺发行认证；不将可重新计算摘要视为签名漏洞。
- 旧开发版档案和品牌别名的迁移兼容：用户要求首版独立产出、去除别名，本次不要求新增迁移系统；仅关注现有数据保护逻辑没有因清理文字被移除。
- 不受本次差异影响的完整语义提取质量、私有suite与固定大型项目验收：本席聚焦规范改名、契约独立及分发安装；不将未运行的套件或大项目回读声称通过。

## Assessment

**Ready to merge：With fixes。**

规范命名、独立运行和常规安装路径符合设计，发现一项经实际复现的并发目标保护问题。修复上述Important并完成对应RED→GREEN及必要回归后，可由执行者按本次单轮修复约定作交付判定；本报告不要求二次review。
