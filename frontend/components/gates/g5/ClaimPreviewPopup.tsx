"use client"

import type { CSSProperties } from "react"
import type { DraftContextClaimDetail } from "../../../types/g5"

type ClaimPreviewPopupProps = Readonly<{
  claim: DraftContextClaimDetail | null
  visible: boolean
}>

const popupStyle: CSSProperties = {
  position: "absolute",
  top: "100%",
  left: 0,
  zIndex: 50,
  background: "#1e293b",
  border: "1px solid rgba(148,163,184,0.2)",
  borderRadius: "8px",
  padding: "10px 14px",
  maxWidth: "320px",
  fontSize: "12px",
  color: "#cbd5e1",
  boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
}

export function ClaimPreviewPopup({ claim, visible }: ClaimPreviewPopupProps) {
  if (!visible || !claim) return null

  return (
    <div style={popupStyle}>
      <div style={{ fontWeight: 600, marginBottom: "4px", color: "#e2e8f0" }}>
        Claim: {claim.claimId}
      </div>
      <div style={{ marginBottom: "6px" }}>{claim.statement}</div>
      {claim.assetDescriptions.length > 0 && (
        <div style={{ borderTop: "1px solid rgba(148,163,184,0.1)", paddingTop: "6px" }}>
          {claim.assetDescriptions.map((desc, i) => (
            <div key={i} style={{ fontSize: "11px", color: "#94a3b8" }}>
              {desc}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
