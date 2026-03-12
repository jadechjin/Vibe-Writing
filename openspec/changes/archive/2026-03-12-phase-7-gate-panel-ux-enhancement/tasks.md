## 1. Backend Schemas

- [x] 1.1 Add `BatchApproveClaimsRequest` and `BatchApproveClaimsResponse` to `backend/app/modules/evidence/schemas.py`
- [x] 1.2 Add `BatchConfirmAssetQCRequest` and `BatchConfirmAssetQCResponse` to `backend/app/modules/assets/schemas.py`

## 2. Backend Services

- [x] 2.1 Implement `batch_approve_claims(session, system_id, claim_ids)` in `backend/app/modules/evidence/service.py` with partial success strategy
- [x] 2.2 Implement `batch_confirm_asset_qc(session, system_id, asset_ids)` in `backend/app/modules/assets/service.py` with partial success strategy

## 3. Backend Routers

- [x] 3.1 Add `POST /systems/{system_id}/claims/batch-approve` endpoint to `backend/app/modules/evidence/router.py`
- [x] 3.2 Add `POST /systems/{system_id}/assets/batch-confirm-qc` endpoint to `backend/app/modules/assets/router.py`

## 4. Backend Tests

- [x] 4.1 Add batch approve claims tests to `backend/tests/modules/evidence/test_evidence_api.py` (all succeed, partial failure, empty input, wrong system)
- [x] 4.2 Add batch confirm QC tests to `backend/tests/modules/assets/test_assets_api.py` (all succeed, missing metadata, empty input)

## 5. Frontend Shared Styles

- [x] 5.1 Create `frontend/styles/gate-theme.ts` exporting `gateTheme` with 9 style constants (panel, sectionCard, title, desc, actionBtn, statusBadge, emptyState, fieldGroup, input)

## 6. Frontend UI Primitives

- [x] 6.1 Create `frontend/components/ui/ActionButton.tsx` (label, onClick, disabled, isPending, variant, style props)
- [x] 6.2 Create `frontend/components/ui/SectionCard.tsx` (title, description, children, headerExtra, style props)
- [x] 6.3 Create `frontend/components/ui/StatusBadge.tsx` (status, variant with auto-inference, style props)
- [x] 6.4 Create `frontend/components/ui/EmptyState.tsx` (text, icon, style props)
- [x] 6.5 Create `frontend/components/ui/ConfirmDialog.tsx` (isOpen, title, message, onConfirm, onCancel, isPending, confirmLabel props)

## 7. Frontend Toast System

- [x] 7.1 Create `frontend/hooks/useToast.ts` with `ToastProvider` and `useToast()` hook (showSuccess, showError, 4000ms auto-dismiss, queue)
- [x] 7.2 Add `ToastProvider` wrapper to `frontend/app/projects/[projectId]/layout.tsx`

## 8. Frontend GateTaskStatus Enhancement

- [x] 8.1 Update `frontend/components/gates/GateTaskStatus.tsx` to show indeterminate progress bar when status is `running`, full bar briefly on `succeeded`

## 9. Frontend Panel Migration

- [x] 9.1 Migrate `FigurePlanPanel.tsx` to use `gateTheme` constants and shared UI primitives; add EmptyState for empty figure plans list
- [x] 9.2 Migrate `AnalysisPanel.tsx` to use `gateTheme` constants and shared UI primitives; add EmptyState
- [x] 9.3 Migrate `ManifestPanel.tsx` to use `gateTheme` + primitives; add batch QC selection UI (checkboxes, Select All, Bulk Actions bar); add ConfirmDialog for manifest confirm; add EmptyState
- [x] 9.4 Migrate `EvidenceMatrixPanel.tsx` to use `gateTheme` + primitives; add batch claim approval UI (checkboxes, Select All, Bulk Actions bar); add EmptyState
- [x] 9.5 Migrate `DraftPanel.tsx` to use `gateTheme` constants and shared UI primitives; add EmptyState

## 10. Frontend Batch Hooks

- [x] 10.1 Add `useBatchApproveClaims(systemId)` hook to `frontend/hooks/useEvidence.ts`
- [x] 10.2 Add `useBatchConfirmAssetQC(systemId)` hook to `frontend/hooks/useManifest.ts`

## 11. Frontend Tests

- [x] 11.1 Create `frontend/components/ui/__tests__/ActionButton.test.tsx` smoke test
- [x] 11.2 Create `frontend/components/ui/__tests__/ConfirmDialog.test.tsx` smoke test (open/close/confirm)
