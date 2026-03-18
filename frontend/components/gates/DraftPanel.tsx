"use client"

import { useEffect, useMemo, useState, type CSSProperties } from "react"

import {
  useAddReviewComment,
  useApproveDraft,
  useDrafts,
  useGenerateSectionDraft,
} from "../../hooks/useDrafts"
import type { SectionDraftDetail } from "../../hooks/useDrafts"
import { useOutlines } from "../../hooks/useEvidence"
import type { SystemDetail } from "../../hooks/useProjects"
import type { Blocker, WorkflowSnapshot } from "../../hooks/useProjectStatus"
import { gateTheme } from "../../styles/gate-theme"
import { ActionButton } from "../ui/ActionButton"
import { EmptyState } from "../ui/EmptyState"
import { SectionCard } from "../ui/SectionCard"
import {
  getLatestDraftsBySection,
  getLatestOutline,
  getOrderedSystemSections,
  type SystemSectionDetail,
} from "./workbenchSelectors"
import { GateTaskStatus } from "./GateTaskStatus"
import { DraftingWorkspace } from "./g5/DraftingWorkspace"

export type GateContentPanelProps = Readonly<{
  snapshot: WorkflowSnapshot | null
  blockers: Blocker[]
  systemId: string
  systemDetail?: SystemDetail | null
}>

type ReviewDraft = {
  commenterId: string
  commentText: string
  decision: "approve" | "request_changes" | "freeze"
}

type SectionGroupKey = "approved" | "needs_review" | "ready_to_generate"

type GroupedSection = {
  section: SystemSectionDetail
  draft: SectionDraftDetail | null
}

type SuccessFeedback = {
  message: string
  sectionKey: string
  baselineSignature: string
}

const SECTION_GROUP_META: Record<
  SectionGroupKey,
  {
    title: string
    description: string
    emptyText: string
  }
> = {
  approved: {
    title: "已通过章节",
    description: "最新已通过草稿，这些章节已可进入章节级验收。",
    emptyText: "暂无已通过的最新草稿。",
  },
  needs_review: {
    title: "待审阅",
    description: "最新草稿已存在，但仍需审阅意见、迭代或批准。",
    emptyText: "当前无章节等待审阅。",
  },
  ready_to_generate: {
    title: "待生成",
    description: "尚无最新草稿的章节，准备就绪后可从已确认提纲生成。",
    emptyText: "所有系统章节均已有最新草稿版本。",
  },
}

const panelStyle = gateTheme.panel

const sectionCardStyle = gateTheme.sectionCard

const titleStyle = gateTheme.title

const descStyle = gateTheme.desc

const summaryGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
  gap: "10px",
  marginTop: "12px",
}

const summaryCardStyle: CSSProperties = {
  padding: "10px 12px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.12)",
  background: "rgba(15, 23, 42, 0.35)",
}

const summaryValueStyle: CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#f8fafc",
}

const summaryLabelStyle: CSSProperties = {
  fontSize: "11px",
  color: "#94a3b8",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginTop: "4px",
}

const listStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "10px",
  marginTop: "12px",
}

const itemStyle: CSSProperties = {
  padding: "12px 16px",
  borderRadius: "12px",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  background: "rgba(15, 23, 42, 0.3)",
}

const itemHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "8px",
}

const itemTitleStyle: CSSProperties = {
  fontSize: "14px",
  fontWeight: 600,
  color: "#f1f5f9",
}

const itemMetaStyle: CSSProperties = {
  fontSize: "12px",
  color: "#94a3b8",
  marginTop: "4px",
}

const groupHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  gap: "12px",
}

const groupMetaStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "4px",
}

const groupCountBadgeStyle: CSSProperties = {
  alignSelf: "center",
  minWidth: "36px",
  padding: "4px 10px",
  borderRadius: "999px",
  border: "1px solid rgba(148, 163, 184, 0.2)",
  background: "rgba(15, 23, 42, 0.45)",
  color: "#e2e8f0",
  fontSize: "12px",
  fontWeight: 700,
  textAlign: "center",
}

