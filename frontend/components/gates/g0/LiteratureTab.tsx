"use client"

import { useRef, useState, type CSSProperties } from "react"

import { useDeleteLiteratureAsset, useLiteratureAssets, useUploadAsset } from "../../../hooks/useLiteratureAssets"

// ---- Props ----

export type LiteratureTabProps = Readonly<{
  systemId: string
  isReadOnly: boolean
}>

// ---- Styles ----

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "14px",
}

const headerStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
}

const titleStyle: CSSProperties = {
  fontSize: "14px",
  fontWeight: 700,
  color: "#f8fafc",
}

const uploadBtnStyle: CSSProperties = {
  padding: "6px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(249, 115, 22, 0.5)",
  background: "rgba(154, 52, 18, 0.15)",
  fontSize: "12px",
  fontWeight: 600,
  color: "#fb923c",
  cursor: "pointer",
}

const uploadBtnDisabledStyle: CSSProperties = {
  ...uploadBtnStyle,
  opacity: 0.4,
  cursor: "not-allowed",
}

const listStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "8px",
}

const itemStyle: CSSProperties = {
  padding: "10px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.15)",
  background: "rgba(15, 23, 42, 0.5)",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
}

const fileNameStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  color: "#e2e8f0",
}

const metaStyle: CSSProperties = {
  fontSize: "11px",
  color: "#64748b",
}

const emptyStyle: CSSProperties = {
  fontSize: "13px",
  color: "#64748b",
  textAlign: "center",
  padding: "24px 0",
}

const feedbackStyle: CSSProperties = {
  fontSize: "12px",
  padding: "6px 10px",
  borderRadius: "8px",
}

const deleteBtnStyle: CSSProperties = {
  padding: "4px 10px",
  borderRadius: "8px",
  border: "1px solid rgba(239, 68, 68, 0.3)",
  background: "transparent",
  fontSize: "11px",
  fontWeight: 600,
  color: "#f87171",
  cursor: "pointer",
}

// ---- Component ----

export function LiteratureTab({ systemId, isReadOnly }: LiteratureTabProps) {
  const { data: assets, isLoading } = useLiteratureAssets(systemId)
  const uploadMutation = useUploadAsset(systemId)
  const deleteMutation = useDeleteLiteratureAsset(systemId)
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; msg: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function handleUploadClick() {
    fileInputRef.current?.click()
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    const storageKey = `ref_lit_${Date.now()}`
    uploadMutation.mutate(
      {
        assetType: "reference_literature",
        fileName: file.name,
        storageKey,
        mimeType: file.type || undefined,
        uploadedBy: "user",
      },
      {
        onSuccess: () => {
          setFeedback({ type: "success", msg: "文献上传成功" })
          setTimeout(() => setFeedback(null), 3000)
        },
        onError: () => {
          setFeedback({ type: "error", msg: "上传失败，请重试" })
          setTimeout(() => setFeedback(null), 5000)
        },
      },
    )

    // reset so the same file can be re-selected
    e.target.value = ""
  }

  function handleDelete(assetId: string, fileName: string) {
    if (!confirm(`确定删除「${fileName}」？`)) return
    deleteMutation.mutate(assetId, {
      onSuccess: () => {
        setFeedback({ type: "success", msg: "已删除" })
        setTimeout(() => setFeedback(null), 2000)
      },
      onError: () => {
        setFeedback({ type: "error", msg: "删除失败，请重试" })
        setTimeout(() => setFeedback(null), 5000)
      },
    })
  }

  const canUpload = !isReadOnly && !uploadMutation.isPending

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <div style={titleStyle}>参考文献 ({assets?.length ?? 0})</div>
        {!isReadOnly ? (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.doc,.docx,.txt,.bib,.ris"
              style={{ display: "none" }}
              onChange={handleFileChange}
            />
            <button
              type="button"
              onClick={handleUploadClick}
              disabled={!canUpload}
              style={canUpload ? uploadBtnStyle : uploadBtnDisabledStyle}
            >
              {uploadMutation.isPending ? "上传中..." : "上传文献"}
            </button>
          </>
        ) : null}
      </div>

      {feedback ? (
        <div
          style={{
            ...feedbackStyle,
            color: feedback.type === "success" ? "#4ade80" : "#f87171",
            background: feedback.type === "success" ? "rgba(22, 101, 52, 0.15)" : "rgba(127, 29, 29, 0.15)",
          }}
        >
          {feedback.msg}
        </div>
      ) : null}

      {isLoading ? (
        <div style={emptyStyle}>加载中...</div>
      ) : !assets || assets.length === 0 ? (
        <div style={emptyStyle}>暂无参考文献，请上传文献资料</div>
      ) : (
        <div style={listStyle}>
          {assets.map((asset) => (
            <div key={asset.id} style={itemStyle}>
              <div style={fileNameStyle}>{asset.fileName}</div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={metaStyle}>
                  v{asset.version} · {new Date(asset.createdAt).toLocaleDateString("zh-CN")}
                </div>
                {!isReadOnly ? (
                  <button
                    type="button"
                    onClick={() => handleDelete(asset.id, asset.fileName)}
                    disabled={deleteMutation.isPending}
                    style={deleteBtnStyle}
                  >
                    删除
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
