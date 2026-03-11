import { useMemo, useState, type CSSProperties } from "react"

import type { AssetDetail } from "../../hooks/useAnalysis"
import { useAssets, useBindAssetMetadata } from "../../hooks/useAnalysis"
import type { WorkflowSnapshot, Blocker } from "../../hooks/useProjectStatus"
import {
  useManifest,
  useGenerateManifest,
  useConfirmManifest,
  useConfirmAssetQC,
} from "../../hooks/useManifest"
import { GateTaskStatus } from "./GateTaskStatus"

// ---- Props ----

export type GateContentPanelProps = Readonly<{
  snapshot: WorkflowSnapshot | null
  blockers: Blocker[]
  systemId: string
}>

type MetadataDraft = {
  semanticDescription: string
  sourceDescription: string
  instrumentInfo: string
  sampleIds: string
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
  verticalAlign: "top",
}

const emptyStateStyle: CSSProperties = {
  padding: "12px",
  textAlign: "center",
  color: "#64748b",
  fontSize: "12px",
  fontStyle: "italic",
}

const statusBadgeStyle: CSSProperties = {
  fontSize: "10px",
  padding: "2px 6px",
  borderRadius: "4px",
  background: "rgba(249, 115, 22, 0.1)",
  color: "#fb923c",
  fontWeight: 600,
}

const metadataFormStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  minWidth: "240px",
}

const fieldGroupStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "4px",
}

const fieldLabelStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  color: "#cbd5e1",
}

const textInputStyle: CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: "8px",
  border: "1px solid rgba(148, 163, 184, 0.18)",
  background: "rgba(15, 23, 42, 0.6)",
  color: "#e2e8f0",
  fontSize: "12px",
  outline: "none",
}

const textareaStyle: CSSProperties = {
  ...textInputStyle,
  resize: "vertical",
  minHeight: "72px",
  fontFamily: "inherit",
}

const helperTextStyle: CSSProperties = {
  fontSize: "11px",
  lineHeight: 1.5,
  color: "#94a3b8",
}

const errorTextStyle: CSSProperties = {
  marginTop: "8px",
  fontSize: "12px",
  color: "#fca5a5",
}

function isDraftStatus(status: string): boolean {
  return status.trim().toLowerCase() === "draft"
}

function isConfirmedStatus(status: string | undefined): boolean {
  const normalized = (status ?? "").trim().toLowerCase()
  return normalized === "confirmed" || normalized === "approved"
}

function getAssetQcStatus(asset: AssetDetail): string | undefined {
  return asset.metadataEntry?.qcStatus
}

function getSemanticDescription(asset: AssetDetail): string {
  return asset.metadataEntry?.semanticDescription ?? ""
}

function createMetadataDraft(asset: AssetDetail): MetadataDraft {
  return {
    semanticDescription: asset.metadataEntry?.semanticDescription ?? "",
    sourceDescription: asset.metadataEntry?.sourceDescription ?? "",
    instrumentInfo: asset.metadataEntry?.instrumentInfo ?? "",
    sampleIds: asset.metadataEntry?.sampleIds?.join(", ") ?? "",
  }
}

function parseSampleIds(value: string): string[] | undefined {
  const items = value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)

  return items.length > 0 ? items : undefined
}

// ---- Component ----

