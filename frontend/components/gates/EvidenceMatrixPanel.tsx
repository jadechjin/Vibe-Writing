"use client"

import { useEffect, useMemo, useState, type CSSProperties } from "react"

import { useAssets } from "../../hooks/useAnalysis"
import {
  useApproveClaim,
  useClaims,
  useCreateClaimEvidenceLink,
  useCreateOutlineBinding,
  useGenerateEvidenceMatrix,
  useGenerateOutline,
  useConfirmOutline,
  useOutlines,
  type ClaimDetail,
  type OutlineAssetBindingDetail,
} from "../../hooks/useEvidence"
import type { SystemDetail } from "../../hooks/useProjects"
import type { Blocker, WorkflowSnapshot } from "../../hooks/useProjectStatus"
import { gateTheme } from "../../styles/gate-theme"
import { ActionButton } from "../ui/ActionButton"
import { EmptyState } from "../ui/EmptyState"
import { SectionCard } from "../ui/SectionCard"
import { StatusBadge } from "../ui/StatusBadge"
import { getLatestClaims, getLatestOutline, getOrderedSystemSections } from "./workbenchSelectors"
import { GateTaskStatus } from "./GateTaskStatus"

export type GateContentPanelProps = Readonly<{
  snapshot: WorkflowSnapshot | null
  blockers: Blocker[]
  systemId: string
  systemDetail?: SystemDetail | null
}>

type BindingDraft = { assetId: string; sectionKey: string }
type LinkDraft = { assetId: string }
type ClaimLinkFeedback = { message: string }

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

const summaryValueStyle: CSSProperties = { fontSize: "18px", fontWeight: 700, color: "#f8fafc" }
const summaryLabelStyle: CSSProperties = {
  fontSize: "11px",
  color: "#94a3b8",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginTop: "4px",
}

const listStyle: CSSProperties = { display: "flex", flexDirection: "column", gap: "10px", marginTop: "12px" }

const itemStyle: CSSProperties = {
  padding: "12px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  background: "rgba(15, 23, 42, 0.3)",
}

const itemHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "8px",
}

const itemTitleStyle: CSSProperties = { fontSize: "13px", fontWeight: 600, color: "#e2e8f0" }
const itemMetaStyle: CSSProperties = { fontSize: "12px", color: "#64748b", marginTop: "4px" }

const actionRowStyle: CSSProperties = { display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "10px" }

const fieldLabelStyle: CSSProperties = { fontSize: "11px", fontWeight: 600, color: "#cbd5e1" }

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

const helperTextStyle: CSSProperties = { marginTop: "8px", fontSize: "12px", lineHeight: 1.5, color: "#94a3b8" }
const subSectionTitleStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 700,
  color: "#cbd5e1",
  textTransform: "uppercase",
  letterSpacing: "0.08em",
}

const successTextStyle: CSSProperties = { marginTop: "8px", fontSize: "12px", color: "#86efac" }
const errorTextStyle: CSSProperties = { marginTop: "8px", fontSize: "12px", color: "#fca5a5" }

const bulkActionsBarStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  padding: "8px 12px",
  background: "rgba(96, 165, 250, 0.08)",
  border: "1px solid rgba(96, 165, 250, 0.2)",
  borderRadius: "8px",
  marginBottom: "8px",
}

const blockerListStyle: CSSProperties = { display: "flex", flexDirection: "column", gap: "6px", marginTop: "8px" }
const blockerItemStyle: CSSProperties = {
  padding: "8px 12px",
  borderRadius: "8px",
  border: "1px solid rgba(248, 113, 113, 0.2)",
  background: "rgba(127, 29, 29, 0.1)",
  fontSize: "12px",
  color: "#fca5a5",
}

