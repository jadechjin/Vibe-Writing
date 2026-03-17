"use client"

import type { CSSProperties } from "react"
import { useState } from "react"
import type { EnhancedOutlineSection, EvidenceGapDetail } from "../../../types/g4"
import type { OutlineAssetBindingDetail, OutlineDetail } from "../../../hooks/useEvidence"
import { ActionButton } from "../../ui/ActionButton"
import { EmptyState } from "../../ui/EmptyState"
import { SectionCard } from "../../ui/SectionCard"
import { StatusBadge } from "../../ui/StatusBadge"
import { EvidenceGapCard } from "./EvidenceGapCard"

type SystemSectionDetail = { id: string; sectionKey: string; title: string; orderNo: number }

type Props = {
  sections: SystemSectionDetail[]
  outlineSections: EnhancedOutlineSection[]
  bindings: Map<string, OutlineAssetBindingDetail>
  gaps: EvidenceGapDetail[]
  assetOptions: Array<{ id: string; label: string }>
  assetNameById: Map<string, string>
  latestOutline: OutlineDetail | null
  isOutlineConfirmed: boolean
  onCreateBinding: (assetId: string, sectionKey: string) => void
  onConfirmOutline: () => void
  isBindingPending: boolean
  isConfirmPending: boolean
  bindingFeedback: string | null
  outlinesLoading: boolean
  outlinesError: Error | null
  confirmOutlineError: string | null
  createBindingError: string | null
  canConfirmOutline: boolean
  confirmOutlineHint: string | null
}

const coverageLabels: Record<string, string> = { covered: "已覆盖", partial: "部分覆盖", uncovered: "未覆盖" }
const coverageVariants: Record<string, "success" | "warning" | "error"> = {
  covered: "success",
  partial: "warning",
  uncovered: "error",
}