const badgeStyle = (status: string): CSSProperties => ({
  padding: "2px 8px",
  borderRadius: "6px",
  fontSize: "11px",
  fontWeight: 600,
  textTransform: "uppercase",
  background:
    status === "approved" ? "rgba(34, 197, 94, 0.15)" : "rgba(249, 115, 22, 0.15)",
  color: status === "approved" ? "#4ade80" : "#fb923c",
  border: `1px solid ${
    status === "approved" ? "rgba(34, 197, 94, 0.3)" : "rgba(249, 115, 22, 0.3)"
  }`,
})

const decisionBadgeStyle = (decision: string | null): CSSProperties => {
  if (decision === "approve") {
    return {
      padding: "2px 8px",
      borderRadius: "999px",
      fontSize: "11px",
      fontWeight: 600,
      background: "rgba(34, 197, 94, 0.15)",
      color: "#86efac",
      border: "1px solid rgba(34, 197, 94, 0.28)",
    }
  }

  if (decision === "freeze") {
    return {
      padding: "2px 8px",
      borderRadius: "999px",
      fontSize: "11px",
      fontWeight: 600,
      background: "rgba(148, 163, 184, 0.14)",
      color: "#cbd5e1",
      border: "1px solid rgba(148, 163, 184, 0.25)",
    }
  }

  return {
    padding: "2px 8px",
    borderRadius: "999px",
    fontSize: "11px",
    fontWeight: 600,
    background: "rgba(249, 115, 22, 0.15)",
    color: "#fdba74",
    border: "1px solid rgba(249, 115, 22, 0.28)",
  }
}

const previewShellStyle: CSSProperties = {
  marginTop: "12px",
  padding: "12px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  background: "rgba(2, 6, 23, 0.28)",
}

const previewHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "8px",
}

const previewToggleStyle: CSSProperties = {
  padding: "4px 10px",
  borderRadius: "999px",
  border: "1px solid rgba(148, 163, 184, 0.3)",
  background: "rgba(51, 65, 85, 0.2)",
  color: "#cbd5e1",
  fontSize: "12px",
  fontWeight: 600,
  cursor: "pointer",
}

const previewUnavailableStyle: CSSProperties = {
  padding: "4px 10px",
  borderRadius: "999px",
  border: "1px solid rgba(100, 116, 139, 0.3)",
  background: "rgba(30, 41, 59, 0.35)",
  color: "#94a3b8",
  fontSize: "11px",
  fontWeight: 600,
  textTransform: "uppercase",
}

const contentPreviewStyle: CSSProperties = {
  fontSize: "13px",
  color: "#cbd5e1",
  marginTop: "10px",
  padding: "10px",
  background: "rgba(2, 6, 23, 0.45)",
  borderRadius: "8px",
  whiteSpace: "pre-wrap",
  lineHeight: 1.5,
}

const actionRowStyle: CSSProperties = {
  display: "flex",
  gap: "8px",
  flexWrap: "wrap",
  marginTop: "10px",
}

const actionBtnStyle: CSSProperties = {
  padding: "6px 14px",
  borderRadius: "8px",
  border: "1px solid rgba(249, 115, 22, 0.5)",
  background: "rgba(154, 52, 18, 0.15)",
  fontSize: "12px",
  fontWeight: 600,
  color: "#fb923c",
  cursor: "pointer",
}

const secondaryBtnStyle: CSSProperties = {
  ...actionBtnStyle,
  border: "1px solid rgba(148, 163, 184, 0.3)",
  background: "rgba(51, 65, 85, 0.2)",
  color: "#cbd5e1",
}

const blockerListStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
  marginTop: "8px",
}

const blockerItemStyle: CSSProperties = {
  padding: "8px 12px",
  borderRadius: "8px",
  border: "1px solid rgba(248, 113, 113, 0.2)",
  background: "rgba(127, 29, 29, 0.1)",
  fontSize: "12px",
  color: "#fca5a5",
}

const fieldGroupStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
  marginTop: "12px",
}

const fieldLabelStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  color: "#cbd5e1",
}

