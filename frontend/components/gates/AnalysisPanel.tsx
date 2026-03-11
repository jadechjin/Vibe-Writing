import { useState, type CSSProperties } from "react"

import type { WorkflowSnapshot, Blocker } from "../../hooks/useProjectStatus"
import {
  useAssets,
  useAnalysisRuns,
  useCreateAnalysisRun,
  useUploadAsset,
} from "../../hooks/useAnalysis"
import { GateTaskStatus } from "./GateTaskStatus"

// ---- Props ----

export type GateContentPanelProps = Readonly<{
  snapshot: WorkflowSnapshot | null
  blockers: Blocker[]
  systemId: string
}>

type UploadFormState = {
  assetType: string
  fileName: string
  storageKey: string
  mimeType: string
  uploadedBy: string
}

const INITIAL_UPLOAD_FORM: UploadFormState = {
  assetType: "figure",
  fileName: "",
  storageKey: "",
  mimeType: "",
  uploadedBy: "workspace-user",
}

// ---- Styles ----

const panelStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "14px",
}

const sectionCardStyle: CSSProperties = {
  padding: "16px",
  borderRadius: "14px",
  border: "1px solid rgba(148, 163, 184, 0.15)",
  background: "rgba(30, 41, 59, 0.38)",
}

const titleStyle: CSSProperties = {
  fontSize: "15px",
  fontWeight: 700,
  color: "#f8fafc",
  marginBottom: "8px",
}

const descStyle: CSSProperties = {
  fontSize: "13px",
  lineHeight: 1.6,
  color: "#94a3b8",
}

const blockerListStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
  marginTop: "8px",
}

const blockerItemStyle: CSSProperties = {
  padding: "8px 12px",
  borderRadius: "8px",
  border: "1px solid rgba(248, 113, 113, 0.2)",
  background: "rgba(127, 29, 29, 0.1)",
  fontSize: "12px",
  color: "#fca5a5",
}

const actionBtnStyle: CSSProperties = {
  padding: "8px 18px",
  borderRadius: "10px",
  border: "1px solid rgba(249, 115, 22, 0.5)",
  background: "rgba(154, 52, 18, 0.15)",
  fontSize: "13px",
  fontWeight: 600,
  color: "#fb923c",
  cursor: "pointer",
  alignSelf: "flex-start",
}

const statusBadgeStyle: CSSProperties = {
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: "6px",
  fontSize: "11px",
  fontWeight: 600,
  background: "rgba(249, 115, 22, 0.15)",
  color: "#fb923c",
  marginLeft: "8px",
}

const subTitleStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 700,
  color: "#cbd5e1",
  marginTop: "12px",
  marginBottom: "6px",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
}

const tableStyle: CSSProperties = {
  width: "100%",
  fontSize: "12px",
  borderCollapse: "collapse",
  marginTop: "8px",
}

const thStyle: CSSProperties = {
  textAlign: "left",
  padding: "6px 8px",
  borderBottom: "1px solid rgba(148, 163, 184, 0.1)",
  color: "#64748b",
}

const tdStyle: CSSProperties = {
  padding: "8px",
  borderBottom: "1px solid rgba(148, 163, 184, 0.05)",
  color: "#e2e8f0",
}

const emptyStateStyle: CSSProperties = {
  padding: "12px",
  textAlign: "center",
  color: "#64748b",
  fontSize: "12px",
  fontStyle: "italic",
}

const formGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: "10px",
  marginTop: "10px",
}

const fieldGroupStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
}

const fieldLabelStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 600,
  color: "#cbd5e1",
}

const inputStyle: CSSProperties = {
  width: "100%",
  padding: "9px 10px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.18)",
  background: "rgba(15, 23, 42, 0.6)",
  color: "#e2e8f0",
  fontSize: "13px",
  outline: "none",
}

const helperTextStyle: CSSProperties = {
  marginTop: "8px",
  fontSize: "12px",
  lineHeight: 1.5,
  color: "#94a3b8",
}

