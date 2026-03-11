# 后端模块边界

## 目录

- `backend/app/core/*`：配置、环境、生命周期
- `backend/app/common/*`：枚举、错误码、响应模型、事件契约
- `backend/app/persistence/*`：Base、Session、ORM、Alembic glue
- `backend/app/modules/projects/*`
- `backend/app/modules/systems/*`
- `backend/app/modules/assets/*`
- `backend/app/modules/evidence/*`
- `backend/app/modules/drafts/*`
- `backend/app/modules/gates/*`
- `backend/app/modules/tasks/*`
- `backend/app/executors/*`
- `backend/app/workflows/*`
- `backend/app/realtime/*`
- `backend/app/api/router.py`
- `backend/app/api/websocket.py`
- `backend/app/main.py`

## 当前阶段的主要业务落点

- `backend/app/modules/assets/*`：已承接资产上传、资产元数据、Manifest 查询/异步生成等最小 G2-G3 业务；生成类接口继续采用 queued handle + 后台任务的薄工作流语义。
- `backend/app/modules/evidence/*`：已落地 FigurePlan 生成/查询/确认、Evidence Matrix 生成、Claim 审批、ClaimEvidenceLink 绑定等最小 G1/G4 后端链路，保持与 assets 一致的 thin workflow + task event 模式。
- `backend/app/modules/drafts/*`：已落地 Outline / OutlineBinding（G4）与 SectionDraft / ReviewComment（G5）后端链路；`POST /systems/{id}/outline/generate`、`POST /systems/{id}/sections/{section_key}/draft` 仅返回 queued handle，真实落库由后台任务完成。当前 drafts contract 已进一步收口：outline confirm 会写入并保留 `approved_at`，section draft 后台执行优先消费受理阶段已归一化并快照化的 `claim_ids`，unexpected failure payload 不再暴露原始异常文本，`outline_json` fallback 与 schema 保持一致并同时支持 dict/list 形态。
- 业务落地顺序仍保持为：业务模块承接领域规则，router 只做请求装配与任务调度，workflow/realtime 负责句柄、事件与状态回写；不把核心逻辑直接堆进 router 或 placeholder workflow。

## 模块模板

每个模块默认采用：

- `router.py`
- `service.py`
- `schemas.py`
- `repository.py`（需要时）
- `__init__.py`

## 不变式

- 业务状态真相在数据库与 workflow，不在 executor。
- `advance` 不允许绕过 gates 直接写状态。
- 生成类接口只下发任务句柄，不同步返回最终产物。
- assets / evidence / drafts 的生成链路统一遵循：`start_system_workflow → 后台任务独立 session 落库 → append_system_workflow_event(TASK_SUCCEEDED/TASK_FAILED) → broadcaster.publish(task event)`。
- drafts/evidence 的 router 只能基于当前 session 的 bind 调度后台任务，不复用请求生命周期内即将关闭的 session；完成路径必须把 outline/draft 等产物标识回写到 workflow context，失败路径必须写 `last_error`。
- Evidence 持久层必须保留“普通证据绑定”和“依赖具体 analysis run 的证据绑定”的语义区分。
- `claim_evidence_links.analysis_run_id` 可为空，但一旦非空且仍被引用，对应 `AnalysisRun` 必须由数据库外键直接拒绝删除，而不是通过 `SET NULL` 回退成普通证据绑定。
