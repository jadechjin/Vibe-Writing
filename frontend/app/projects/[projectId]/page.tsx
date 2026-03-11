"use client"

import { type CSSProperties, useState } from "react"
import { useParams } from "next/navigation"

import {
  useProjectDetail,
  useCreateSystem,
  type CreateSystemInput,
} from "../../../hooks/useProjects"

const containerStyle: CSSProperties = {
  minHeight: "100vh",
  background:
    "radial-gradient(circle at top, rgba(30, 64, 175, 0.18), transparent 34%), linear-gradient(180deg, #020617 0%, #0f172a 56%, #111827 100%)",
  color: "#e2e8f0",
  padding: "32px 24px",
  maxWidth: "1440px",
  margin: "0 auto",
}

const pageStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "24px",
}

const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "flex-start",
  justifyContent: "space-between",
  gap: "16px",
}

const titleStyle: CSSProperties = {
  fontSize: "22px",
  fontWeight: 700,
  color: "#f8fafc",
}

const metaStyle: CSSProperties = {
  fontSize: "13px",
  color: "#94a3b8",
  marginTop: "4px",
}

const backLinkStyle: CSSProperties = {
  fontSize: "13px",
  color: "#60a5fa",
  textDecoration: "none",
  marginBottom: "4px",
  display: "inline-block",
}

const sectionTitleStyle: CSSProperties = {
  fontSize: "16px",
  fontWeight: 600,
  color: "#e2e8f0",
  marginBottom: "12px",
}

const listStyle: CSSProperties = {
  display: "grid",
  gap: "10px",
}

const systemCardStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "12px",
  padding: "16px 18px",
  borderRadius: "14px",
  border: "1px solid rgba(148, 163, 184, 0.16)",
  background: "rgba(15, 23, 42, 0.6)",
  cursor: "pointer",
  textDecoration: "none",
  color: "inherit",
}

const systemNameStyle: CSSProperties = {
  fontSize: "15px",
  fontWeight: 600,
  color: "#f8fafc",
}

const systemMetaStyle: CSSProperties = {
  fontSize: "12px",
  color: "#94a3b8",
}

const badgeStyle: CSSProperties = {
  padding: "4px 10px",
  borderRadius: "8px",
  fontSize: "11px",
  fontWeight: 600,
  background: "rgba(249, 115, 22, 0.15)",
  color: "#fb923c",
  border: "1px solid rgba(249, 115, 22, 0.3)",
}

const createBtnStyle: CSSProperties = {
  padding: "10px 20px",
  borderRadius: "12px",
  border: "1px solid rgba(59, 130, 246, 0.6)",
  background: "rgba(30, 64, 175, 0.3)",
  color: "#93c5fd",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
}

const emptyStyle: CSSProperties = {
  textAlign: "center",
  padding: "36px 24px",
  color: "#64748b",
  fontSize: "14px",
}

const formOverlayStyle: CSSProperties = {
  position: "fixed",
  inset: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "rgba(0, 0, 0, 0.6)",
  zIndex: 100,
}

const formCardStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "14px",
  padding: "28px",
  borderRadius: "20px",
  border: "1px solid rgba(148, 163, 184, 0.2)",
  background: "#0f172a",
  minWidth: "380px",
  maxWidth: "480px",
}

const inputStyle: CSSProperties = {
  padding: "10px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.25)",
  background: "rgba(15, 23, 42, 0.8)",
  color: "#e2e8f0",
  fontSize: "14px",
  outline: "none",
}

const textareaStyle: CSSProperties = {
  ...inputStyle,
  minHeight: "60px",
  resize: "vertical" as const,
  fontFamily: "inherit",
}

const formActionsStyle: CSSProperties = {
  display: "flex",
  gap: "10px",
  justifyContent: "flex-end",
}

const cancelBtnStyle: CSSProperties = {
  padding: "8px 16px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.2)",
  background: "transparent",
  color: "#94a3b8",
  fontSize: "14px",
  cursor: "pointer",
}

const submitBtnStyle: CSSProperties = {
  padding: "8px 16px",
  borderRadius: "10px",
  border: "1px solid rgba(59, 130, 246, 0.6)",
  background: "rgba(30, 64, 175, 0.4)",
  color: "#93c5fd",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
}

const infoRowStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "12px",
}

const infoBlockStyle: CSSProperties = {
  padding: "14px 16px",
  borderRadius: "12px",
  border: "1px solid rgba(148, 163, 184, 0.12)",
  background: "rgba(15, 23, 42, 0.5)",
}

const infoLabelStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  color: "#94a3b8",
  marginBottom: "4px",
}

const infoValueStyle: CSSProperties = {
  fontSize: "14px",
  color: "#e2e8f0",
}

export default function ProjectPage() {
  const params = useParams<{ projectId: string }>()
  const projectId = params.projectId
  const { data: project, isLoading, error } = useProjectDetail(projectId)
  const createSystem = useCreateSystem(projectId)
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState("")
  const [researchGoal, setResearchGoal] = useState("")

  function handleCreateSystem() {
    if (!title.trim()) {
      return
    }

    const input: CreateSystemInput = {
      title: title.trim(),
      researchGoal: researchGoal.trim() || null,
    }

    createSystem.mutate(input, {
      onSuccess: () => {
        setShowForm(false)
        setTitle("")
        setResearchGoal("")
      },
    })
  }

  if (isLoading) {
    return <div style={containerStyle}><div style={emptyStyle}>Loading project...</div></div>
  }

  if (error || !project) {
    return <div style={containerStyle}><div style={emptyStyle}>Failed to load project: {error?.message ?? "Not found"}</div></div>
  }

  return (
    <div style={containerStyle}>
    <div style={pageStyle}>
      <a href="/projects" style={backLinkStyle}>
        &larr; All Projects
      </a>

      <div style={headerStyle}>
        <div>
          <div style={titleStyle}>{project.name}</div>
          <div style={metaStyle}>
            Owner: {project.ownerId} | Status: {project.status} | {project.systems.length} system{project.systems.length !== 1 ? "s" : ""}
          </div>
        </div>
        <button type="button" style={createBtnStyle} onClick={() => setShowForm(true)}>
          + New System
        </button>
      </div>

      <div style={infoRowStyle}>
        <div style={infoBlockStyle}>
          <div style={infoLabelStyle}>Project ID</div>
          <div style={infoValueStyle}>{project.id}</div>
        </div>
        <div style={infoBlockStyle}>
          <div style={infoLabelStyle}>Created</div>
          <div style={infoValueStyle}>{new Date(project.createdAt).toLocaleDateString()}</div>
        </div>
      </div>

      <div>
        <div style={sectionTitleStyle}>Experimental Systems</div>
        {project.systems.length === 0 ? (
          <div style={emptyStyle}>
            No experimental systems yet. Create one to start the workflow.
          </div>
        ) : (
          <div style={listStyle}>
            {project.systems.map((sys) => (
              <a
                key={sys.id}
                href={`/projects/${projectId}/systems/${sys.id}`}
                style={systemCardStyle}
              >
                <div>
                  <div style={systemNameStyle}>
                    #{sys.systemNo} {sys.title}
                  </div>
                  <div style={systemMetaStyle}>
                    {sys.sectionCount} section{sys.sectionCount !== 1 ? "s" : ""}
                  </div>
                </div>
                <span style={badgeStyle}>{sys.status}</span>
              </a>
            ))}
          </div>
        )}
      </div>

      {showForm ? (
        <div style={formOverlayStyle} onClick={() => setShowForm(false)}>
          <div style={formCardStyle} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontSize: "18px", fontWeight: 700, color: "#f8fafc" }}>
              Create Experimental System
            </div>
            <input
              style={inputStyle}
              placeholder="System title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <textarea
              style={textareaStyle}
              placeholder="Research goal (optional)"
              value={researchGoal}
              onChange={(e) => setResearchGoal(e.target.value)}
            />
            {createSystem.isError ? (
              <div style={{ color: "#f87171", fontSize: "13px" }}>
                {createSystem.error.message}
              </div>
            ) : null}
            <div style={formActionsStyle}>
              <button type="button" style={cancelBtnStyle} onClick={() => setShowForm(false)}>
                Cancel
              </button>
              <button
                type="button"
                style={submitBtnStyle}
                onClick={handleCreateSystem}
                disabled={createSystem.isPending}
              >
                {createSystem.isPending ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
    </div>
  )
}