const errorTextStyle: CSSProperties = {
  marginTop: "8px",
  fontSize: "12px",
  color: "#fca5a5",
}

function normalizeText(value: string): string {
  return value.trim()
}

function describeAssetStatus(qcStatus: string | undefined): string {
  if (!qcStatus) {
    return "Metadata pending"
  }

  if (qcStatus === "confirmed" || qcStatus === "approved") {
    return `QC ${qcStatus}`
  }

  return `QC ${qcStatus}`
}

// ---- Component ----

export function AnalysisPanel({ systemId, snapshot, blockers }: GateContentPanelProps) {
  const currentState = snapshot?.currentState ?? null
  const [uploadForm, setUploadForm] = useState<UploadFormState>(INITIAL_UPLOAD_FORM)

  const { data: assets, isLoading: assetsLoading, error: assetsError } = useAssets(systemId)
  const { data: runs, isLoading: runsLoading, error: runsError } = useAnalysisRuns(systemId)
  const uploadAsset = useUploadAsset(systemId)
  const createRun = useCreateAnalysisRun(systemId)

  const canSubmitUpload =
    normalizeText(uploadForm.assetType).length > 0 &&
    normalizeText(uploadForm.fileName).length > 0 &&
    normalizeText(uploadForm.storageKey).length > 0 &&
    normalizeText(uploadForm.uploadedBy).length > 0 &&
    !uploadAsset.isPending

  const uploadErrorMessage = uploadAsset.error instanceof Error ? uploadAsset.error.message : null
  const createRunErrorMessage = createRun.error instanceof Error ? createRun.error.message : null

  function updateUploadForm<K extends keyof UploadFormState>(key: K, value: UploadFormState[K]) {
    setUploadForm((prev) => ({ ...prev, [key]: value }))
  }

  function handleUploadAsset() {
    if (!canSubmitUpload) {
      return
    }

    uploadAsset.mutate(
      {
        assetType: normalizeText(uploadForm.assetType),
        fileName: normalizeText(uploadForm.fileName),
        storageKey: normalizeText(uploadForm.storageKey),
        mimeType: normalizeText(uploadForm.mimeType) || undefined,
        uploadedBy: normalizeText(uploadForm.uploadedBy),
      },
      {
        onSuccess: () => {
          setUploadForm((prev) => ({
            ...prev,
            fileName: "",
            storageKey: "",
            mimeType: "",
          }))
        },
      },
    )
  }

  return (
    <div style={panelStyle}>
      <GateTaskStatus systemId={systemId} gateKey="G2" />
      <div style={sectionCardStyle}>
        <div style={titleStyle}>
          Data &amp; Analysis
          {currentState ? <span style={statusBadgeStyle}>{currentState}</span> : null}
        </div>
        <div style={descStyle}>
          上传实验数据、触发分析任务。分析完成后可推进至资产确认。
        </div>

        <div style={subTitleStyle}>Record Uploaded Asset</div>
        <div style={helperTextStyle}>
          当前接口记录资产条目而不是直接上传二进制文件。请填写文件名、存储路径和资产类型。
        </div>
        <div style={formGridStyle}>
          <div style={fieldGroupStyle}>
            <label style={fieldLabelStyle}>Asset Type</label>
            <input
              value={uploadForm.assetType}
              onChange={(event) => updateUploadForm("assetType", event.target.value)}
              placeholder="figure"
              style={inputStyle}
            />
          </div>
          <div style={fieldGroupStyle}>
            <label style={fieldLabelStyle}>File Name</label>
            <input
              value={uploadForm.fileName}
              onChange={(event) => updateUploadForm("fileName", event.target.value)}
              placeholder="figure-1.png"
              style={inputStyle}
            />
          </div>
          <div style={fieldGroupStyle}>
            <label style={fieldLabelStyle}>Storage Key</label>
            <input
              value={uploadForm.storageKey}
              onChange={(event) => updateUploadForm("storageKey", event.target.value)}
              placeholder="uploads/figure-1.png"
              style={inputStyle}
            />
          </div>
          <div style={fieldGroupStyle}>
            <label style={fieldLabelStyle}>MIME Type</label>
            <input
              value={uploadForm.mimeType}
              onChange={(event) => updateUploadForm("mimeType", event.target.value)}
              placeholder="image/png"
              style={inputStyle}
            />
          </div>
          <div style={fieldGroupStyle}>
            <label style={fieldLabelStyle}>Uploaded By</label>
            <input
              value={uploadForm.uploadedBy}
              onChange={(event) => updateUploadForm("uploadedBy", event.target.value)}
              placeholder="workspace-user"
              style={inputStyle}
            />
          </div>
        </div>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "12px" }}>
          <button
            type="button"
            style={actionBtnStyle}
            onClick={handleUploadAsset}
            disabled={!canSubmitUpload}
          >
            {uploadAsset.isPending ? "Adding Asset..." : "Add Asset"}
          </button>
        </div>
        {uploadErrorMessage ? <div style={errorTextStyle}>Asset upload failed: {uploadErrorMessage}</div> : null}

        <div style={subTitleStyle}>Uploaded Assets</div>
        {assetsLoading ? (
          <div style={emptyStateStyle}>Loading assets...</div>
        ) : assetsError ? (
          <div style={{ ...emptyStateStyle, color: "#fca5a5" }}>
            Error loading assets: {assetsError instanceof Error ? assetsError.message : "Unknown error"}
          </div>
        ) : !assets || assets.length === 0 ? (
          <div style={emptyStateStyle}>No assets uploaded yet.</div>
        ) : (
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>File Name</th>
                <th style={thStyle}>Type</th>
                <th style={thStyle}>Status</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => (
                <tr key={asset.id}>
                  <td style={tdStyle}>{asset.fileName}</td>
                  <td style={tdStyle}>{asset.assetType}</td>
                  <td style={tdStyle}>{describeAssetStatus(asset.metadataEntry?.qcStatus)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div style={subTitleStyle}>Analysis Runs</div>
        <div style={helperTextStyle}>
          当前面板仅展示分析任务状态。G2 的完成以真实后端分析结果为准，不在这里提供手动完成入口。
        </div>
        {runsLoading ? (
          <div style={emptyStateStyle}>Loading runs...</div>
        ) : runsError ? (
          <div style={{ ...emptyStateStyle, color: "#fca5a5" }}>
            Error loading runs: {runsError instanceof Error ? runsError.message : "Unknown error"}
          </div>
        ) : !runs || runs.length === 0 ? (
          <div style={emptyStateStyle}>No analysis runs yet.</div>
        ) : (
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Type</th>
                <th style={thStyle}>Status</th>
                <th style={thStyle}>Summary</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td style={tdStyle}>{run.runType}</td>
                  <td style={tdStyle}>{run.status}</td>
                  <td style={tdStyle}>{run.summary || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" as const }}>
        <button
          type="button"
          style={actionBtnStyle}
          onClick={() => createRun.mutate()}
          disabled={createRun.isPending}
        >
          {createRun.isPending ? "Creating Run..." : "Create Analysis Run"}
        </button>
      </div>
      {createRunErrorMessage ? <div style={errorTextStyle}>Analysis run creation failed: {createRunErrorMessage}</div> : null}

      {blockers.length > 0 ? (
        <div style={sectionCardStyle}>
          <div style={{ ...titleStyle, fontSize: "13px", color: "#fca5a5" }}>
            Blockers ({blockers.length})
          </div>
          <div style={blockerListStyle}>
            {blockers.map((b, i) => (
              <div key={`${b.code}-${i}`} style={blockerItemStyle}>
                <strong>{b.code}</strong>: {b.message}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
