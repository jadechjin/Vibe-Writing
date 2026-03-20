"use client"

import { useState, type CSSProperties } from "react"

import type { WorkflowSnapshot, Blocker } from "../../hooks/useProjectStatus"
import {
  useManifestPreview,
  useConfirmManifestFromPreview,
  type ManifestFigurePlanEntry,
  type ManifestIssue,
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

// ---- Styles ----

const statsGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(4, 1fr)",
  gap: "8px",
  marginBottom: "12px",
}

const statCardStyle: CSSProperties = {
  padding: "10px 12px",
  borderRadius: "10px",
  background: "rgba(15, 23, 42, 0.5)",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  textAlign: "center",
}

const statValueStyle: CSSProperties = {
  fontSize: "20px",
  fontWeight: 700,
  color: "#f8fafc",
}

const statLabelStyle: CSSProperties = {
  fontSize: "11px",
  color: "#94a3b8",
  marginTop: "2px",
}

const planRowStyle: CSSProperties = {
  padding: "10px 12px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.08)",
  background: "rgba(15, 23, 42, 0.35)",
  marginBottom: "6px",
  display: "flex",
  flexDirection: "column",
  gap: "6px",
}

const planHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
}

const planTitleStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  color: "#e2e8f0",
}

const assetChipsStyle: CSSProperties = {
  display: "flex",
  gap: "4px",
  flexWrap: "wrap",
}

const assetChipStyle: CSSProperties = {
  fontSize: "10px",
  padding: "2px 6px",
  borderRadius: "4px",
  background: "rgba(96, 165, 250, 0.1)",
  border: "1px solid rgba(96, 165, 250, 0.2)",
  color: "#93c5fd",
}

const issueItemStyle: CSSProperties = {
  padding: "8px 12px",
  borderRadius: "8px",
  fontSize: "12px",
  marginBottom: "4px",
}

const blockerItemStyle: CSSProperties = {
  ...issueItemStyle,
  border: "1px solid rgba(248, 113, 113, 0.2)",
  background: "rgba(127, 29, 29, 0.1)",
  color: "#fca5a5",
}

const warningItemStyle: CSSProperties = {
  ...issueItemStyle,
  border: "1px solid rgba(251, 191, 36, 0.2)",
  background: "rgba(120, 53, 15, 0.1)",
  color: "#fbbf24",
}

const manifestBarStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "10px 14px",
  borderRadius: "10px",
  background: "rgba(15, 23, 42, 0.4)",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  marginBottom: "12px",
}

const expandedDetailStyle: CSSProperties = {
  padding: "8px 10px",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.5)",
  fontSize: "11px",
  color: "#94a3b8",
  lineHeight: 1.6,
}

// ---- Helpers ----

function completenessLabel(c: string): { text: string; variant: "success" | "error" | "warning" } {
  switch (c) {
    case "complete":
      return { text: "完成", variant: "success" }
    case "missing_assets":
      return { text: "缺少图片", variant: "error" }
    case "missing_evidence":
      return { text: "缺少分析", variant: "error" }
    default:
      return { text: c, variant: "warning" }
  }
}

// ---- Component ----

