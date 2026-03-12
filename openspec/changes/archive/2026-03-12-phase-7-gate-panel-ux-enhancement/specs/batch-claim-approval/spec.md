## ADDED Requirements

### Requirement: Batch approve claims endpoint
The system SHALL expose `POST /systems/{system_id}/claims/batch-approve` accepting body `{ claimIds: string[] }`. The endpoint SHALL process each claim independently (partial success). Response: `{ succeeded: string[], failed: { claimId: string, error: string }[] }`. The endpoint SHALL validate that all `claimIds` belong to the given `system_id`.

#### Scenario: All claims approved successfully
- **WHEN** all provided claim IDs are valid and belong to the system
- **THEN** response `succeeded` contains all IDs and `failed` is empty

#### Scenario: Partial failure
- **WHEN** some claim IDs are invalid (not found or wrong system)
- **THEN** valid claims are approved and returned in `succeeded`; invalid ones appear in `failed` with error message

#### Scenario: section_ref validation
- **WHEN** a claim's `section_ref` is not in the system's defined sections
- **THEN** that claim appears in `failed` with an appropriate error message

#### Scenario: Empty input
- **WHEN** `claimIds` is an empty array
- **THEN** response is `{ succeeded: [], failed: [] }` with HTTP 200

### Requirement: Batch approve claims frontend hook
The system SHALL provide a `useBatchApproveClaims(systemId)` hook in `frontend/hooks/useEvidence.ts` exposing a `batchApprove(claimIds: string[])` async function and `isPending: boolean` state.

#### Scenario: Hook triggers API call
- **WHEN** `batchApprove(["id1", "id2"])` is called
- **THEN** a POST request is sent to `/systems/{systemId}/claims/batch-approve`

### Requirement: Batch selection UI in EvidenceMatrixPanel
The `EvidenceMatrixPanel` SHALL render a checkbox next to each claim in the review queue. A "Bulk Actions" bar SHALL appear when one or more claims are selected, offering an "Approve Selected" button. A "Select All" checkbox SHALL be available in the list header.

#### Scenario: Select all
- **WHEN** user clicks "Select All"
- **THEN** all visible claims are selected and checkboxes are checked

#### Scenario: Approve selected triggers batch
- **WHEN** user clicks "Approve Selected" with claims selected
- **THEN** `batchApprove` is called with selected claim IDs and a toast shows the result
