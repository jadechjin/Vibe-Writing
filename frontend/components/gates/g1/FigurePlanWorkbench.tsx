"use client"

import { useEffect, useState, type CSSProperties } from "react"

import {
  useConfirmFigurePlan,
  useDeleteFigurePlan,
  usePatchFigurePlan,
  type FigurePlanDetail,
  type FigurePlanPatchInput,
} from "../../../hooks/useFigurePlan"
import type { SystemDetail } from "../../../hooks/useProjects"
import { useSkeleton } from "../../../hooks/useSkeletons"
import { AgentChat } from "./AgentChat"
import { FigurePlanUpload } from "./FigurePlanUpload"

type Section = SystemDetail["sections"][number]

export type FigurePlanWorkbenchProps = Readonly<{
  systemId: string
  sections: Section[]
  plans: FigurePlanDetail[]
  skeletonId?: string
  onSelectPlan?: (planId: string) => void
}>

const containerStyle: CSSProperties = {
  display: "flex", gap: "1px", minHeight: "400px",
  borderRadius: "12px", overflow: "hidden",
  border: "1px solid rgba(148,163,184,0.12)",
  background: "rgba(15,23,42,0.3)",
}

const listPaneStyle: CSSProperties = {
  width: "40%", minWidth: "280px",
  borderRight: "1px solid rgba(148,163,184,0.08)",
  display: "flex", flexDirection: "column", gap: "6px",
}

const rightStyle: CSSProperties = {
  flex: 1, overflowY: "auto", padding: "14px",
}

const listHeaderStyle: CSSProperties = {
  padding: "12px",
  borderBottom: "1px solid rgba(148,163,184,0.08)",
  display: "flex",
  flexDirection: "column",
  gap: "10px",
}

const filterRowStyle: CSSProperties = {
  display: "flex",
  gap: "8px",
  flexWrap: "wrap",
}

const filterButtonStyle: CSSProperties = {
  padding: "6px 10px",
  borderRadius: "999px",
  border: "1px solid rgba(148,163,184,0.14)",
  background: "rgba(15,23,42,0.45)",
  color: "#94a3b8",
  fontSize: "12px",
  fontWeight: 600,
  cursor: "pointer",
}

const filterButtonActiveStyle: CSSProperties = {
  ...filterButtonStyle,
  border: "1px solid rgba(249,115,22,0.45)",
  background: "rgba(249,115,22,0.08)",
  color: "#fb923c",
}

const listBodyStyle: CSSProperties = {
  overflowY: "auto",
  padding: "12px",
  display: "flex",
  flexDirection: "column",
  gap: "8px",
}

const cardStyle: CSSProperties = {
  padding: "10px 12px", borderRadius: "8px",
  border: "1px solid rgba(148,163,184,0.1)",
  background: "rgba(15,23,42,0.4)", cursor: "pointer",
}

const cardActiveStyle: CSSProperties = {
  ...cardStyle, border: "1px solid rgba(251,146,60,0.4)",
  background: "rgba(249,115,22,0.06)",
}

const badgeBase: CSSProperties = {
  fontSize: "10px", fontWeight: 600, padding: "1px 6px",
  borderRadius: "4px", display: "inline-block",
}

const buttonBaseStyle: CSSProperties = {
  padding: "6px 12px",
  borderRadius: "8px",
  border: "1px solid rgba(148,163,184,0.15)",
  background: "rgba(15,23,42,0.55)",
  color: "#e2e8f0",
  fontSize: "12px",
  fontWeight: 600,
  cursor: "pointer",
}

const buttonDisabledStyle: CSSProperties = {
  opacity: 0.5,
  cursor: "not-allowed",
}

const primaryButtonStyle: CSSProperties = {
  ...buttonBaseStyle,
  border: "1px solid rgba(249,115,22,0.5)",
  color: "#fb923c",
  background: "rgba(154,52,18,0.15)",
}

