"use client"

import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react"
import { useQueryClient } from "@tanstack/react-query"

import { useAssets } from "../../hooks/useAnalysis"
import { ApiError } from "../../lib/api"
import {
  useApproveClaim,
  useBatchApproveClaims,
  useClaims,
  useCreateClaimEvidenceLink,
  useCreateOutlineBinding,
  useEvidenceGaps,
  useG4Snapshot,
  useGenerateEvidenceMatrix,
  useGenerateOutline,
  useConfirmOutline,
  useOutlines,
  useRebuildG4Snapshot,
  type OutlineAssetBindingDetail,
} from "../../hooks/useEvidence"
import { useSystemAdvance } from "../../hooks/useSystemAdvance"
import type { EnhancedOutlineJson, EnhancedOutlineSection } from "../../types/g4"
import type { SystemDetail } from "../../hooks/useProjects"
import type { Blocker, WorkflowSnapshot } from "../../hooks/useProjectStatus"
import { gateTheme } from "../../styles/gate-theme"
import { ActionButton } from "../ui/ActionButton"
import { ConfirmDialog } from "../ui/ConfirmDialog"
import { EmptyState } from "../ui/EmptyState"
import { SectionCard } from "../ui/SectionCard"
import { getLatestClaims, getLatestOutline, getOrderedSystemSections } from "./workbenchSelectors"
import { GateTaskStatus } from "./GateTaskStatus"
import { useWebSocket } from "../../hooks/useWebSocket"
import { G4StatsOverview } from "./g2/G4StatsOverview"
import { ClaimList } from "./g2/ClaimList"
import { StalenessIndicator } from "./g2/StalenessIndicator"
import { SectionOutlineList } from "./g2/SectionOutlineList"
import { G4IssueDetailPanel } from "./g2/G4IssueDetailPanel"
import { resolveG4IssueDetail, type G4IssueAction } from "./g2/issueDetails"

export type GateContentPanelProps = Readonly<{
  snapshot: WorkflowSnapshot | null
  blockers: Blocker[]
  systemId: string
  systemDetail?: SystemDetail | null
}>

const actionRowStyle: CSSProperties = { display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "10px" }
const errorTextStyle: CSSProperties = { marginTop: "8px", fontSize: "12px", color: "#fca5a5" }
const blockerListStyle: CSSProperties = { display: "flex", flexDirection: "column", gap: "6px", marginTop: "8px" }
const blockerItemStyle: CSSProperties = {
  padding: "8px 12px",
  borderRadius: "8px",
  border: "1px solid rgba(248, 113, 113, 0.2)",
  background: "rgba(127, 29, 29, 0.1)",
  fontSize: "12px",
  color: "#fca5a5",
}
const readinessListStyle: CSSProperties = { display: "flex", flexDirection: "column", gap: "8px", marginTop: "10px" }
const readinessRowStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "12px",
  padding: "10px 12px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.12)",
  background: "rgba(15, 23, 42, 0.35)",
  fontSize: "12px",
  color: "#cbd5e1",
}
const readinessPassStyle: CSSProperties = { color: "#86efac", fontWeight: 600 }
const readinessFailStyle: CSSProperties = { color: "#fca5a5", fontWeight: 600 }
const focusedSectionStyle: CSSProperties = {
  borderRadius: "18px",
  outline: "2px solid rgba(56, 189, 248, 0.45)",
  outlineOffset: "4px",
}

type SectionStatusSummary = {
  missingClaimSections: string[]
  missingBindingSections: string[]
  claimsMissingEvidence: string[]
  hasOutlineReadyBlocker: boolean
  hasSnapshotStaleBlocker: boolean
}

function getBlockerDetails(blockers: Blocker[]): SectionStatusSummary {
  const missingClaimSections = new Set<string>()
  const missingBindingSections = new Set<string>()
  const claimsMissingEvidence = new Set<string>()
  let hasOutlineReadyBlocker = false
  let hasSnapshotStaleBlocker = false

  for (const blocker of blockers) {
    if (blocker.code === "section_missing_claims") {
      for (const section of (blocker.details.sections as string[] | undefined) ?? []) missingClaimSections.add(section)
    }
    if (blocker.code === "section_missing_binding") {
      for (const section of (blocker.details.sections as string[] | undefined) ?? []) missingBindingSections.add(section)
    }
    if (blocker.code === "evidence_matrix_not_ready") {
      for (const claimId of (blocker.details.claims_missing_evidence as string[] | undefined) ?? []) claimsMissingEvidence.add(claimId)
    }
    if (blocker.code === "outline_not_ready") hasOutlineReadyBlocker = true
    if (blocker.code === "snapshot_stale") hasSnapshotStaleBlocker = true
  }

  return {
    missingClaimSections: [...missingClaimSections],
    missingBindingSections: [...missingBindingSections],
    claimsMissingEvidence: [...claimsMissingEvidence],
    hasOutlineReadyBlocker,
    hasSnapshotStaleBlocker,
  }
}

