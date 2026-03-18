// G5 Smart Draft Generation — Frontend Types

export type TraceabilityEntry = {
  claimTag: string
  textExcerpt: string
  charStart: number
  charEnd: number
}

export type DraftContextClaimDetail = {
  claimId: string
  statement: string
  sectionRef: string
  assetDescriptions: string[]
}

export type DraftContextPack = {
  systemSummary: string
  sectionKey: string
  outlineNodes: Record<string, unknown>[]
  claims: DraftContextClaimDetail[]
  promptText: string
}

export type DraftChatMessageDetail = {
  id: string
  sessionId: string
  role: string
  content: string
  status: string
  turnIndex: number
  errorText: string | null
  createdAt: string
  updatedAt: string
}

export type DraftValidateResponse = {
  draft: import("../hooks/useDrafts").SectionDraftDetail
  validationPassed: boolean
  errors: Array<Record<string, unknown>>
}
