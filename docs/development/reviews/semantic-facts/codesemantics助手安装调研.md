# codesemantics 助手安装方式调研

调研目的为产出标准Skill及轻量安装程序，不将开发流程插件当作产出依赖。2026-11-09实际只读获取下列公开页面；官方独立文档域名和搜索引擎被网络代理403拒绝，因此改读可访问的公开源码/技能仓库，不伪称所有资料均来自官方文档。

| 助手或机制 | 实际来源与结论 | 本次提供方式 |
| --- | --- | --- |
| Codex | openai/skills的公开安装器说明SKILL.md与CODEX_HOME/skills；vercel-labs/skills注册表列项目及默认用户.agents/skills | 用户/项目目录预设；显式CODEX_HOME优先；--target可覆盖 |
| CodeArts | CodeArtsAgent/CodeArtsSkills公开技能仓库列.codeartsdoer/skills及刷新/启用；公开多助手注册表codearts-agent一致 | 用户及项目目录预设；不自动改认证或启用状态文件，安装后由宿主刷新/启用 |
| AtomCode | 找到DonaldKellett/skills公开镜像及atomcode主题，未找到足够明确的默认目录约定 | 保留标准Skill结构，通过--target指定实际目录，不猜测 |
| Qcode | 找到zxqQing/QCode公开项目，但不能据此断言就是用户所指产品；注册表另列Qwen Code与Qoder，名称不应混同 | --assistant qcode配合--target；不自动映射到Qwen Code/Qoder目录 |
| 标准Agent Skills | SKILL.md描述头、随包脚本和引用文件，可由宿主读取后执行 | 自包含目录/zip、Python标准库安装器，运行命令与仓库cwd无关 |

来源：

- https://github.com/openai/skills
- https://github.com/openai/skills/blob/main/skills/.system/skill-installer/scripts/install-skill-from-github.py
- https://github.com/vercel-labs/skills/blob/main/src/agents.ts
- https://github.com/CodeArtsAgent/CodeArtsSkills
- https://github.com/DonaldKellett/skills
- https://github.com/zxqQing/QCode

本次真实验证为临时目录部署、依赖准备和独立查询；环境没有这些完整助手应用，不声称四者实际IDE端到端加载/触发已通过。明确目录部署是可用入口，助手自身的导入、启用、权限和模型认证仍由宿主提供。安装程序不依赖第三方技能安装器或Node/npm。
