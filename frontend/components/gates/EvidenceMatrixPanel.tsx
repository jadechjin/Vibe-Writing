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
import { getLatestClaims, getLatestOutline, getOrderedSystemSections } from "./workbenchSelectors"
import { GateTaskStatus } from "./GateTaskStatus"

export type GateContentPanelProps = Readonly<{
  snapshot: WorkflowSnapshot | null
  blockers: Blocker[]
  systemId: string
  systemDetail?: SystemDetail | null
}>

type BindingDraft = {
  assetId: string
  sectionKey: string
}

type LinkDraft = {
  assetId: string
}

type ClaimLinkFeedback = {
  message: string
}

const panelStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "14px",
}

const sectionCardStyle: CSSProperties = {
  padding: "16px",
  borderRadius: "14px",
  border: "1px solid rgba(148, 163, 184, 0.15)",
  background: "rgba(30, 41, 59, 0.38)",
}

const titleStyle: CSSProperties = {
  fontSize: "15px",
  fontWeight: 700,
  color: "#f8fafc",
  marginBottom: "8px",
}

const descStyle: CSSProperties = {
  fontSize: "13px",
  lineHeight: 1.6,
  color: "#94a3b8",
}

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

const itemTitleStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  color: "#e2e8f0",
}

const itemMetaStyle: CSSProperties = {
  fontSize: "12px",
  color: "#64748b",
  marginTop: "4px",
}

const actionRowStyle: CSSProperties = {
  display: "flex",
  gap: "8px",
  flexWrap: "wrap",
  marginTop: "10px",
}

const actionBtnStyle: CSSProperties = {
  padding: "8px 18px",
  borderRadius: "10px",
  border: "1px solid rgba(249, 115, 22, 0.5)",
  background: "rgba(154, 52, 18, 0.15)",
  fontSize: "13px",
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

const badgeStyle = (status: string): CSSProperties => ({
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: "6px",
  fontSize: "11px",
  fontWeight: 600,
  textTransform: "uppercase",
  background:
    status === "approved" || status === "confirmed"
      ? "rgba(34, 197, 94, 0.15)"
      : "rgba(249, 115, 22, 0.15)",
  color:
    status === "approved" || status === "confirmed" ? "#4ade80" : "#fb923c",
  border: `1px solid ${
    status === "approved" || status === "confirmed"
      ? "rgba(34, 197, 94, 0.3)"
      : "rgba(249, 115, 22, 0.3)"
  }`,
})

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
  marginTop: "10px",
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

const helperTextStyle: CSSProperties = {
  marginTop: "8px",
  fontSize: "12px",
  lineHeight: 1.5,
  color: "#94a3b8",
}

const subSectionTitleStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 700,
  color: "#cbd5e1",
  textTransform: "uppercase",
  letterSpacing: "0.08em",
}

const successTextStyle: CSSProperties = {
  marginTop: "8px",
  fontSize: "12px",
  color: "#86efac",
}

const emptyStateStyle: CSSProperties = {
  padding: "12px",
  textAlign: "center",
  color: "#64748b",
  fontSize: "12px",
  fontStyle: "italic",
}