const inputStyle: CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: "8px",
  border: "1px solid rgba(148, 163, 184, 0.18)",
  background: "rgba(15, 23, 42, 0.6)",
  color: "#e2e8f0",
  fontSize: "12px",
  outline: "none",
}

const textareaStyle: CSSProperties = {
  ...inputStyle,
  resize: "vertical",
  minHeight: "72px",
  fontFamily: "inherit",
}

const commentListStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  marginTop: "12px",
}

const commentItemStyle: CSSProperties = {
  padding: "10px 12px",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.45)",
  border: "1px solid rgba(148, 163, 184, 0.08)",
}

const commentHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "8px",
  flexWrap: "wrap",
}

const commentMetaStyle: CSSProperties = {
  fontSize: "11px",
  color: "#94a3b8",
}

const helperTextStyle: CSSProperties = {
  marginTop: "8px",
  fontSize: "12px",
  lineHeight: 1.5,
  color: "#94a3b8",
}

const emptyStateStyle = gateTheme.emptyState

const errorTextStyle: CSSProperties = {
  marginTop: "8px",
  fontSize: "12px",
  color: "#fca5a5",
}

const successTextStyle: CSSProperties = {
  marginTop: "8px",
  fontSize: "12px",
  color: "#86efac",
}

const subSectionTitleStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 700,
  color: "#cbd5e1",
  textTransform: "uppercase",
  letterSpacing: "0.08em",
}

const INITIAL_REVIEW_DRAFT: ReviewDraft = {
  commenterId: "reviewer-1",
  commentText: "",
  decision: "request_changes",
}

function normalizeText(value: string): string {
  return value.trim()
}

function isDraftPreviewable(draft: SectionDraftDetail | null): boolean {
  return Boolean(draft && normalizeText(draft.contentMd).length > 0)
}

function getDecisionLabel(decision: string | null): string {
  switch (decision) {
    case "approve":
      return "通过"
    case "freeze":
      return "冻结"
    case "request_changes":
      return "请求修改"
    default:
      return "评论"
  }
}

function getDraftStatusLabel(status: string): string {
  switch (status) {
    case "approved":
      return "已通过"
    case "needs_review":
      return "待审阅"
    case "draft":
      return "草稿"
    default:
      return status
  }
}

function getFeedbackKey(kind: "generate" | "approve" | "review", id: string): string {
  return `${kind}:${id}`
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "未知错误"
}