const dangerButtonStyle: CSSProperties = {
  ...buttonBaseStyle,
  border: "1px solid rgba(248,113,113,0.5)",
  color: "#f87171",
  background: "rgba(127,29,29,0.15)",
}

const editButtonStyle: CSSProperties = {
  ...buttonBaseStyle,
  border: "1px solid rgba(96,165,250,0.5)",
  color: "#60a5fa",
  background: "rgba(30,64,175,0.15)",
}

const importanceColors: Record<string, { color: string; bg: string }> = {
  high: { color: "#f87171", bg: "rgba(127,29,29,0.2)" },
  medium: { color: "#fbbf24", bg: "rgba(120,53,15,0.2)" },
  low: { color: "#94a3b8", bg: "rgba(148,163,184,0.1)" },
}

const statusColors: Record<string, { color: string; bg: string }> = {
  pending: { color: "#94a3b8", bg: "rgba(148,163,184,0.1)" },
  confirmed: { color: "#4ade80", bg: "rgba(22,101,52,0.2)" },
  needs_review: { color: "#fbbf24", bg: "rgba(120,53,15,0.2)" },
  delivered: { color: "#60a5fa", bg: "rgba(30,64,175,0.2)" },
  draft: { color: "#fbbf24", bg: "rgba(120,53,15,0.2)" },
}

const emptyStyle: CSSProperties = {
  fontSize: "12px", color: "#64748b", textAlign: "center", padding: "32px 0",
}

const detailLabelStyle: CSSProperties = { fontSize: "11px", color: "#64748b", marginBottom: "2px" }
const detailValueStyle: CSSProperties = { fontSize: "13px", color: "#e2e8f0", marginBottom: "10px" }
const fieldBlockStyle: CSSProperties = { display: "flex", flexDirection: "column", gap: "6px", marginBottom: "12px" }
const fieldLabelStyle: CSSProperties = { fontSize: "11px", color: "#94a3b8", fontWeight: 600, display: "flex", flexDirection: "column", gap: "6px" }
const inputStyle: CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: "8px",
  border: "1px solid rgba(148,163,184,0.16)",
  background: "rgba(15,23,42,0.6)",
  color: "#e2e8f0",
  fontSize: "13px",
  outline: "none",
}
const textareaStyle: CSSProperties = {
  ...inputStyle,
  minHeight: "96px",
  resize: "vertical",
  lineHeight: 1.5,
}
const selectStyle: CSSProperties = {
  ...inputStyle,
  appearance: "none",
}
const panelHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  gap: "12px",
  marginBottom: "12px",
}

const cardEditBtnStyle: CSSProperties = {
  background: "none", border: "none", color: "#60a5fa",
  cursor: "pointer", fontSize: "13px", padding: "0 2px", flexShrink: 0,
}

const cardMetaStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "8px",
  marginBottom: "6px",
}

const cardPreviewStyle: CSSProperties = {
  fontSize: "12px",
  color: "#94a3b8",
  lineHeight: 1.5,
  display: "-webkit-box",
  WebkitBoxOrient: "vertical",
  WebkitLineClamp: 2,
  overflow: "hidden",
}

const cardSecondaryMetaStyle: CSSProperties = {
  fontSize: "11px",
  color: "#64748b",
}

const editorOverlayStyle: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(2,6,23,0.72)",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  padding: "24px",
  zIndex: 40,
}

const editorCardStyle: CSSProperties = {
  width: "min(760px, 100%)",
  maxHeight: "calc(100vh - 48px)",
  overflowY: "auto",
  borderRadius: "16px",
  border: "1px solid rgba(148,163,184,0.14)",
  background: "#0f172a",
  boxShadow: "0 28px 70px rgba(2,6,23,0.45)",
}

const editorHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "12px",
  padding: "18px 20px 14px",
  borderBottom: "1px solid rgba(148,163,184,0.08)",
}