// Styles — dark theme inline CSSProperties
const metaBarStyle: CSSProperties = {
  display: "flex", gap: "12px", alignItems: "center", fontSize: "12px",
  color: "#94a3b8", padding: "8px 0", borderBottom: "1px solid rgba(148,163,184,0.1)",
}
const listStyle: CSSProperties = { display: "flex", flexDirection: "column", gap: "10px", marginTop: "12px" }
const sectionRowStyle: CSSProperties = {
  padding: "12px", border: "1px solid rgba(148,163,184,0.1)",
  borderRadius: "10px", background: "rgba(15,23,42,0.3)",
}
const sectionHeaderStyle: CSSProperties = {
  display: "flex", justifyContent: "space-between", alignItems: "center",
  cursor: "pointer", userSelect: "none",
}
const sectionTitleStyle: CSSProperties = { fontSize: "13px", fontWeight: 600, color: "#e2e8f0" }
const sectionKeyStyle: CSSProperties = { fontSize: "11px", color: "#64748b" }
const chipStyle: CSSProperties = {
  fontSize: "10px", padding: "2px 6px", borderRadius: "4px",
  background: "rgba(148,163,184,0.15)", color: "#94a3b8",
}
const gapChipStyle: CSSProperties = {
  fontSize: "10px", padding: "2px 6px", borderRadius: "4px",
  background: "rgba(248,113,113,0.15)", color: "#fca5a5",
}
const expandedStyle: CSSProperties = {
  marginTop: "8px", paddingLeft: "20px", display: "flex", flexDirection: "column", gap: "8px",
}
const subTitleStyle: CSSProperties = { fontSize: "11px", fontWeight: 600, color: "#cbd5e1", marginBottom: "4px" }
const refItemStyle: CSSProperties = { display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#e2e8f0" }
const refSummaryStyle: CSSProperties = { fontSize: "11px", color: "#94a3b8" }
const bindingInfoStyle: CSSProperties = { marginTop: "8px" }
const noteStyle: CSSProperties = { fontSize: "11px", color: "#64748b" }
const selectStyle: CSSProperties = {
  padding: "6px 8px", borderRadius: "8px",
  border: "1px solid rgba(148,163,184,0.18)", background: "rgba(15,23,42,0.6)",
  color: "#e2e8f0", fontSize: "12px", outline: "none",
}
const actionRowStyle: CSSProperties = { display: "flex", gap: "8px", marginTop: "12px" }
const feedbackStyle: CSSProperties = { marginTop: "8px", fontSize: "12px", color: "#86efac" }
const errorStyle: CSSProperties = { marginTop: "8px", fontSize: "12px", color: "#fca5a5" }

function SectionBindingForm({ sectionKey, assetOptions, onBind, isPending }: {
  sectionKey: string
  assetOptions: Array<{ id: string; label: string }>
  onBind: (assetId: string) => void
  isPending: boolean
}) {
  const [selectedAsset, setSelectedAsset] = useState("")
  return (
    <div style={{ display: "flex", gap: "8px", alignItems: "center", marginTop: "8px" }}>
      <select style={selectStyle} value={selectedAsset} onChange={(e) => setSelectedAsset(e.target.value)}>
        <option value="">选择资产</option>
        {assetOptions.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
      </select>
      <ActionButton
        label={isPending ? "绑定中..." : "绑定"}
        onClick={() => { onBind(selectedAsset); setSelectedAsset("") }}
        disabled={isPending || !selectedAsset}
        isPending={isPending}
        variant="secondary"
        style={{ padding: "4px 12px", fontSize: "11px" }}
      />
    </div>
  )
}

export function SectionOutlineList({
  sections, outlineSections, bindings, gaps, assetOptions, assetNameById,
  latestOutline, isOutlineConfirmed, onCreateBinding, onConfirmOutline,
  isBindingPending, isConfirmPending, bindingFeedback,
  outlinesLoading, outlinesError, confirmOutlineError, createBindingError, canConfirmOutline, confirmOutlineHint,
}: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  function toggle(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  return (
    <SectionCard title="章节与提纲">
      {outlinesLoading ? <EmptyState text="加载提纲中..." /> : outlinesError ? (
        <div style={errorStyle}>Outline 加载失败：{outlinesError.message}</div>
      ) : (
        <>
          {latestOutline && (
            <div style={metaBarStyle}>
              <span>提纲 v{latestOutline.version}</span>
              <StatusBadge status={latestOutline.status} />
              <span>基于 {latestOutline.generatedFromClaimsJson.length} 条 Claims</span>
              <span>绑定数：{latestOutline.bindings.length}</span>
              {latestOutline.approvedAt && <span>确认时间：{new Date(latestOutline.approvedAt).toLocaleString()}</span>}
            </div>
          )}

          <div style={listStyle}>
            {sections.map((section) => {
              const outlineSection = outlineSections.find((s) => s.sectionKey === section.sectionKey)
              const binding = bindings.get(section.sectionKey)
              const sectionGaps = gaps.filter((g) => g.sectionKey === section.sectionKey)
              const coverage = outlineSection?.coverage ?? "uncovered"
              const claimCount = outlineSection?.claimIds?.length ?? 0
              const isExpanded = expanded.has(section.sectionKey)

              return (
                <div key={section.id} style={sectionRowStyle}>
                  <div style={sectionHeaderStyle} onClick={() => toggle(section.sectionKey)}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span>{isExpanded ? "\u25BE" : "\u25B8"}</span>
                      <span style={sectionTitleStyle}>{section.title}</span>
                      <span style={sectionKeyStyle}>{section.sectionKey}</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <StatusBadge status={coverageLabels[coverage] ?? coverage} variant={coverageVariants[coverage]} />
                      {claimCount > 0 && <span style={chipStyle}>{claimCount} claims</span>}
                      {binding ? (
                        <StatusBadge status="已绑定" variant="success" />
                      ) : (
                        <StatusBadge status="待绑定" variant="pending" />
                      )}
                      {sectionGaps.length > 0 && <span style={gapChipStyle}>{sectionGaps.length} 缺口</span>}
                    </div>
                  </div>

                  {isExpanded && (
                    <div style={expandedStyle}>
                      {outlineSection?.evidenceLinkRefs && outlineSection.evidenceLinkRefs.length > 0 && (
                        <div>
                          <div style={subTitleStyle}>证据链接</div>
                          {outlineSection.evidenceLinkRefs.map((ref, i) => (
                            <div key={i} style={refItemStyle}>
                              <span>{assetNameById.get(ref.assetId) ?? ref.assetId.slice(0, 8)}</span>
                              <StatusBadge status={ref.strength} variant={ref.strength === "strong" ? "success" : ref.strength === "weak" ? "error" : "pending"} />
                            </div>
                          ))}
                        </div>
                      )}

                      {outlineSection?.analysisRunRefs && outlineSection.analysisRunRefs.length > 0 && (
                        <div>
                          <div style={subTitleStyle}>分析结果</div>
                          {outlineSection.analysisRunRefs.map((ref, i) => (
                            <div key={i} style={refItemStyle}>
                              <StatusBadge status={ref.status} />
                              <span style={refSummaryStyle}>{ref.summary ?? "无摘要"}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {binding ? (
                        <div style={bindingInfoStyle}>
                          <span style={subTitleStyle}>已绑定资产</span>
                          <span>{assetNameById.get(binding.assetId) ?? binding.assetId}</span>
                          {binding.bindingNote && <span style={noteStyle}>备注：{binding.bindingNote}</span>}
                        </div>
                      ) : latestOutline && assetOptions.length > 0 ? (
                        <SectionBindingForm
                          sectionKey={section.sectionKey}
                          assetOptions={assetOptions}
                          onBind={(assetId) => onCreateBinding(assetId, section.sectionKey)}
                          isPending={isBindingPending}
                        />
                      ) : null}

                      {sectionGaps.length > 0 && (
                        <div style={{ marginTop: "8px" }}>
                          {sectionGaps.map((gap, i) => (
                            <EvidenceGapCard key={`${gap.gapType}-${i}`} gap={gap} />
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
            {sections.length === 0 && <EmptyState text="暂无系统章节。" />}
          </div>

          {latestOutline && !isOutlineConfirmed && (
            <div style={actionRowStyle}>
              <ActionButton
                label={isConfirmPending ? "确认中..." : "确认提纲"}
                onClick={onConfirmOutline}
                disabled={isConfirmPending || !canConfirmOutline}
                isPending={isConfirmPending}
              />
            </div>
          )}
          {confirmOutlineHint ? <div style={errorStyle}>{confirmOutlineHint}</div> : null}
          {bindingFeedback && <div style={feedbackStyle}>{bindingFeedback}</div>}
          {confirmOutlineError && <div style={errorStyle}>Outline 确认失败：{confirmOutlineError}</div>}
          {createBindingError && <div style={errorStyle}>Outline 绑定失败：{createBindingError}</div>}
        </>
      )}
    </SectionCard>
  )
}
