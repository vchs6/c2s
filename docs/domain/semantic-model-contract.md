# 语义模型公共契约

依据ADR-0013和ADR-0014，产品仅公开semantic-entity-model-2及请求/结果V2。公开校验器validate_semantic_entity_model_v2不接受V1；内部共用实体结构不变量不作为旧模型校验接口导出。

语义实体、属性、类型化关系、来源构造、实现/测试映射、主张、证据、取得运行及覆盖共同表达可追溯上游事实。sourceRecords独立于实体；derived_analysis保留premiseIds/method；legacy_payload仅是已有V2数据可能包含的历史工件，不构成V1导入/导出服务。实体身份不按名称/路径自动合并，源码声明不自动证明业务边界或运行时行为。

规范请求包含scope、view、target、facets、detail及expandDepth；self隐含自身全部已取得属性，子实体按显式深度展开。来源与实体覆盖独立；缺口、冲突、未展开和持久化状态不能混为一谈。JSON/Markdown共用同一结果，纯档案查询不重建来源。

SQLite按scope+输入指纹+分析配置隔离，注册、事实/证据合并、引用、覆盖及回执原子提交。仅V2公开存取；纯旧库明确拒绝且不改写，混合库不访问旧载荷。缓存不能掩盖保存失败，retryable不满足复用。显式完整备份见archive_backup模块，不自动迁移或恢复V1。

历史Schema、目录摘要及旧报告留作追溯；测试侧冻结辅助只校验历史原件，产品不导出。当前算法自有schema_version=1.0.0与已撤销实体V1是不同契约。

约束和最终实跑、测试退休清单及独立审核见docs/development/reviews/semantic-facts/移除V1交付核验.md。共享开发验证不能声称私有盲验收，结构合法不能声称语义解释完整或运行时等价。
