"use client"

import { useState, type CSSProperties } from "react"
import type { ClaimDetail } from "../../../hooks/useEvidence"
import { ClaimRow } from "./ClaimRow"
import { ActionButton } from "../../ui/ActionButton"
import { EmptyState } from "../../ui/EmptyState"

type Props = {
  claims: ClaimDetail[]
  assetNameById: Map<string, string>
  assetOptions: Array<{ id: string; label: string }>
  onApprove: (claimId: string) => void
  onCreateEvidenceLink: (claimId: string, assetId: string) => void
  onBatchApprove: (claimIds: string[]) => void
  isApproving: boolean
  approvingClaimId?: string
  isLinking: boolean
  linkingClaimId?: string
}

const listStyle: CSSProperties = { display: "flex", flexDirection: "column", gap: "10px" }
const groupTitleStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 700,
  color: "#cbd5e1",
  textTransform: "uppercase",
  letterSpacing: "0.08em",
}
const bulkBarStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  padding: "8px 12px",
  background: "rgba(96, 165, 250, 0.08)",
  border: "1px solid rgba(96, 165, 250, 0.2)",
  borderRadius: "8px",
  marginBottom: "8px",
}

export function ClaimList({
  claims,
  assetNameById,
  assetOptions,
  onApprove,
  onCreateEvidenceLink,
  onBatchApprove,
  isApproving,
  approvingClaimId,
  isLinking,
  linkingClaimId,
}: Props) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const approved = claims.filter((c) => c.status === "approved")
  const pending = claims.filter((c) => c.status !== "approved")
  const approvablePending = pending.filter((c) => (c.evidenceLinks ?? []).length > 0)
  const allSelected = approvablePending.length > 0 && approvablePending.every((c) => selectedIds.has(c.id))

  function toggle(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function toggleAll() {
    setSelectedIds(allSelected ? new Set() : new Set(approvablePending.map((c) => c.id)))
  }

  function handleBatch() {
    onBatchApprove(Array.from(selectedIds))
    setSelectedIds(new Set())
  }

  if (claims.length === 0) return <EmptyState text="尚未生成 Claims。" />

  return (
    <div style={listStyle}>
      {selectedIds.size > 0 ? (
        <div style={bulkBarStyle}>
          <span style={{ fontSize: "12px", color: "#94a3b8" }}>已选 {selectedIds.size} 项</span>
          <ActionButton label="批量批准" onClick={handleBatch} disabled={isApproving} style={{ padding: "4px 12px", fontSize: "11px" }} />
          <ActionButton label="清除" onClick={() => setSelectedIds(new Set())} variant="secondary" style={{ padding: "4px 10px", fontSize: "11px" }} />
        </div>
      ) : null}

      {[
        { key: "approved", title: `已批准 (${approved.length})`, items: approved, showSelect: false },
        { key: "pending", title: `待处理 (${pending.length})`, items: pending, showSelect: true },
      ].map((group) => (
        <div key={group.key}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
            {group.showSelect && pending.length > 0 ? (
              <input type="checkbox" checked={allSelected} onChange={toggleAll} title="全选" />
            ) : null}
            <div style={groupTitleStyle}>{group.title}</div>
          </div>
          <div style={listStyle}>
            {group.items.map((claim) => (
              <ClaimRow
                key={claim.id}
                claim={claim}
                assetNameById={assetNameById}
                assetOptions={assetOptions}
                isApproving={isApproving && approvingClaimId === claim.id}
                isLinking={isLinking && linkingClaimId === claim.id}
                onApprove={() => onApprove(claim.id)}
                onCreateEvidenceLink={(assetId) => onCreateEvidenceLink(claim.id, assetId)}
                isSelected={selectedIds.has(claim.id)}
                onToggleSelect={() => toggle(claim.id)}
              />
            ))}
            {group.items.length === 0 ? <EmptyState text="该分组暂无 Claims。" /> : null}
          </div>
        </div>
      ))}
    </div>
  )
}
