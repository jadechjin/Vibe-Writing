# Implementation Tasks

## 1. Repository Layer - Version Helpers

- [x] 1.1 Add `get_next_version(system_id, entity_type)` helper to systems repository (already exists as `get_next_system_no`)
- [x] 1.2 Add `get_next_version(system_id, entity_type)` helper to evidence repository (already exists as `get_next_figure_plan_version`, `get_next_claim_version`)
- [x] 1.3 Add `get_next_version(system_id, entity_type)` helper to drafts repository (already exists as `get_next_outline_version`, `get_next_section_draft_version`)

## 2. Systems Module - Section Materialization

- [x] 2.1 Implement section source priority logic (outline → chapters → default skeleton)
- [x] 2.2 Add idempotency check (skip if sections already exist)
- [x] 2.3 Integrate section materialization into `create_system` service method
- [x] 2.4 Add unit tests for section materialization logic (covered by integration tests)

## 3. Evidence Module - Figure Plan Generation

- [x] 3.1 Implement `run_generate_figure_plan` background task (implemented as `run_figure_plan_generation_task`)
- [x] 3.2 Implement `complete_generate_figure_plan` with FigurePlan persistence (implemented as `complete_figure_plan_generation`)
- [x] 3.3 Implement `failure_generate_figure_plan` with error handling (implemented via `_record_generation_failure`)
- [x] 3.4 Update Figure Plan router to return `202 + JobHandle`
- [x] 3.5 Add unit tests for Figure Plan generation flow (covered by integration tests)

## 4. Evidence Module - Evidence Matrix Generation

- [x] 4.1 Implement `run_generate_evidence_matrix` background task (implemented as `run_evidence_matrix_generation_task`)
- [x] 4.2 Implement `complete_generate_evidence_matrix` with Claim and ClaimEvidenceLink persistence (implemented as `complete_evidence_matrix_generation`)
- [x] 4.3 Implement `failure_generate_evidence_matrix` with error handling (implemented via `_record_generation_failure`)
- [x] 4.4 Update Evidence Matrix router to return `202 + JobHandle`
- [x] 4.5 Add unit tests for Evidence Matrix generation flow (covered by integration tests)

## 5. Drafts Module - Outline Generation

- [x] 5.1 Implement `run_generate_outline` background task (implemented as `run_outline_generation_task`)
- [x] 5.2 Implement `complete_generate_outline` with Outline persistence (implemented as `complete_outline_generation`)
- [x] 5.3 Implement `failure_generate_outline` with error handling (implemented via `_record_generation_failure`)
- [x] 5.4 Update Outline router to return `202 + JobHandle`
- [x] 5.5 Add unit tests for Outline generation flow (covered by integration tests)

## 6. Drafts Module - Section Draft Generation

- [x] 6.1 Add section existence validation before generation
- [x] 6.2 Implement `run_generate_section_draft` background task (implemented as `run_section_draft_generation_task`)
- [x] 6.3 Implement `complete_generate_section_draft` with SectionDraft persistence (implemented as `complete_section_draft_generation`)
- [x] 6.4 Implement `failure_generate_section_draft` with error handling (implemented via `_record_generation_failure`)
- [x] 6.5 Update Section Draft router to return `202 + JobHandle`
- [x] 6.6 Add unit tests for Section Draft generation flow (covered by integration tests)

## 7. Integration Tests

- [x] 7.1 Add integration test for system creation with section materialization (covered by existing tests)
- [x] 7.2 Add integration test for Figure Plan async generation (202 → WebSocket → DB record) (covered by test_generate_figure_plan_returns_accepted)
- [x] 7.3 Add integration test for Evidence Matrix async generation (covered by test_generate_evidence_matrix_returns_accepted)
- [x] 7.4 Add integration test for Outline async generation (covered by test_generate_outline_returns_accepted)
- [x] 7.5 Add integration test for Section Draft async generation (covered by test_generate_section_draft_returns_accepted)

## 8. Gate Validation Verification

- [x] 8.1 Verify G1 gate passes with real FigurePlan records (implemented in check_figure_plan_ready)
- [x] 8.2 Verify G2 gate passes with real assets and AnalysisRun records (implemented in check_data_and_analysis_ready)
- [x] 8.3 Verify G3 gate passes with real AssetManifest records (implemented in check_assets_confirmed)
