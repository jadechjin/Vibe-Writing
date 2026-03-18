"use client"

import { useState, type CSSProperties, type ReactNode } from "react"

type TraceableTextProps = Readonly<{
  content: string
  onClaimHover?: (claimTag: string | null) => void
}>

const CLAIM_RE = /\[Claim:([^\]]+)\]/g

const tagStyle: CSSProperties = {
  background: "rgba(59,130,246,0.15)",
  borderBottom: "2px solid #3b82f6",
  cursor: "pointer",
  padding: "0 2px",
  borderRadius: "2px",
}

export function TraceableText({ content, onClaimHover }: TraceableTextProps) {
  const parts: ReactNode[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  const re = new RegExp(CLAIM_RE.source, "g")
  while ((match = re.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index))
    }
    const tag = match[1]
    parts.push(
      <span
        key={match.index}
        style={tagStyle}
        onMouseEnter={() => onClaimHover?.(tag)}
        onMouseLeave={() => onClaimHover?.(null)}
        title={`Claim: ${tag}`}
      >
        {match[0]}
      </span>,
    )
    lastIndex = re.lastIndex
  }
  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex))
  }

  return <span style={{ whiteSpace: "pre-wrap" }}>{parts}</span>
}