function normalizeText(value: string): string {
  return value.trim()
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

  const generateEvidenceMatrix = useGenerateEvidenceMatrix(systemId)
  const approveClaim = useApproveClaim(systemId)
  const createClaimLink = useCreateClaimEvidenceLink(systemId)
  const generateOutline = useGenerateOutline(systemId)
  const confirmOutline = useConfirmOutline(systemId)
  const createOutlineBinding = useCreateOutlineBinding(systemId)

  const latestOutline = useMemo(() => getLatestOutline(outlines), [outlines])
  const isOutlineConfirmed = latestOutline?.status === "confirmed"
  const currentState = snapshot?.currentState ?? null
  const sections = useMemo(() => getOrderedSystemSections(systemDetail), [systemDetail])

  const sortedClaims = useMemo(() => getLatestClaims(claims), [claims])
  const approvedClaims = useMemo(() => sortedClaims.filter((c) => c.status === "approved"), [sortedClaims])
  const pendingClaims = useMemo(() => sortedClaims.filter((c) => c.status !== "approved"), [sortedClaims])
  const approvedClaimCount = approvedClaims.length
  const pendingClaimCount = pendingClaims.length

  const assetOptions = useMemo(
    () => (assets ?? []).map((asset) => ({ id: asset.id, label: `${asset.fileName} · ${asset.assetType}` })),
    [assets],
  )
  const assetNameById = useMemo(() => new Map(assetOptions.map((a) => [a.id, a.label])), [assetOptions])
  const bindingBySectionKey = useMemo(
    () => new Map((latestOutline?.bindings ?? []).map((b) => [b.sectionKey, b])),
    [latestOutline],
  )

  const [bindingDraft, setBindingDraft] = useState<BindingDraft>({
    assetId: "",
    sectionKey: sections[0]?.sectionKey ?? "",
  })
  const [linkDrafts, setLinkDrafts] = useState<Record<string, LinkDraft>>({})
  const [claimLinkFeedback, setClaimLinkFeedback] = useState<Record<string, ClaimLinkFeedback>>({})
  const [bindingFeedback, setBindingFeedback] = useState<string | null>(null)
  const [selectedClaimIds, setSelectedClaimIds] = useState<Set<string>>(new Set())

  const generateEvidenceError = generateEvidenceMatrix.error instanceof Error ? generateEvidenceMatrix.error.message : null
  const approveClaimError = approveClaim.error instanceof Error ? approveClaim.error.message : null
  const createLinkError = createClaimLink.error instanceof Error ? createClaimLink.error.message : null
  const generateOutlineError = generateOutline.error instanceof Error ? generateOutline.error.message : null
  const confirmOutlineError = confirmOutline.error instanceof Error ? confirmOutline.error.message : null
  const createBindingError = createOutlineBinding.error instanceof Error ? createOutlineBinding.error.message : null

  useEffect(() => {
    setBindingFeedback(null)
  }, [latestOutline?.id, latestOutline?.updatedAt])

  const approvablePendingClaims = pendingClaims
  const allPendingSelected =
    approvablePendingClaims.length > 0 && approvablePendingClaims.every((c) => selectedClaimIds.has(c.id))

  function toggleSelectAllPending() {
    if (allPendingSelected) {
      setSelectedClaimIds(new Set())
    } else {
      setSelectedClaimIds(new Set(approvablePendingClaims.map((c) => c.id)))
    }
  }

  function toggleClaim(claimId: string) {
    setSelectedClaimIds((prev) => {
      const next = new Set(prev)
      if (next.has(claimId)) next.delete(claimId)
      else next.add(claimId)
      return next
    })
  }

  function handleBulkApproveClaims() {
    for (const claimId of selectedClaimIds) {
      approveClaim.mutate(claimId)
    }
    setSelectedClaimIds(new Set())
  }

  function getLinkDraft(claimId: string): LinkDraft {
    return linkDrafts[claimId] ?? { assetId: "" }
  }

  function getKnownBindingMessage(claim: ClaimDetail): string {
    if (!latestOutline) return "尚无已确认的提纲上下文。"
    const normalizedSectionRef = normalizeText(claim.sectionRef ?? "")
    if (!normalizedSectionRef) return "Claim 章节尚未分配。"
    const sectionBinding = bindingBySectionKey.get(normalizedSectionRef)
    if (sectionBinding) {
      return `已知绑定：章节 ${normalizedSectionRef} 当前关联至 ${assetNameById.get(sectionBinding.assetId) ?? sectionBinding.assetId}。`
    }
    return "该章节尚无已知提纲绑定。"
  }

  function isClaimBoundToKnownSection(claim: ClaimDetail): boolean {
    const normalizedSectionRef = normalizeText(claim.sectionRef ?? "")
    return normalizedSectionRef.length > 0 && bindingBySectionKey.has(normalizedSectionRef)
  }

  function updateLinkDraft(claimId: string, patch: Partial<LinkDraft>) {
    setLinkDrafts((prev) => ({ ...prev, [claimId]: { ...getLinkDraft(claimId), ...patch } }))
    setClaimLinkFeedback((prev) => {
      if (!prev[claimId]) return prev
      const next = { ...prev }
      delete next[claimId]
      return next
    })
  }

  function handleCreateLink(claimId: string) {
    const assetId = normalizeText(getLinkDraft(claimId).assetId)
    if (!assetId) return

    setClaimLinkFeedback((prev) => { const next = { ...prev }; delete next[claimId]; return next })

    createClaimLink.mutate(
      { claimId, input: { assetId } },
      {
        onSuccess: () => {
          setLinkDrafts((prev) => ({ ...prev, [claimId]: { assetId: "" } }))
          setClaimLinkFeedback((prev) => ({
            ...prev,
            [claimId]: { message: `证据链接已保存，使用 ${assetNameById.get(assetId) ?? assetId}。` },
          }))
        },
      },
    )
  }

  function handleCreateBinding() {
    if (!latestOutline) return
    const assetId = normalizeText(bindingDraft.assetId)
    const sectionKey = normalizeText(bindingDraft.sectionKey)
    if (!assetId || !sectionKey) return

    const existingBinding = bindingBySectionKey.get(sectionKey)
    if (existingBinding) {
      const existingLabel = assetNameById.get(existingBinding.assetId) ?? existingBinding.assetId
      const nextLabel = assetNameById.get(assetId) ?? assetId
      setBindingFeedback(
        existingBinding.assetId === assetId
          ? `章节 ${sectionKey} 已绑定至 ${existingLabel}。`
          : `章节 ${sectionKey} 已有绑定至 ${existingLabel}，替换为 ${nextLabel} 前请先审查。`,
      )
      return
    }

    setBindingFeedback(null)
    createOutlineBinding.mutate(
      { outlineId: latestOutline.id, input: { assetId, sectionKey } },
      {
        onSuccess: (binding: OutlineAssetBindingDetail) => {
          setBindingDraft({ assetId: "", sectionKey: sections[0]?.sectionKey ?? "" })
          setBindingFeedback(`已添加提纲绑定：${binding.sectionKey}，使用 ${assetNameById.get(binding.assetId) ?? binding.assetId}。`)
        },
      },
    )
  }

  return (
    <div style={gateTheme.panel}>
      <GateTaskStatus systemId={systemId} gateKey="G4" />

      <SectionCard
        title="证据与提纲"
        description={`当前状态：${currentState ?? "Unknown"}。先生成 Evidence Matrix，再筛查并批准 claims，随后补证据与提纲绑定，最后确认 Outline。`}
      >
        <div style={summaryGridStyle}>
          {[
            { value: sortedClaims.length, label: "Claims" },
            { value: approvedClaimCount, label: "已批准" },
            { value: pendingClaimCount, label: "待处理" },
            { value: latestOutline?.bindings.length ?? 0, label: "绑定数" },
          ].map(({ value, label }) => (
            <div key={label} style={summaryCardStyle}>
              <div style={summaryValueStyle}>{value}</div>
              <div style={summaryLabelStyle}>{label}</div>
            </div>
          ))}
        </div>
        <div style={actionRowStyle}>
          <ActionButton
            label={generateEvidenceMatrix.isPending ? "生成证据矩阵中..." : "生成证据矩阵"}
            onClick={() => generateEvidenceMatrix.mutate()}
            disabled={generateEvidenceMatrix.isPending}
            isPending={generateEvidenceMatrix.isPending}
          />
          <ActionButton
            label={generateOutline.isPending ? "生成提纲中..." : "生成提纲"}
            onClick={() => generateOutline.mutate()}
            disabled={generateOutline.isPending || isOutlineConfirmed}
            variant="secondary"
          />
        </div>
        {generateEvidenceError ? <div style={errorTextStyle}>Evidence Matrix 生成失败：{generateEvidenceError}</div> : null}
        {generateOutlineError ? <div style={errorTextStyle}>Outline 生成失败：{generateOutlineError}</div> : null}
      </SectionCard>

      <SectionCard
        title="Claims 审查队列"
        description="Claims 会按 latest-only 规则拆成 Approved 与 Pending 两组。"
      >
        {claimsLoading ? (
          <EmptyState text="加载 Claims 中..." />
        ) : claimsError ? (
          <div style={errorTextStyle}>Claims 加载失败：{claimsError instanceof Error ? claimsError.message : "未知错误"}</div>
        ) : (
          <div style={listStyle}>
            {selectedClaimIds.size > 0 ? (
              <div style={bulkActionsBarStyle}>
                <span style={{ fontSize: "12px", color: "#94a3b8" }}>已选 {selectedClaimIds.size} 项</span>
                <ActionButton
                  label={approveClaim.isPending ? "批准中..." : "批量批准 Claims"}
                  onClick={handleBulkApproveClaims}
                  disabled={approveClaim.isPending}
                  isPending={approveClaim.isPending}
                  style={{ padding: "4px 12px", fontSize: "11px" }}
                />
                <ActionButton
                  label="清除"
                  onClick={() => setSelectedClaimIds(new Set())}
                  variant="secondary"
                  style={{ padding: "4px 10px", fontSize: "11px" }}
                />
              </div>
            ) : null}

            {[
              { key: "approved", title: `已批准 (${approvedClaims.length})`, items: approvedClaims },
              { key: "pending", title: `待处理 (${pendingClaims.length})`, items: pendingClaims },
            ].map((group) => (
              <div key={group.key} style={itemStyle}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {group.key === "pending" && approvablePendingClaims.length > 0 ? (
                    <input
                      type="checkbox"
                      checked={allPendingSelected}
                      onChange={toggleSelectAllPending}
                      title="全选待处理 Claims"
                    />
                  ) : null}
                  <div style={subSectionTitleStyle}>{group.title}</div>
                </div>
                <div style={listStyle}>
                  {group.items.map((claim) => {
                    const linkDraft = getLinkDraft(claim.id)
                    const canBindEvidence = normalizeText(linkDraft.assetId).length > 0
                    const isApprovingThisClaim = approveClaim.isPending && approveClaim.variables === claim.id
                    const isBindingThisClaim = createClaimLink.isPending && createClaimLink.variables?.claimId === claim.id
                    const linkFeedback = claimLinkFeedback[claim.id] ?? null
                    const knownBinding = isClaimBoundToKnownSection(claim)
                    const isPending = claim.status !== "approved"

                    return (
                      <div key={claim.id} style={itemStyle}>
                        <div style={itemHeaderStyle}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            {isPending ? (
                              <input
                                type="checkbox"
                                checked={selectedClaimIds.has(claim.id)}
                                onChange={() => toggleClaim(claim.id)}
                              />
                            ) : null}
                            <div style={itemTitleStyle}>{claim.claimId}: {claim.statement}</div>
                          </div>
                          <StatusBadge status={claim.status} />
                        </div>
                        <div style={itemMetaStyle}>章节：{claim.sectionRef ?? "未分配"}</div>
                        <div style={itemMetaStyle}>置信度：{claim.confidenceLevel}</div>
                        {claim.approvedAt ? (
                          <div style={itemMetaStyle}>批准时间：{new Date(claim.approvedAt).toLocaleString()}</div>
                        ) : null}
                        <div style={helperTextStyle}>
                          {knownBinding ? "已有章节绑定。" : "尚无章节绑定。"}
                          {getKnownBindingMessage(claim)}
                        </div>
                        <div style={actionRowStyle}>
                          {isPending ? (
                            <ActionButton
                              label={isApprovingThisClaim ? "批准中..." : "批准 Claim"}
                              onClick={() => approveClaim.mutate(claim.id)}
                              disabled={approveClaim.isPending}
                              isPending={isApprovingThisClaim}
                            />
                          ) : null}
                        </div>
                        {assetOptions.length > 0 ? (
                          <div style={{ ...gateTheme.fieldGroup, marginTop: "10px" }}>
                            <label style={fieldLabelStyle} htmlFor={`claim-link-${claim.id}`}>
                              绑定证据资产
                            </label>
                            <select
                              id={`claim-link-${claim.id}`}
                              style={inputStyle}
                              value={linkDraft.assetId}
                              onChange={(event) => updateLinkDraft(claim.id, { assetId: event.target.value })}
                            >
                              <option value="">选择资产</option>
                              {assetOptions.map((asset) => (
                                <option key={asset.id} value={asset.id}>{asset.label}</option>
                              ))}
                            </select>
                            <ActionButton
                              label={isBindingThisClaim ? "绑定中..." : "创建证据链接"}
                              onClick={() => handleCreateLink(claim.id)}
                              disabled={!canBindEvidence || createClaimLink.isPending}
                              isPending={isBindingThisClaim}
                              variant="secondary"
                            />
                            {linkFeedback ? <div style={successTextStyle}>{linkFeedback.message}</div> : null}
                          </div>
                        ) : (
                          <div style={helperTextStyle}>当前没有可用 asset，先去 G2/G3 补齐数据与资产确认。</div>
                        )}
                      </div>
                    )
                  })}
                  {group.items.length === 0 ? <EmptyState text="该分组暂无 Claims。" /> : null}
                </div>
              </div>
            ))}
            {sortedClaims.length === 0 ? <EmptyState text="尚未生成 Claims。" /> : null}
          </div>
        )}
        {approveClaimError ? <div style={errorTextStyle}>Claim 审批失败：{approveClaimError}</div> : null}
        {createLinkError ? <div style={errorTextStyle}>Evidence 绑定失败：{createLinkError}</div> : null}
      </SectionCard>

      <SectionCard title="提纲策略">
        {outlinesLoading ? (
          <EmptyState text="加载提纲中..." />
        ) : outlinesError ? (
          <div style={errorTextStyle}>Outline 加载失败：{outlinesError instanceof Error ? outlinesError.message : "Unknown error"}</div>
        ) : latestOutline ? (
          <div style={listStyle}>
            <div style={itemStyle}>
              <div style={itemHeaderStyle}>
                <div style={itemTitleStyle}>Outline v{latestOutline.version}</div>
                <StatusBadge status={latestOutline.status} />
              </div>
              <div style={itemMetaStyle}>
                Based on {latestOutline.generatedFromClaimsJson.length} claims. Updated:{" "}
                {new Date(latestOutline.updatedAt).toLocaleString()}
              </div>
              {latestOutline.approvedAt ? (
                <div style={itemMetaStyle}>Confirmed: {new Date(latestOutline.approvedAt).toLocaleString()}</div>
              ) : null}
              <div style={itemMetaStyle}>Current bindings: {latestOutline.bindings.length}</div>
              <div style={listStyle}>
                {sections.map((section) => {
                  const binding = bindingBySectionKey.get(section.sectionKey)
                  return (
                    <div key={section.id} style={itemStyle}>
                      <div style={itemHeaderStyle}>
                        <div style={itemTitleStyle}>{section.title}</div>
                        <StatusBadge status={binding ? "Bound" : "Waiting"} variant={binding ? "success" : "pending"} />
                      </div>
                      <div style={itemMetaStyle}>Key: {section.sectionKey}</div>
                      {binding ? (
                        <>
                          <div style={itemMetaStyle}>Asset: {assetNameById.get(binding.assetId) ?? binding.assetId}</div>
                          {binding.bindingNote ? <div style={itemMetaStyle}>Note: {binding.bindingNote}</div> : null}
                        </>
                      ) : (
                        <EmptyState text="No binding for this section yet." />
                      )}
                    </div>
                  )
                })}
                {sections.length === 0 ? <EmptyState text="No system sections available." /> : null}
              </div>
              {assetOptions.length > 0 && sections.length > 0 ? (
                <div style={{ ...gateTheme.fieldGroup, marginTop: "10px" }}>
                  <label style={fieldLabelStyle} htmlFor="outline-binding-asset-id">Outline binding asset</label>
                  <select
                    id="outline-binding-asset-id"
                    style={inputStyle}
                    value={bindingDraft.assetId}
                    onChange={(event) => { setBindingDraft((prev) => ({ ...prev, assetId: event.target.value })); setBindingFeedback(null) }}
                  >
                    <option value="">Select an asset</option>
                    {assetOptions.map((asset) => <option key={asset.id} value={asset.id}>{asset.label}</option>)}
                  </select>
                  <label style={fieldLabelStyle} htmlFor="outline-binding-section-key">Target section</label>
                  <select
                    id="outline-binding-section-key"
                    style={inputStyle}
                    value={bindingDraft.sectionKey}
                    onChange={(event) => { setBindingDraft((prev) => ({ ...prev, sectionKey: event.target.value })); setBindingFeedback(null) }}
                  >
                    <option value="">Select a section</option>
                    {sections.map((section) => <option key={section.id} value={section.sectionKey}>{section.title}</option>)}
                  </select>
                </div>
              ) : (
                <div style={helperTextStyle}>需要同时有可用 assets 和系统 sections，才能创建 outline binding。</div>
              )}
              <div style={actionRowStyle}>
                <ActionButton
                  label={createOutlineBinding.isPending ? "Binding..." : "Add Outline Binding"}
                  onClick={handleCreateBinding}
                  disabled={createOutlineBinding.isPending || !normalizeText(bindingDraft.assetId) || !normalizeText(bindingDraft.sectionKey)}
                  isPending={createOutlineBinding.isPending}
                  variant="secondary"
                />
                {!isOutlineConfirmed ? (
                  <ActionButton
                    label={confirmOutline.isPending ? "Confirming..." : "Confirm Outline"}
                    onClick={() => confirmOutline.mutate(latestOutline.id)}
                    disabled={confirmOutline.isPending}
                    isPending={confirmOutline.isPending}
                  />
                ) : null}
              </div>
              {bindingFeedback ? <div style={{ marginTop: "8px", fontSize: "12px", color: "#86efac" }}>{bindingFeedback}</div> : null}
            </div>
          </div>
        ) : (
          <div style={listStyle}>
            <div style={itemStyle}>
              <div style={itemTitleStyle}>No outline generated yet.</div>
              <div style={helperTextStyle}>Outline 尚未生成，但当前 system sections 仍会保留可见，方便先检查后续绑定目标。</div>
            </div>
            {sections.map((section) => (
              <div key={section.id} style={itemStyle}>
                <div style={itemHeaderStyle}>
                  <div style={itemTitleStyle}>{section.title}</div>
                  <StatusBadge status="Waiting" variant="pending" />
                </div>
                <div style={itemMetaStyle}>Key: {section.sectionKey}</div>
                <EmptyState text="Generate an outline to start binding assets for this section." />
              </div>
            ))}
            {sections.length === 0 ? <EmptyState text="No system sections available." /> : null}
          </div>
        )}
        {createBindingError ? <div style={errorTextStyle}>Outline 绑定失败：{createBindingError}</div> : null}
        {confirmOutlineError ? <div style={errorTextStyle}>Outline 确认失败：{confirmOutlineError}</div> : null}
      </SectionCard>

      {blockers.length > 0 ? (
        <SectionCard title={<span style={{ fontSize: "13px", color: "#fca5a5" }}>Blockers ({blockers.length})</span>}>
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
