## ADDED Requirements

### Requirement: Batch confirm asset QC endpoint
The system SHALL expose `POST /systems/{system_id}/assets/batch-confirm-qc` accepting body `{ assetIds: string[] }`. The endpoint SHALL process each asset independently (partial success). Response: `{ succeeded: string[], failed: { assetId: string, error: string }[] }`. The endpoint SHALL validate that all `assetIds` belong to the given `system_id`.

#### Scenario: All assets confirmed successfully
- **WHEN** all provided asset IDs have metadata and belong to the system
- **THEN** response `succeeded` contains all IDs and `failed` is empty

#### Scenario: Asset without metadata fails gracefully
- **WHEN** an asset ID has no associated `AssetMetadata` record
- **THEN** that asset appears in `failed` with "Asset metadata not found" error

#### Scenario: Empty input
- **WHEN** `assetIds` is an empty array
- **THEN** response is `{ succeeded: [], failed: [] }` with HTTP 200

### Requirement: Batch confirm asset QC frontend hook
The system SHALL provide a `useBatchConfirmAssetQC(systemId)` hook in `frontend/hooks/useManifest.ts` exposing a `batchConfirmQC(assetIds: string[])` async function and `isPending: boolean` state.

#### Scenario: Hook triggers API call
- **WHEN** `batchConfirmQC(["id1", "id2"])` is called
- **THEN** a POST request is sent to `/systems/{systemId}/assets/batch-confirm-qc`

### Requirement: Batch selection UI in ManifestPanel
The `ManifestPanel` SHALL render a checkbox next to each asset in the assets table. A "Bulk Actions" bar SHALL appear when one or more assets are selected, offering a "Confirm QC Selected" button. A "Select All" checkbox SHALL be available in the table header.

#### Scenario: Confirm QC selected triggers batch
- **WHEN** user clicks "Confirm QC Selected" with assets selected
- **THEN** `batchConfirmQC` is called with selected asset IDs and a toast shows the result

#### Scenario: Already-confirmed assets are visually distinct
- **WHEN** an asset already has `qc_status="confirmed"`
- **THEN** its checkbox is disabled and it shows a confirmed badge