const errorTextStyle: CSSProperties = {
  marginTop: "8px",
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
  const { data: outlines, isLoading: outlinesLoading, error: outlinesError } =
    useOutlines(systemId)
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
  const approvedClaims = useMemo(
    () => sortedClaims.filter((claim) => claim.status === "approved"),
    [sortedClaims],
  )
  const pendingClaims = useMemo(
    () => sortedClaims.filter((claim) => claim.status !== "approved"),
    [sortedClaims],
  )

  const approvedClaimCount = useMemo(
    () => sortedClaims.filter((claim) => claim.status === "approved").length,
    [sortedClaims],
  )
  const pendingClaimCount = sortedClaims.length - approvedClaimCount

  const assetOptions = useMemo(() => {
    return (assets ?? []).map((asset) => ({
      id: asset.id,
      label: `${asset.fileName} · ${asset.assetType}`,
    }))
  }, [assets])

  const assetNameById = useMemo(() => {
    return new Map(assetOptions.map((asset) => [asset.id, asset.label]))
  }, [assetOptions])
  const bindingBySectionKey = useMemo(() => {
    return new Map((latestOutline?.bindings ?? []).map((binding) => [binding.sectionKey, binding]))
  }, [latestOutline])

  const [bindingDraft, setBindingDraft] = useState<BindingDraft>({
    assetId: "",
    sectionKey: sections[0]?.sectionKey ?? "",
  })
  const [linkDrafts, setLinkDrafts] = useState<Record<string, LinkDraft>>({})
  const [claimLinkFeedback, setClaimLinkFeedback] = useState<Record<string, ClaimLinkFeedback>>({})
  const [bindingFeedback, setBindingFeedback] = useState<string | null>(null)

  const generateEvidenceError =
    generateEvidenceMatrix.error instanceof Error
      ? generateEvidenceMatrix.error.message
      : null
  const approveClaimError = approveClaim.error instanceof Error ? approveClaim.error.message : null
  const createLinkError =
    createClaimLink.error instanceof Error ? createClaimLink.error.message : null
  const generateOutlineError =
    generateOutline.error instanceof Error ? generateOutline.error.message : null
  const confirmOutlineError =
    confirmOutline.error instanceof Error ? confirmOutline.error.message : null
  const createBindingError =
    createOutlineBinding.error instanceof Error ? createOutlineBinding.error.message : null

  useEffect(() => {
    setBindingFeedback(null)
  }, [latestOutline?.id, latestOutline?.updatedAt])

  function getLinkDraft(claimId: string): LinkDraft {
    return linkDrafts[claimId] ?? { assetId: "" }
  }

  function getKnownBindingMessage(claim: ClaimDetail): string {
    if (!latestOutline) {
      return "No confirmed outline context yet. Claim-level history is not fully available."
    }

    const normalizedSectionRef = normalizeText(claim.sectionRef ?? "")
    if (!normalizedSectionRef) {
      return "Claim section is not assigned yet, so outline-bound visibility is unavailable."
    }

    const sectionBinding = bindingBySectionKey.get(normalizedSectionRef)
    if (sectionBinding) {
      return `Known binding: section ${normalizedSectionRef} is currently linked to ${assetNameById.get(sectionBinding.assetId) ?? sectionBinding.assetId}.`
    }

    return "No known outline binding for this section yet. Historical claim-level link truth is limited to current query data and new mutation results."
  }

  function isClaimBoundToKnownSection(claim: ClaimDetail): boolean {
    const normalizedSectionRef = normalizeText(claim.sectionRef ?? "")

    return normalizedSectionRef.length > 0 && bindingBySectionKey.has(normalizedSectionRef)
  }

  function updateLinkDraft(claimId: string, patch: Partial<LinkDraft>) {
    setLinkDrafts((prev) => ({
      ...prev,
      [claimId]: {
        ...getLinkDraft(claimId),
        ...patch,
      },
    }))
    setClaimLinkFeedback((prev) => {
      if (!prev[claimId]) {
        return prev
      }

      const nextFeedback = { ...prev }
      delete nextFeedback[claimId]
      return nextFeedback
    })
  }

  function handleCreateLink(claimId: string) {
    const assetId = normalizeText(getLinkDraft(claimId).assetId)
    if (!assetId) {
      return
    }

    setClaimLinkFeedback((prev) => {
      const nextFeedback = { ...prev }
      delete nextFeedback[claimId]
      return nextFeedback
    })

    createClaimLink.mutate(
      {
        claimId,
        input: { assetId },
      },
      {
        onSuccess: () => {
          setLinkDrafts((prev) => ({
            ...prev,
            [claimId]: { assetId: "" },
          }))
          setClaimLinkFeedback((prev) => ({
            ...prev,
            [claimId]: {
              message: `Evidence link saved for this claim using ${assetNameById.get(assetId) ?? assetId}.`,
            },
          }))
        },
      },
    )
  }

  function handleCreateBinding() {
    if (!latestOutline) {
      return
    }

    const assetId = normalizeText(bindingDraft.assetId)
    const sectionKey = normalizeText(bindingDraft.sectionKey)
    if (!assetId || !sectionKey) {
      return
    }

    const existingBinding = bindingBySectionKey.get(sectionKey)
    if (existingBinding) {
      const existingAssetLabel = assetNameById.get(existingBinding.assetId) ?? existingBinding.assetId
      const nextAssetLabel = assetNameById.get(assetId) ?? assetId

      setBindingFeedback(
        existingBinding.assetId === assetId
          ? `Section ${sectionKey} is already bound to ${existingAssetLabel}.`
          : `Section ${sectionKey} already has a known binding to ${existingAssetLabel}. Review it before replacing with ${nextAssetLabel}.`,
      )
      return
    }

    setBindingFeedback(null)

    createOutlineBinding.mutate(
      {
        outlineId: latestOutline.id,
        input: {
          assetId,
          sectionKey,
        },
      },
      {
        onSuccess: (binding: OutlineAssetBindingDetail) => {
          setBindingDraft({
            assetId: "",
            sectionKey: sections[0]?.sectionKey ?? "",
          })
          setBindingFeedback(
            `Added outline binding for ${binding.sectionKey} using ${assetNameById.get(binding.assetId) ?? binding.assetId}.`,
          )
        },
      },
    )
  }

  return (
    <div style={panelStyle}>
      <GateTaskStatus systemId={systemId} gateKey="G4" />
      <div style={sectionCardStyle}>
        <div style={titleStyle}>Evidence &amp; Outline</div>
        <div style={descStyle}>
          当前状态：{currentState ?? "Unknown"}。先生成 Evidence Matrix，再筛查并批准 claims，随后补证据与提纲绑定，最后确认 Outline。
        </div>
        <div style={summaryGridStyle}>
          <div style={summaryCardStyle}>
            <div style={summaryValueStyle}>{sortedClaims.length}</div>
            <div style={summaryLabelStyle}>Claims</div>
          </div>
          <div style={summaryCardStyle}>
            <div style={summaryValueStyle}>{approvedClaimCount}</div>
            <div style={summaryLabelStyle}>Approved</div>
          </div>
          <div style={summaryCardStyle}>
            <div style={summaryValueStyle}>{pendingClaimCount}</div>
            <div style={summaryLabelStyle}>Pending</div>
          </div>
          <div style={summaryCardStyle}>
            <div style={summaryValueStyle}>{latestOutline?.bindings.length ?? 0}</div>
            <div style={summaryLabelStyle}>Bindings</div>
          </div>
        </div>
        <div style={actionRowStyle}>
          <button
            type="button"
            style={actionBtnStyle}
            onClick={() => generateEvidenceMatrix.mutate()}
            disabled={generateEvidenceMatrix.isPending}
          >
            {generateEvidenceMatrix.isPending
              ? "Generating Evidence Matrix..."
              : "Generate Evidence Matrix"}
          </button>
          <button
            type="button"
            style={secondaryBtnStyle}
            onClick={() => generateOutline.mutate()}
            disabled={generateOutline.isPending || isOutlineConfirmed}
          >
            {generateOutline.isPending ? "Generating Outline..." : "Generate Outline"}
          </button>
        </div>
        {generateEvidenceError ? (
          <div style={errorTextStyle}>Evidence Matrix 生成失败：{generateEvidenceError}</div>
        ) : null}
        {generateOutlineError ? (
          <div style={errorTextStyle}>Outline 生成失败：{generateOutlineError}</div>
        ) : null}
      </div>

      <div style={sectionCardStyle}>
        <div style={titleStyle}>Claims Review Queue</div>
        <div style={descStyle}>
          Claims 会按 latest-only 规则拆成 Approved 与 Pending 两组。claim-level evidence-link 历史没有完整 read model，所以这里只展示当前已知的 section binding 线索与最近一次本地提交结果。
        </div>
        {claimsLoading ? (
          <div style={emptyStateStyle}>Loading claims...</div>
        ) : claimsError ? (
          <div style={errorTextStyle}>
            Claims 加载失败：{claimsError instanceof Error ? claimsError.message : "Unknown error"}
          </div>
        ) : (
          <div style={listStyle}>
            {[
              {
                key: "approved",
                title: `Approved (${approvedClaims.length})`,
                items: approvedClaims,
              },
              {
                key: "pending",
                title: `Pending (${pendingClaims.length})`,
                items: pendingClaims,
              },
            ].map((group) => (
              <div key={group.key} style={itemStyle}>
                <div style={subSectionTitleStyle}>{group.title}</div>
                <div style={listStyle}>
                  {group.items.map((claim) => {
                    const linkDraft = getLinkDraft(claim.id)
                    const canBindEvidence = normalizeText(linkDraft.assetId).length > 0
                    const isApprovingThisClaim =
                      approveClaim.isPending && approveClaim.variables === claim.id
                    const isBindingThisClaim =
                      createClaimLink.isPending && createClaimLink.variables?.claimId === claim.id
                    const linkFeedback = claimLinkFeedback[claim.id] ?? null
                    const knownBinding = isClaimBoundToKnownSection(claim)

                    return (
                      <div key={claim.id} style={itemStyle}>
                        <div style={itemHeaderStyle}>
                          <div style={itemTitleStyle}>
                            {claim.claimId}: {claim.statement}
                          </div>
                          <span style={badgeStyle(claim.status)}>{claim.status}</span>
                        </div>
                        <div style={itemMetaStyle}>Section: {claim.sectionRef ?? "Unassigned"}</div>
                        <div style={itemMetaStyle}>Confidence: {claim.confidenceLevel}</div>
                        {claim.approvedAt ? (
                          <div style={itemMetaStyle}>
                            Approved: {new Date(claim.approvedAt).toLocaleString()}
                          </div>
                        ) : null}
                        <div style={helperTextStyle}>
                          {knownBinding ? "Known section binding is available. " : "Known section binding is not available yet. "}
                          {getKnownBindingMessage(claim)}
                        </div>
                        <div style={actionRowStyle}>
                          {claim.status !== "approved" ? (
                            <button
                              type="button"
                              style={actionBtnStyle}
                              onClick={() => approveClaim.mutate(claim.id)}
                              disabled={approveClaim.isPending}
                            >
                              {isApprovingThisClaim ? "Approving..." : "Approve Claim"}
                            </button>
                          ) : null}
                        </div>
                        {assetOptions.length > 0 ? (
                          <div style={fieldGroupStyle}>
                            <label style={fieldLabelStyle} htmlFor={`claim-link-${claim.id}`}>
                              Bind evidence asset
                            </label>
                            <select
                              id={`claim-link-${claim.id}`}
                              style={inputStyle}
                              value={linkDraft.assetId}
                              onChange={(event) =>
                                updateLinkDraft(claim.id, { assetId: event.target.value })
                              }
                            >
                              <option value="">Select an asset</option>
                              {assetOptions.map((asset) => (
                                <option key={asset.id} value={asset.id}>
                                  {asset.label}
                                </option>
                              ))}
                            </select>
                            <button
                              type="button"
                              style={secondaryBtnStyle}
                              onClick={() => handleCreateLink(claim.id)}
                              disabled={!canBindEvidence || createClaimLink.isPending}
                            >
                              {isBindingThisClaim ? "Binding..." : "Create Evidence Link"}
                            </button>
                            {linkFeedback ? (
                              <div style={successTextStyle}>{linkFeedback.message}</div>
                            ) : null}
                          </div>
                        ) : (
                          <div style={helperTextStyle}>
                            当前没有可用 asset，先去 G2/G3 补齐数据与资产确认。
                          </div>
                        )}
                      </div>
                    )
                  })}
                  {group.items.length === 0 ? (
                    <div style={emptyStateStyle}>No claims in this group yet.</div>
                  ) : null}
                </div>
              </div>
            ))}
            {sortedClaims.length === 0 ? (
              <div style={emptyStateStyle}>No claims generated yet.</div>
            ) : null}
          </div>
        )}
        {approveClaimError ? (
          <div style={errorTextStyle}>Claim 审批失败：{approveClaimError}</div>
        ) : null}
        {createLinkError ? (
          <div style={errorTextStyle}>Evidence 绑定失败：{createLinkError}</div>
        ) : null}
      </div>

      <div style={sectionCardStyle}>
        <div style={titleStyle}>Outline Strategy</div>
        {outlinesLoading ? (
          <div style={emptyStateStyle}>Loading outlines...</div>
        ) : outlinesError ? (
          <div style={errorTextStyle}>
            Outline 加载失败：{outlinesError instanceof Error ? outlinesError.message : "Unknown error"}
          </div>
        ) : latestOutline ? (
          <div style={listStyle}>
            <div style={itemStyle}>
              <div style={itemHeaderStyle}>
                <div style={itemTitleStyle}>Outline v{latestOutline.version}</div>
                <span style={badgeStyle(latestOutline.status)}>{latestOutline.status}</span>
              </div>
              <div style={itemMetaStyle}>
                Based on {latestOutline.generatedFromClaimsJson.length} claims. Updated:{" "}
                {new Date(latestOutline.updatedAt).toLocaleString()}
              </div>
              {latestOutline.approvedAt ? (
                <div style={itemMetaStyle}>
                  Confirmed: {new Date(latestOutline.approvedAt).toLocaleString()}
                </div>
              ) : null}
              <div style={itemMetaStyle}>
                Current bindings: {latestOutline.bindings.length}
              </div>
              <div style={listStyle}>
                {sections.map((section) => {
                  const binding = bindingBySectionKey.get(section.sectionKey)
                  return (
                    <div key={section.id} style={itemStyle}>
                      <div style={itemHeaderStyle}>
                        <div style={itemTitleStyle}>{section.title}</div>
                        {binding ? (
                          <span style={badgeStyle("confirmed")}>Bound</span>
                        ) : (
                          <span style={badgeStyle("pending")}>Waiting</span>
                        )}
                      </div>
                      <div style={itemMetaStyle}>Key: {section.sectionKey}</div>
                      {binding ? (
                        <>
                          <div style={itemMetaStyle}>
                            Asset: {assetNameById.get(binding.assetId) ?? binding.assetId}
                          </div>
                          {binding.bindingNote ? (
                            <div style={itemMetaStyle}>Note: {binding.bindingNote}</div>
                          ) : null}
                        </>
                      ) : (
                        <div style={emptyStateStyle}>No binding for this section yet.</div>
                      )}
                    </div>
                  )
                })}
                {sections.length === 0 ? (
                  <div style={emptyStateStyle}>No system sections available.</div>
                ) : null}
              </div>
              {assetOptions.length > 0 && sections.length > 0 ? (
                <div style={fieldGroupStyle}>
                  <label style={fieldLabelStyle} htmlFor="outline-binding-asset-id">
                    Outline binding asset
                  </label>
                  <select
                    id="outline-binding-asset-id"
                    style={inputStyle}
                    value={bindingDraft.assetId}
                    onChange={(event) => {
                      setBindingDraft((prev) => ({ ...prev, assetId: event.target.value }))
                      setBindingFeedback(null)
                    }}
                  >
                    <option value="">Select an asset</option>
                    {assetOptions.map((asset) => (
                      <option key={asset.id} value={asset.id}>
                        {asset.label}
                      </option>
                    ))}
                  </select>
                  <label style={fieldLabelStyle} htmlFor="outline-binding-section-key">
                    Target section
                  </label>
                  <select
                    id="outline-binding-section-key"
                    style={inputStyle}
                    value={bindingDraft.sectionKey}
                    onChange={(event) => {
                      setBindingDraft((prev) => ({ ...prev, sectionKey: event.target.value }))
                      setBindingFeedback(null)
                    }}
                  >
                    <option value="">Select a section</option>
                    {sections.map((section) => (
                      <option key={section.id} value={section.sectionKey}>
                        {section.title}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div style={helperTextStyle}>
                  需要同时有可用 assets 和系统 sections，才能创建 outline binding。
                </div>
              )}
              <div style={actionRowStyle}>
                <button
                  type="button"
                  style={secondaryBtnStyle}
                  onClick={handleCreateBinding}
                  disabled={
                    createOutlineBinding.isPending ||
                    !normalizeText(bindingDraft.assetId) ||
                    !normalizeText(bindingDraft.sectionKey)
                  }
                >
                  {createOutlineBinding.isPending ? "Binding..." : "Add Outline Binding"}
                </button>
                {!isOutlineConfirmed ? (
                  <button
                    type="button"
                    style={actionBtnStyle}
                    onClick={() => confirmOutline.mutate(latestOutline.id)}
                    disabled={confirmOutline.isPending}
                  >
                    {confirmOutline.isPending ? "Confirming..." : "Confirm Outline"}
                  </button>
                ) : null}
              </div>
              {bindingFeedback ? <div style={successTextStyle}>{bindingFeedback}</div> : null}
            </div>
          </div>
        ) : (
          <div style={listStyle}>
            <div style={itemStyle}>
              <div style={itemTitleStyle}>No outline generated yet.</div>
              <div style={helperTextStyle}>
                Outline 尚未生成，但当前 system sections 仍会保留可见，方便先检查后续绑定目标。
              </div>
            </div>
            {sections.map((section) => (
              <div key={section.id} style={itemStyle}>
                <div style={itemHeaderStyle}>
                  <div style={itemTitleStyle}>{section.title}</div>
                  <span style={badgeStyle("pending")}>Waiting</span>
                </div>
                <div style={itemMetaStyle}>Key: {section.sectionKey}</div>
                <div style={emptyStateStyle}>Generate an outline to start binding assets for this section.</div>
              </div>
            ))}
            {sections.length === 0 ? (
              <div style={emptyStateStyle}>No system sections available.</div>
            ) : null}
          </div>
        )}
        {createBindingError ? (
          <div style={errorTextStyle}>Outline 绑定失败：{createBindingError}</div>
        ) : null}
        {confirmOutlineError ? (
          <div style={errorTextStyle}>Outline 确认失败：{confirmOutlineError}</div>
        ) : null}
      </div>

      {blockers.length > 0 ? (
        <div style={sectionCardStyle}>
          <div style={{ ...titleStyle, fontSize: "13px", color: "#fca5a5" }}>
            Blockers ({blockers.length})
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
