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

const sidebarStyle: CSSProperties = {
  width: "25%", minWidth: "180px",
  borderRight: "1px solid rgba(148,163,184,0.08)",
  overflowY: "auto", padding: "8px 0",
}

const sidebarItemBase: CSSProperties = {
  padding: "8px 14px", fontSize: "12px", fontWeight: 600,
  cursor: "pointer", color: "#94a3b8",
  borderLeft: "3px solid transparent",
}

const sidebarItemActive: CSSProperties = {
  ...sidebarItemBase, color: "#fb923c",
  borderLeftColor: "#fb923c", background: "rgba(249,115,22,0.06)",
}

const middleStyle: CSSProperties = {
  width: "30%", minWidth: "200px",
  borderRight: "1px solid rgba(148,163,184,0.08)",
  overflowY: "auto", padding: "8px",
  display: "flex", flexDirection: "column", gap: "6px",
}

const rightStyle: CSSProperties = {
  flex: 1, overflowY: "auto", padding: "14px",
}

const cardStyle: CSSProperties = {
  padding: "10px 12px", borderRadius: "8px",
  border: "1px solid rgba(148,163,184,0.1)",
  background: "rgba(15,23,42,0.4)", cursor: "pointer",
}

const cardActiveStyle: CSSProperties = {
  ...cardStyle, borderColor: "rgba(251,146,60,0.4)",
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

const cardInlineInputStyle: CSSProperties = {
  width: "100%", padding: "4px 6px", borderRadius: "4px",
  border: "1px solid rgba(148,163,184,0.2)", background: "rgba(15,23,42,0.6)",
  color: "#e2e8f0", fontSize: "12px", outline: "none",
}

const cardInlineBtnRow: CSSProperties = {
  display: "flex", gap: "6px", justifyContent: "flex-end", marginTop: "6px",
}

const cardInlineSaveBtn: CSSProperties = {
  padding: "2px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 600,
  border: "1px solid rgba(74,222,128,0.4)", background: "rgba(22,101,52,0.15)",
  color: "#4ade80", cursor: "pointer",
}

const cardInlineCancelBtn: CSSProperties = {
  padding: "2px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 600,
  border: "1px solid rgba(148,163,184,0.2)", background: "transparent",
  color: "#94a3b8", cursor: "pointer",
}

function InlineCardEditor({ plan, isSaving, onSave, onCancel }: {
  plan: FigurePlanDetail; isSaving: boolean
  onSave: (figureNo: string, title: string) => void; onCancel: () => void
}) {
  const [figureNo, setFigureNo] = useState(plan.figureNo)
  const [title, setTitle] = useState(plan.title)
  return (
    <div onClick={(e) => e.stopPropagation()} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      <input style={cardInlineInputStyle} value={figureNo}
        onChange={(e) => setFigureNo(e.target.value)} placeholder="Figure No" />
      <input style={cardInlineInputStyle} value={title}
        onChange={(e) => setTitle(e.target.value)} placeholder="标题" />
      <div style={cardInlineBtnRow}>
        <button type="button" style={cardInlineCancelBtn} onClick={onCancel}>取消</button>
        <button type="button" style={isSaving ? { ...cardInlineSaveBtn, opacity: 0.5 } : cardInlineSaveBtn}
          disabled={isSaving} onClick={() => onSave(figureNo, title)}>
          {isSaving ? "..." : "保存"}</button>
      </div>
    </div>
  )
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
  const [removedPlanIds, setRemovedPlanIds] = useState<string[]>([])
  const [editingCardId, setEditingCardId] = useState<string | null>(null)
  const patchMut = usePatchFigurePlan(systemId)
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
  const planCountsByFigureId = visiblePlans.reduce((counts, plan) => {
    const fid = normalizeFigureId(plan.figureNo)
    if (fid) counts.set(fid, (counts.get(fid) ?? 0) + 1)
    return counts
  }, new Map<string, number>())
  const filteredPlans = selectedFilterKey === "__all__"
    ? visiblePlans
    : selectedFilterKey === "__unlinked__"
      ? unlinkedPlans
      : visiblePlans.filter((plan) => normalizeFigureId(plan.figureNo) === selectedFilterKey)

  const selectedPlan = filteredPlans.find((plan) => plan.id === selectedPlanId) ?? filteredPlans[0] ?? null

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

    if (nextPlanId) {
      onSelectPlan?.(nextPlanId)
    }
  }

  return (
    <>
      <div style={containerStyle}>
        <div style={sidebarStyle}>
          <div
            style={selectedFilterKey === "__all__" ? sidebarItemActive : sidebarItemBase}
            onClick={() => handleSelectFilter("__all__")}
          >
            全部 ({visiblePlans.length})
          </div>
          {figureFramework.map((fig) => {
            const count = planCountsByFigureId.get(fig.figureId) ?? 0
            return (
              <div
                key={fig.figureId}
                style={selectedFilterKey === fig.figureId ? sidebarItemActive : { ...sidebarItemBase, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                onClick={() => handleSelectFilter(fig.figureId)}
                title={`${fig.figureId}: ${fig.title}`}
              >
                {fig.figureId}: {fig.title} ({count})
              </div>
            )
          })}
          {unlinkedPlans.length > 0 ? (
            <div
              style={selectedFilterKey === "__unlinked__" ? sidebarItemActive : sidebarItemBase}
              onClick={() => handleSelectFilter("__unlinked__")}
            >
              未关联 ({unlinkedPlans.length})
            </div>
          ) : null}
        </div>

        <div style={middleStyle}>
          {filteredPlans.length === 0 ? (
            <div style={emptyStyle}>该筛选条件下暂无图表规划</div>
          ) : (
            filteredPlans.map((plan) => {
              const isActive = selectedPlan?.id === plan.id
              const statusColor = statusColors[plan.status] ?? statusColors.pending
              const isCardEditing = editingCardId === plan.id
              return (
                <div
                  key={plan.id}
                  style={isActive ? cardActiveStyle : cardStyle}
                  onClick={() => { if (!isCardEditing) handleSelectPlan(plan.id) }}
                >
                  <div style={{ display: "flex", gap: "6px", alignItems: "center", marginBottom: "4px" }}>
                    <span style={{ ...badgeBase, color: statusColor.color, background: statusColor.bg }}>{plan.status}</span>
                    {plan.methodJson?.importance ? (
                      <span style={{
                        ...badgeBase,
                        color: (importanceColors[String(plan.methodJson.importance)] ?? importanceColors.low).color,
                        background: (importanceColors[String(plan.methodJson.importance)] ?? importanceColors.low).bg,
                      }}>
                        {String(plan.methodJson.importance)}
                      </span>
                    ) : null}
                    <span style={{ marginLeft: "auto" }} />
                    {!isCardEditing ? (
                      <button type="button" title="编辑" style={cardEditBtnStyle}
                        onClick={(e) => { e.stopPropagation(); setEditingCardId(plan.id) }}>✎</button>
                    ) : null}
                  </div>
                  {isCardEditing ? (
                    <InlineCardEditor
                      plan={plan}
                      isSaving={patchMut.isPending}
                      onSave={(figureNo, title) => {
                        patchMut.mutate(
                          { planId: plan.id, input: { figureNo, title } },
                          { onSuccess: () => setEditingCardId(null) },
                        )
                      }}
                      onCancel={() => setEditingCardId(null)}
                    />
                  ) : (
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "#e2e8f0" }}>
                      {plan.figureNo}: {plan.title}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>

        <div style={rightStyle}>
          {selectedPlan ? (
            <FigurePlanDetailPanel
              key={selectedPlan.id}
              systemId={systemId}
              plan={selectedPlan}
              sections={sections}
              onDeleteSuccess={handleDeleteSuccess}
            />
          ) : (
            <div style={emptyStyle}>选择一个图表规划查看详情</div>
          )}
        </div>
      </div>
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
  sections,
  onDeleteSuccess,
}: Readonly<{
  systemId: string
  plan: FigurePlanDetail
  sections: Section[]
  onDeleteSuccess: (planId: string) => void
}>) {
  const patchMut = usePatchFigurePlan(systemId)
  const deleteMut = useDeleteFigurePlan(systemId)
  const confirmMut = useConfirmFigurePlan(systemId)

  const canConfirm = plan.status !== "confirmed" && plan.status !== "approved" && plan.status !== "delivered"

  const [isEditing, setIsEditing] = useState(false)
  const [draft, setDraft] = useState<FigurePlanDraft>(() => buildDraftFromPlan(plan))

  function handleDraftChange<K extends keyof FigurePlanDraft>(key: K, value: FigurePlanDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }))
  }

  function handleStartEdit() {
    setDraft(buildDraftFromPlan(plan))
    setIsEditing(true)
  }

  function handleCancelEdit() {
    setDraft(buildDraftFromPlan(plan))
    setIsEditing(false)
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
          setIsEditing(false)
        },
      },
    )
  }

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
        {!isEditing ? (
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
              onClick={handleStartEdit}
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
        ) : null}
      </div>

      {isEditing ? (
        <div>
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
            <button
              type="button"
              aria-label="Cancel Editing"
              onClick={handleCancelEdit}
              style={buttonBaseStyle}
            >
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
      ) : (
        <>
          {plan.claimText ? (
            <>
              <div style={detailLabelStyle}>论证目的</div>
              <div style={detailValueStyle}>{plan.claimText}</div>
            </>
          ) : null}

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
        </>
      )}
    </div>
  )
}
