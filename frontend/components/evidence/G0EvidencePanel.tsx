"use client"

import type { CSSProperties } from "react"

import { useLiteratureAssets } from "../../hooks/useLiteratureAssets"

export type G0EvidencePanelProps = Readonly<{
  systemId: string
}>

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "12px",
}

const titleStyle: CSSProperties = {
  fontSize: "14px",
  fontWeight: 700,
  color: "#f8fafc",
}

const descStyle: CSSProperties = {
  fontSize: "13px",
  color: "#94a3b8",
  lineHeight: 1.5,
}

const listStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
}

const itemStyle: CSSProperties = {
  fontSize: "13px",
  color: "#e2e8f0",
  padding: "8px 12px",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.5)",
  border: "1px solid rgba(148, 163, 184, 0.1)",
}

export function G0EvidencePanel({ systemId }: G0EvidencePanelProps) {
  const { data: assets, isLoading } = useLiteratureAssets(systemId)

  return (
    <div style={containerStyle}>
      <div style={titleStyle}>参考文献</div>
      <div style={descStyle}>
        上传的参考文献将作为结构骨架生成的输入来源。
      </div>
      {isLoading ? (
        <div style={{ fontSize: "12px", color: "#64748b" }}>加载中...</div>
      ) : !assets || assets.length === 0 ? (
        <div style={{ fontSize: "12px", color: "#64748b" }}>
          暂无文献，请在右侧工作台上传。
        </div>
      ) : (
        <div style={listStyle}>
          {assets.map((a) => (
            <div key={a.id} style={itemStyle}>{a.fileName}</div>
          ))}
        </div>
      )}
    </div>
  )
}
