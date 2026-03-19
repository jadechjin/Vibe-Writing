"use client"

import { useState, type CSSProperties } from "react"
import type { EnhancedOutlineSection } from "../../../types/g4"
import { OutlineNode } from "./OutlineNode"

type Props = {
  sections: EnhancedOutlineSection[]
}

const sectionStyle: CSSProperties = {
  padding: "12px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  background: "rgba(15, 23, 42, 0.3)",
}

const sectionHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  cursor: "pointer",
  userSelect: "none",
}

const titleStyle: CSSProperties = { fontSize: "13px", fontWeight: 600, color: "#e2e8f0" }
const metaStyle: CSSProperties = { fontSize: "11px", color: "#64748b" }
const nodesStyle: CSSProperties = { display: "flex", flexDirection: "column", gap: "6px", marginTop: "8px" }

export function OutlineTreeView({ sections }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set(sections.map((s) => s.sectionKey)))

  function toggle(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {sections.map((section, idx) => (
        <div key={`${section.sectionKey}-${idx}`} style={sectionStyle}>
          <div style={sectionHeaderStyle} onClick={() => toggle(section.sectionKey)}>
            <div style={titleStyle}>
              {expanded.has(section.sectionKey) ? "▾" : "▸"} {section.sectionKey}
            </div>
            <div style={metaStyle}>
              {(section.nodes ?? []).length} nodes · {(section.claimIds ?? []).length} claims
            </div>
          </div>
          {expanded.has(section.sectionKey) ? (
            <div style={nodesStyle}>
              {(section.nodes ?? []).map((node, i) => (
                <OutlineNode key={`${section.sectionKey}-${node.nodeType}-${i}`} node={node} />
              ))}
              {(section.nodes ?? []).length === 0 ? (
                <div style={metaStyle}>该章节暂无节点。</div>
              ) : null}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  )
}