/** Normalize outline JSON that may contain snake_case keys (legacy data) to camelCase. */
function normalizeOutlineJson(raw: unknown): EnhancedOutlineJson | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null
  const obj = raw as Record<string, unknown>
  if (!obj.sections || !Array.isArray(obj.sections)) return null

  const meta = (obj.meta ?? {}) as Record<string, unknown>
  const normalizedMeta = {
    fingerprint: (meta.fingerprint ?? undefined) as string | undefined,
    generatedAt: (meta.generatedAt ?? meta.generated_at ?? undefined) as string | undefined,
    claimRefs: ((meta.claimRefs ?? meta.claim_refs ?? []) as Array<Record<string, unknown>>).map((r) => ({
      claimId: (r.claimId ?? r.claim_id ?? "") as string,
      version: (r.version ?? 0) as number,
    })),
    inputSummary: (() => {
      const raw = (meta.inputSummary ?? meta.input_summary ?? undefined) as Record<string, unknown> | undefined
      if (!raw) return undefined
      return {
        sectionCount: (raw.sectionCount ?? raw.section_count ?? 0) as number,
        claimCount: (raw.claimCount ?? raw.claim_count ?? 0) as number,
        linkCount: (raw.linkCount ?? raw.link_count ?? 0) as number,
        runCount: (raw.runCount ?? raw.run_count ?? 0) as number,
      }
    })(),
  }

  const sections = (obj.sections as Array<Record<string, unknown>>).map((sec) => ({
    sectionKey: (sec.sectionKey ?? sec.section_key ?? "") as string,
    sectionTitle: (sec.sectionTitle ?? sec.section_title ?? "") as string,
    claimIds: (sec.claimIds ?? sec.claim_ids ?? []) as string[],
    evidenceLinkRefs: ((sec.evidenceLinkRefs ?? sec.evidence_link_refs ?? []) as Array<Record<string, unknown>>).map((r) => ({
      claimId: (r.claimId ?? r.claim_id ?? "") as string,
      assetId: (r.assetId ?? r.asset_id ?? "") as string,
      strength: (r.strength ?? "unknown") as string,
    })),
    analysisRunRefs: ((sec.analysisRunRefs ?? sec.analysis_run_refs ?? []) as Array<Record<string, unknown>>).map((r) => ({
      runId: (r.runId ?? r.run_id ?? "") as string,
      status: (r.status ?? "unknown") as string,
      summary: (r.summary ?? "") as string,
    })),
    nodes: ((sec.nodes ?? []) as Array<Record<string, unknown>>).map((n) => ({
      nodeType: (n.nodeType ?? n.node_type ?? "summary") as "background" | "method" | "result" | "summary",
      claimIds: (n.claimIds ?? n.claim_ids ?? []) as string[],
      evidenceStrength: (n.evidenceStrength ?? n.evidence_strength ?? "unknown") as string,
    })),
    bindingSuggestions: ((sec.bindingSuggestions ?? sec.binding_suggestions ?? []) as Array<Record<string, unknown>>).map((s) => ({
      assetId: (s.assetId ?? s.asset_id ?? "") as string,
      reason: (s.reason ?? "") as string,
    })),
    coverage: (sec.coverage ?? "uncovered") as "covered" | "uncovered" | "partial",
  }))

  return { meta: normalizedMeta, sections }
}