export function ManifestPanel({ systemId, blockers }: GateContentPanelProps) {
  const { data: preview, isLoading, error } = useManifestPreview(systemId)
  const confirmManifest = useConfirmManifestFromPreview(systemId)
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [expandedPlanId, setExpandedPlanId] = useState<string | null>(null)

  const manifest = preview?.manifest ?? null
  const summary = preview?.summary
  const figurePlans = preview?.figurePlans ?? []
  const orphanAssets = preview?.orphanAssets ?? []
  const issues = preview?.issues ?? []
  const blockerIssues = issues.filter((i) => i.severity === "blocker")
  const warningIssues = issues.filter((i) => i.severity === "warning")
  const hasBlockers = blockerIssues.length > 0
  const manifestConfirmed = manifest?.status === "confirmed" || manifest?.status === "approved"

  return (
    <div style={gateTheme.panel}>
      <GateTaskStatus systemId={systemId} gateKey="G2" />

      <ConfirmDialog
        isOpen={showConfirmDialog}
        title="确认 Manifest"
        message="确定要确认此 Manifest 吗？此操作将冻结当前资产快照并推进至证据矩阵阶段。"
        onConfirm={() => {
          confirmManifest.mutate()
          setShowConfirmDialog(false)
        }}
        onCancel={() => setShowConfirmDialog(false)}
        isPending={confirmManifest.isPending}
        confirmLabel="确认 Manifest"
      />

      {isLoading ? (
        <EmptyState text="加载审计数据中..." />
      ) : error ? (
        <EmptyState
          text={`加载失败：${error instanceof Error ? error.message : "未知错误"}`}
          style={{ color: "#fca5a5" }}
        />
      ) : (
        <>
          {/* Layer 1: Summary stats */}
          {summary ? (
            <div style={statsGridStyle}>
              <div style={statCardStyle}>
                <div style={statValueStyle}>{summary.totalPlans}</div>
                <div style={statLabelStyle}>图表计划</div>
              </div>
              <div style={statCardStyle}>
                <div style={{ ...statValueStyle, color: summary.completePlans === summary.totalPlans ? "#4ade80" : "#fbbf24" }}>
                  {summary.completePlans}/{summary.totalPlans}
                </div>
                <div style={statLabelStyle}>完成</div>
              </div>
              <div style={statCardStyle}>
                <div style={{ ...statValueStyle, color: summary.confirmedAssets === summary.totalAssets ? "#4ade80" : "#94a3b8" }}>
                  {summary.confirmedAssets}/{summary.totalAssets}
                </div>
                <div style={statLabelStyle}>QC 通过</div>
              </div>
              <div style={statCardStyle}>
                <div style={{ ...statValueStyle, color: summary.blockerCount > 0 ? "#f87171" : "#4ade80" }}>
                  {summary.blockerCount}
                </div>
                <div style={statLabelStyle}>阻塞项</div>
              </div>
            </div>
          ) : null}

          {/* Manifest confirm action */}
          {manifestConfirmed ? (
            <div style={manifestBarStyle}>
              <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                <span style={{ fontSize: "13px", color: "#4ade80", fontWeight: 600 }}>Manifest 已确认</span>
                <span style={{ fontSize: "12px", color: "#94a3b8" }}>v{manifest!.version}</span>
                <StatusBadge status={manifest!.status} />
              </div>
            </div>
          ) : (
            <div style={{
              padding: "16px",
              borderRadius: "12px",
              border: hasBlockers ? "1px solid rgba(251, 191, 36, 0.3)" : "1px solid rgba(34, 197, 94, 0.3)",
              background: hasBlockers ? "rgba(120, 53, 15, 0.12)" : "rgba(20, 83, 45, 0.12)",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
              alignItems: "center",
              textAlign: "center",
            }}>
              <div style={{ fontSize: "13px", fontWeight: 600, color: hasBlockers ? "#fbbf24" : "#4ade80" }}>
                {hasBlockers ? "存在资产问题，请先解决下方标记的阻塞项" : "全部资产审核通过，可以确认冻结"}
              </div>
              {hasBlockers ? (
                <div style={{ fontSize: "12px", color: "#94a3b8" }}>
                  {blockerIssues.length} 个阻塞项需要解决后才能确认 Manifest
                </div>
              ) : null}
              <ActionButton
                label="确认 Manifest"
                onClick={() => setShowConfirmDialog(true)}
                disabled={hasBlockers || confirmManifest.isPending}
                isPending={confirmManifest.isPending}
              />
            </div>
          )}

          {/* Layer 2: FigurePlan audit list */}
          <SectionCard title="图表计划审计" description="以图表计划为核心的资产完整性审阅。">
            {figurePlans.length === 0 ? (
              <EmptyState text="暂无已确认的图表计划。" />
            ) : (
              figurePlans.map((plan) => {
                const cl = completenessLabel(plan.completeness)
                const isExpanded = expandedPlanId === plan.figurePlanId
                return (
                  <div key={plan.figurePlanId} style={planRowStyle}>
                    <div
                      style={{ ...planHeaderStyle, cursor: "pointer" }}
                      onClick={() => setExpandedPlanId(isExpanded ? null : plan.figurePlanId)}
                    >
                      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        <span style={{ fontSize: "12px", color: "#60a5fa", fontWeight: 600 }}>{plan.figureNo}</span>
                        <span style={planTitleStyle}>{plan.title}</span>
                      </div>
                      <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                        <span style={{ fontSize: "10px", color: "#64748b" }}>
                          {plan.assets.length} 图片
                        </span>
                        <StatusBadge status={cl.text} variant={cl.variant} />
                      </div>
                    </div>
                    {plan.assets.length > 0 ? (
                      <div style={assetChipsStyle}>
                        {plan.assets.map((a) => (
                          <span key={a.id} style={assetChipStyle}>
                            {a.fileName}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    {isExpanded ? (
                      <FigurePlanDetail plan={plan} />
                    ) : null}
                  </div>
                )
              })
            )}
          </SectionCard>

          {/* Layer 3: Issues panel */}
          {issues.length > 0 ? (
            <SectionCard
              title={<span style={{ fontSize: "13px", color: blockerIssues.length > 0 ? "#fca5a5" : "#fbbf24" }}>问题 ({issues.length})</span>}
            >
              {blockerIssues.map((issue, i) => (
                <IssueCard key={`b-${i}`} issue={issue} variant="blocker" />
              ))}
              {warningIssues.map((issue, i) => (
                <IssueCard key={`w-${i}`} issue={issue} variant="warning" />
              ))}
            </SectionCard>
          ) : null}

          {/* Orphan assets */}
          {orphanAssets.length > 0 ? (
            <SectionCard title={`孤儿资产 (${orphanAssets.length})`} description="未关联到任何图表计划的文件。">
              <div style={assetChipsStyle}>
                {orphanAssets.map((a) => (
                  <span key={a.id} style={{ ...assetChipStyle, background: "rgba(251, 191, 36, 0.1)", borderColor: "rgba(251, 191, 36, 0.2)", color: "#fbbf24" }}>
                    {a.fileName} ({a.assetType})
                  </span>
                ))}
              </div>
            </SectionCard>
          ) : null}

          {confirmManifest.error instanceof Error ? (
            <div style={{ fontSize: "12px", color: "#fca5a5", marginTop: "8px" }}>
              Manifest 确认失败：{confirmManifest.error.message}
            </div>
          ) : null}
        </>
      )}
    </div>
  )
}

// ---- Expanded detail sub-component ----

function FigurePlanDetail({ plan }: { plan: ManifestFigurePlanEntry }) {
  return (
    <div style={expandedDetailStyle}>
      {plan.dataQuestion ? (
        <div style={{ marginBottom: "6px" }}>
          <strong style={{ color: "#cbd5e1" }}>研究问题：</strong>{plan.dataQuestion}
        </div>
      ) : null}
      {plan.evidenceText ? (
        <div style={{ marginBottom: "6px" }}>
          <strong style={{ color: "#cbd5e1" }}>分析结论：</strong>
          {plan.evidenceText.length > 200 ? `${plan.evidenceText.slice(0, 200)}...` : plan.evidenceText}
        </div>
      ) : (
        <div style={{ marginBottom: "6px", color: "#f87171" }}>
          <strong>分析结论：</strong>缺失
        </div>
      )}
      {plan.latestAnalysis ? (
        <div>
          <strong style={{ color: "#cbd5e1" }}>AI 分析：</strong>
          {plan.latestAnalysis.summary ?? plan.latestAnalysis.status}
        </div>
      ) : null}
    </div>
  )
}

// ---- Issue card sub-component ----

const issueDetailStyle: CSSProperties = {
  fontSize: "11px",
  lineHeight: 1.6,
  marginTop: "6px",
  color: "#cbd5e1",
}

const resolutionStyle: CSSProperties = {
  fontSize: "11px",
  lineHeight: 1.5,
  marginTop: "4px",
  padding: "4px 8px",
  borderRadius: "6px",
  background: "rgba(148, 163, 184, 0.08)",
  color: "#94a3b8",
}

function IssueCard({ issue, variant }: { issue: ManifestIssue; variant: "blocker" | "warning" }) {
  const baseStyle = variant === "blocker" ? blockerItemStyle : warningItemStyle
  const label = variant === "blocker" ? "阻塞" : "警告"

  return (
    <div style={baseStyle}>
      <div>
        <strong>{label}</strong>: {issue.message}
      </div>
      {issue.detail ? (
        <div style={issueDetailStyle}>{issue.detail}</div>
      ) : null}
      {issue.resolution ? (
        <div style={resolutionStyle}>
          <strong>解决方法：</strong>{issue.resolution}
        </div>
      ) : null}
    </div>
  )
}
