## Why

Phase 1-6 已完成 G0→G5 全链闭环和多实验体系管理，但各 gate 面板（G1-G5）仍处于"最小可用"状态：5 个面板存在大量重复的 CSSProperties 定义、缺乏共享 UI 原语、无实时进度反馈（后端 TaskEvent.progress 字段已存在但前端未消费）、无批量操作支持、无操作成功/失败 toast、无确认对话框、无空态引导。本次变更将这些面板从"能用"升级到"好用"。

## What Changes

- 抽取共享样式模块 `frontend/styles/gate-theme.ts`，消除 5 个面板间的 CSSProperties 重复
- 抽取共享 UI 原语组件（ActionButton, SectionCard, StatusBadge, DataTable, EmptyState, ConfirmDialog, Toast）
- 增强 GateTaskStatus 组件，消费 `task.progress` 事件展示真实进度条（0-100%）
- 新增后端 batch 端点：批量审批 claims、批量确认资产 QC
- 新增前端批量操作 UI：多选 + 批量操作按钮
- 新增操作反馈系统：成功/失败 toast 通知、危险操作确认对话框、空态引导提示

## Capabilities

### New Capabilities
- `shared-gate-theme`: 共享样式模块，统一 5 个 gate 面板的视觉语言
- `shared-ui-primitives`: 共享 UI 原语组件库（ActionButton, SectionCard, StatusBadge, DataTable, EmptyState）
- `realtime-progress-feedback`: GateTaskStatus 消费 TaskEvent.progress 展示真实进度条
- `batch-claim-approval`: 批量审批 claims 的后端端点和前端多选 UI
- `batch-asset-qc-confirm`: 批量确认资产 QC 的后端端点和前端多选 UI
- `operation-feedback-system`: Toast 通知 + 确认对话框 + 空态引导

### Modified Capabilities
- `gate-task-status`: 增强进度展示，从 spinner 升级为真实进度条
- `gate-panel`: 各 gate 面板迁移到共享样式和共享组件

## Impact

**前端**：
- `frontend/styles/gate-theme.ts`（新建）：共享样式常量
- `frontend/components/ui/`（新建目录）：ActionButton, SectionCard, StatusBadge, DataTable, EmptyState, ConfirmDialog, Toast
- `frontend/components/gates/GateTaskStatus.tsx`（修改）：消费 progress 事件
- `frontend/components/gates/FigurePlanPanel.tsx`（修改）：迁移到共享样式和组件
- `frontend/components/gates/AnalysisPanel.tsx`（修改）：同上
- `frontend/components/gates/ManifestPanel.tsx`（修改）：同上 + 批量 QC 确认
- `frontend/components/gates/EvidenceMatrixPanel.tsx`（修改）：同上 + 批量 claim 审批
- `frontend/components/gates/DraftPanel.tsx`（修改）：同上
- `frontend/hooks/useEvidence.ts`（修改）：新增 useBatchApproveClaims hook
- `frontend/hooks/useManifest.ts`（修改）：新增 useBatchConfirmAssetQC hook
- `frontend/hooks/useToast.ts`（新建）：Toast 状态管理

**后端**：
- `backend/app/modules/evidence/router.py`（修改）：新增 `POST /systems/{id}/claims/batch-approve`
- `backend/app/modules/evidence/service.py`（修改）：新增 `batch_approve_claims()`
- `backend/app/modules/assets/router.py`（修改）：新增 `POST /systems/{id}/assets/batch-confirm-qc`
- `backend/app/modules/assets/service.py`（修改）：新增 `batch_confirm_asset_qc()`
- `backend/app/modules/evidence/schemas.py`（修改）：新增 batch request/response 类型
- `backend/app/modules/assets/schemas.py`（修改）：同上

**测试**：
- `backend/tests/modules/evidence/test_evidence_api.py`（修改）：batch approve 测试
- `backend/tests/modules/assets/test_assets_api.py`（修改）：batch QC confirm 测试
- `frontend/components/ui/__tests__/`（新建）：共享组件 smoke tests

**依赖**：
- 无新外部依赖（继续使用 inline CSSProperties，不引入 UI 库）
- 后端 batch 端点复用现有 service 层单项操作的事务语义