export function DraftPanel({
  snapshot,
  systemId,
  systemDetail,
  blockers,
}: GateContentPanelProps) {
  const { data: drafts, isLoading: draftsLoading, error: draftsError } = useDrafts(systemId)
  const { data: outlines } = useOutlines(systemId)

  const generateDraft = useGenerateSectionDraft(systemId)
  const approveDraft = useApproveDraft(systemId)
  const addReviewComment = useAddReviewComment(systemId)

  const latestOutline = useMemo(() => getLatestOutline(outlines), [outlines])
  const hasConfirmedOutline = latestOutline?.approvedAt != null
  const currentState = snapshot?.currentState ?? null
  const sections = useMemo(() => getOrderedSystemSections(systemDetail), [systemDetail])

  const [reviewingDraftId, setReviewingDraftId] = useState<string | null>(null)
  const [reviewDrafts, setReviewDrafts] = useState<Record<string, ReviewDraft>>({})
  const [expandedSectionKeys, setExpandedSectionKeys] = useState<Set<string>>(() => new Set())
  const [successMessages, setSuccessMessages] = useState<Record<string, SuccessFeedback>>({})
  const [generateErrorMessages, setGenerateErrorMessages] = useState<Record<string, string>>({})
  const [approveErrorMessages, setApproveErrorMessages] = useState<Record<string, string>>({})
  const [reviewErrorMessages, setReviewErrorMessages] = useState<Record<string, string>>({})
  const [pendingGenerateSectionKey, setPendingGenerateSectionKey] = useState<string | null>(null)
  const [pendingApproveDraftId, setPendingApproveDraftId] = useState<string | null>(null)
  const [pendingReviewDraftId, setPendingReviewDraftId] = useState<string | null>(null)

  const draftBySectionKey = useMemo(() => getLatestDraftsBySection(drafts), [drafts])
  const sectionSignatureByKey = useMemo(() => {
    return new Map(
      sections.map((section) => {
        const draft = draftBySectionKey.get(section.sectionKey) ?? null
        const signature = [
          section.sectionKey,
          draft?.id ?? "",
          draft?.status ?? "",
          draft?.updatedAt ?? "",
          draft?.approvedAt ?? "",
          draft?.reviewComments.length ?? 0,
        ].join(":")
        return [section.sectionKey, signature] as const
      }),
    )
  }, [draftBySectionKey, sections])

  const groupedSections = useMemo(() => {
    const grouped: Record<SectionGroupKey, GroupedSection[]> = {
      approved: [],
      needs_review: [],
      ready_to_generate: [],
    }

    for (const section of sections) {
      const draft = draftBySectionKey.get(section.sectionKey) ?? null
      if (!draft) {
        grouped.ready_to_generate.push({ section, draft: null })
        continue
      }

      if (draft.status === "approved") {
        grouped.approved.push({ section, draft })
        continue
      }

      grouped.needs_review.push({ section, draft })
    }

    return grouped
  }, [draftBySectionKey, sections])

  const generatedDraftCount = groupedSections.approved.length + groupedSections.needs_review.length
  const approvedDraftCount = groupedSections.approved.length
  const needsReviewCount = groupedSections.needs_review.length
  const readyToGenerateCount = groupedSections.ready_to_generate.length
  const hasPendingSectionAction =
    pendingGenerateSectionKey !== null ||
    pendingApproveDraftId !== null ||
    pendingReviewDraftId !== null

  useEffect(() => {
    setSuccessMessages((prev) => {
      let changed = false
      const next: Record<string, SuccessFeedback> = {}

      for (const [key, feedback] of Object.entries(prev)) {
        const currentSignature = sectionSignatureByKey.get(feedback.sectionKey)
        if (currentSignature === feedback.baselineSignature) {
          next[key] = feedback
          continue
        }
        changed = true
      }

      return changed ? next : prev
    })
  }, [sectionSignatureByKey])

  useEffect(() => {
    setExpandedSectionKeys((current) => {
      const next = new Set<string>()
      for (const sectionKey of current) {
        const draft = draftBySectionKey.get(sectionKey)
        if (isDraftPreviewable(draft ?? null)) {
          next.add(sectionKey)
        }
      }
      return next
    })
  }, [draftBySectionKey])

  function clearSuccess(keys: string[]) {
    setSuccessMessages((prev) => {
      let changed = false
      const next = { ...prev }
      for (const key of keys) {
        if (key in next) {
          delete next[key]
          changed = true
        }
      }
      return changed ? next : prev
    })
  }

  function clearSectionSuccess(sectionKey: string) {
    setSuccessMessages((prev) => {
      let changed = false
      const next: Record<string, SuccessFeedback> = {}
      for (const [key, feedback] of Object.entries(prev)) {
        if (feedback.sectionKey === sectionKey) {
          changed = true
          continue
        }
        next[key] = feedback
      }
      return changed ? next : prev
    })
  }

  function rememberSuccess(feedbackKey: string, sectionKey: string, message: string) {
    setSuccessMessages((prev) => ({
      ...prev,
      [feedbackKey]: {
        message,
        sectionKey,
        baselineSignature: sectionSignatureByKey.get(sectionKey) ?? `${sectionKey}:missing`,
      },
    }))
  }

  function clearGenerateError(sectionKey: string) {
    setGenerateErrorMessages((prev) => {
      if (!(sectionKey in prev)) {
        return prev
      }
      const next = { ...prev }
      delete next[sectionKey]
      return next
    })
  }

  function clearApproveError(draftId: string) {
    setApproveErrorMessages((prev) => {
      if (!(draftId in prev)) {
        return prev
      }
      const next = { ...prev }
      delete next[draftId]
      return next
    })
  }

  function clearReviewError(draftId: string) {
    setReviewErrorMessages((prev) => {
      if (!(draftId in prev)) {
        return prev
      }
      const next = { ...prev }
      delete next[draftId]
      return next
    })
  }

  function getReviewDraft(draftId: string): ReviewDraft {
    return reviewDrafts[draftId] ?? INITIAL_REVIEW_DRAFT
  }

  function updateReviewDraft(draftId: string, patch: Partial<ReviewDraft>) {
    clearSuccess([getFeedbackKey("review", draftId)])
    clearReviewError(draftId)
    setReviewDrafts((prev) => ({
      ...prev,
      [draftId]: {
        ...getReviewDraft(draftId),
        ...patch,
      },
    }))
  }

  function togglePreview(sectionKey: string) {
    clearSectionSuccess(sectionKey)
    setExpandedSectionKeys((prev) => {
      const next = new Set(prev)
      if (next.has(sectionKey)) {
        next.delete(sectionKey)
      } else {
        next.add(sectionKey)
      }
      return next
    })
  }

  function handleGenerate(sectionKey: string) {
    if (!latestOutline || !hasConfirmedOutline || hasPendingSectionAction) {
      return
    }

    clearSectionSuccess(sectionKey)
    clearGenerateError(sectionKey)
    setPendingGenerateSectionKey(sectionKey)
    generateDraft.mutate(
      {
        sectionKey,
        claimIds: [],
        outlineId: latestOutline.id,
      },
      {
        onSuccess: () => {
          rememberSuccess(
            getFeedbackKey("generate", sectionKey),
            sectionKey,
            "草稿生成已排队。刷新后此提示将自动清除。",
          )
        },
        onError: (error) => {
          setGenerateErrorMessages((prev) => ({
            ...prev,
            [sectionKey]: getErrorMessage(error),
          }))
        },
        onSettled: () => {
          setPendingGenerateSectionKey((current) =>
            current === sectionKey ? null : current,
          )
        },
      },
    )
  }

  function handleApprove(draft: SectionDraftDetail) {
    if (hasPendingSectionAction) {
      return
    }

    clearSectionSuccess(draft.sectionKey)
    clearApproveError(draft.id)
    setPendingApproveDraftId(draft.id)
    approveDraft.mutate(draft.id, {
      onSuccess: () => {
        rememberSuccess(
          getFeedbackKey("approve", draft.id),
          draft.sectionKey,
          "草稿批准已提交。刷新后此提示将自动清除。",
        )
      },
      onError: (error) => {
        setApproveErrorMessages((prev) => ({
          ...prev,
          [draft.id]: getErrorMessage(error),
        }))
      },
      onSettled: () => {
        setPendingApproveDraftId((current) => (current === draft.id ? null : current))
      },
    })
  }

  function handleSubmitReview(draft: SectionDraftDetail) {
    if (hasPendingSectionAction) {
      return
    }

    const reviewDraft = getReviewDraft(draft.id)
    if (!normalizeText(reviewDraft.commenterId) || !normalizeText(reviewDraft.commentText)) {
      return
    }

    clearSectionSuccess(draft.sectionKey)
    clearReviewError(draft.id)
    setPendingReviewDraftId(draft.id)
    addReviewComment.mutate(
      {
        draftId: draft.id,
        input: {
          commenterId: normalizeText(reviewDraft.commenterId),
          commentText: normalizeText(reviewDraft.commentText),
          decision: reviewDraft.decision,
        },
      },
      {
        onSuccess: () => {
          setReviewDrafts((prev) => ({
            ...prev,
            [draft.id]: INITIAL_REVIEW_DRAFT,
          }))
          setReviewingDraftId((current) => (current === draft.id ? null : current))
          rememberSuccess(
            getFeedbackKey("review", draft.id),
            draft.sectionKey,
            "审阅意见已提交。刷新后此提示将自动清除。",
          )
        },
        onError: (error) => {
          setReviewErrorMessages((prev) => ({
            ...prev,
            [draft.id]: getErrorMessage(error),
          }))
        },
        onSettled: () => {
          setPendingReviewDraftId((current) => (current === draft.id ? null : current))
        },
      },
    )
  }

  function getPrimaryActionHelper(
    draft: SectionDraftDetail | null,
    isActionBusy: boolean,
  ): { disabled: boolean; message: string } {
    if (isActionBusy) {
      return {
        disabled: true,
        message:
          "当前已有章节操作进行中，请等待最新任务更新后再触发。",
      }
    }

    if (!hasConfirmedOutline) {
      return {
        disabled: true,
        message: "在 G4 确认最新提纲前，无法生成草稿。",
      }
    }

    if (draft) {
      return {
        disabled: true,
        message:
          "该章节已有最新草稿，请先审阅或批准当前版本。",
      }
    }

    if (blockers.length > 0) {
      return {
        disabled: true,
        message: `工作流阻塞：${blockers[0].message}`,
      }
    }

    return {
      disabled: false,
      message: "已就绪，可从最新已确认提纲生成。",
    }
  }

  function renderPreview(sectionKey: string, draft: SectionDraftDetail | null) {
    const previewable = isDraftPreviewable(draft)
    const isExpanded = expandedSectionKeys.has(sectionKey)

    return (
      <div style={previewShellStyle}>
        <div style={previewHeaderStyle}>
          <div style={subSectionTitleStyle}>最新草稿预览</div>
          {previewable ? (
            <button
              type="button"
              style={previewToggleStyle}
              onClick={() => togglePreview(sectionKey)}
            >
              {isExpanded ? "收起预览" : "展开预览"}
            </button>
          ) : (
            <span style={previewUnavailableStyle}>不可用</span>
          )}
        </div>
        {!draft ? (
          <div style={helperTextStyle}>
            该章节尚无最新草稿，暂无预览。
          </div>
        ) : !previewable ? (
          <div style={helperTextStyle}>
            最新草稿已存在，但内容为空，暂无法预览。
          </div>
        ) : isExpanded ? (
          <div style={contentPreviewStyle}>{draft.contentMd}</div>
        ) : (
          <div style={helperTextStyle}>
            预览默认收起，需要查看最新草稿内容时展开。
          </div>
        )}
      </div>
    )
  }

  function renderCommentList(draft: SectionDraftDetail) {
    return (
      <div style={commentListStyle}>
        {draft.reviewComments.map((comment) => (
          <div key={comment.id} style={commentItemStyle}>
            <div style={commentHeaderStyle}>
              <div style={commentMetaStyle}>
                {comment.commenterId} · {new Date(comment.createdAt).toLocaleString()}
              </div>
              <span style={decisionBadgeStyle(comment.decision)}>
                {getDecisionLabel(comment.decision)}
              </span>
            </div>
            <div style={{ ...descStyle, marginTop: "6px" }}>{comment.commentText}</div>
          </div>
        ))}
        {draft.reviewComments.length === 0 ? (
          <div style={emptyStateStyle}>暂无审阅意见。</div>
        ) : null}
      </div>
    )
  }

  function renderSection(section: SystemSectionDetail, draft: SectionDraftDetail | null) {
    const isGeneratingSection = pendingGenerateSectionKey === section.sectionKey
    const isApprovingDraft = draft ? pendingApproveDraftId === draft.id : false
    const isSubmittingReview = draft ? pendingReviewDraftId === draft.id : false
    const reviewDraft = draft ? getReviewDraft(draft.id) : INITIAL_REVIEW_DRAFT
    const actionHelper = getPrimaryActionHelper(draft, hasPendingSectionAction)

    const generateFeedbackKey = getFeedbackKey("generate", section.sectionKey)
    const approveFeedbackKey = draft ? getFeedbackKey("approve", draft.id) : null
    const reviewFeedbackKey = draft ? getFeedbackKey("review", draft.id) : null

    const generateSuccess = successMessages[generateFeedbackKey]?.message
    const approveSuccess = approveFeedbackKey
      ? successMessages[approveFeedbackKey]?.message
      : null
    const reviewSuccess = reviewFeedbackKey
      ? successMessages[reviewFeedbackKey]?.message
      : null

    const generateError = generateErrorMessages[section.sectionKey]
    const approveError = draft ? approveErrorMessages[draft.id] : null
    const reviewError = draft ? reviewErrorMessages[draft.id] : null

    return (
      <div key={section.id} style={itemStyle}>
        <div style={itemHeaderStyle}>
          <div>
            <div style={itemTitleStyle}>{section.title}</div>
            <div style={itemMetaStyle}>章节键值：{section.sectionKey}</div>
          </div>
          {draft ? <span style={badgeStyle(draft.status)}>{getDraftStatusLabel(draft.status)}</span> : null}
        </div>

        {draft ? (
          <>
            <div style={itemMetaStyle}>
              使用 Claims：{draft.generatedFromClaimsJson.length} · 版本 {draft.version}
            </div>
            <div style={itemMetaStyle}>审阅意见数：{draft.reviewComments.length}</div>
            {draft.approvedAt ? (
              <div style={itemMetaStyle}>
                批准时间：{new Date(draft.approvedAt).toLocaleString()}
              </div>
            ) : null}
          </>
        ) : (
          <div style={itemMetaStyle}>该章节尚无最新草稿记录。</div>
        )}

        {renderPreview(section.sectionKey, draft)}

        <div style={actionRowStyle}>
          <button
            type="button"
            style={actionBtnStyle}
            onClick={() => handleGenerate(section.sectionKey)}
            disabled={actionHelper.disabled}
          >
            {isGeneratingSection ? "生成中..." : "生成草稿"}
          </button>

          {draft && draft.status !== "approved" ? (
            <button
              type="button"
              style={secondaryBtnStyle}
              onClick={() => handleApprove(draft)}
              disabled={hasPendingSectionAction}
            >
              {isApprovingDraft ? "批准中..." : "批准草稿"}
            </button>
          ) : null}

          {draft ? (
            <button
              type="button"
              style={secondaryBtnStyle}
              onClick={() => {
                clearSectionSuccess(draft.sectionKey)
                clearReviewError(draft.id)
                setReviewingDraftId((current) => (current === draft.id ? null : draft.id))
              }}
              disabled={hasPendingSectionAction}
            >
              {reviewingDraftId === draft.id ? "隐藏审阅表单" : "添加审阅意见"}
            </button>
          ) : null}
        </div>

        <div style={helperTextStyle}>{actionHelper.message}</div>
        {generateSuccess ? <div style={successTextStyle}>{generateSuccess}</div> : null}
        {generateError ? <div style={errorTextStyle}>{generateError}</div> : null}
        {approveSuccess ? <div style={successTextStyle}>{approveSuccess}</div> : null}
        {approveError ? <div style={errorTextStyle}>{approveError}</div> : null}

        {draft ? renderCommentList(draft) : null}
        {reviewSuccess ? <div style={successTextStyle}>{reviewSuccess}</div> : null}
        {reviewError ? <div style={errorTextStyle}>{reviewError}</div> : null}

        {draft && reviewingDraftId === draft.id ? (
          <div style={fieldGroupStyle}>
            <label style={fieldLabelStyle} htmlFor={`reviewer-${draft.id}`}>
              评审人 ID
            </label>
            <input
              id={`reviewer-${draft.id}`}
              style={inputStyle}
              value={reviewDraft.commenterId}
              onChange={(event) =>
                updateReviewDraft(draft.id, {
                  commenterId: event.target.value,
                })
              }
            />
            <label style={fieldLabelStyle} htmlFor={`decision-${draft.id}`}>
              决定
            </label>
            <select
              id={`decision-${draft.id}`}
              style={inputStyle}
              value={reviewDraft.decision}
              onChange={(event) =>
                updateReviewDraft(draft.id, {
                  decision: event.target.value as ReviewDraft["decision"],
                })
              }
            >
              <option value="request_changes">要求修改</option>
              <option value="approve">批准</option>
              <option value="freeze">冻结</option>
            </select>
            <label style={fieldLabelStyle} htmlFor={`review-text-${draft.id}`}>
              意见
            </label>
            <textarea
              id={`review-text-${draft.id}`}
              style={textareaStyle}
              value={reviewDraft.commentText}
              onChange={(event) =>
                updateReviewDraft(draft.id, {
                  commentText: event.target.value,
                })
              }
              placeholder="描述需要修改的内容或该章节已就绪的原因。"
            />
            <button
              type="button"
              style={actionBtnStyle}
              onClick={() => handleSubmitReview(draft)}
              disabled={hasPendingSectionAction}
            >
              {isSubmittingReview ? "提交中..." : "提交审阅意见"}
            </button>
          </div>
        ) : null}
      </div>
    )
  }

  // Section_Drafting: show DraftingWorkspace for AI-assisted drafting
  if (currentState === "Section_Drafting" || currentState === "Outline_Ready") {
    const workspaceSections = sections.map((s) => ({
      sectionKey: s.sectionKey,
      title: s.title,
    }))
    if (workspaceSections.length > 0) {
      return (
        <div style={panelStyle}>
          <GateTaskStatus systemId={systemId} gateKey="G5" />
          <DraftingWorkspace systemId={systemId} sections={workspaceSections} />
        </div>
      )
    }
  }

  return (
    <div style={panelStyle}>
      <GateTaskStatus systemId={systemId} gateKey="G5" />
      <div style={sectionCardStyle}>
        <div style={titleStyle}>章节起草与审阅</div>
        <div style={descStyle}>
          当前状态：{currentState ?? "未知"}。G5 现在按 latest draft 真相把 section 稳定分成 approved、needs review、ready to generate 三组，避免 transport 顺序把界面搞成一坨。
        </div>
        <div style={summaryGridStyle}>
          <div style={summaryCardStyle}>
            <div style={summaryValueStyle}>{sections.length}</div>
            <div style={summaryLabelStyle}>章节</div>
          </div>
          <div style={summaryCardStyle}>
            <div style={summaryValueStyle}>{generatedDraftCount}</div>
            <div style={summaryLabelStyle}>草稿</div>
          </div>
          <div style={summaryCardStyle}>
            <div style={summaryValueStyle}>{approvedDraftCount}</div>
            <div style={summaryLabelStyle}>已通过</div>
          </div>
          <div style={summaryCardStyle}>
            <div style={summaryValueStyle}>{needsReviewCount}</div>
            <div style={summaryLabelStyle}>待审阅</div>
          </div>
          <div style={summaryCardStyle}>
            <div style={summaryValueStyle}>{readyToGenerateCount}</div>
            <div style={summaryLabelStyle}>待生成</div>
          </div>
        </div>
      </div>

      {draftsLoading ? (
        <div style={sectionCardStyle}>
          <div style={emptyStateStyle}>加载草稿中...</div>
        </div>
      ) : draftsError ? (
        <div style={sectionCardStyle}>
          <div style={errorTextStyle}>
            Drafts 加载失败：{draftsError instanceof Error ? draftsError.message : "未知错误"}
          </div>
        </div>
      ) : sections.length === 0 ? (
        <div style={sectionCardStyle}>
          <div style={emptyStateStyle}>暂无系统章节。</div>
        </div>
      ) : (
        (Object.keys(SECTION_GROUP_META) as SectionGroupKey[]).map((groupKey) => {
          const group = groupedSections[groupKey]
          const groupMeta = SECTION_GROUP_META[groupKey]

          return (
            <div key={groupKey} style={sectionCardStyle}>
              <div style={groupHeaderStyle}>
                <div style={groupMetaStyle}>
                  <div style={titleStyle}>{groupMeta.title}</div>
                  <div style={descStyle}>{groupMeta.description}</div>
                </div>
                <div style={groupCountBadgeStyle}>{group.length}</div>
              </div>

              {group.length === 0 ? (
                <div style={emptyStateStyle}>{groupMeta.emptyText}</div>
              ) : (
                <div style={listStyle}>
                  {group.map(({ section, draft }) => renderSection(section, draft))}
                </div>
              )}
            </div>
          )
        })
      )}

      {blockers.length > 0 ? (
        <div style={sectionCardStyle}>
          <div style={{ ...titleStyle, fontSize: "13px", color: "#fca5a5" }}>
            阻塞项 ({blockers.length})
          </div>
          <div style={blockerListStyle}>
            {blockers.map((blocker, index) => (
              <div key={`${blocker.code}-${index}`} style={blockerItemStyle}>
                <strong>{blocker.code}</strong>: {blocker.message}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
