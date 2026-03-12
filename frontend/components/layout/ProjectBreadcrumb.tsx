"use client"

import { type CSSProperties } from "react"
import { useParams } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"

import type { ProjectDetail } from "../../hooks/useProjects"

const navStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "6px",
  fontSize: "13px",
  color: "#94a3b8",
  marginBottom: "16px",
}

const linkStyle: CSSProperties = {
  color: "#60a5fa",
  textDecoration: "none",
}

const separatorStyle: CSSProperties = {
  color: "#475569",
}

const currentStyle: CSSProperties = {
  color: "#e2e8f0",
  fontWeight: 500,
}

export function ProjectBreadcrumb({ projectId }: { projectId: string }) {
  const params = useParams<{ systemId?: string }>()
  const systemId = params.systemId ?? null
  const queryClient = useQueryClient()

  const project = queryClient.getQueryData<ProjectDetail>(["projects", projectId])
  const projectLabel = project?.name ?? "Project"

  const system = systemId
    ? project?.systems.find((s) => s.id === systemId)
    : null
  const systemLabel = system
    ? `#${system.systemNo} ${system.title}`
    : null

  return (
    <nav style={navStyle}>
      <a href="/projects" style={linkStyle}>Projects</a>
      <span style={separatorStyle}>/</span>
      {systemId ? (
        <>
          <a href={`/projects/${projectId}`} style={linkStyle}>{projectLabel}</a>
          <span style={separatorStyle}>/</span>
          <span style={currentStyle}>{systemLabel ?? "System"}</span>
        </>
      ) : (
        <span style={currentStyle}>{projectLabel}</span>
      )}
    </nav>
  )
}
