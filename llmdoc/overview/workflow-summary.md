# 工作流摘要

## 固定门禁映射

- G0 → `System_Defined`
- G1 → `Figure_Plan_Ready`
- G2 → `Data_Uploaded + Analysis_Ready`
- G3 → `Assets_Confirmed`
- G4 → `Evidence_Matrix_Ready + Outline_Ready`
- G5 → `Chapter_Approved`

## 单实验体系闭环

1. 创建项目
2. 创建实验体系
3. 确认 system card（G0）
4. 生成并确认 Figure Plan（G1）
5. 上传数据/图像并完成分析（G2）
6. 生成并确认 Manifest 与资产状态（G3）
7. 生成并确认 Evidence Matrix 与 Outline（G4）
8. 逐节生成、批注、审批草稿直至章节通过（G5）

## G4/G5 真相层约束

- 已批准 claims 构成 Evidence Matrix 的 approved truth layer（已批准真相层）。
- `claim.section_ref` 必须属于当前 system 的 `SystemSection.section_key` 集合；非法值必须在 claim 审批阶段以 `422` 拒绝，不应在 G4/G5 之前进入 approved truth layer。
- G4 gate 会对已批准 claims 做兜底检查；若发现非法 `section_ref`，返回 blocker：`code=approved_claim_sections_invalid`、`message=Approved claims reference undefined sections.`、`required_checks=[Evidence_Matrix_Ready]`。
- G5 生成 section draft 的既有 section 校验继续保留，但只作为最后防线。

## 当前实现优先级（Phase 2）

- G0→G1→G2→G3→G4→G5 全链闭环已完成：所有 gate 的前后端基础设施均已落地，包括后端端点（systems/assets/evidence/drafts router）、前端面板组件（SystemDefinitionForm/FigurePlanPanel/AnalysisPanel/ManifestPanel/EvidenceMatrixPanel/DraftPanel）、React Query hooks、GatePanel 集成、门禁逻辑（check_system_defined/check_figure_plan_ready/check_data_and_analysis_ready/check_assets_confirmed/check_evidence_and_outline_ready/check_chapter_approved）。
- 下一步优先级：完善业务生成器的前端承接（Figure Plan / Evidence Matrix / Outline / Section Draft 的完整生成逻辑）、补充更细的审核体验、更多批量操作与更强的用户提示。
- assets、evidence、drafts 的生成类后端链路统一采用 queued handle + 后台任务落库 + workflow/task event 回写的 thin workflow 模式，Temporal 暂不扩展为真实长流程。

## 异步边界

以下动作必须异步返回 `workflow_id` / `job_id`：

- Figure Plan 生成
- Manifest 生成
- Evidence Matrix 生成
- Outline 生成
- Section Draft 生成
- Vision 校验
- 数据分析

其中 Outline 与 Section Draft 现已补齐完整后台完成链路：router 只负责返回 handle 并基于 session bind 启动后台任务；service 在独立 session 中完成落库、写入 `TASK_SUCCEEDED` / `TASK_FAILED` 工作流事件，并通过 broadcaster 发布对应 task event，保持与 assets/evidence 相同的薄工作流语义。
