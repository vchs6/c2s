# codesemantics

从Python/Rust项目源码、工程清单和说明材料提取可追溯的语义事实，查询源码组织、数据与计算实体、属性关系、测试关联、函数算法和伪代码。结果提供JSON或Markdown，保留证据、取得状态与分析缺口。

## 安装

解压codesemantics分发包，在包含install.py的目录执行。安装器使用Python标准库，默认准备独立环境和最小运行依赖：

```bash
python3 install.py --assistant codex
python3 install.py --assistant codearts
python3 install.py --assistant atomcode --target /指定的技能目录/codesemantics
python3 install.py --assistant qcode --target /指定的技能目录/codesemantics
```

在源码仓库中使用同一安装程序的入口：

```bash
python3 scripts/install_codesemantics.py --assistant codex
```

Codex默认使用用户或项目根目录下的.agents/skills；设置CODEX_HOME时用户级使用该目录的skills子目录，可用--target覆盖；CodeArts参考其公开技能仓库的~/.codeartsdoer/skills与项目.codeartsdoer/skills。AtomCode、Qcode需要显式给出当前产品实际使用的目标目录，不将相似名称视为同一助手。安装结束后在助手中刷新/启用技能或重启会话。项目级安装使用--scope project并通过--project-dir指定实际项目目录；在解压目录运行时不要把解压目录误当作项目目录。

产出文件和独立环境写入指定Skill目录；准备过程中使用临时目录和包管理器缓存，不修改助手认证或其他技能。目标已存在时默认拒绝覆盖；--replace仅替换完整性校验通过的本产品目录，准备环境失败会回滚。--no-runtime只部署文件，适合离线复制；运行前仍须准备依赖。--python可指定正式版Python3.12；当前解释器不满足时会查找python3.12或使用已安装的uv准备环境。

## 运行依赖

已验证Linux x86_64与正式版Python3.12。最小依赖为jsonschema4.26.0、tree-sitter0.26.0、tree-sitter-rust0.24.2，Python安装环境自带ast/tomllib/sqlite3。不需要Node/npm、数据库服务或其他项目分析Skill。原生Rust workspace查询条件需要Cargo；仅做Rust静态解析不需要Rust工具链。

代理有终端、下载网络和写权限时可代为安装；用户不必逐包手工准备。这里的安装发生在代理可操作的执行环境，云工作区安装不等于个人电脑已安装。首次准备依赖需要下载网络，查询入口不自动联网安装。

## 使用

在任意目录，通过安装目标中的命令入口运行：

```bash
python3 /技能目录/codesemantics/scripts/check.py
python3 /技能目录/codesemantics/scripts/codesemantics.py --help
python3 /技能目录/codesemantics/scripts/codesemantics.py query \
  --root /项目目录 --select modules --store /项目外/facts.sqlite --format json
```

完整参数、结构化请求、算法、图输出、备份及状态解释见[使用说明](skill/使用说明.md)。Skill发现入口为[SKILL.md](skill/SKILL.md)。事实档案使用SQLite，JSON/Markdown为查询输出。

## 能力边界

静态分析不证明全部业务意图、运行时等价、宏展开或完整调用绑定。未取得的事实显式报告缺口；伪代码是带来源映射的部分静态投影。安装目录部署测试与真实助手中的自动触发验证分别报告；其他系统和架构的查询运行未验证。

## 分发完整性

manifest.json记录文件清单与SHA-256；安装前核对清单、路径和摘要。该检查用于发现损坏，不是发行者签名。分发包只包含本Skill运行内容，安装器不会把工作区、凭据、缓存或开发材料复制到目标目录。