const editorBodyStyle: CSSProperties = {
  padding: "18px 20px 20px",
}

type FigurePlanDraft = {
  figureNo: string
  title: string
  claimText: string
  sectionKey: string
  briefText: string
}

type FigureFrameworkEntry = Readonly<{
  figureId: string
  title: string
  type?: string
  importance?: string
  dataQuestion?: string
}>

function normalizeFigureId(value: unknown): string | null {
  if (typeof value !== "string") return null
  const normalized = value.trim()
  return normalized || null
}

function extractFigureFramework(
  skeletonJson: Record<string, unknown> | undefined,
): FigureFrameworkEntry[] {
  const raw = skeletonJson?.figure_framework
  if (!Array.isArray(raw)) return []

  const entries = new Map<string, FigureFrameworkEntry>()
  for (const entry of raw) {
    if (!entry || typeof entry !== "object") continue
    const fig = entry as Record<string, unknown>
    const figureId = normalizeFigureId(fig.figure_id)
    if (!figureId || entries.has(figureId)) continue
    const title = typeof fig.title === "string" ? fig.title.trim() : figureId
    entries.set(figureId, {
      figureId,
      title: title || figureId,
      type: typeof fig.type === "string" ? fig.type.trim() || undefined : undefined,
      importance: typeof fig.importance === "string" ? fig.importance.trim() || undefined : undefined,
      dataQuestion: typeof fig.data_question === "string" ? fig.data_question.trim() || undefined : undefined,
    })
  }
  return [...entries.values()]
}

function buildDraftFromPlan(plan: FigurePlanDetail): FigurePlanDraft {
  return {
    figureNo: plan.figureNo,
    title: plan.title,
    claimText: plan.claimText,
    sectionKey: plan.sectionKey ?? "",
    briefText: plan.briefText ?? "",
  }
}

