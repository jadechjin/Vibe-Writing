## 1. Documentation Review and Validation

- [ ] 1.1 Review proposal.md for completeness and accuracy
- [ ] 1.2 Review design.md technical decisions against actual implementation
- [ ] 1.3 Review all three spec files for requirement coverage
- [ ] 1.4 Validate that all constraints from research phase are documented

## 2. Code Pattern Verification

- [ ] 2.1 Verify async-generation-pattern spec against evidence/service.py implementation
- [ ] 2.2 Verify async-generation-pattern spec against drafts/service.py implementation
- [ ] 2.3 Verify frontend-gate-integration spec against GatePanel.tsx implementation
- [ ] 2.4 Verify frontend-gate-integration spec against useEvidence and useDrafts hooks
- [ ] 2.5 Verify workflow-task-event-model spec against TaskWorkflowService implementation

## 3. Risk and Mitigation Documentation

- [ ] 3.1 Document durability risk mitigation strategies in design.md
- [ ] 3.2 Document evidence failure path inconsistency and proposed fix
- [ ] 3.3 Document concurrent version conflict scenarios and mitigations
- [ ] 3.4 Document input drift behavior and when it's acceptable
- [ ] 3.5 Document WebSocket event loss scenarios and fallback strategies

## 4. Success Criteria Validation

- [ ] 4.1 Validate backend success criteria against actual test cases
- [ ] 4.2 Validate frontend success criteria against actual UI behavior
- [ ] 4.3 Document any gaps between documented criteria and actual implementation

## 5. Open Questions Resolution

- [ ] 5.1 Decide whether Outline should snapshot claim IDs (document decision in design.md)
- [ ] 5.2 Decide whether evidence should add rollback in failure handlers (document decision)
- [ ] 5.3 Decide whether to add task.started/task.progress events (document decision)
- [ ] 5.4 Decide whether to implement WebSocket polling fallback (document decision)
- [ ] 5.5 Define durability strategy threshold (document decision)

## 6. Reference Documentation Creation

- [ ] 6.1 Create quick reference guide for implementing new async generation features
- [ ] 6.2 Create checklist for frontend gate integration
- [ ] 6.3 Create troubleshooting guide for common async generation issues
- [ ] 6.4 Create migration guide if any patterns need to be updated

## 7. Final Review and Archive

- [ ] 7.1 Conduct peer review of all documentation artifacts
- [ ] 7.2 Address review feedback and update artifacts
- [ ] 7.3 Verify all tasks are complete
- [ ] 7.4 Archive change using `/ccg:spec-review` and `/opsx:archive`
