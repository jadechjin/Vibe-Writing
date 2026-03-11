# Team Plan: G0-G5 全链推进

## 概述

基于研究结论，按 G0→G1→G2→G3→G4→G5 顺序逐 gate 闭环，每个 gate 后端与前端交错推进。共 14 个子任务，分 6 个 Layer 执行。

## Codex 分析摘要

- **推荐方案 A**：G0 优先，然后按 G1→G2→G3→G4→G5 逐 gate 闭环。不能跳步，因为 G4/G5 的 gate 事实上被 G2/G3 卡住。
- **G0 隐藏缺口**：后端缺 `GET /systems/{id}` 端点（当前只有 `PATCH`），前端无法预填表单。需补 `get_system_detail()` 到 `systems/router.py`。
- **G2 假闭环**：gate 查 `AnalysisRun`，但没有创建 AnalysisRun 的 API。需在 `assets` 模块补 AnalysisRun CRUD。
- **evidence/drafts 从空包起建**：需逐层搭建 repository → service → schemas → router。
- **事件双重记录**：`advance_system()` 先 `start_system_workflow()` 再 `record_gate_blocked/passed()`，建议后续新模块统一事件命名。
- **状态语义混用**：`confirmed/approved` 在 gate 中被混合当作可通过状态，需统一。

## Gemini 分析摘要

- **G0 编辑流 UI**：在 GatePanel 中 G0 active 时条件渲染 SystemDefinitionForm，表单校验 + blocker 联动高亮缺失字段。
- **插件化 Gate 内容**：定义标准化 GateContentProps，确保 G1-G5 组件可作为插件插入 GatePanel。
- **乐观更新**：保存后立即 `queryClient.setQueryData` 避免轮询返回旧数据。
- **权限控制**：G0 完成后应强制只读，防止后续阶段误改。
- **组件拆分**：SystemDefinitionForm 独立文件，useUpdateSystem + useSystemDetail 独立 hook。

## 技术方案

### 后端
- G0：补 `GET /systems/{id}` 端点，前端用于预填。
- G1：`evidence` 模块补 FigurePlan CRUD（生成异步返回 JobHandle）。
- G2：`assets` 模块补 AnalysisRun CRUD（create/list/complete）。
- G3：`assets` 模块补 manifest 确认 + 资产 QC 确认语义分离。
- G4：`evidence` 模块补 Claims + ClaimEvidenceLink CRUD；`drafts` 模块补 Outline + OutlineAssetBinding。
- G5：`drafts` 模块补 SectionDraft + ReviewComment + 审批流。
- 路由装配：每批次完成后统一在 `api/router.py` 注册新 router。

### 前端
- G0：新增 `useUpdateSystem` + `useSystemDetail` hook；新增 SystemDefinitionForm 组件嵌入 GatePanel。
- G1-G5：每个 gate 在 GatePanel/EvidenceHub 中按条件渲染对应工作组件（不重做壳层）。

## 子任务列表