export function EvidenceMatrixPanel({
  snapshot,
  systemId,
  blockers,
  systemDetail,
}: GateContentPanelProps) {
  const { data: claims, isLoading: claimsLoading, error: claimsError } = useClaims(systemId)
  const { data: outlines, isLoading: outlinesLoading, error: outlinesError } = useOutlines(systemId)
  const { data: assets } = useAssets(systemId)
  const { data: g4Snapshot } = useG4Snapshot(systemId)
  const { data: evidenceGaps } = useEvidenceGaps(systemId)
  const queryClient = useQueryClient()
  const claimsSectionRef = useRef<HTMLDivElement | null>(null)
  const readinessSectionRef = useRef<HTMLDivElement | null>(null)
  const outlineSectionRef = useRef<HTMLDivElement | null>(null)

  // Invalidate G4 queries when background tasks complete
  useWebSocket({
    systemId,
    onInvalidate: (event) => {
      if (event.status === "succeeded" || event.status === "failed") {
        queryClient.invalidateQueries({ queryKey: ["claims", systemId] })
        queryClient.invalidateQueries({ queryKey: ["outlines", systemId] })
        queryClient.invalidateQueries({ queryKey: ["g4-snapshot", systemId] })
        queryClient.invalidateQueries({ queryKey: ["evidence-gaps", systemId] })
      }
    },
  })

  const generateEvidenceMatrix = useGenerateEvidenceMatrix(systemId)
  const rebuildSnapshot = useRebuildG4Snapshot(systemId)
  const approveClaim = useApproveClaim(systemId)
  const batchApprove = useBatchApproveClaims(systemId)
  const createClaimLink = useCreateClaimEvidenceLink(systemId)
  const generateOutline = useGenerateOutline(systemId)
  const confirmOutline = useConfirmOutline(systemId)
  const createOutlineBinding = useCreateOutlineBinding(systemId)
  const advance = useSystemAdvance(systemId)

  const latestOutline = useMemo(() => getLatestOutline(outlines), [outlines])
  const isOutlineConfirmed = latestOutline?.status === "confirmed"
  const currentState = snapshot?.currentState ?? null
  const sections = useMemo(() => getOrderedSystemSections(systemDetail), [systemDetail])

  const sortedClaims = useMemo(() => getLatestClaims(claims), [claims])
  const approvedClaims = useMemo(() => sortedClaims.filter((c) => c.status === "approved"), [sortedClaims])
  const pendingClaims = useMemo(() => sortedClaims.filter((c) => c.status !== "approved"), [sortedClaims])

  const assetOptions = useMemo(
    () => (assets ?? []).map((asset) => ({ id: asset.id, label: `${asset.fileName} · ${asset.assetType}` })),
    [assets],
  )
  const assetNameById = useMemo(() => new Map(assetOptions.map((a) => [a.id, a.label])), [assetOptions])
  const bindingBySectionKey = useMemo(
    () => new Map((latestOutline?.bindings ?? []).map((b) => [b.sectionKey, b])),
    [latestOutline],
  )

  // Parse enhanced outline JSON
  const enhancedOutline = useMemo(() => normalizeOutlineJson(latestOutline?.outlineJson), [latestOutline])
  const outlineSections: EnhancedOutlineSection[] = enhancedOutline?.sections ?? []
  const outlineFingerprint = enhancedOutline?.meta?.fingerprint
  const snapshotFingerprint = g4Snapshot?.fingerprint
  const blockingBlockers = useMemo(
    () => blockers.filter((blocker) => blocker.code !== "snapshot_stale"),
    [blockers],
  )

  // Coverage rate
  const totalSections = sections.length
  const coveredSections = sections.filter((s) => approvedClaims.some((c) => c.sectionRef === s.sectionKey)).length
  const coverageRate = totalSections > 0 ? coveredSections / totalSections : 0

  const [bindingFeedback, setBindingFeedback] = useState<string | null>(null)
  const [showForceRegenerateDialog, setShowForceRegenerateDialog] = useState(false)
  const [showIssueDetailPanel, setShowIssueDetailPanel] = useState(false)
  const [focusedModule, setFocusedModule] = useState<"claims" | "outline" | "readiness" | null>(null)
  const {
    missingClaimSections,
    missingBindingSections,
    claimsMissingEvidence,
    hasOutlineReadyBlocker,
    hasSnapshotStaleBlocker,
  } = useMemo(() => getBlockerDetails(blockers), [blockers])

  const generateEvidenceError = generateEvidenceMatrix.error instanceof Error ? generateEvidenceMatrix.error.message : null
  const generateEvidenceIssue = useMemo(() => resolveG4IssueDetail(generateEvidenceMatrix.error), [generateEvidenceMatrix.error])
  const generateEvidenceConflict =
    generateEvidenceIssue?.code === "evidence_matrix_regeneration_conflict" ||
    (generateEvidenceMatrix.error instanceof ApiError && generateEvidenceMatrix.error.status === 409)
  const generateOutlineError = generateOutline.error instanceof Error ? generateOutline.error.message : null
  const confirmOutlineError = confirmOutline.error instanceof Error ? confirmOutline.error.message : null
  const createLinkError = createClaimLink.error instanceof Error ? createClaimLink.error.message : null
  const createBindingError = createOutlineBinding.error instanceof Error ? createOutlineBinding.error.message : null
  const advanceError = advance.error instanceof Error ? advance.error.message : null
  const sectionsWithoutBindings = useMemo(
    () => sections.filter((section) => !bindingBySectionKey.has(section.sectionKey)).map((section) => section.sectionKey),
    [bindingBySectionKey, sections],
  )
  const canConfirmOutline = !!latestOutline && sectionsWithoutBindings.length === 0
  const confirmOutlineHint =
    latestOutline && sectionsWithoutBindings.length > 0 ? `还有 ${sectionsWithoutBindings.length} 个章节未绑定资产：${sectionsWithoutBindings.join(", ")}` : null
  const isSnapshotStale =
    hasSnapshotStaleBlocker || (!!outlineFingerprint && !!snapshotFingerprint && outlineFingerprint !== snapshotFingerprint)
  const canAdvance = blockingBlockers.length === 0 && currentState !== "Outline_Ready"
  const advanceHint = canAdvance
    ? "全部门禁条件已满足，可以从 G4 推进到 G5。"
    : `当前无法推进：${blockingBlockers[0]?.message ?? "仍有未满足条件。"}`

  useEffect(() => {
    setBindingFeedback(null)
  }, [latestOutline?.id, latestOutline?.updatedAt])

  useEffect(() => {
    if (!generateEvidenceConflict) {
      setShowForceRegenerateDialog(false)
    }
  }, [generateEvidenceConflict])

  useEffect(() => {
    if (!generateEvidenceIssue) {
      setShowIssueDetailPanel(false)
    }
  }, [generateEvidenceIssue])

  useEffect(() => {
    if (!focusedModule) return
    const timer = window.setTimeout(() => {
      setFocusedModule(null)
    }, 1600)
    return () => window.clearTimeout(timer)
  }, [focusedModule])

  function handleCreateBinding(assetId: string, sectionKey: string) {
    if (!latestOutline) return
    const existingBinding = bindingBySectionKey.get(sectionKey)
    if (existingBinding) {
      const existingLabel = assetNameById.get(existingBinding.assetId) ?? existingBinding.assetId
      setBindingFeedback(`章节 ${sectionKey} 已有绑定至 ${existingLabel}。`)
      return
    }
    setBindingFeedback(null)
    createOutlineBinding.mutate(
      { outlineId: latestOutline.id, input: { assetId, sectionKey } },
      {
        onSuccess: (binding: OutlineAssetBindingDetail) => {
          setBindingFeedback(`已添加提纲绑定：${binding.sectionKey}`)
        },
      },
    )
  }

  function focusModule(target: "claims" | "outline" | "readiness") {
    const refMap = {
      claims: claimsSectionRef,
      outline: outlineSectionRef,
      readiness: readinessSectionRef,
    }
    const node = refMap[target].current
    node?.scrollIntoView({ behavior: "smooth", block: "center" })
    setFocusedModule(target)
  }

  function getFocusedSectionStyle(target: "claims" | "outline" | "readiness"): CSSProperties | undefined {
    return focusedModule === target ? focusedSectionStyle : undefined
  }

  function handleIssueAction(action: G4IssueAction) {
    if (action.id === "focus-claims") {
      focusModule("claims")
      return
    }
    if (action.id === "focus-outline") {
      focusModule("outline")
      return
    }
    if (action.id === "focus-readiness") {
      focusModule("readiness")
      return
    }
    if (action.id === "force-regenerate") {
      setShowForceRegenerateDialog(true)
    }
  }

  return (
    <div style={gateTheme.panel}>
      <GateTaskStatus systemId={systemId} gateKey="G4" />
      <G4IssueDetailPanel
        issue={generateEvidenceIssue}
        isOpen={showIssueDetailPanel}
        onClose={() => setShowIssueDetailPanel(false)}
        onAction={handleIssueAction}
      />

      <ConfirmDialog
        isOpen={showForceRegenerateDialog}
        title="强制重建证据矩阵"
        message="继续重建会使当前最新 Approved Claims 与已确认 Outline 失效，后续需要重新审查与确认。"
        onConfirm={() => {
          generateEvidenceMatrix.mutate({ forceRegenerate: true })
          setShowForceRegenerateDialog(false)
        }}
        onCancel={() => setShowForceRegenerateDialog(false)}
        isPending={generateEvidenceMatrix.isPending}
        confirmLabel="确认重建"
      />

      <StalenessIndicator outlineFingerprint={outlineFingerprint} currentFingerprint={snapshotFingerprint} />

      <SectionCard
        title="证据与提纲"
        description={`当前状态：${currentState ?? "未知"}。先生成 Evidence Matrix，再筛查并批准 claims，随后补证据与提纲绑定，最后确认 Outline。`}
      >
        <G4StatsOverview
          claimCount={sortedClaims.length}
          approvedCount={approvedClaims.length}
          pendingCount={pendingClaims.length}
          bindingCount={latestOutline?.bindings.length ?? 0}
          sectionCount={sections.length}
          coveredSectionCount={coveredSections}
          coverageRate={coverageRate}
        />
        <div style={actionRowStyle}>
          <ActionButton
            label={generateEvidenceMatrix.isPending ? "生成证据矩阵中..." : "生成证据矩阵"}
            onClick={() => generateEvidenceMatrix.mutate({})}
            disabled={generateEvidenceMatrix.isPending}
            isPending={generateEvidenceMatrix.isPending}
          />
          <ActionButton
            label={generateOutline.isPending ? "生成提纲中..." : approvedClaims.length === 0 ? "生成提纲（需先批准 Claims）" : "生成提纲"}
            onClick={() => generateOutline.mutate()}
            disabled={generateOutline.isPending || isOutlineConfirmed || approvedClaims.length === 0}
            variant="secondary"
          />
          <ActionButton
            label={rebuildSnapshot.isPending ? "刷新快照中..." : "刷新快照"}
            onClick={() => rebuildSnapshot.mutate()}
            disabled={rebuildSnapshot.isPending}
            variant="secondary"
          />
        </div>
        {generateEvidenceError ? <div style={errorTextStyle}>Evidence Matrix 生成失败：{generateEvidenceError}</div> : null}
        {generateEvidenceIssue ? (
          <div style={actionRowStyle}>
            <ActionButton
              label="查看详情"
              onClick={() => setShowIssueDetailPanel(true)}
              disabled={generateEvidenceMatrix.isPending}
              variant="secondary"
            />
            {generateEvidenceConflict ? (
              <ActionButton
                label="继续重建"
                onClick={() => setShowForceRegenerateDialog(true)}
                disabled={generateEvidenceMatrix.isPending}
                variant="danger"
              />
            ) : null}
          </div>
        ) : null}
        {generateOutlineError ? <div style={errorTextStyle}>Outline 生成失败：{generateOutlineError}</div> : null}
      </SectionCard>

      <div ref={readinessSectionRef} style={getFocusedSectionStyle("readiness")}>
        <SectionCard
          title="推进条件"
          description="G4 通过看的是门禁真相，不是表面上点过哪些按钮。以下 4 项同时满足后，才能推进到 G5。"
        >
        <div style={readinessListStyle}>
          <div style={readinessRowStyle}>
            <span>章节 Approved Claims</span>
            <span style={missingClaimSections.length === 0 ? readinessPassStyle : readinessFailStyle}>
              {missingClaimSections.length === 0 ? "已满足" : `缺少 ${missingClaimSections.join(", ")}`}
            </span>
          </div>
          <div style={readinessRowStyle}>
            <span>Approved Claim 证据链接</span>
            <span style={claimsMissingEvidence.length === 0 ? readinessPassStyle : readinessFailStyle}>
              {claimsMissingEvidence.length === 0 ? "已满足" : `缺少 ${claimsMissingEvidence.length} 条`}
            </span>
          </div>
          <div style={readinessRowStyle}>
            <span>最新提纲已确认</span>
            <span style={!hasOutlineReadyBlocker && isOutlineConfirmed ? readinessPassStyle : readinessFailStyle}>
              {!hasOutlineReadyBlocker && isOutlineConfirmed ? "已满足" : "未满足"}
            </span>
          </div>
          <div style={readinessRowStyle}>
            <span>章节 Outline 绑定</span>
            <span style={missingBindingSections.length === 0 && sectionsWithoutBindings.length === 0 ? readinessPassStyle : readinessFailStyle}>
              {missingBindingSections.length === 0 && sectionsWithoutBindings.length === 0
                ? "已满足"
                : `缺少 ${(missingBindingSections.length > 0 ? missingBindingSections : sectionsWithoutBindings).join(", ")}`}
            </span>
          </div>
          <div style={readinessRowStyle}>
            <span>快照新鲜度</span>
            <span style={!isSnapshotStale ? readinessPassStyle : readinessFailStyle}>
              {!isSnapshotStale ? "已满足" : "建议刷新后重审"}
            </span>
          </div>
        </div>
        <div style={actionRowStyle}>
          <ActionButton
            label={advance.isPending ? "推进中..." : "推进到 G5"}
            onClick={() => advance.advance()}
            disabled={!canAdvance || advance.isPending}
            isPending={advance.isPending}
          />
        </div>
        <div style={canAdvance ? { marginTop: "8px", fontSize: "12px", color: "#86efac" } : errorTextStyle}>{advanceHint}</div>
        {advanceError ? <div style={errorTextStyle}>推进失败：{advanceError}</div> : null}
        </SectionCard>
      </div>

      <div ref={claimsSectionRef} style={getFocusedSectionStyle("claims")}>
        <SectionCard
          title="Claims 审查队列"
          description="Claims 会按 latest-only 规则拆成 Approved 与 Pending 两组，含证据强度标签。"
        >
        {claimsLoading ? (
          <EmptyState text="加载 Claims 中..." />
        ) : claimsError ? (
          <div style={errorTextStyle}>Claims 加载失败：{claimsError instanceof Error ? claimsError.message : "未知错误"}</div>
        ) : (
          <ClaimList
            claims={sortedClaims}
            assetNameById={assetNameById}
            assetOptions={assetOptions}
            onApprove={(claimId) => approveClaim.mutate(claimId)}
            onCreateEvidenceLink={(claimId, assetId) => createClaimLink.mutate({ claimId, input: { assetId } })}
            onBatchApprove={(ids) => batchApprove.mutate(ids)}
            isApproving={approveClaim.isPending || batchApprove.isPending}
            approvingClaimId={approveClaim.variables as string | undefined}
            isLinking={createClaimLink.isPending}
            linkingClaimId={createClaimLink.variables?.claimId}
          />
        )}
        {createLinkError ? <div style={errorTextStyle}>Evidence 绑定失败：{createLinkError}</div> : null}
        </SectionCard>
      </div>

      <div ref={outlineSectionRef} style={getFocusedSectionStyle("outline")}>
        <SectionOutlineList
          sections={sections}
          outlineSections={outlineSections}
          bindings={bindingBySectionKey}
          gaps={evidenceGaps ?? []}
          assetOptions={assetOptions}
          assetNameById={assetNameById}
          latestOutline={latestOutline}
          isOutlineConfirmed={isOutlineConfirmed}
          onCreateBinding={handleCreateBinding}
          onConfirmOutline={() => latestOutline && confirmOutline.mutate(latestOutline.id)}
          isBindingPending={createOutlineBinding.isPending}
          isConfirmPending={confirmOutline.isPending}
          bindingFeedback={bindingFeedback}
          outlinesLoading={outlinesLoading}
          outlinesError={outlinesError instanceof Error ? outlinesError : null}
          confirmOutlineError={confirmOutlineError}
          createBindingError={createBindingError}
          canConfirmOutline={canConfirmOutline}
          confirmOutlineHint={confirmOutlineHint}
        />
      </div>

      {blockers.length > 0 ? (
        <SectionCard title={<span style={{ fontSize: "13px", color: "#fca5a5" }}>阻塞项 ({blockers.length})</span>}>
          <div style={blockerListStyle}>
            {blockers.map((blocker, index) => (
              <div key={`${blocker.code}-${index}`} style={blockerItemStyle}>
                <strong>{blocker.code}</strong>: {blocker.message}
              </div>
            ))}
          </div>
        </SectionCard>
      ) : null}
    </div>
  )
}
