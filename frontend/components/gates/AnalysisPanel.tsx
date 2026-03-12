import { useState, type CSSProperties } from "react"

import type { WorkflowSnapshot, Blocker } from "../../hooks/useProjectStatus"
import {
  useAssets,
  useAnalysisRuns,
  useCreateAnalysisRun,
  useUploadAsset,
} from "../../hooks/useAnalysis"
import { gateTheme } from "../../styles/gate-theme"
import { ActionButton } from "../ui/ActionButton"
import { EmptyState } from "../ui/EmptyState"
import { SectionCard } from "../ui/SectionCard"
import { StatusBadge } from "../ui/StatusBadge"
import { GateTaskStatus } from "./GateTaskStatus"

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

const formGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: "10px",
  marginTop: "10px",
}

const fieldLabelStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 600,
  color: "#cbd5e1",
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

function normalizeText(value: string): string {
  return value.trim()
}

function describeAssetStatus(qcStatus: string | undefined): string {
  if (!qcStatus) return "Metadata pending"
  return `QC ${qcStatus}`
}

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
    if (!canSubmitUpload) return

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
          setUploadForm((prev) => ({ ...prev, fileName: "", storageKey: "", mimeType: "" }))
        },
      },
    )
  }

  return (
    <div style={gateTheme.panel}>
      <GateTaskStatus systemId={systemId} gateKey="G2" />
      <SectionCard
        title={
          <span>
            Data &amp; Analysis
            {currentState ? <StatusBadge status={currentState} style={{ marginLeft: "8px" }} /> : null}
          </span>
        }
        description="上传实验数据、触发分析任务。分析完成后可推进至资产确认。"
      >
        <div style={subTitleStyle}>Record Uploaded Asset</div>
        <div style={helperTextStyle}>
          当前接口记录资产条目而不是直接上传二进制文件。请填写文件名、存储路径和资产类型。
        </div>
        <div style={formGridStyle}>
          {(["assetType", "fileName", "storageKey", "mimeType", "uploadedBy"] as const).map((key) => (
            <div key={key} style={gateTheme.fieldGroup}>
              <label style={fieldLabelStyle}>{key === "assetType" ? "Asset Type" : key === "fileName" ? "File Name" : key === "storageKey" ? "Storage Key" : key === "mimeType" ? "MIME Type" : "Uploaded By"}</label>
              <input
                value={uploadForm[key]}
                onChange={(event) => updateUploadForm(key, event.target.value)}
                placeholder={key === "assetType" ? "figure" : key === "fileName" ? "figure-1.png" : key === "storageKey" ? "uploads/figure-1.png" : key === "mimeType" ? "image/png" : "workspace-user"}
                style={gateTheme.input}
              />
            </div>
          ))}
        </div>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" as const, marginTop: "12px" }}>
          <ActionButton
            label={uploadAsset.isPending ? "Adding Asset..." : "Add Asset"}
            onClick={handleUploadAsset}
            disabled={!canSubmitUpload}
            isPending={uploadAsset.isPending}
          />
        </div>
        {uploadErrorMessage ? <div style={errorTextStyle}>Asset upload failed: {uploadErrorMessage}</div> : null}

        <div style={subTitleStyle}>Uploaded Assets</div>
        {assetsLoading ? (
          <EmptyState text="Loading assets..." />
        ) : assetsError ? (
          <EmptyState text={`Error loading assets: ${assetsError instanceof Error ? assetsError.message : "Unknown error"}`} style={{ color: "#fca5a5" }} />
        ) : !assets || assets.length === 0 ? (
          <EmptyState text="No assets uploaded yet." />
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
          <EmptyState text="Loading runs..." />
        ) : runsError ? (
          <EmptyState text={`Error loading runs: ${runsError instanceof Error ? runsError.message : "Unknown error"}`} style={{ color: "#fca5a5" }} />
        ) : !runs || runs.length === 0 ? (
          <EmptyState text="No analysis runs yet." />
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
      </SectionCard>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" as const }}>
        <ActionButton
          label={createRun.isPending ? "Creating Run..." : "Create Analysis Run"}
          onClick={() => createRun.mutate()}
          disabled={createRun.isPending}
          isPending={createRun.isPending}
        />
      </div>
      {createRunErrorMessage ? <div style={errorTextStyle}>Analysis run creation failed: {createRunErrorMessage}</div> : null}

      {blockers.length > 0 ? (
        <SectionCard title={<span style={{ fontSize: "13px", color: "#fca5a5" }}>Blockers ({blockers.length})</span>}>
          <div style={blockerListStyle}>
            {blockers.map((b, i) => (
              <div key={`${b.code}-${i}`} style={blockerItemStyle}>
                <strong>{b.code}</strong>: {b.message}
              </div>
            ))}
          </div>
        </SectionCard>
      ) : null}
    </div>
  )
}