### Task 1: 后端补 GET /systems/{id} 端点
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/systems/router.py`（新增 `GET /systems/{system_id}` 路由）
  - `backend/app/modules/systems/service.py`（新增 `get_system_detail()` 函数）
- **依赖**: 无
- **实施步骤**:
  1. 在 `service.py` 新增 `get_system_detail(session, system_id) -> SystemDetail`，复用 `_build_system_detail()`。
  2. 在 `router.py` 新增 `@router.get("/systems/{system_id}", response_model=ApiResponse[SystemDetail])`。
  3. 返回 `SystemDetail` 包含全部 G0 字段 + sections。
- **验收标准**: `GET /api/systems/{id}` 返回完整 system detail 含 researchGoal / samplesSubjects / ... / systemCardJson。

### Task 2: 前端 useUpdateSystem + useSystemDetail hooks
- **类型**: 前端
- **文件范围**:
  - `frontend/hooks/useSystem.ts`（新文件）
- **依赖**: Task 1
- **实施步骤**:
  1. 新建 `frontend/hooks/useSystem.ts`。
  2. 实现 `useSystemDetail(systemId)` → `GET /systems/{systemId}` → 返回 `SystemDetail` 类型（复用 `useProjects.ts` 已有的 `SystemDetail` 类型定义）。
  3. 实现 `useUpdateSystem(systemId)` → mutation 调用 `PATCH /systems/{systemId}` → onSuccess invalidate `["system", systemId]` + `["workflow", systemId]`。
- **验收标准**: 两个 hook 可正常调用后端 API，TypeScript 类型无报错。

### Task 3: 前端 SystemDefinitionForm 组件
- **类型**: 前端
- **文件范围**:
  - `frontend/components/gates/SystemDefinitionForm.tsx`（新文件）
- **依赖**: Task 2
- **实施步骤**:
  1. 新建组件，接收 `initialData: SystemDetail | null`、`blockers: Blocker[]`、`onSave: (data) => void`、`isReadOnly: boolean` props。
  2. 渲染 6 个字段：researchGoal / samplesSubjects / variablesControls / outputMetrics / methodsSummary（textarea）+ systemCardJson（JSON 文本框）。
  3. 前端校验：所有字段非空 + systemCardJson 是有效 JSON。
  4. blocker 联动：从 `blockers[0].details.missing_fields` 提取缺失字段列表，对应字段标红。
  5. 保存按钮调用 `onSave`。
- **验收标准**: 表单能显示当前值、标红缺失字段、保存后回调。

### Task 4: 前端 GatePanel + SystemPage 集成 G0 编辑流
- **类型**: 前端
- **文件范围**:
  - `frontend/components/gates/GatePanel.tsx`（修改：G0 active 时渲染 SystemDefinitionForm）
  - `frontend/app/projects/[projectId]/systems/[systemId]/page.tsx`（修改：注入 systemDetail + updateSystem）
- **依赖**: Task 3
- **实施步骤**:
  1. `GatePanel` 新增 props：`systemDetail`, `onUpdateSystem`, `isUpdating`。
  2. 在 `gateKey === "G0" && gateVisualState === "active"` 时渲染 `SystemDefinitionForm`，传入 blockers 联动。
  3. G0 passed 后切换为只读展示。
  4. `SystemPage` 中调用 `useSystemDetail` + `useUpdateSystem`，将 detail/mutation 传入 GatePanel。
- **验收标准**: G0 active 时表单可编辑保存；保存后 Advance 可通过 G0（Draft → System_Defined）。

### Task 5: 后端 Evidence 模块 - FigurePlan (G1)
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/evidence/schemas.py`（新建）
  - `backend/app/modules/evidence/repository.py`（新建）
  - `backend/app/modules/evidence/service.py`（新建）
  - `backend/app/modules/evidence/router.py`（新建）
- **依赖**: 无
- **实施步骤**:
  1. `schemas.py`：定义 FigurePlanDetail / FigurePlanGenerateRequest / FigurePlanConfirmRequest。
  2. `repository.py`：实现 list_figure_plans / get_figure_plan / create_figure_plan / update_figure_plan_status。
  3. `service.py`：实现 `generate_figure_plan()`（异步返回 JobHandle）、`list_figure_plans()`、`confirm_figure_plan()`。
  4. `router.py`：暴露 `POST /systems/{id}/figure-plans/generate`、`GET /systems/{id}/figure-plans`、`PATCH /figure-plans/{id}`。
- **验收标准**: 生成返回 JobHandle；确认后 FigurePlan.status = "confirmed"；G1 gate 可通过。

### Task 6: 后端 Assets 模块 - AnalysisRun (G2)
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/assets/schemas.py`（追加 AnalysisRun 相关类型）
  - `backend/app/modules/assets/repository.py`（追加 AnalysisRun CRUD）
  - `backend/app/modules/assets/service.py`（追加 create_analysis_run / list_analysis_runs / complete_analysis_run）
  - `backend/app/modules/assets/router.py`（追加 AnalysisRun 路由）
- **依赖**: 无
- **实施步骤**:
  1. `schemas.py`：定义 AnalysisRunDetail / AnalysisRunCreateRequest / AnalysisRunCompleteRequest。
  2. `repository.py`：实现 create_analysis_run / get_analysis_run / list_analysis_runs_for_system / update_analysis_run_status。
  3. `service.py`：实现 `create_analysis_run()`（创建记录 + 异步返回 JobHandle）、`complete_analysis_run()`（标记 succeeded/failed）、`list_analysis_runs()`。
  4. `router.py`：暴露 `POST /systems/{id}/analysis-runs`、`GET /systems/{id}/analysis-runs`、`PATCH /analysis-runs/{id}/complete`。
- **验收标准**: 创建 AnalysisRun 后 G2 gate 的 `analysis_not_ready` blocker 消除。

### Task 7: 后端 Assets 模块 - 资产确认/QC (G3)
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/assets/schemas.py`（追加 manifest confirm / QC confirm 类型）
  - `backend/app/modules/assets/service.py`（追加 confirm_manifest / confirm_asset_qc）
  - `backend/app/modules/assets/router.py`（追加确认路由）
- **依赖**: Task 6（共享 assets 模块，但文件范围与 Task 6 不冲突：Task 6 是 AnalysisRun 相关函数/路由，Task 7 是 manifest confirm / QC 相关函数/路由）
- **实施步骤**:
  1. `service.py`：新增 `confirm_manifest(session, manifest_id)`（将 manifest.status 设为 "confirmed"）和 `confirm_asset_qc(session, asset_id)`（将 metadata.qc_status 设为 "confirmed"）。
  2. `router.py`：暴露 `POST /manifests/{id}/confirm` 和 `POST /assets/{id}/confirm-qc`。
  3. `schemas.py`：追加 ManifestConfirmResponse / AssetQCConfirmResponse。
