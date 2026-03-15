"use client"

import { type CSSProperties, useCallback, useState } from "react"
import { useParams } from "next/navigation"

import {
  useProjectDetail,
  useCreateSystem,
  useDeleteSystem,
  type CreateSystemInput,
} from "../../../hooks/useProjects"
import { ApiError } from "../../../lib/api"
import { SystemCard } from "../../../components/dashboard/SystemCard"
import { ProjectStats } from "../../../components/dashboard/ProjectStats"

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

export default function ProjectPage() {
  const params = useParams<{ projectId: string }>()
  const projectId = params.projectId
  const { data: project, isLoading, error } = useProjectDetail(projectId)
  const createSystem = useCreateSystem(projectId)
  const deleteSystem = useDeleteSystem(projectId)
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState("")
  const [deleteErrorMsg, setDeleteErrorMsg] = useState<string | null>(null)
  const [deletingSystemId, setDeletingSystemId] = useState<string | null>(null)
  const [errorSystemId, setErrorSystemId] = useState<string | null>(null)

  const handleDeleteSystem = useCallback(
    (systemId: string) => {
      setDeletingSystemId(systemId)
      setDeleteErrorMsg(null)
      setErrorSystemId(null)
      deleteSystem.mutate(systemId, {
        onSuccess: () => {
          setDeletingSystemId(null)
        },
        onError: (err: Error) => {
          const status = err instanceof ApiError ? err.status : 0
          const msg = status === 409
            ? "该体系存在关联数据，无法删除。请先移除相关资产和工作流数据。"
            : err.message
          setDeleteErrorMsg(msg)
          setErrorSystemId(systemId)
          setDeletingSystemId(null)
        },
      })
    },
    [deleteSystem],
  )

  function handleCreateSystem() {
    if (!title.trim()) {
      return
    }

    const input: CreateSystemInput = {
      title: title.trim(),
    }

    createSystem.mutate(input, {
      onSuccess: () => {
        setShowForm(false)
        setTitle("")
      },
    })
  }

  if (isLoading) {
    return <div style={emptyStyle}>加载项目中...</div>
  }

  if (error || !project) {
    return <div style={emptyStyle}>加载项目失败：{error?.message ?? "未找到"}</div>
  }

  return (
    <div style={pageStyle}>
      <div style={headerStyle}>
        <div>
          <div style={titleStyle}>{project.name}</div>
          <div style={metaStyle}>
            负责人：{project.ownerId} | 状态：{project.status} | {project.systems.length} 个实验体系
          </div>
        </div>
        <button type="button" style={createBtnStyle} onClick={() => setShowForm(true)}>
          + 新建实验体系
        </button>
      </div>

      <ProjectStats
        completedSystemCount={project.completedSystemCount}
        introductionUnlocked={project.introductionUnlocked}
        totalSystemCount={project.systems.length}
      />

      <div>
        <div style={sectionTitleStyle}>实验体系</div>
        {project.systems.length === 0 ? (
          <div style={emptyStyle}>
            暂无实验体系，创建一个开始工作流。
          </div>
        ) : (
          <div style={listStyle}>
            {project.systems.map((sys) => (
              <SystemCard
                key={sys.id}
                system={sys}
                projectId={projectId}
                onDelete={handleDeleteSystem}
                isDeleting={deletingSystemId === sys.id}
                deleteError={errorSystemId === sys.id ? deleteErrorMsg : null}
              />
            ))}
          </div>
        )}
      </div>

      {showForm ? (
        <div style={formOverlayStyle} onClick={() => setShowForm(false)}>
          <div style={formCardStyle} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontSize: "18px", fontWeight: 700, color: "#f8fafc" }}>
              创建实验体系
            </div>
            <input
              style={inputStyle}
              placeholder="体系标题"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            {createSystem.isError ? (
              <div style={{ color: "#f87171", fontSize: "13px" }}>
                {createSystem.error.message}
              </div>
            ) : null}
            <div style={formActionsStyle}>
              <button type="button" style={cancelBtnStyle} onClick={() => setShowForm(false)}>
                取消
              </button>
              <button
                type="button"
                style={submitBtnStyle}
                onClick={handleCreateSystem}
                disabled={createSystem.isPending}
              >
                {createSystem.isPending ? "创建中..." : "创建"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
