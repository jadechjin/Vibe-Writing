"use client"

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
import { gateTheme } from "../../styles/gate-theme"
import { ActionButton } from "../ui/ActionButton"
import { ConfirmDialog } from "../ui/ConfirmDialog"
import { EmptyState } from "../ui/EmptyState"
import { SectionCard } from "../ui/SectionCard"
import { StatusBadge } from "../ui/StatusBadge"
import { GateTaskStatus } from "./GateTaskStatus"

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

const metadataFormStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  minWidth: "240px",
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

const bulkActionsBarStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  padding: "8px 12px",
  background: "rgba(96, 165, 250, 0.08)",
  border: "1px solid rgba(96, 165, 250, 0.2)",
  borderRadius: "8px",
  marginBottom: "8px",
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
  const items = value.split(",").map((item) => item.trim()).filter(Boolean)
  return items.length > 0 ? items : undefined
}

export function ManifestPanel({ systemId, blockers }: GateContentPanelProps) {
  const { data: manifest, isLoading: manifestLoading, error: manifestError } = useManifest(systemId)
  const { data: assets, isLoading: assetsLoading, error: assetsError } = useAssets(systemId)

  const generateManifest = useGenerateManifest(systemId)
  const confirmManifest = useConfirmManifest(systemId)
  const confirmAssetQC = useConfirmAssetQC(systemId)
  const bindAssetMetadata = useBindAssetMetadata(systemId)

  const [metadataDrafts, setMetadataDrafts] = useState<Record<string, MetadataDraft>>({})
  const [selectedAssetIds, setSelectedAssetIds] = useState<Set<string>>(new Set())
  const [showConfirmManifestDialog, setShowConfirmManifestDialog] = useState(false)

  const manifestAssetCount =
    manifest && typeof manifest.manifestJson.assetCount === "number"
      ? manifest.manifestJson.assetCount
      : null

  const bindErrorMessage = bindAssetMetadata.error instanceof Error ? bindAssetMetadata.error.message : null
  const confirmManifestErrorMessage = confirmManifest.error instanceof Error ? confirmManifest.error.message : null
  const confirmQcErrorMessage = confirmAssetQC.error instanceof Error ? confirmAssetQC.error.message : null
  const generateManifestErrorMessage = generateManifest.error instanceof Error ? generateManifest.error.message : null

  const derivedDrafts = useMemo(() => {
    const next: Record<string, MetadataDraft> = {}
    for (const asset of assets ?? []) {
      next[asset.id] = metadataDrafts[asset.id] ?? createMetadataDraft(asset)
    }
    return next
  }, [assets, metadataDrafts])

  const confirmableAssets = useMemo(
    () => (assets ?? []).filter((a) => getSemanticDescription(a).trim().length > 0 && !isConfirmedStatus(getAssetQcStatus(a))),
    [assets],
  )

  const allConfirmableSelected =
    confirmableAssets.length > 0 && confirmableAssets.every((a) => selectedAssetIds.has(a.id))

  function toggleSelectAll() {
    if (allConfirmableSelected) {
      setSelectedAssetIds(new Set())
    } else {
      setSelectedAssetIds(new Set(confirmableAssets.map((a) => a.id)))
    }
  }

  function toggleAsset(assetId: string) {
    setSelectedAssetIds((prev) => {
      const next = new Set(prev)
      if (next.has(assetId)) {
        next.delete(assetId)
      } else {
        next.add(assetId)
      }
      return next
    })
  }

  function handleBulkConfirmQC() {
    for (const assetId of selectedAssetIds) {
      confirmAssetQC.mutate(assetId)
    }
    setSelectedAssetIds(new Set())
  }

  function updateMetadataDraft(asset: AssetDetail, patch: Partial<MetadataDraft>) {
    setMetadataDrafts((prev) => ({
      ...prev,
      [asset.id]: { ...(prev[asset.id] ?? createMetadataDraft(asset)), ...patch },
    }))
  }

  function handleSaveMetadata(asset: AssetDetail) {
    const draft = derivedDrafts[asset.id]
    if (!draft || draft.semanticDescription.trim().length === 0) return

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
          setMetadataDrafts((prev) => ({ ...prev, [asset.id]: createMetadataDraft(updatedAsset) }))
        },
      },
    )
  }

  return (
    <div style={gateTheme.panel}>
      <GateTaskStatus systemId={systemId} gateKey="G3" />

      <ConfirmDialog
        isOpen={showConfirmManifestDialog}
        title="确认 Manifest"
        message="确定要确认此 Manifest 吗？此操作将推进工作流至证据矩阵阶段。"
        onConfirm={() => {
          if (manifest) {
            confirmManifest.mutate(manifest.id)
          }
          setShowConfirmManifestDialog(false)
        }}
        onCancel={() => setShowConfirmManifestDialog(false)}
        isPending={confirmManifest.isPending}
        confirmLabel="确认 Manifest"
      />

      <SectionCard title="资产确认" description="确认 Manifest 与资产 QC 状态。全部确认后可推进至 Evidence Matrix 阶段。">
        <div style={subTitleStyle}>最新 Manifest</div>
        {manifestLoading ? (
          <EmptyState text="加载 Manifest 中..." />
        ) : manifestError ? (
          <EmptyState text={`加载 Manifest 失败：${manifestError instanceof Error ? manifestError.message : "未知错误"}`} style={{ color: "#fca5a5" }} />
        ) : !manifest ? (
          <EmptyState text="尚未生成 Manifest。" />
        ) : (
          <div style={{ padding: "10px", background: "rgba(15, 23, 42, 0.4)", borderRadius: "8px", marginBottom: "12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "12px", color: "#94a3b8" }}>版本：{manifest.version}</span>
              <StatusBadge status={manifest.status} />
            </div>
            {manifestAssetCount !== null ? (
              <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "6px" }}>
                Manifest 中的资产数：{manifestAssetCount}
              </div>
            ) : null}
            {isDraftStatus(manifest.status) ? (
              <ActionButton
                label="确认 Manifest"
                onClick={() => setShowConfirmManifestDialog(true)}
                disabled={confirmManifest.isPending}
                style={{ marginTop: "8px", padding: "4px 12px", fontSize: "11px" }}
              />
            ) : null}
          </div>
        )}

        <div style={subTitleStyle}>资产元数据与 QC</div>
        <div style={helperTextStyle}>
          G3 通过前，资产至少需要语义描述；保存元数据后再做 QC 确认更符合 gate 校验语义。
        </div>

        {assetsLoading ? (
          <EmptyState text="Loading assets..." />
        ) : assetsError ? (
          <EmptyState text={`Error loading assets: ${assetsError instanceof Error ? assetsError.message : "未知错误"}`} style={{ color: "#fca5a5" }} />
        ) : !assets || assets.length === 0 ? (
          <EmptyState text="No assets found." />
        ) : (
          <>
            {selectedAssetIds.size > 0 ? (
              <div style={bulkActionsBarStyle}>
                <span style={{ fontSize: "12px", color: "#94a3b8" }}>{selectedAssetIds.size} 已选</span>
                <ActionButton
                  label={confirmAssetQC.isPending ? "确认中..." : "批量确认 QC"}
                  onClick={handleBulkConfirmQC}
                  disabled={confirmAssetQC.isPending}
                  isPending={confirmAssetQC.isPending}
                  style={{ padding: "4px 12px", fontSize: "11px" }}
                />
                <ActionButton
                  label="清除"
                  onClick={() => setSelectedAssetIds(new Set())}
                  variant="secondary"
                  style={{ padding: "4px 10px", fontSize: "11px" }}
                />
              </div>
            ) : null}
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>
                    <input
                      type="checkbox"
                      checked={allConfirmableSelected}
                      onChange={toggleSelectAll}
                      title="全选可确认资产"
                    />
                  </th>
                  <th style={thStyle}>文件名</th>
                  <th style={thStyle}>类型</th>
                  <th style={thStyle}>元数据</th>
                  <th style={thStyle}>QC 状态</th>
                  <th style={thStyle}>操作</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((asset) => {
                  const qcStatus = getAssetQcStatus(asset)
                  const semanticDescription = getSemanticDescription(asset)
                  const metadataReady = semanticDescription.trim().length > 0
                  const draft = derivedDrafts[asset.id] ?? createMetadataDraft(asset)
                  const isSavingMetadata = bindAssetMetadata.isPending && bindAssetMetadata.variables?.assetId === asset.id
                  const isConfirmingQc = confirmAssetQC.isPending && confirmAssetQC.variables === asset.id
                  const isConfirmed = isConfirmedStatus(qcStatus)
                  const isSelectable = metadataReady && !isConfirmed

                  return (
                    <tr key={asset.id}>
                      <td style={tdStyle}>
                        <input
                          type="checkbox"
                          checked={selectedAssetIds.has(asset.id)}
                          onChange={() => toggleAsset(asset.id)}
                          disabled={!isSelectable}
                        />
                      </td>
                      <td style={tdStyle}>{asset.fileName}</td>
                      <td style={tdStyle}>{asset.assetType}</td>
                      <td style={tdStyle}>
                        <div style={metadataFormStyle}>
                          <div style={gateTheme.fieldGroup}>
                            <label style={fieldLabelStyle}>语义描述</label>
                            <textarea
                              value={draft.semanticDescription}
                              onChange={(event) => updateMetadataDraft(asset, { semanticDescription: event.target.value })}
                              rows={3}
                              style={textareaStyle}
                              placeholder="描述该资产证明或代表的内容"
                            />
                          </div>
                          <div style={gateTheme.fieldGroup}>
                            <label style={fieldLabelStyle}>来源描述</label>
                            <input
                              value={draft.sourceDescription}
                              onChange={(event) => updateMetadataDraft(asset, { sourceDescription: event.target.value })}
                              style={textInputStyle}
                              placeholder="实验 A / 成像批次"
                            />
                          </div>
                          <div style={gateTheme.fieldGroup}>
                            <label style={fieldLabelStyle}>仪器信息</label>
                            <input
                              value={draft.instrumentInfo}
                              onChange={(event) => updateMetadataDraft(asset, { instrumentInfo: event.target.value })}
                              style={textInputStyle}
                              placeholder="Leica SP8"
                            />
                          </div>
                          <div style={gateTheme.fieldGroup}>
                            <label style={fieldLabelStyle}>样本 ID</label>
                            <input
                              value={draft.sampleIds}
                              onChange={(event) => updateMetadataDraft(asset, { sampleIds: event.target.value })}
                              style={textInputStyle}
                              placeholder="sample-1, sample-2"
                            />
                          </div>
                          <ActionButton
                            label={isSavingMetadata ? "保存中..." : "保存元数据"}
                            onClick={() => handleSaveMetadata(asset)}
                            disabled={isSavingMetadata || draft.semanticDescription.trim().length === 0}
                            isPending={isSavingMetadata}
                            style={{ padding: "6px 10px", fontSize: "11px" }}
                          />
                        </div>
                      </td>
                      <td style={tdStyle}>
                        {metadataReady ? qcStatus ?? "待确认" : "需要语义描述"}
                      </td>
                      <td style={tdStyle}>
                        {!metadataReady ? (
                          <StatusBadge status="需要元数据" variant="error" />
                        ) : isConfirmed ? (
                          <StatusBadge status="QC 已确认" variant="success" />
                        ) : (
                          <ActionButton
                            label={isConfirmingQc ? "确认中..." : "确认 QC"}
                            onClick={() => confirmAssetQC.mutate(asset.id)}
                            disabled={confirmAssetQC.isPending}
                            isPending={isConfirmingQc}
                            style={{ padding: "2px 6px", fontSize: "10px" }}
                          />
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </>
        )}
      </SectionCard>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" as const }}>
        <ActionButton
          label={generateManifest.isPending ? "生成中..." : "生成 Manifest"}
          onClick={() => generateManifest.mutate()}
          disabled={generateManifest.isPending}
          isPending={generateManifest.isPending}
        />
      </div>
      {generateManifestErrorMessage ? <div style={errorTextStyle}>Manifest 生成失败：{generateManifestErrorMessage}</div> : null}
      {confirmManifestErrorMessage ? <div style={errorTextStyle}>Manifest 确认失败：{confirmManifestErrorMessage}</div> : null}
      {bindErrorMessage ? <div style={errorTextStyle}>元数据保存失败：{bindErrorMessage}</div> : null}
      {confirmQcErrorMessage ? <div style={errorTextStyle}>QC 确认失败：{confirmQcErrorMessage}</div> : null}

      {blockers.length > 0 ? (
        <SectionCard title={<span style={{ fontSize: "13px", color: "#fca5a5" }}>阻塞项 ({blockers.length})</span>}>
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
