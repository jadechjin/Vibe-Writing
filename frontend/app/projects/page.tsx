"use client"

import { type CSSProperties, useState } from "react"

import { useProjectList, useCreateProject, type CreateProjectInput } from "../../hooks/useProjects"

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
  alignItems: "center",
  justifyContent: "space-between",
  gap: "16px",
}

const titleStyle: CSSProperties = {
  fontSize: "22px",
  fontWeight: 700,
  color: "#f8fafc",
}

const subtitleStyle: CSSProperties = {
  fontSize: "14px",
  color: "#94a3b8",
  marginTop: "4px",
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

const listStyle: CSSProperties = {
  display: "grid",
  gap: "12px",
}

const cardStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "16px",
  padding: "18px 20px",
  borderRadius: "16px",
  border: "1px solid rgba(148, 163, 184, 0.16)",
  background: "rgba(15, 23, 42, 0.6)",
  cursor: "pointer",
  textDecoration: "none",
  color: "inherit",
}

const cardNameStyle: CSSProperties = {
  fontSize: "16px",
  fontWeight: 600,
  color: "#f8fafc",
}

const cardMetaStyle: CSSProperties = {
  fontSize: "13px",
  color: "#94a3b8",
}

const badgeStyle: CSSProperties = {
  padding: "4px 12px",
  borderRadius: "8px",
  fontSize: "12px",
  fontWeight: 600,
  background: "rgba(59, 130, 246, 0.15)",
  color: "#60a5fa",
  border: "1px solid rgba(59, 130, 246, 0.3)",
}

const emptyStyle: CSSProperties = {
  textAlign: "center",
  padding: "48px 24px",
  color: "#64748b",
  fontSize: "15px",
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
  gap: "16px",
  padding: "28px",
  borderRadius: "20px",
  border: "1px solid rgba(148, 163, 184, 0.2)",
  background: "#0f172a",
  minWidth: "360px",
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

export default function ProjectsPage() {
  const { data: projects, isLoading, error } = useProjectList()
  const createProject = useCreateProject()
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState("")
  const [ownerId, setOwnerId] = useState("")

  function handleCreate() {
    if (!name.trim() || !ownerId.trim()) {
      return
    }

    const input: CreateProjectInput = {
      name: name.trim(),
      ownerId: ownerId.trim(),
    }

    createProject.mutate(input, {
      onSuccess: () => {
        setShowForm(false)
        setName("")
        setOwnerId("")
      },
    })
  }

  if (isLoading) {
    return <div style={containerStyle}><div style={emptyStyle}>Loading projects...</div></div>
  }

  if (error) {
    return <div style={containerStyle}><div style={emptyStyle}>Failed to load projects: {error.message}</div></div>
  }

  return (
    <div style={containerStyle}>
    <div style={pageStyle}>
      <div style={headerStyle}>
        <div>
          <div style={titleStyle}>Projects</div>
          <div style={subtitleStyle}>Select a project to enter its workspace</div>
        </div>
        <button type="button" style={createBtnStyle} onClick={() => setShowForm(true)}>
          + New Project
        </button>
      </div>

      {!projects || projects.length === 0 ? (
        <div style={emptyStyle}>No projects yet. Create one to get started.</div>
      ) : (
        <div style={listStyle}>
          {projects.map((project) => (
            <a
              key={project.id}
              href={`/projects/${project.id}`}
              style={cardStyle}
            >
              <div>
                <div style={cardNameStyle}>{project.name}</div>
                <div style={cardMetaStyle}>
                  {project.systemCount} system{project.systemCount !== 1 ? "s" : ""} | Owner: {project.ownerId}
                </div>
              </div>
              <span style={badgeStyle}>{project.status}</span>
            </a>
          ))}
        </div>
      )}

      {showForm ? (
        <div style={formOverlayStyle} onClick={() => setShowForm(false)}>
          <div style={formCardStyle} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontSize: "18px", fontWeight: 700, color: "#f8fafc" }}>
              Create Project
            </div>
            <input
              style={inputStyle}
              placeholder="Project name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <input
              style={inputStyle}
              placeholder="Owner ID"
              value={ownerId}
              onChange={(e) => setOwnerId(e.target.value)}
            />
            {createProject.isError ? (
              <div style={{ color: "#f87171", fontSize: "13px" }}>
                {createProject.error.message}
              </div>
            ) : null}
            <div style={formActionsStyle}>
              <button type="button" style={cancelBtnStyle} onClick={() => setShowForm(false)}>
                Cancel
              </button>
              <button
                type="button"
                style={submitBtnStyle}
                onClick={handleCreate}
                disabled={createProject.isPending}
              >
                {createProject.isPending ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
    </div>
  )
}
