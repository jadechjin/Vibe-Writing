## ADDED Requirements

### Requirement: Toast notification system
The system SHALL provide a `ToastProvider` React context provider and `useToast()` hook. `useToast()` SHALL expose `showSuccess(message: string)` and `showError(message: string)` functions. Toasts SHALL auto-dismiss after 4000ms. Multiple toasts SHALL queue and display sequentially. `ToastProvider` SHALL be added to `frontend/app/projects/[projectId]/layout.tsx`.

#### Scenario: Success toast appears and auto-dismisses
- **WHEN** `showSuccess("Approved 5 claims")` is called
- **THEN** a success toast is visible for 4000ms then disappears

#### Scenario: Error toast appears
- **WHEN** `showError("2 claims failed to approve")` is called
- **THEN** an error toast with red styling is visible

#### Scenario: Multiple toasts queue
- **WHEN** two toasts are triggered in quick succession
- **THEN** they display sequentially, not overlapping

### Requirement: Confirm dialog for destructive actions
Gate panels SHALL use `ConfirmDialog` before executing irreversible actions (e.g., confirming manifest, approving all claims). The dialog SHALL be triggered by the action button and require explicit user confirmation before proceeding.

#### Scenario: Manifest confirm requires dialog
- **WHEN** user clicks "Confirm Manifest" in ManifestPanel
- **THEN** a ConfirmDialog appears asking for confirmation before the API call is made

#### Scenario: Cancel aborts action
- **WHEN** user clicks Cancel in the ConfirmDialog
- **THEN** no API call is made and the dialog closes

### Requirement: Empty state guidance in gate panels
Each gate panel SHALL display an `EmptyState` component when its primary data list is empty (no figure plans, no claims, no assets, no sections, no drafts).

#### Scenario: Empty claims list shows guidance
- **WHEN** EvidenceMatrixPanel has no claims
- **THEN** an EmptyState with text "No claims generated yet. Generate the evidence matrix to get started." is shown

#### Scenario: Empty assets list shows guidance
- **WHEN** ManifestPanel has no assets
- **THEN** an EmptyState with appropriate guidance text is shown
