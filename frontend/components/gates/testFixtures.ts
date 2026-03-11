import type { AssetDetail } from "../../hooks/useAnalysis"
import type { SectionDraftDetail, ReviewCommentDetail } from "../../hooks/useDrafts"
import type { ClaimDetail, OutlineAssetBindingDetail, OutlineDetail } from "../../hooks/useEvidence"
import type { SystemDetail } from "../../hooks/useProjects"
import type { Blocker, WorkflowSnapshot, WorkflowEventRecord } from "../../hooks/useProjectStatus"

export function buildSystemDetail(overrides: Partial<SystemDetail> = {}): SystemDetail {
  return {
    id: "system-1",
    projectId: "project-1",
    systemNo: 1,
    title: "Test System",
    status: "active",
    researchGoal: null,
    samplesSubjects: null,
    variablesControls: null,
    outputMetrics: null,
    methodsSummary: null,
    systemCardJson: {},
    sections: [
      { id: "section-intro", sectionKey: "intro", title: "Introduction", orderNo: 1 },
      { id: "section-methods", sectionKey: "methods", title: "Methods", orderNo: 2 },
      { id: "section-results", sectionKey: "results", title: "Results", orderNo: 3 },
    ],
    createdAt: "2026-03-11T00:00:00Z",
    updatedAt: "2026-03-11T00:00:00Z",
    ...overrides,
  }
}

export function buildWorkflowEvent(overrides: Partial<WorkflowEventRecord> = {}): WorkflowEventRecord {
  return {
    id: "event-1",
    eventType: "workflow.state_changed",
    status: "succeeded",
    message: "Workflow moved forward.",
    fromState: "Evidence_Matrix_Ready",
    toState: "Outline_Ready",
    progress: 60,
    payload: {},
    createdAt: "2026-03-11T00:00:00Z",
    ...overrides,
  }
}

export function buildBlocker(overrides: Partial<Blocker> = {}): Blocker {
  return {
    code: "missing_outline",
    message: "Outline confirmation is required.",
    gate: "G5",
    currentState: "Section_Drafting",
    requiredChecks: ["Outline_Ready"],
    details: {},
    ...overrides,
  }
}

export function buildWorkflowSnapshot(overrides: Partial<WorkflowSnapshot> = {}): WorkflowSnapshot {
  return {
    workflowId: "workflow-1",
    jobId: "job-1",
    projectId: "project-1",
    systemId: "system-1",
    workflowKey: "system_workflow",
    currentState: "Evidence_Matrix_Ready",
    currentGate: "G4",
    status: "running",
    context: {},
    version: 1,
    startedAt: "2026-03-11T00:00:00Z",
    completedAt: null,
    lastError: null,
    latestEvent: buildWorkflowEvent(),
    latestBlockers: [],
    events: [buildWorkflowEvent()],
    ...overrides,
  }
}

export function buildAsset(overrides: Partial<AssetDetail> = {}): AssetDetail {
  return {
    id: "asset-1",
    projectId: "project-1",
    systemId: "system-1",
    assetType: "figure",
    fileName: "figure-1.png",
    storageKey: "assets/figure-1.png",
    mimeType: "image/png",
    version: 1,
    uploadedBy: "tester",
    createdAt: "2026-03-11T00:00:00Z",
    updatedAt: "2026-03-11T00:00:00Z",
    metadataEntry: null,
    ...overrides,
  }
}

export function buildClaim(overrides: Partial<ClaimDetail> = {}): ClaimDetail {
  return {
    id: "claim-record-1",
    systemId: "system-1",
    claimId: "claim-1",
    statement: "Claim statement",
    sectionRef: "intro",
    confidenceLevel: "high",
    status: "pending",
    version: 1,
    approvedAt: null,
    createdAt: "2026-03-11T00:00:00Z",
    updatedAt: "2026-03-11T00:00:00Z",
    ...overrides,
  }
}

export function buildOutlineBinding(overrides: Partial<OutlineAssetBindingDetail> = {}): OutlineAssetBindingDetail {
  return {
    id: "binding-1",
    outlineId: "outline-1",
    assetId: "asset-1",
    sectionKey: "intro",
    bindingNote: null,
    createdAt: "2026-03-11T00:00:00Z",
    updatedAt: "2026-03-11T00:00:00Z",
    ...overrides,
  }
}

export function buildOutline(overrides: Partial<OutlineDetail> = {}): OutlineDetail {
  return {
    id: "outline-1",
    systemId: "system-1",
    version: 1,
    outlineJson: {
      sections: [
        { sectionKey: "intro", title: "Introduction" },
        { sectionKey: "methods", title: "Methods" },
      ],
    },
    status: "draft",
    generatedFromClaimsJson: ["claim-1"],
    bindings: [],
    approvedAt: null,
    createdAt: "2026-03-11T00:00:00Z",
    updatedAt: "2026-03-11T00:00:00Z",
    ...overrides,
  }
}

export function buildReviewComment(overrides: Partial<ReviewCommentDetail> = {}): ReviewCommentDetail {
  return {
    id: "comment-1",
    draftId: "draft-1",
    commenterId: "reviewer-1",
    commentText: "Please clarify the evidence chain.",
    decision: "request_changes",
    contextJson: {},
    resolvedAt: null,
    createdAt: "2026-03-11T00:00:00Z",
    updatedAt: "2026-03-11T00:00:00Z",
    ...overrides,
  }
}

export function buildDraft(overrides: Partial<SectionDraftDetail> = {}): SectionDraftDetail {
  return {
    id: "draft-1",
    systemId: "system-1",
    outlineId: "outline-1",
    sectionKey: "intro",
    version: 1,
    contentMd: "Draft content",
    status: "pending_review",
    generatedFromClaimsJson: ["claim-1"],
    reviewComments: [],
    approvedAt: null,
    createdAt: "2026-03-11T00:00:00Z",
    updatedAt: "2026-03-11T00:00:00Z",
    ...overrides,
  }
}
