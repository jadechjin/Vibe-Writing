"use client"

import { useCallback, useRef, useState, type CSSProperties, type DragEvent } from "react"

import {
  useDeleteFigurePlanAsset,
  useFigurePlanAssets,
  useUploadFigurePlanAsset,
} from "../../../hooks/useFigurePlanAssets"

type FigurePlanUploadProps = Readonly<{
  planId: string
}>

const dropZoneBase: CSSProperties = {
  padding: "16px",
  borderRadius: "10px",
  border: "1px dashed rgba(148,163,184,0.25)",
  textAlign: "center",
  cursor: "pointer",
  transition: "border-color 0.2s, background 0.2s",
}

const dropZoneActive: CSSProperties = {
  ...dropZoneBase,
  borderColor: "rgba(251,146,60,0.6)",
  background: "rgba(249,115,22,0.06)",
}

const gridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(80px, 1fr))",
  gap: "8px",
  marginTop: "10px",
}

const thumbWrap: CSSProperties = {
  position: "relative",
  borderRadius: "8px",
  overflow: "hidden",
  border: "1px solid rgba(148,163,184,0.12)",
  background: "rgba(15,23,42,0.5)",
  aspectRatio: "1",
}

const thumbImg: CSSProperties = {
  width: "100%",
  height: "100%",
  objectFit: "cover",
  display: "block",
}

const deleteBtn: CSSProperties = {
  position: "absolute",
  top: "2px",
  right: "2px",
  width: "18px",
  height: "18px",
  borderRadius: "50%",
  border: "none",
  background: "rgba(127,29,29,0.8)",
  color: "#fca5a5",
  fontSize: "11px",
  lineHeight: "18px",
  textAlign: "center",
  cursor: "pointer",
  padding: 0,
}

const labelStyle: CSSProperties = {
  fontSize: "11px",
  color: "#94a3b8",
  fontWeight: 600,
  marginBottom: "6px",
}

const errorStyle: CSSProperties = {
  fontSize: "11px",
  color: "#fca5a5",
  marginTop: "6px",
}

export function FigurePlanUpload({ planId }: FigurePlanUploadProps) {
  const { data: assets } = useFigurePlanAssets(planId)
  const uploadMut = useUploadFigurePlanAsset(planId)
  const deleteMut = useDeleteFigurePlanAsset(planId)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files) return
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        if (file.type.startsWith("image/")) {
          uploadMut.mutate(file)
        }
      }
    },
    [uploadMut],
  )

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      handleFiles(e.dataTransfer.files)
    },
    [handleFiles],
  )

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => setIsDragging(false), [])

  return (
    <div>
      <div style={labelStyle}>素材图片</div>
      <div
        style={isDragging ? dropZoneActive : dropZoneBase}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          style={{ display: "none" }}
          onChange={(e) => {
            handleFiles(e.target.files)
            e.target.value = ""
          }}
        />
        <div style={{ fontSize: "12px", color: isDragging ? "#fb923c" : "#64748b", pointerEvents: "none" }}>
          {uploadMut.isPending ? "上传中..." : isDragging ? "可以松开了" : "拖拽图片到此处，或点击选择"}
        </div>
      </div>

      {uploadMut.error instanceof Error ? (
        <div style={errorStyle}>上传失败：{uploadMut.error.message}</div>
      ) : null}

      {assets && assets.length > 0 ? (
        <div style={gridStyle}>
          {assets.map((asset) => (
            <div key={asset.id} style={thumbWrap}>
              {asset.previewUrl ? (
                <img src={asset.previewUrl} alt={asset.fileName} style={thumbImg} />
              ) : (
                <div style={{ ...thumbImg, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "10px", color: "#64748b" }}>
                  {asset.fileName}
                </div>
              )}
              <button
                type="button"
                style={deleteBtn}
                title="移除"
                disabled={deleteMut.isPending}
                onClick={() => deleteMut.mutate(asset.id)}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}
