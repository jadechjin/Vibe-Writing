# 核心数据模型映射

## 项目层

- `projects`
- `project_members`

## 实验体系层

- `experimental_systems`
- `system_sections`

## 资产层

- `assets`
- `asset_metadata`
- `asset_manifests`

## 图表与证据层

- `figure_plans`
- `figure_plan_assets`
- `claims`
- `claim_evidence_links`
- `analysis_runs`

## 写作层

- `outlines`
- `outline_asset_bindings`
- `section_drafts`
- `review_comments`

## 工作流层

- `workflow_instances`
- `workflow_events`
- `approval_tasks`

## 数据建模要求

- 所有核心表都应具备审计字段
- Manifest 必须独立实体化并支持版本化
- Draft、Outline、WorkflowEvent 必须可追溯

## Evidence / Analysis 约束

- `claims.section_ref` 是对所属 system 下 `system_sections.section_key` 的业务引用；claim 在进入 `approved` 前必须命中该集合。非法 `section_ref` 不得在 G4/G5 之前进入 approved truth layer，G4 负责兜底阻断，G5 保留最终 section 校验。
- `claim_evidence_links.analysis_run_id` 允许为 `NULL`，表示该证据绑定不依赖某次具体 `analysis_runs` 记录，只表达 claim 与 asset 的证据绑定关系。
- `claim_evidence_links` 的唯一性由两条部分唯一索引共同保证，并且这两条索引仍然保留，是当前唯一性约束设计的一部分：
  - `ix_claim_evidence_links_unique_without_run`：当 `analysis_run_id IS NULL` 时，`(claim_record_id, asset_id)` 必须唯一。
  - `ix_claim_evidence_links_unique_with_run`：当 `analysis_run_id IS NOT NULL` 时，`(claim_record_id, asset_id, analysis_run_id)` 必须唯一。
- 若某条 `claim_evidence_links` 仍引用某个 `analysis_runs.id`，数据库必须拒绝删除该 `AnalysisRun`；这里不允许使用 `ON DELETE SET NULL` 将 run-bound link 静默降级为 `NULL` 绑定，因为这会破坏当前唯一性语义。
