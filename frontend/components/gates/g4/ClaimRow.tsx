"use client"

import { useState, type CSSProperties } from "react"
import type { ClaimDetail } from "../../../hooks/useEvidence"
import { EvidenceLinkTag } from "./EvidenceLinkTag"
import { StatusBadge } from "../../ui/StatusBadge"
import { ActionButton } from "../../ui/ActionButton"

type AssetOption = {
  id: string
  label: string
}

type Props = {
  claim: ClaimDetail
  assetNameById: Map<string, string>
  assetOptions: AssetOption[]
  isApproving?: boolean
  isLinking?: boolean
  onApprove?: () => void
  onCreateEvidenceLink?: (assetId: string) => void
  isSelected?: boolean
  onToggleSelect?: () => void
}

const rowStyle: CSSProperties = {
  padding: "12px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  background: "rgba(15, 23, 42, 0.3)",
}

const headerStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "8px",
}

const titleStyle: CSSProperties = { fontSize: "13px", fontWeight: 600, color: "#e2e8f0" }
const metaStyle: CSSProperties = { fontSize: "12px", color: "#64748b", marginTop: "4px" }
const linksStyle: CSSProperties = { display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "6px" }
const fieldGroupStyle: CSSProperties = { display: "flex", flexDirection: "column", gap: "6px", marginTop: "10px" }
const fieldLabelStyle: CSSProperties = { fontSize: "11px", fontWeight: 600, color: "#cbd5e1" }
const selectStyle: CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: "8px",
  border: "1px solid rgba(148, 163, 184, 0.18)",
  background: "rgba(15, 23, 42, 0.6)",
  color: "#e2e8f0",
  fontSize: "12px",
  outline: "none",
}

const strengthBadge = (strength: string): CSSProperties => {
  const colors: Record<string, string> = { strong: "#86efac", medium: "#fde68a", weak: "#fca5a5" }
  const color = colors[strength] ?? "#94a3b8"
  return {
    fontSize: "10px",
    fontWeight: 600,
    padding: "2px 6px",
    borderRadius: "4px",
    background: `${color}20`,
    color,
  }
}

export function ClaimRow({
  claim,
  assetNameById,
  assetOptions,
  isApproving,
  isLinking,
  onApprove,
  onCreateEvidenceLink,
  isSelected,
  onToggleSelect,
}: Props) {
  const [selectedAssetId, setSelectedAssetId] = useState("")
  const isPending = claim.status !== "approved"
  const links = claim.evidenceLinks ?? []
  const overall = claim.strengthSummary?.overall
  const canApprove = links.length > 0
  const canCreateEvidenceLink = selectedAssetId.length > 0

  function handleCreateEvidenceLink() {
    if (!onCreateEvidenceLink || !canCreateEvidenceLink) return
    onCreateEvidenceLink(selectedAssetId)
    setSelectedAssetId("")
  }

  return (
    <div style={rowStyle}>
      <div style={headerStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {isPending && onToggleSelect && canApprove ? (
            <input type="checkbox" checked={isSelected} onChange={onToggleSelect} />
          ) : null}
          <div style={titleStyle}>{claim.claimId}: {claim.statement}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {overall && overall !== "none" ? <span style={strengthBadge(overall)}>{overall}</span> : null}
          <StatusBadge status={claim.status} />
        </div>
      </div>
      <div style={metaStyle}>章节：{claim.sectionRef ?? "未分配"} · 置信度：{claim.confidenceLevel}</div>
      {claim.approvedAt ? (
        <div style={metaStyle}>批准时间：{new Date(claim.approvedAt).toLocaleString()}</div>
      ) : null}
      {links.length > 0 ? (
        <div style={linksStyle}>
          {links.map((link) => (
            <EvidenceLinkTag
              key={link.id}
              assetName={assetNameById.get(link.assetId) ?? link.assetId.slice(0, 8)}
              strength={link.statisticalSupport?.strength as string | undefined}
            />
          ))}
        </div>
      ) : (
        <>
          <div style={metaStyle}>需先补充至少 1 条证据链接后再批准。</div>
          {assetOptions.length > 0 && onCreateEvidenceLink ? (
            <div style={fieldGroupStyle}>
              <label htmlFor={`claim-link-${claim.id}`} style={fieldLabelStyle}>
                绑定证据资产
              </label>
              <select
                id={`claim-link-${claim.id}`}
                style={selectStyle}
                value={selectedAssetId}
                onChange={(event) => setSelectedAssetId(event.target.value)}
              >
                <option value="">选择资产</option>
                {assetOptions.map((asset) => (
                  <option key={asset.id} value={asset.id}>
                    {asset.label}
                  </option>
                ))}
              </select>
              <ActionButton
                label={isLinking ? "绑定中..." : "创建证据链接"}
                onClick={handleCreateEvidenceLink}
                disabled={isLinking || !canCreateEvidenceLink}
                isPending={isLinking}
                variant="secondary"
              />
            </div>
          ) : (
            <div style={metaStyle}>当前没有可用资产，暂时无法补充证据链接。</div>
          )}
        </>
      )}
      {isPending && onApprove ? (
        <div style={{ marginTop: "8px" }}>
          <ActionButton
            label={isApproving ? "批准中..." : "批准 Claim"}
            onClick={onApprove}
            disabled={isApproving || !canApprove}
            isPending={isApproving}
          />
        </div>
      ) : null}
    </div>
  )
}
