// G4 Evidence Matrix Redesign — Frontend Types

export type G4SnapshotDetail = {
  id: string
  systemId: string
  fingerprint: string
  skeletonVersion: number
  manifestVersion: number | null
  planVersionsJson: Record<string, number>
  assetVersionsJson: Record<string, string>
  runVersionsJson: Record<string, string>
  createdAt: string
  updatedAt: string
}

export type EvidenceGapDetail = {
  gapType: "missing_evidence" | "missing_analysis" | "weak_evidence" | "section_uncovered" | "pending_approval" | "binding_missing"
  severity: "blocker" | "warning" | "info"
  remediationStage: "G2" | "G3" | "G4"
  claimId: string | null
  sectionKey: string | null
  assetId: string | null
  message: string
  suggestedAction: string
  remediationHint: string
}

export type BindingSuggestion = {
  assetId: string
  reason: string
}

export type OutlineNodeData = {
  nodeType: "background" | "method" | "result" | "summary"
  claimIds: string[]
  evidenceStrength: string
}

export type EvidenceLinkRef = {
  claimId: string
  assetId: string
  strength: string
}

export type AnalysisRunRef = {
  runId: string
  status: string
  summary: string
}

export type EnhancedOutlineSection = {
  sectionKey: string
  sectionTitle: string
  claimIds: string[]
  evidenceLinkRefs: EvidenceLinkRef[]
  analysisRunRefs: AnalysisRunRef[]
  nodes: OutlineNodeData[]
  bindingSuggestions: BindingSuggestion[]
  coverage: "covered" | "uncovered" | "partial"
}

export type InputSummary = {
  sectionCount: number
  claimCount: number
  linkCount: number
  runCount: number
}

export type EnhancedOutlineMeta = {
  fingerprint?: string
  generatedAt?: string
  claimRefs?: Array<{ claimId: string; version: number }>
  inputSummary?: InputSummary
}

export type EnhancedOutlineJson = {
  meta?: EnhancedOutlineMeta
  sections: EnhancedOutlineSection[]
}

export type StrengthSummary = {
  overall: string
  linkCount: number
  distribution?: {
    strong: number
    medium: number
    weak: number
  }
}