- **验收标准**: 确认后 G3 gate 的 `assets_not_confirmed` blocker 消除。

### Task 8: 后端路由装配 - 注册 evidence router
- **类型**: 后端
- **文件范围**:
  - `backend/app/api/router.py`（修改：include evidence_router）
- **依赖**: Task 5
- **实施步骤**:
  1. `from app.modules.evidence.router import router as evidence_router`
  2. `api_router.include_router(evidence_router)`
- **验收标准**: evidence 模块路由可通过 `/api/...` 前缀访问。

### Task 9: 后端 Evidence 模块 - Claims + ClaimEvidenceLink (G4)
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/evidence/schemas.py`（追加 Claim / ClaimEvidenceLink 类型）
  - `backend/app/modules/evidence/repository.py`（追加 Claim CRUD）
  - `backend/app/modules/evidence/service.py`（追加 generate_evidence_matrix / list_claims / approve_claim / bind_claim_evidence）
  - `backend/app/modules/evidence/router.py`（追加 Claims 路由）
- **依赖**: Task 5, Task 8
- **实施步骤**:
  1. `repository.py`：实现 create_claim / list_claims / get_claim / update_claim_status / create_claim_evidence_link / list_links_for_claim。
  2. `service.py`：实现 `generate_evidence_matrix()`（异步返回 JobHandle）、`list_claims()`、`approve_claim()`、`bind_claim_evidence()`。
  3. `router.py`：暴露 `POST /systems/{id}/evidence-matrix/generate`、`GET /systems/{id}/claims`、`PATCH /claims/{id}`、`POST /claims/{id}/evidence-links`。
  4. 遵守 HC-10: Evidence Matrix 由 claims + claim_evidence_links 表达，不新增表。
  5. 遵守 HC-14: 保持两条部分唯一索引语义。
- **验收标准**: approved claims 均有 evidence link 后 G4 的 `evidence_matrix_not_ready` blocker 消除。

### Task 10: 后端 Drafts 模块 - Outline (G4)
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/drafts/schemas.py`（新建）
  - `backend/app/modules/drafts/repository.py`（新建）
  - `backend/app/modules/drafts/service.py`（新建）
  - `backend/app/modules/drafts/router.py`（新建）
- **依赖**: 无
- **实施步骤**:
  1. `schemas.py`：定义 OutlineDetail / OutlineGenerateRequest / OutlineConfirmRequest / OutlineBindingDetail。
  2. `repository.py`：实现 create_outline / get_outline / list_outlines / update_outline_status / create_outline_binding / list_outline_bindings。
  3. `service.py`：实现 `generate_outline()`（异步返回 JobHandle）、`confirm_outline()`、`bind_outline_assets()`。
  4. `router.py`：暴露 `POST /systems/{id}/outline/generate`、`GET /systems/{id}/outlines`、`PATCH /outlines/{id}`、`POST /outlines/{id}/bindings`。
- **验收标准**: confirmed outline + 至少一个 binding 后 G4 的 `outline_not_ready` blocker 消除。

### Task 11: 后端 Drafts 模块 - SectionDraft + Review (G5)
- **类型**: 后端
- **文件范围**:
  - `backend/app/modules/drafts/schemas.py`（追加 SectionDraft / ReviewComment 类型）
  - `backend/app/modules/drafts/repository.py`（追加 SectionDraft CRUD）
  - `backend/app/modules/drafts/service.py`（追加 generate_section_draft / approve_draft / add_review_comment）
  - `backend/app/modules/drafts/router.py`（追加 Draft 路由）
- **依赖**: Task 10
- **实施步骤**:
  1. `repository.py`：实现 create_section_draft / list_section_drafts / get_section_draft / update_draft_status / create_review_comment。
  2. `service.py`：实现 `generate_section_draft()`（异步返回 JobHandle，遵守 HC-13: 只消费已批准 claims）、`approve_section_draft()`、`add_review_comment()`。
  3. `router.py`：暴露 `POST /systems/{id}/sections/{sectionKey}/draft`、`GET /systems/{id}/drafts`、`POST /drafts/{id}/approve`、`POST /drafts/{id}/review`。
- **验收标准**: 全部 section 有 approved draft 后 G5 gate 可通过。

### Task 12: 后端路由装配 - 注册 drafts router
- **类型**: 后端
- **文件范围**:
  - `backend/app/api/router.py`（修改：include drafts_router）
- **依赖**: Task 10
- **实施步骤**:
  1. `from app.modules.drafts.router import router as drafts_router`
  2. `api_router.include_router(drafts_router)`
