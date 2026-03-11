# 仓库现状

## 当前事实

- 仓库已完成 MVP 初始化与控制平面闭环（Phase 1.5）。
- 后端已落地：Projects/Systems/Gates/Tasks 模块、SQLAlchemy 模型与迁移、FastAPI 路由装配、进程内 broadcaster、WebSocket 真实事件推送。
- 前端已落地：Next.js App Router 页面骨架、项目列表/详情页、系统工作台页、GateNav/MainShell/ProjectWorkspace 布局组件、EvidenceHub/GatePanel/WorkflowPanel 工作区面板、StatusTray 任务托盘、React Query 数据层、底层 WebSocket client。
- 前端工作台装配已完成：系统页真实挂载 MainShell 并注入 EvidenceHub / GatePanel / StatusTray 到对应槽位，GateNav 基于真实 gateItems 渲染，根 layout 不再无条件套壳。
- 2026-03-10 已完成一轮 G4/G5 收口：backend drafts contract hardening 已落地，outline confirm 会写入并保留 `approved_at`，section draft 后台任务优先消费受理阶段快照化的 `claim_ids`，unexpected failure payload 不再暴露原始异常文本，`outline_json` fallback 已同时支持 `{sections:[...]}` 与 list 形态。对应回归：`backend/tests/modules/drafts/test_drafts_api.py` 31 passed、`backend/tests/modules/evidence/test_evidence_api.py` 18 passed。
- 前端 G4/G5 工作台已从空态/占位推进到可操作状态：EvidenceMatrixPanel 现支持 Evidence Matrix 生成、claim 审批、claim evidence-link 创建、outline 生成/确认、outline binding 展示与创建、可用 assets 展示；DraftPanel 现支持 section draft 生成、review comments 展示、review comment 提交、draft 审批；系统页对 websocket `task.succeeded` / `task.failed` 也会触发 workflow invalidation。
- 2026-03-11 已完成 G5 `DraftPanel` 第三阶段 refinement：基于 system sections + latest draft 真相加入 deterministic section grouping（approved / needs-review / ready-to-generate）、collapsed-by-default draft preview、review decision markers、section-scoped local inline feedback、single-priority disabled helper reasons；并已根据双模型审查修正 3 个问题：已有 latest draft / blocker 时禁用生成、避免跨 section pending/error 串味、success 反馈仅在对应 section authoritative refresh 后清理。对应前端验证：`frontend` 目录下 `npm run typecheck` 已重新通过。
- 2026-03-11 已完成 OpenSpec change `refine-g4-g5-workbench-and-minimal-acceptance` 的 Phase 4/5 全部落地：最小自动化验收基线已从规划转为实际可运行的前端测试套件。采用 `Vitest + JSDOM + React Testing Library` 的 panel-level smoke，直接覆盖 `EvidenceMatrixPanel`（G4）与 `DraftPanel`（G5）。测试证明了两项关键语义：(1) deterministic latest-selection（version-first, updatedAt-second 排序）；(2) async truth split（202 Accepted ≠ artifact ready，websocket 可能缺失）。测试基础设施包括 `vitest.config.ts`（JSDOM 环境）、`vitest.setup.ts`（jest-dom matchers）、`testUtils.tsx`（QueryClient provider wrapper）、`testFixtures.ts`（contract-shaped fixture builders）。对应 OpenSpec delta specs 已同步至主 specs 并归档。
- 已重新运行前端 `npm run test:smoke` 与 `npm run typecheck`，均通过。
- 2026-03-11 已确认 G0 收口完整落地：后端 `GET /systems/{id}` 与 `PATCH /systems/{id}` 端点已存在（`backend/app/modules/systems/router.py`），前端 `SystemDefinitionForm` 组件已支持编辑模式（`frontend/components/gates/SystemDefinitionForm.tsx`），`useSystemDetail` 与 `useUpdateSystem` hooks 已实现（`frontend/hooks/useSystem.ts`），`GatePanel` 已集成 SystemDefinitionForm 并在 G0 active/passed 状态下渲染表单（`frontend/components/gates/GatePanel.tsx:262-319`），系统页已传递 `systemDetail` 与 `onUpdateSystem` 给 GatePanel（`frontend/app/projects/[projectId]/systems/[systemId]/page.tsx:180-244`）。G0 门禁逻辑 `check_system_defined` 已存在（`backend/app/modules/gates/service.py:64-81`）。后端测试已覆盖 update 端点（`backend/tests/modules/systems/test_systems_api.py:384-405`）。G0 可操作闭环已完整实现，无需补充工作。
- 2026-03-11 已确认 G1/G2/G3 收口完整落地：**G1 (Figure Plan)** - 后端 `evidence` 模块已实现 FigurePlan 生成/列表/确认端点（`backend/app/modules/evidence/router.py`），前端 `FigurePlanPanel` 组件已支持生成/确认 Figure Plan（`frontend/components/gates/FigurePlanPanel.tsx`），`useFigurePlans`/`useGenerateFigurePlan`/`useConfirmFigurePlan` hooks 已实现（`frontend/hooks/useFigurePlan.ts`），门禁逻辑 `check_figure_plan_ready` 已存在（`backend/app/modules/gates/service.py:95-122`）。**G2 (Data & Analysis)** - 后端 `assets` 模块已实现资产上传/分析任务创建端点（`backend/app/modules/assets/router.py`），前端 `AnalysisPanel` 组件已支持上传资产、创建分析任务（`frontend/components/gates/AnalysisPanel.tsx`），`useAssets`/`useUploadAsset`/`useAnalysisRuns`/`useCreateAnalysisRun` hooks 已实现（`frontend/hooks/useAnalysis.ts`），门禁逻辑 `check_data_and_analysis_ready` 已存在。**G3 (Assets Confirmation)** - 后端 `assets` 模块已实现 Manifest 生成/确认/资产 QC 确认端点（`backend/app/modules/assets/router.py`），前端 `ManifestPanel` 组件已支持生成/确认 Manifest、确认资产 QC、绑定元数据（`frontend/components/gates/ManifestPanel.tsx`），`useManifest`/`useGenerateManifest`/`useConfirmManifest`/`useConfirmAssetQC`/`useBindAssetMetadata` hooks 已实现（`frontend/hooks/useManifest.ts`），门禁逻辑 `check_assets_confirmed` 已存在。G1/G2/G3 可操作闭环已完整实现，无需补充工作。

## 已建立的基线

- 目录骨架（backend/app/modules/*, frontend/app/*, frontend/components/*）
- 公共契约（ApiResponse, WorkflowSnapshot, Blocker, GateNavItem 等）
- 数据层基础设施（SQLAlchemy 模型, Alembic 迁移, React Query hooks）
- 工作流主控边界（gates.service, tasks.service, system_workflow）
- 实时通道（broadcaster + /ws/tasks + useWebSocket）
- llmdoc 文档基线

## 当前缺口

- Figure Plan / Evidence Matrix / Outline / Section Draft 的完整业务生成器尚未全部完成前端承接，当前以最小后端落地为主。
- Phase 2 已完成 G0→G1→G2→G3→G4→G5 全链闭环：所有 gate 的前端工作台均已具备最小可操作闭环，后端 `backend/app/modules/assets`、`backend/app/modules/evidence`、`backend/app/modules/drafts` 均已进入最小可用阶段，统一保持 thin workflow / task event 模式，不扩成真实长流程编排。
- 多实验体系后的跨体系整合未开始。

## Builder 约束

所有 Builder 在动手前必须先阅读：

- `llmdoc/index.md`
- `llmdoc/overview/*`
- 至少 3 篇相关 architecture/reference 文档
