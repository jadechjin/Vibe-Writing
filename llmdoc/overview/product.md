# 产品概述

## 产品定义

本系统是“实验体系驱动的毕业论文工作流平台”，不是自由对话式论文生成工具。

## MVP 目标

先完成单实验体系闭环：

`项目创建 → 体系定义 → Figure Plan → 数据上传/分析 → Manifest → Evidence Matrix → Outline → Section Draft → Review / Approve`

## 当前实现优先级（Phase 2）

- G0 优先：补 `GET /systems/{id}` 端点 + SystemDefinitionForm 编辑流，使 G0 可操作闭环。
- 然后 G1→G2→G3→G4→G5 逐 gate 全链闭环：evidence/drafts 模块从空包起建，每个 gate 补后端 API + 前端工作台面板。
- 不扩 Temporal 长流程，不重做前端工作台壳层，继续沿用 thin workflow + task event 模式。

## 产品原则

1. 实验体系是最小推进单元。
2. Evidence Matrix 是唯一事实源。
3. 门禁驱动，而不是自由聊天驱动。
4. 图表与分析先于正文写作。
5. 所有关键工件必须可版本化、可追溯、可审批、可退回。

## MVP 非目标

- 整篇终稿自动排版导出
- 多实验体系后的绪论/结论跨体系整合
- 多人实时协作编辑
- 重型 RAG / 文献知识库
- 全自动参考文献管理