- **验收标准**: drafts 模块路由可通过 `/api/...` 前缀访问。

### Task 13: 后端测试 - G1-G5 各 gate 闭环测试
- **类型**: 后端测试
- **文件范围**:
  - `backend/tests/modules/evidence/test_evidence_api.py`（新建）
  - `backend/tests/modules/drafts/test_drafts_api.py`（新建）
- **依赖**: Task 8, Task 12
- **实施步骤**:
  1. `test_evidence_api.py`：覆盖 FigurePlan 生成/确认、Claims CRUD、ClaimEvidenceLink 绑定、Evidence Matrix 生成。
  2. `test_drafts_api.py`：覆盖 Outline 生成/确认/绑定、SectionDraft 生成/审批、ReviewComment。
  3. 两个测试文件均使用现有 SQLite + TestClient 模式（参考 `test_assets_api.py`）。
  4. 验证 G1-G5 各 gate 校验在数据就位后可通过。
- **验收标准**: pytest 全通过；每个 gate 至少有 blocked + passed 两种场景覆盖。

### Task 14: 前端 G1-G5 工作台占位面板
- **类型**: 前端
- **文件范围**:
  - `frontend/components/gates/FigurePlanPanel.tsx`（新建）
  - `frontend/components/gates/AnalysisPanel.tsx`（新建）
  - `frontend/components/gates/ManifestPanel.tsx`（新建）
  - `frontend/components/gates/EvidenceMatrixPanel.tsx`（新建）
  - `frontend/components/gates/DraftPanel.tsx`（新建）
  - `frontend/components/gates/GatePanel.tsx`（修改：按 gate 条件渲染对应面板）
- **依赖**: Task 4
- **实施步骤**:
  1. 每个面板组件接收 `snapshot / blockers / systemId` props，展示当前 gate 状态、blockers、操作按钮入口（按钮暂不接后端，标记为 TODO）。
  2. `GatePanel.tsx` 按 gateKey 条件渲染对应面板，替代当前的纯文案空态。
  3. 保持现有 GatePanel props 接口向后兼容（新增可选 props）。
- **验收标准**: 每个 gate 阶段有对应的操作面板（至少展示状态 + blocker + 按钮占位），不再是纯文案。

## 文件冲突检查

⚠️ 以下冲突已通过依赖关系解决：

- `backend/app/modules/assets/schemas.py` — Task 6 (AnalysisRun 类型) 和 Task 7 (confirm 类型) 均追加内容。解决方案：Task 7 依赖 Task 6，串行执行，各自追加不同类名。
- `backend/app/modules/assets/service.py` — 同上，Task 6 和 Task 7 追加不同函数名。
- `backend/app/modules/assets/router.py` — 同上。
- `backend/app/api/router.py` — Task 8 (evidence) 和 Task 12 (drafts)，通过 Layer 分离。
- `frontend/components/gates/GatePanel.tsx` — Task 4 (G0) 和 Task 14 (G1-G5)，通过 Layer 分离。

✅ 其余所有任务文件范围无冲突。

## 并行分组

- **Layer 1 (并行, 3 Builder)**: Task 1, Task 5, Task 6
- **Layer 2 (依赖 Layer 1, 并行, 3 Builder)**: Task 2, Task 7, Task 8
- **Layer 3 (依赖 Layer 2, 并行, 3 Builder)**: Task 3, Task 9, Task 10
- **Layer 4 (依赖 Layer 3, 并行, 3 Builder)**: Task 4, Task 11, Task 12
- **Layer 5 (依赖 Layer 4, 并行, 2 Builder)**: Task 13, Task 14
- **Layer 6 (依赖全部)**: 手动集成验证

## 验证清单

- [ ] `GET /api/systems/{id}` 返回完整 SystemDetail
- [ ] G0 前端可编辑保存 + Advance 通过
- [ ] `POST /api/systems/{id}/figure-plans/generate` 返回 JobHandle
- [ ] G1 gate 确认后可通过
- [ ] `POST /api/systems/{id}/analysis-runs` 创建 AnalysisRun
- [ ] G2 gate 有 succeeded AnalysisRun 后可通过
- [ ] `POST /api/manifests/{id}/confirm` 确认 manifest
- [ ] G3 gate 确认后可通过
- [ ] `POST /api/systems/{id}/evidence-matrix/generate` 返回 JobHandle
- [ ] G4 gate approved claims + confirmed outline 后可通过
- [ ] `POST /api/systems/{id}/sections/{key}/draft` 返回 JobHandle
- [ ] G5 gate 全 section approved draft 后可通过
- [ ] 不破坏现有测试基线
- [ ] 前端每个 gate 有操作面板（不再是纯文案空态）