export function ManifestPanel({ systemId, blockers }: GateContentPanelProps) {
  const {
    data: manifest,
    isLoading: manifestLoading,
    error: manifestError,
  } = useManifest(systemId)
  const { data: assets, isLoading: assetsLoading, error: assetsError } = useAssets(systemId)

  const generateManifest = useGenerateManifest(systemId)
  const confirmManifest = useConfirmManifest(systemId)
  const confirmAssetQC = useConfirmAssetQC(systemId)
  const bindAssetMetadata = useBindAssetMetadata(systemId)
  const [metadataDrafts, setMetadataDrafts] = useState<Record<string, MetadataDraft>>({})

  const manifestAssetCount =
    manifest && typeof manifest.manifestJson.assetCount === "number"
      ? manifest.manifestJson.assetCount
      : null

  const bindErrorMessage = bindAssetMetadata.error instanceof Error ? bindAssetMetadata.error.message : null
  const confirmManifestErrorMessage =
    confirmManifest.error instanceof Error ? confirmManifest.error.message : null
  const confirmQcErrorMessage = confirmAssetQC.error instanceof Error ? confirmAssetQC.error.message : null
  const generateManifestErrorMessage =
    generateManifest.error instanceof Error ? generateManifest.error.message : null

  const derivedDrafts = useMemo(() => {
    const next: Record<string, MetadataDraft> = {}
    for (const asset of assets ?? []) {
      next[asset.id] = metadataDrafts[asset.id] ?? createMetadataDraft(asset)
    }
    return next
  }, [assets, metadataDrafts])

  function updateMetadataDraft(asset: AssetDetail, patch: Partial<MetadataDraft>) {
    setMetadataDrafts((prev) => ({
      ...prev,
      [asset.id]: {
        ...(prev[asset.id] ?? createMetadataDraft(asset)),
        ...patch,
      },
    }))
  }

  function handleSaveMetadata(asset: AssetDetail) {
    const draft = derivedDrafts[asset.id]
    if (!draft || draft.semanticDescription.trim().length === 0) {
      return
    }

    bindAssetMetadata.mutate(
      {
        assetId: asset.id,
        input: {
          semanticDescription: draft.semanticDescription.trim(),
          sourceDescription: draft.sourceDescription.trim() || undefined,
          instrumentInfo: draft.instrumentInfo.trim() || undefined,
          sampleIds: parseSampleIds(draft.sampleIds),
        },
      },
      {
        onSuccess: (updatedAsset) => {
          setMetadataDrafts((prev) => ({
            ...prev,
            [asset.id]: createMetadataDraft(updatedAsset),
          }))
        },
      },
    )
  }

  return (
    <div style={panelStyle}>
      <GateTaskStatus systemId={systemId} gateKey="G3" />
      <div style={sectionCardStyle}>
        <div style={titleStyle}>Assets Confirmation</div>
        <div style={descStyle}>
          确认 Manifest 与资产 QC 状态。全部确认后可推进至 Evidence Matrix 阶段。
        </div>

        <div style={subTitleStyle}>Latest Manifest</div>
        {manifestLoading ? (
          <div style={emptyStateStyle}>Loading manifest...</div>
        ) : manifestError ? (
          <div style={{ ...emptyStateStyle, color: "#fca5a5" }}>
            Error loading manifest: {manifestError instanceof Error ? manifestError.message : "Unknown error"}
          </div>
        ) : !manifest ? (
          <div style={emptyStateStyle}>No manifest generated yet.</div>
        ) : (
          <div
            style={{
              padding: "10px",
              background: "rgba(15, 23, 42, 0.4)",
              borderRadius: "8px",
              marginBottom: "12px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "12px", color: "#94a3b8" }}>Version: {manifest.version}</span>
              <span style={statusBadgeStyle}>{manifest.status}</span>
            </div>
            {manifestAssetCount !== null ? (
              <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "6px" }}>
                Assets in manifest: {manifestAssetCount}
              </div>
            ) : null}
            {isDraftStatus(manifest.status) ? (
              <button
                type="button"
                style={{ ...actionBtnStyle, marginTop: "8px", padding: "4px 12px", fontSize: "11px" }}
                onClick={() => confirmManifest.mutate(manifest.id)}
                disabled={confirmManifest.isPending}
              >
                {confirmManifest.isPending ? "Confirming..." : "Confirm Manifest"}
              </button>
            ) : null}
          </div>
        )}

        <div style={subTitleStyle}>Assets Metadata &amp; QC</div>
        <div style={helperTextStyle}>
          G3 通过前，资产至少需要语义描述；保存元数据后再做 QC 确认更符合 gate 校验语义。
        </div>
        {assetsLoading ? (
          <div style={emptyStateStyle}>Loading assets...</div>
        ) : assetsError ? (
          <div style={{ ...emptyStateStyle, color: "#fca5a5" }}>
            Error loading assets: {assetsError instanceof Error ? assetsError.message : "Unknown error"}
          </div>
        ) : !assets || assets.length === 0 ? (
          <div style={emptyStateStyle}>No assets found.</div>
        ) : (
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>File Name</th>
                <th style={thStyle}>Type</th>
                <th style={thStyle}>Metadata</th>
                <th style={thStyle}>QC Status</th>
                <th style={thStyle}>Action</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => {
                const qcStatus = getAssetQcStatus(asset)
                const semanticDescription = getSemanticDescription(asset)
                const metadataReady = semanticDescription.trim().length > 0
                const draft = derivedDrafts[asset.id] ?? createMetadataDraft(asset)
                const isSavingMetadata =
                  bindAssetMetadata.isPending && bindAssetMetadata.variables?.assetId === asset.id
                const isConfirmingQc =
                  confirmAssetQC.isPending && confirmAssetQC.variables === asset.id

                return (
                  <tr key={asset.id}>
                    <td style={tdStyle}>{asset.fileName}</td>
                    <td style={tdStyle}>{asset.assetType}</td>
                    <td style={tdStyle}>
                      <div style={metadataFormStyle}>
                        <div style={fieldGroupStyle}>
                          <label style={fieldLabelStyle}>Semantic Description</label>
                          <textarea
                            value={draft.semanticDescription}
                            onChange={(event) =>
                              updateMetadataDraft(asset, {
                                semanticDescription: event.target.value,
                              })
                            }
                            rows={3}
                            style={textareaStyle}
                            placeholder="Describe what this asset proves or represents"
                          />
                        </div>
                        <div style={fieldGroupStyle}>
                          <label style={fieldLabelStyle}>Source Description</label>
                          <input
                            value={draft.sourceDescription}
                            onChange={(event) =>
                              updateMetadataDraft(asset, {
                                sourceDescription: event.target.value,
                              })
                            }
                            style={textInputStyle}
                            placeholder="Experiment A / imaging batch"
                          />
                        </div>
                        <div style={fieldGroupStyle}>
                          <label style={fieldLabelStyle}>Instrument Info</label>
                          <input
                            value={draft.instrumentInfo}
                            onChange={(event) =>
                              updateMetadataDraft(asset, {
                                instrumentInfo: event.target.value,
                              })
                            }
                            style={textInputStyle}
                            placeholder="Leica SP8"
                          />
                        </div>
                        <div style={fieldGroupStyle}>
                          <label style={fieldLabelStyle}>Sample IDs</label>
                          <input
                            value={draft.sampleIds}
                            onChange={(event) =>
                              updateMetadataDraft(asset, {
                                sampleIds: event.target.value,
                              })
                            }
                            style={textInputStyle}
                            placeholder="sample-1, sample-2"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => handleSaveMetadata(asset)}
                          style={{ ...actionBtnStyle, padding: "6px 10px", fontSize: "11px" }}
                          disabled={isSavingMetadata || draft.semanticDescription.trim().length === 0}
                        >
                          {isSavingMetadata ? "Saving..." : "Save Metadata"}
                        </button>
                      </div>
                    </td>
                    <td style={tdStyle}>
                      {metadataReady ? qcStatus ?? "pending" : "semantic description required"}
                    </td>
                    <td style={tdStyle}>
                      {!metadataReady ? (
                        <span style={{ ...statusBadgeStyle, background: "rgba(248, 113, 113, 0.1)", color: "#fca5a5" }}>
                          Metadata required
                        </span>
                      ) : isConfirmedStatus(qcStatus) ? (
                        <span style={{ ...statusBadgeStyle, background: "rgba(52, 211, 153, 0.1)", color: "#34d399" }}>
                          QC Confirmed
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => confirmAssetQC.mutate(asset.id)}
                          style={{ ...actionBtnStyle, padding: "2px 6px", fontSize: "10px" }}
                          disabled={confirmAssetQC.isPending}
                        >
                          {isConfirmingQc ? "Confirming..." : "Confirm QC"}
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" as const }}>
        <button
          type="button"
          style={actionBtnStyle}
          onClick={() => generateManifest.mutate()}
          disabled={generateManifest.isPending}
        >
          {generateManifest.isPending ? "Generating..." : "Generate Manifest"}
        </button>
      </div>
      {generateManifestErrorMessage ? (
        <div style={errorTextStyle}>Manifest generation failed: {generateManifestErrorMessage}</div>
      ) : null}
      {confirmManifestErrorMessage ? (
        <div style={errorTextStyle}>Manifest confirmation failed: {confirmManifestErrorMessage}</div>
      ) : null}
      {bindErrorMessage ? <div style={errorTextStyle}>Metadata save failed: {bindErrorMessage}</div> : null}
      {confirmQcErrorMessage ? <div style={errorTextStyle}>QC confirmation failed: {confirmQcErrorMessage}</div> : null}

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