export function FigurePlanWorkbench({
  systemId,
  sections,
  plans,
  skeletonId,
  onSelectPlan,
}: FigurePlanWorkbenchProps) {
  const [selectedFilterKey, setSelectedFilterKey] = useState<string | null>("__all__")
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null)
  const [editingPlanId, setEditingPlanId] = useState<string | null>(null)
  const [removedPlanIds, setRemovedPlanIds] = useState<string[]>([])
  const { data: skeletonDetail } = useSkeleton(skeletonId ?? "")

  const figureFramework = extractFigureFramework(skeletonDetail?.skeletonJson as Record<string, unknown> | undefined)
  const figureIds = new Set(figureFramework.map((f) => f.figureId))

  useEffect(() => {
    setRemovedPlanIds((current) => current.filter((id) => plans.some((plan) => plan.id === id)))
  }, [plans])

  const visiblePlans = plans.filter((plan) => !removedPlanIds.includes(plan.id))
  const unlinkedPlans = visiblePlans.filter((plan) => {
    const fid = normalizeFigureId(plan.figureNo)
    return !fid || !figureIds.has(fid)
  })
  const filteredPlans = selectedFilterKey === "__all__"
    ? visiblePlans
    : selectedFilterKey === "__unlinked__"
      ? unlinkedPlans
      : visiblePlans.filter((plan) => normalizeFigureId(plan.figureNo) === selectedFilterKey)

  const selectedPlan = filteredPlans.find((plan) => plan.id === selectedPlanId) ?? filteredPlans[0] ?? null
  const editingPlan = visiblePlans.find((plan) => plan.id === editingPlanId) ?? null

  function handleSelectFilter(key: string) {
    setSelectedFilterKey(key)
    setSelectedPlanId(null)
  }

  function handleSelectPlan(planId: string) {
    setSelectedPlanId(planId)
    onSelectPlan?.(planId)
  }

  function handleDeleteSuccess(planId: string) {
    const remainingPlans = filteredPlans.filter((plan) => plan.id !== planId)
    const nextPlanId = remainingPlans[0]?.id ?? null

    setRemovedPlanIds((current) => current.includes(planId) ? current : [...current, planId])
    setSelectedPlanId(nextPlanId)
    setEditingPlanId((current) => (current === planId ? null : current))

    if (nextPlanId) {
      onSelectPlan?.(nextPlanId)
    }
  }

  return (
    <>
      <div style={containerStyle}>
        <div style={listPaneStyle}>
          <div style={listHeaderStyle}>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "#f8fafc" }}>图表规划列表</div>
            <div style={filterRowStyle}>
              <button
                type="button"
                style={selectedFilterKey === "__all__" ? filterButtonActiveStyle : filterButtonStyle}
                onClick={() => handleSelectFilter("__all__")}
              >
                全部 ({visiblePlans.length})
              </button>
              {unlinkedPlans.length > 0 ? (
                <button
                  type="button"
                  style={selectedFilterKey === "__unlinked__" ? filterButtonActiveStyle : filterButtonStyle}
                  onClick={() => handleSelectFilter("__unlinked__")}
                >
                  未关联 ({unlinkedPlans.length})
                </button>
              ) : null}
            </div>
          </div>
          <div style={listBodyStyle}>
            {filteredPlans.length === 0 ? (
              <div style={emptyStyle}>该筛选条件下暂无图表规划</div>
            ) : (
              filteredPlans.map((plan) => {
                const isActive = selectedPlan?.id === plan.id
                const statusColor = statusColors[plan.status] ?? statusColors.pending
                const importanceKey = String(plan.methodJson?.importance ?? "")
                const importanceToken = importanceColors[importanceKey] ?? null
                return (
                  <div
                    key={plan.id}
                    style={isActive ? cardActiveStyle : cardStyle}
                    onClick={() => handleSelectPlan(plan.id)}
                  >
                    <div style={cardMetaStyle}>
                      <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
                        <span style={{ ...badgeBase, color: statusColor.color, background: statusColor.bg }}>
                          {plan.status}
                        </span>
                        {importanceToken ? (
                          <span
                            style={{
                              ...badgeBase,
                              color: importanceToken.color,
                              background: importanceToken.bg,
                            }}
                          >
                            {importanceKey}
                          </span>
                        ) : null}
                      </div>
                      <button
                        type="button"
                        aria-label="Open Figure Plan Editor"
                        title="编辑"
                        style={{
                          ...cardEditBtnStyle,
                          color: plan.briefText ? "#f8fafc" : "#60a5fa",
                        }}
                        onClick={(event) => {
                          event.stopPropagation()
                          setEditingPlanId(plan.id)
                        }}
                      >
                        ✎
                      </button>
                    </div>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "#e2e8f0", marginBottom: "6px" }}>
                      {plan.figureNo}: {plan.title}
                    </div>
                    <div style={cardPreviewStyle}>
                      {plan.claimText || plan.briefText || "暂无论证摘要，点击编辑补充图表规划信息。"}
                    </div>
                    <div style={{ ...cardSecondaryMetaStyle, marginTop: "8px" }}>
                      {plan.sectionKey ? `章节：${plan.sectionKey}` : "未关联章节"}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>

        <div style={rightStyle}>
          {selectedPlan ? (
            <FigurePlanDetailPanel
              key={selectedPlan.id}
              systemId={systemId}
              plan={selectedPlan}
              figureFramework={figureFramework}
              onDeleteSuccess={handleDeleteSuccess}
              onEdit={() => setEditingPlanId(selectedPlan.id)}
            />
          ) : (
            <div style={emptyStyle}>选择一个图表规划查看详情</div>
          )}
        </div>
      </div>
      {editingPlan ? (
        <FigurePlanEditorOverlay
          systemId={systemId}
          plan={editingPlan}
          sections={sections}
          onClose={() => setEditingPlanId(null)}
        />
      ) : null}
    </>
  )
}

const confirmButtonStyle: CSSProperties = {
  ...buttonBaseStyle,
  border: "1px solid rgba(74,222,128,0.5)",
  color: "#4ade80",
  background: "rgba(22,101,52,0.15)",
}

function FigurePlanDetailPanel({
  systemId,
  plan,
  figureFramework,
  onDeleteSuccess,
  onEdit,
}: Readonly<{
  systemId: string
  plan: FigurePlanDetail
  figureFramework: FigureFrameworkEntry[]
  onDeleteSuccess: (planId: string) => void
  onEdit: () => void
}>) {
  const deleteMut = useDeleteFigurePlan(systemId)
  const confirmMut = useConfirmFigurePlan(systemId)

  const canConfirm = plan.status !== "confirmed" && plan.status !== "approved" && plan.status !== "delivered"

  function handleDelete() {
    if (!window.confirm("确定要删除这个图表规划吗？")) return
    deleteMut.mutate(plan.id, {
      onSuccess: () => {
        onDeleteSuccess(plan.id)
      },
    })
  }

  return (
    <div>
      <div style={panelHeaderStyle}>
        <div style={{ fontSize: "15px", fontWeight: 700, color: "#f8fafc" }}>
          {plan.figureNo}: {plan.title}
        </div>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {canConfirm ? (
            <button
              type="button"
              aria-label="Confirm Figure Plan"
              onClick={() => confirmMut.mutate(plan.id)}
              disabled={confirmMut.isPending}
              style={confirmMut.isPending ? { ...confirmButtonStyle, ...buttonDisabledStyle } : confirmButtonStyle}
            >
              {confirmMut.isPending ? "确认中..." : "确认规划"}
            </button>
          ) : null}
          <button
            type="button"
            aria-label="Edit Figure Plan"
            onClick={onEdit}
            style={editButtonStyle}
          >
            编辑
          </button>
          <button
            type="button"
            aria-label="Delete Figure Plan"
            onClick={handleDelete}
            disabled={deleteMut.isPending}
            style={deleteMut.isPending ? { ...dangerButtonStyle, ...buttonDisabledStyle } : dangerButtonStyle}
          >
            删除
          </button>
        </div>
      </div>

      {plan.claimText ? (
        <>
          <div style={detailLabelStyle}>论证目的</div>
          <div style={detailValueStyle}>{plan.claimText}</div>
        </>
      ) : null}

      {(() => {
        const q = plan.dataQuestion ?? figureFramework.find((f) => f.figureId === plan.figureNo)?.dataQuestion
        return q ? (
          <>
            <div style={detailLabelStyle}>数据问题</div>
            <div style={{ ...detailValueStyle, color: "#fbbf24" }}>{q}</div>
          </>
        ) : null
      })()}

      {plan.sectionKey ? (
        <>
          <div style={detailLabelStyle}>关联章节</div>
          <div style={detailValueStyle}>{plan.sectionKey}</div>
        </>
      ) : null}

      {plan.skeletonVersion != null ? (
        <>
          <div style={detailLabelStyle}>骨架版本</div>
          <div style={detailValueStyle}>v{plan.skeletonVersion}</div>
        </>
      ) : null}

      {plan.briefText ? (
        <>
          <div style={detailLabelStyle}>图表简述</div>
          <div style={{
            ...detailValueStyle,
            padding: "8px 10px",
            borderRadius: "8px",
            background: "rgba(15,23,42,0.5)",
            border: "1px solid rgba(148,163,184,0.08)",
          }}>
            {plan.briefText}
          </div>
        </>
      ) : null}

      {plan.briefConfirmedAt ? (
        <>
          <div style={detailLabelStyle}>简述确认时间</div>
          <div style={detailValueStyle}>{new Date(plan.briefConfirmedAt).toLocaleString()}</div>
        </>
      ) : null}

      <div style={{ marginTop: "16px" }}>
        <FigurePlanUpload planId={plan.id} />
      </div>

      <div style={{ marginTop: "10px" }}>
        <AgentChat key={plan.id} planId={plan.id} />
      </div>
    </div>
  )
}

function FigurePlanEditorOverlay({
  systemId,
  plan,
  sections,
  onClose,
}: Readonly<{
  systemId: string
  plan: FigurePlanDetail
  sections: Section[]
  onClose: () => void
}>) {
  const patchMut = usePatchFigurePlan(systemId)
  const [draft, setDraft] = useState<FigurePlanDraft>(() => buildDraftFromPlan(plan))

  useEffect(() => {
    setDraft(buildDraftFromPlan(plan))
  }, [plan])

  function handleDraftChange<K extends keyof FigurePlanDraft>(key: K, value: FigurePlanDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }))
  }

  function handleSave() {
    const input: FigurePlanPatchInput = {
      figureNo: draft.figureNo,
      title: draft.title,
      claimText: draft.claimText,
      briefText: draft.briefText.trim() ? draft.briefText : null,
      sectionKey: draft.sectionKey || null,
    }

    patchMut.mutate(
      { planId: plan.id, input },
      {
        onSuccess: () => {
          onClose()
        },
      },
    )
  }

  return (
    <div style={editorOverlayStyle}>
      <div role="dialog" aria-modal="true" aria-labelledby="figure-plan-editor-title" style={editorCardStyle}>
        <div style={editorHeaderStyle}>
          <div>
            <div id="figure-plan-editor-title" style={{ fontSize: "16px", fontWeight: 700, color: "#f8fafc" }}>
              编辑图表规划
            </div>
            <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>
              {plan.figureNo}: {plan.title}
            </div>
          </div>
          <button
            type="button"
            aria-label="Close Figure Plan Editor"
            onClick={onClose}
            style={buttonBaseStyle}
          >
            关闭
          </button>
        </div>
        <div style={editorBodyStyle}>
          <div style={fieldBlockStyle}>
            <label style={fieldLabelStyle}>
              Figure No
              <input
                aria-label="Figure No"
                value={draft.figureNo}
                onChange={(event) => handleDraftChange("figureNo", event.target.value)}
                style={inputStyle}
              />
            </label>
          </div>

          <div style={fieldBlockStyle}>
            <label style={fieldLabelStyle}>
              Title
              <input
                aria-label="Title"
                value={draft.title}
                onChange={(event) => handleDraftChange("title", event.target.value)}
                style={inputStyle}
              />
            </label>
          </div>

          <div style={fieldBlockStyle}>
            <label style={fieldLabelStyle}>
              Claim Text
              <textarea
                aria-label="Claim Text"
                value={draft.claimText}
                onChange={(event) => handleDraftChange("claimText", event.target.value)}
                style={textareaStyle}
              />
            </label>
          </div>

          <div style={fieldBlockStyle}>
            <label style={fieldLabelStyle}>
              Section
              <select
                aria-label="Section"
                value={draft.sectionKey}
                onChange={(event) => handleDraftChange("sectionKey", event.target.value)}
                style={selectStyle}
              >
                <option value="">未关联</option>
                {sections.map((section) => (
                  <option key={section.sectionKey} value={section.sectionKey}>
                    {section.title}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div style={fieldBlockStyle}>
            <label style={fieldLabelStyle}>
              Brief Text
              <textarea
                aria-label="Brief Text"
                value={draft.briefText}
                onChange={(event) => handleDraftChange("briefText", event.target.value)}
                style={textareaStyle}
              />
            </label>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
            <button type="button" aria-label="Cancel Editing" onClick={onClose} style={buttonBaseStyle}>
              取消
            </button>
            <button
              type="button"
              aria-label="Save Figure Plan"
              onClick={handleSave}
              disabled={patchMut.isPending}
              style={patchMut.isPending ? { ...primaryButtonStyle, ...buttonDisabledStyle } : primaryButtonStyle}
            >
              {patchMut.isPending ? "保存中..." : "保存"}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
