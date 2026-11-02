# M1原生接口公开试验

属于获取3.1.1/3.2.1的证据，不是产品验收或独立suite。固定源版本及完整结果见experiment-results.json中的m1_native_interface_experiment_2026_11_02。

Linux x86_64、Python3.12.14/tomllib标准库；Cargo1.99.1。对固定regex/click全目录盘点、复制，不按Git忽略/隐藏/src缩范围；保留符号链接形式不跟随。本次实际没有symlink/特殊项。regex盘点484文件/105目录，click211文件/43目录，包含Git元数据；数量不是项目数或完整语义覆盖。复制前/后与原目录逐文件内容摘要一致，工具执行前后副本内容不变，原目录不变且git clean。没有模型调用，本次工具实验不构成端到端产品Token优化证明。

Regex在外置副本执行`cargo metadata --format-version 1 --no-deps --offline --manifest-path <副本绝对Cargo.toml>`，cwd为该副本，timeout60秒。实测exit0、格式1、7个package/7个workspace_member、11个target；成员ID均关联到package，target路径均存在且可映射回范围内原路径，workspace_root映射正确。resolve=null，不当完整依赖解析、构建或交叉target支持。opaque package ID仍不是Project身份。原生stdout外置临时保存，证据记录其实际摘要，不提交随机绝对副本路径或把Cargo.toml当stdout来源。

Click用tomllib只读pyproject，project.name=click、backend=flit_core.buildapi、module绑定click，四个候选入口中仅src/click/__init__.py存在。不import或执行项目源，不安装/调用Flit后端；这是本设计Flit声明入口规则的文件存在性核验，不是Flit构建兼容证明。该固定commit的version不是dynamic；动态字段边界只是设计场景，未作实测声明。

耗时/复制字节为本次测量，不承诺SLO或性能提升。权限失败、symlink、未知backend、损坏TOML/Cargo失败路径未运行，保留3.2.1未完成，不冒测试覆盖。M1工程边界规则仍是有据技术判定，不宣称普遍项目真值。公共准备3.1.1能核的所选接口/副本/版本已取证，父调研任务与产品适配均未完成。
