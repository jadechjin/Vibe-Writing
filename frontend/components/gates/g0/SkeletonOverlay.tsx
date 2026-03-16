"use client"

import { useCallback, useEffect, useState, type CSSProperties, type ReactNode } from "react"

import {
  useSkeletons,
  useSkeleton,
  useGenerateSkeleton,
  useConfirmSkeleton,
  useDeleteSkeleton,
  usePatchSkeleton,
} from "../../../hooks/useSkeletons"
import type { SkeletonSummary } from "../../../hooks/useSkeletons"

// ---- Types ----

type DimensionKey =
  | "sections"
  | "research_questions"
  | "analysis_strategy"
  | "figure_framework"
  | "argument_chains"
  | "cross_experiment_links"

const DIMENSIONS: { key: DimensionKey; label: string }[] = [
  { key: "sections", label: "章节结构" },
  { key: "research_questions", label: "研究问题" },
  { key: "analysis_strategy", label: "分析策略" },
  { key: "figure_framework", label: "图表框架" },
  { key: "argument_chains", label: "论证链" },
  { key: "cross_experiment_links", label: "实验关联" },
]

import GenerationPanel from "./GenerationPanel"

export type SkeletonOverlayProps = Readonly<{
  systemId: string
  isReadOnly: boolean
  onClose: () => void
  initialMode?: "list" | "generating"
}>

// ---- Styles ----

const backdropStyle: CSSProperties = {
  position: "fixed",
  top: 0, left: 0, right: 0, bottom: 0,
  background: "rgba(0, 0, 0, 0.55)",
  backdropFilter: "blur(6px)",
  WebkitBackdropFilter: "blur(6px)",
  zIndex: 1000,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
}

const panelStyle: CSSProperties = {
  width: "90vw", maxWidth: "960px", maxHeight: "85vh",
  borderRadius: "16px",
  border: "1px solid rgba(148, 163, 184, 0.15)",
  background: "rgba(15, 23, 42, 0.95)",
  boxShadow: "0 25px 50px rgba(0, 0, 0, 0.5)",
  display: "flex", flexDirection: "column", overflow: "hidden",
}

const headerStyle: CSSProperties = {
  display: "flex", justifyContent: "space-between", alignItems: "center",
  padding: "16px 20px",
  borderBottom: "1px solid rgba(148, 163, 184, 0.1)",
  flexShrink: 0,
}

const titleStyle: CSSProperties = { fontSize: "15px", fontWeight: 700, color: "#f8fafc" }

const closeBtnStyle: CSSProperties = {
  width: "32px", height: "32px", borderRadius: "8px",
  border: "1px solid rgba(148, 163, 184, 0.15)",
  background: "transparent", color: "#94a3b8", fontSize: "16px",
  cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
}

const scrollAreaStyle: CSSProperties = {
  flex: 1, overflowY: "auto", padding: "16px 20px",
  display: "flex", flexDirection: "column", gap: "10px",
}

const cardStyle: CSSProperties = {
  padding: "14px 16px", borderRadius: "12px",
  border: "1px solid rgba(148, 163, 184, 0.15)",
  background: "rgba(15, 23, 42, 0.5)",
  cursor: "pointer",
}

const cardExpandedStyle: CSSProperties = {
  ...cardStyle, borderColor: "rgba(251, 146, 60, 0.3)", cursor: "default",
}

const cardHeaderStyle: CSSProperties = {
  display: "flex", justifyContent: "space-between", alignItems: "center",
}

const versionStyle: CSSProperties = { fontSize: "13px", fontWeight: 700, color: "#e2e8f0" }
const summaryStyle: CSSProperties = { fontSize: "12px", color: "#94a3b8", marginLeft: "8px" }
const timeStyle: CSSProperties = { fontSize: "11px", color: "#64748b" }

const btnBase: CSSProperties = {
  padding: "6px 14px", borderRadius: "10px", fontSize: "12px", fontWeight: 600, cursor: "pointer",
}
const genBtnStyle: CSSProperties = {
  ...btnBase, border: "1px solid rgba(249,115,22,0.5)",
  background: "rgba(154,52,18,0.15)", color: "#fb923c",
}
const confirmBtnStyle: CSSProperties = {
  ...btnBase, padding: "4px 12px", borderRadius: "8px",
  border: "1px solid rgba(74,222,128,0.5)",
  background: "rgba(22,101,52,0.15)", color: "#4ade80",
}
const editBtnStyle: CSSProperties = {
  ...btnBase, padding: "4px 12px", borderRadius: "8px",
  border: "1px solid rgba(96,165,250,0.5)",
  background: "rgba(30,64,175,0.15)", color: "#60a5fa",
}
const deleteBtnStyle: CSSProperties = {
  ...btnBase, padding: "4px 12px", borderRadius: "8px",
  border: "1px solid rgba(248,113,113,0.5)",
  background: "rgba(127,29,29,0.15)", color: "#f87171",
}
const btnDisabled: CSSProperties = { opacity: 0.4, cursor: "not-allowed" }

const dimTabBarStyle: CSSProperties = {
  display: "flex", gap: "2px", marginTop: "12px",
  borderBottom: "1px solid rgba(148,163,184,0.1)", flexWrap: "wrap",
}
const dimTabStyle: CSSProperties = {
  padding: "6px 12px", fontSize: "12px", fontWeight: 600, color: "#64748b",
  background: "transparent", border: "none",
  borderBottom: "2px solid transparent", cursor: "pointer", whiteSpace: "nowrap",
}
const dimTabActiveStyle: CSSProperties = {
  ...dimTabStyle, color: "#fb923c", borderBottomColor: "#fb923c",
}

const dimContentStyle: CSSProperties = {
  marginTop: "12px", padding: "12px 14px", borderRadius: "10px",
  background: "rgba(15,23,42,0.7)", border: "1px solid rgba(148,163,184,0.08)",
  fontSize: "13px", color: "#cbd5e1", lineHeight: 1.6,
  maxHeight: "320px", overflowY: "auto",
}

const emptyDimStyle: CSSProperties = {
  fontSize: "12px", color: "#64748b", padding: "16px 0", textAlign: "center",
}

const feedbackStyle: CSSProperties = {
  fontSize: "12px", padding: "6px 10px", borderRadius: "8px", margin: "0 20px",
}

const textareaStyle: CSSProperties = {
  width: "100%", minHeight: "200px", padding: "10px 12px", borderRadius: "8px",
  border: "1px solid rgba(148,163,184,0.2)", background: "rgba(15,23,42,0.8)",
  color: "#e2e8f0", fontSize: "12px", fontFamily: "monospace", lineHeight: 1.6,
  resize: "vertical", outline: "none",
}

const emptyStyle: CSSProperties = {
  fontSize: "13px", color: "#64748b", textAlign: "center", padding: "40px 0",
}

const badgeBase: CSSProperties = {
  fontSize: "11px", fontWeight: 600, padding: "2px 8px", borderRadius: "6px",
}

const importanceBadgeStyle = (level: string): CSSProperties => {
  const colors: Record<string, { color: string; bg: string }> = {
    high: { color: "#f87171", bg: "rgba(127,29,29,0.2)" },
    medium: { color: "#fbbf24", bg: "rgba(120,53,15,0.2)" },
    low: { color: "#94a3b8", bg: "rgba(148,163,184,0.1)" },
  }
  const c = colors[level] ?? colors.low
  return { ...badgeBase, color: c.color, background: c.bg }
}

function statusBadge(status: string): CSSProperties {
  if (status === "confirmed")
    return { ...badgeBase, color: "#4ade80", background: "rgba(22,101,52,0.2)" }
  return { ...badgeBase, color: "#fbbf24", background: "rgba(120,53,15,0.2)" }
}

// ---- sub-item card style ----
const subCardStyle: CSSProperties = {
  padding: "10px 12px", borderRadius: "8px",
  border: "1px solid rgba(148,163,184,0.08)",
  background: "rgba(15,23,42,0.5)", marginBottom: "8px",
}
const subLabelStyle: CSSProperties = { fontSize: "11px", color: "#64748b", marginBottom: "2px" }
const subValueStyle: CSSProperties = { fontSize: "13px", color: "#e2e8f0" }
const tagStyle: CSSProperties = {
  display: "inline-block", fontSize: "10px", padding: "1px 6px", borderRadius: "4px",
  background: "rgba(148,163,184,0.1)", color: "#94a3b8", marginRight: "4px",
}

// ---- Inline edit styles ----

const subCardEditableStyle: CSSProperties = {
  ...subCardStyle, position: "relative", cursor: "pointer",
  transition: "border-color 0.15s",
}

const subCardEditingStyle: CSSProperties = {
  ...subCardStyle, position: "relative", cursor: "default",
  borderColor: "rgba(96,165,250,0.4)", background: "rgba(15,23,42,0.7)",
}

const pencilBtnStyle: CSSProperties = {
  position: "absolute", top: "8px", right: "8px",
  width: "22px", height: "22px", borderRadius: "6px",
  border: "1px solid rgba(148,163,184,0.15)", background: "rgba(15,23,42,0.6)",
  color: "#64748b", fontSize: "11px", cursor: "pointer",
  display: "flex", alignItems: "center", justifyContent: "center",
  transition: "color 0.15s, border-color 0.15s",
}

const inlineInputStyle: CSSProperties = {
  width: "100%", padding: "6px 8px", borderRadius: "6px",
  border: "1px solid rgba(148,163,184,0.16)", background: "rgba(15,23,42,0.6)",
  color: "#e2e8f0", fontSize: "12px", outline: "none",
}

const inlineTextareaStyle: CSSProperties = {
  ...inlineInputStyle, minHeight: "56px", resize: "vertical", lineHeight: 1.5,
}

const inlineSelectStyle: CSSProperties = {
  ...inlineInputStyle, appearance: "none" as const,
}

const inlineFieldLabel: CSSProperties = {
  fontSize: "10px", color: "#64748b", fontWeight: 600, marginBottom: "2px",
}

const inlineFieldBlock: CSSProperties = {
  display: "flex", flexDirection: "column", gap: "2px", marginBottom: "6px",
}

const inlineActionRow: CSSProperties = {
  display: "flex", gap: "6px", justifyContent: "flex-end", marginTop: "6px",
}

const inlineSaveBtnStyle: CSSProperties = {
  ...btnBase, padding: "4px 12px", borderRadius: "8px",
  border: "1px solid rgba(74,222,128,0.5)",
  background: "rgba(22,101,52,0.15)", color: "#4ade80", fontSize: "11px",
}

const inlineCancelBtnStyle: CSSProperties = {
  ...btnBase, padding: "4px 12px", borderRadius: "8px",
  border: "1px solid rgba(148,163,184,0.2)",
  background: "transparent", color: "#94a3b8", fontSize: "11px",
}

const tagEditableStyle: CSSProperties = {
  ...tagStyle, cursor: "default", display: "inline-flex", alignItems: "center", gap: "4px",
}

const tagRemoveBtnStyle: CSSProperties = {
  background: "none", border: "none", color: "#94a3b8", fontSize: "10px",
  cursor: "pointer", padding: "0 1px", lineHeight: 1,
}

const tagAddRowStyle: CSSProperties = {
  display: "inline-flex", gap: "4px", alignItems: "center", marginTop: "4px",
}

const tagAddInputStyle: CSSProperties = {
  padding: "2px 6px", borderRadius: "4px", fontSize: "10px",
  border: "1px solid rgba(148,163,184,0.15)", background: "rgba(15,23,42,0.5)",
  color: "#e2e8f0", outline: "none", width: "100px",
}

const tagAddBtnStyle: CSSProperties = {
  padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 600,
  border: "1px solid rgba(96,165,250,0.4)", background: "rgba(30,64,175,0.1)",
  color: "#60a5fa", cursor: "pointer",
}

// ---- TagInput component ----

function TagInput({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const [input, setInput] = useState("")
  function handleAdd() {
    const trimmed = input.trim()
    if (!trimmed || value.includes(trimmed)) return
    onChange([...value, trimmed])
    setInput("")
  }
  return (
    <div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
        {value.map((tag) => (
          <span key={tag} style={tagEditableStyle}>
            {tag}
            <button type="button" style={tagRemoveBtnStyle}
              onClick={() => onChange(value.filter((t) => t !== tag))}>✕</button>
          </span>
        ))}
      </div>
      <div style={tagAddRowStyle}>
        <input style={tagAddInputStyle} value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleAdd() } }}
          placeholder="输入后回车" />
        <button type="button" style={tagAddBtnStyle} onClick={handleAdd}>添加</button>
      </div>
    </div>
  )
}

// ---- Inline edit form renderers ----

type InlineEditProps = {
  isEditable: boolean
  editingIndex: number | null
  onStartEdit: (index: number) => void
  onSaveItem: (index: number, updated: Record<string, unknown>) => void
  onCancelEdit: () => void
  isSaving: boolean
  onSaveTopLevelField?: (field: string, value: unknown) => void
}

function SectionEditForm({ item, onSave, onCancel, isSaving }: {
  item: Record<string, unknown>; onSave: (v: Record<string, unknown>) => void; onCancel: () => void; isSaving: boolean
}) {
  const [key, setKey] = useState(String(item.key ?? ""))
  const [title, setTitle] = useState(String(item.title ?? ""))
  const [description, setDescription] = useState(String(item.description ?? ""))
  return (
    <>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>Key</div>
        <input style={inlineInputStyle} value={key} onChange={(e) => setKey(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>标题</div>
        <input style={inlineInputStyle} value={title} onChange={(e) => setTitle(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>描述</div>
        <textarea style={inlineTextareaStyle} value={description} onChange={(e) => setDescription(e.target.value)} /></div>
      <div style={inlineActionRow}>
        <button type="button" style={inlineCancelBtnStyle} onClick={onCancel}>取消</button>
        <button type="button" style={isSaving ? { ...inlineSaveBtnStyle, ...btnDisabled } : inlineSaveBtnStyle}
          disabled={isSaving} onClick={() => onSave({ ...item, key, title, description })}>
          {isSaving ? "保存中..." : "保存"}</button>
      </div>
    </>
  )
}

function ResearchQuestionEditForm({ item, onSave, onCancel, isSaving }: {
  item: Record<string, unknown>; onSave: (v: Record<string, unknown>) => void; onCancel: () => void; isSaving: boolean
}) {
  const [question, setQuestion] = useState(String(item.question ?? ""))
  const [hypothesis, setHypothesis] = useState(String(item.hypothesis ?? ""))
  const [rationale, setRationale] = useState(String(item.rationale ?? ""))
  const [relatedSections, setRelatedSections] = useState<string[]>(
    Array.isArray(item.related_sections) ? (item.related_sections as string[]) : [],
  )
  return (
    <>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>研究问题</div>
        <textarea style={inlineTextareaStyle} value={question} onChange={(e) => setQuestion(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>假设</div>
        <textarea style={inlineTextareaStyle} value={hypothesis} onChange={(e) => setHypothesis(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>依据</div>
        <textarea style={inlineTextareaStyle} value={rationale} onChange={(e) => setRationale(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>关联章节</div>
        <TagInput value={relatedSections} onChange={setRelatedSections} /></div>
      <div style={inlineActionRow}>
        <button type="button" style={inlineCancelBtnStyle} onClick={onCancel}>取消</button>
        <button type="button" style={isSaving ? { ...inlineSaveBtnStyle, ...btnDisabled } : inlineSaveBtnStyle}
          disabled={isSaving} onClick={() => onSave({ ...item, question, hypothesis, rationale, related_sections: relatedSections })}>
          {isSaving ? "保存中..." : "保存"}</button>
      </div>
    </>
  )
}

function AnalysisMethodEditForm({ item, onSave, onCancel, isSaving }: {
  item: Record<string, unknown>; onSave: (v: Record<string, unknown>) => void; onCancel: () => void; isSaving: boolean
}) {
  const [name, setName] = useState(String(item.name ?? ""))
  const [purpose, setPurpose] = useState(String(item.purpose ?? ""))
  const [dataReq, setDataReq] = useState(String(item.data_requirements ?? ""))
  const [addrQ, setAddrQ] = useState<string[]>(
    Array.isArray(item.addresses_questions) ? (item.addresses_questions as string[]) : [],
  )
  return (
    <>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>方法名称</div>
        <input style={inlineInputStyle} value={name} onChange={(e) => setName(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>目的</div>
        <textarea style={inlineTextareaStyle} value={purpose} onChange={(e) => setPurpose(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>数据需求</div>
        <textarea style={inlineTextareaStyle} value={dataReq} onChange={(e) => setDataReq(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>关联问题</div>
        <TagInput value={addrQ} onChange={setAddrQ} /></div>
      <div style={inlineActionRow}>
        <button type="button" style={inlineCancelBtnStyle} onClick={onCancel}>取消</button>
        <button type="button" style={isSaving ? { ...inlineSaveBtnStyle, ...btnDisabled } : inlineSaveBtnStyle}
          disabled={isSaving} onClick={() => onSave({ ...item, name, purpose, data_requirements: dataReq, addresses_questions: addrQ })}>
          {isSaving ? "保存中..." : "保存"}</button>
      </div>
    </>
  )
}

function FigureFrameworkEditForm({ item, onSave, onCancel, isSaving }: {
  item: Record<string, unknown>; onSave: (v: Record<string, unknown>) => void; onCancel: () => void; isSaving: boolean
}) {
  const [figureId, setFigureId] = useState(String(item.figure_id ?? ""))
  const [title, setTitle] = useState(String(item.title ?? ""))
  const [type, setType] = useState(String(item.type ?? ""))
  const [importance, setImportance] = useState(String(item.importance ?? "medium"))
  const [purpose, setPurpose] = useState(String(item.purpose ?? ""))
  const [dataSource, setDataSource] = useState(String(item.data_source ?? ""))
  const [dataPrep, setDataPrep] = useState(String(item.data_preparation ?? ""))
  const [dataQuestion, setDataQuestion] = useState(String(item.data_question ?? ""))
  return (
    <>
      <div style={{ display: "flex", gap: "8px" }}>
        <div style={{ ...inlineFieldBlock, flex: 1 }}><div style={inlineFieldLabel}>Figure ID</div>
          <input style={inlineInputStyle} value={figureId} onChange={(e) => setFigureId(e.target.value)} /></div>
        <div style={{ ...inlineFieldBlock, flex: 1 }}><div style={inlineFieldLabel}>类型</div>
          <input style={inlineInputStyle} value={type} onChange={(e) => setType(e.target.value)} /></div>
        <div style={{ ...inlineFieldBlock, width: "100px" }}><div style={inlineFieldLabel}>重要性</div>
          <select style={inlineSelectStyle} value={importance} onChange={(e) => setImportance(e.target.value)}>
            <option value="high">high</option><option value="medium">medium</option><option value="low">low</option>
          </select></div>
      </div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>标题</div>
        <input style={inlineInputStyle} value={title} onChange={(e) => setTitle(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>目的</div>
        <textarea style={inlineTextareaStyle} value={purpose} onChange={(e) => setPurpose(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>数据来源</div>
        <input style={inlineInputStyle} value={dataSource} onChange={(e) => setDataSource(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>数据准备</div>
        <textarea style={inlineTextareaStyle} value={dataPrep} onChange={(e) => setDataPrep(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>数据问题</div>
        <textarea style={inlineTextareaStyle} value={dataQuestion} onChange={(e) => setDataQuestion(e.target.value)} placeholder="这张图需要回答的具体数据问题" /></div>
      <div style={inlineActionRow}>
        <button type="button" style={inlineCancelBtnStyle} onClick={onCancel}>取消</button>
        <button type="button" style={isSaving ? { ...inlineSaveBtnStyle, ...btnDisabled } : inlineSaveBtnStyle}
          disabled={isSaving} onClick={() => onSave({ ...item, figure_id: figureId, title, type, importance, purpose, data_source: dataSource, data_preparation: dataPrep, data_question: dataQuestion })}>
          {isSaving ? "保存中..." : "保存"}</button>
      </div>
    </>
  )
}

function ArgumentChainEditForm({ item, onSave, onCancel, isSaving }: {
  item: Record<string, unknown>; onSave: (v: Record<string, unknown>) => void; onCancel: () => void; isSaving: boolean
}) {
  const [sectionKey, setSectionKey] = useState(String(item.section_key ?? ""))
  const [claim, setClaim] = useState(String(item.claim ?? ""))
  const [reasoningType, setReasoningType] = useState(String(item.reasoning_type ?? ""))
  const [evidenceNeeded, setEvidenceNeeded] = useState<string[]>(
    Array.isArray(item.evidence_needed) ? (item.evidence_needed as string[]) : [],
  )
  const [dependsOn, setDependsOn] = useState<string[]>(
    Array.isArray(item.depends_on) ? (item.depends_on as string[]) : [],
  )
  return (
    <>
      <div style={{ display: "flex", gap: "8px" }}>
        <div style={{ ...inlineFieldBlock, flex: 1 }}><div style={inlineFieldLabel}>章节 Key</div>
          <input style={inlineInputStyle} value={sectionKey} onChange={(e) => setSectionKey(e.target.value)} /></div>
        <div style={{ ...inlineFieldBlock, flex: 1 }}><div style={inlineFieldLabel}>推理类型</div>
          <input style={inlineInputStyle} value={reasoningType} onChange={(e) => setReasoningType(e.target.value)} /></div>
      </div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>论点</div>
        <textarea style={inlineTextareaStyle} value={claim} onChange={(e) => setClaim(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>所需证据</div>
        <TagInput value={evidenceNeeded} onChange={setEvidenceNeeded} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>依赖</div>
        <TagInput value={dependsOn} onChange={setDependsOn} /></div>
      <div style={inlineActionRow}>
        <button type="button" style={inlineCancelBtnStyle} onClick={onCancel}>取消</button>
        <button type="button" style={isSaving ? { ...inlineSaveBtnStyle, ...btnDisabled } : inlineSaveBtnStyle}
          disabled={isSaving} onClick={() => onSave({ ...item, section_key: sectionKey, claim, reasoning_type: reasoningType, evidence_needed: evidenceNeeded, depends_on: dependsOn })}>
          {isSaving ? "保存中..." : "保存"}</button>
      </div>
    </>
  )
}

function CrossLinkEditForm({ item, onSave, onCancel, isSaving }: {
  item: Record<string, unknown>; onSave: (v: Record<string, unknown>) => void; onCancel: () => void; isSaving: boolean
}) {
  const [fromSection, setFromSection] = useState(String(item.from_section ?? ""))
  const [toSection, setToSection] = useState(String(item.to_section ?? ""))
  const [relationship, setRelationship] = useState(String(item.relationship ?? ""))
  const [description, setDescription] = useState(String(item.description ?? ""))
  const [sharedVars, setSharedVars] = useState<string[]>(
    Array.isArray(item.shared_variables) ? (item.shared_variables as string[]) : [],
  )
  return (
    <>
      <div style={{ display: "flex", gap: "8px" }}>
        <div style={{ ...inlineFieldBlock, flex: 1 }}><div style={inlineFieldLabel}>来源章节</div>
          <input style={inlineInputStyle} value={fromSection} onChange={(e) => setFromSection(e.target.value)} /></div>
        <div style={{ ...inlineFieldBlock, flex: 1 }}><div style={inlineFieldLabel}>目标章节</div>
          <input style={inlineInputStyle} value={toSection} onChange={(e) => setToSection(e.target.value)} /></div>
      </div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>关系</div>
        <input style={inlineInputStyle} value={relationship} onChange={(e) => setRelationship(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>描述</div>
        <textarea style={inlineTextareaStyle} value={description} onChange={(e) => setDescription(e.target.value)} /></div>
      <div style={inlineFieldBlock}><div style={inlineFieldLabel}>共享变量</div>
        <TagInput value={sharedVars} onChange={setSharedVars} /></div>
      <div style={inlineActionRow}>
        <button type="button" style={inlineCancelBtnStyle} onClick={onCancel}>取消</button>
        <button type="button" style={isSaving ? { ...inlineSaveBtnStyle, ...btnDisabled } : inlineSaveBtnStyle}
          disabled={isSaving} onClick={() => onSave({ ...item, from_section: fromSection, to_section: toSection, relationship, description, shared_variables: sharedVars })}>
          {isSaving ? "保存中..." : "保存"}</button>
      </div>
    </>
  )
}

// ---- Editable wrapper for sub-item cards ----

function EditableCard({ index, item, isEditable, editingIndex, onStartEdit, children, editForm }: {
  index: number; item: Record<string, unknown>; isEditable: boolean
  editingIndex: number | null; onStartEdit: (i: number) => void
  children: ReactNode; editForm: ReactNode
}) {
  const isThis = editingIndex === index
  if (isThis) return <div style={subCardEditingStyle}>{editForm}</div>
  return (
    <div style={isEditable ? subCardEditableStyle : subCardStyle}>
      {isEditable && editingIndex === null ? (
        <button type="button" style={pencilBtnStyle} aria-label="编辑此条目"
          onClick={(e) => { e.stopPropagation(); onStartEdit(index) }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "#60a5fa"; (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(96,165,250,0.4)" }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "#64748b"; (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(148,163,184,0.15)" }}>
          ✎
        </button>
      ) : null}
      {children}
    </div>
  )
}

// ---- Dimension renderers (with inline edit support) ----

function renderSections(data: unknown, ep: InlineEditProps): ReactNode {
  if (!Array.isArray(data)) return null
  return data.map((s: Record<string, unknown>, i: number) => (
    <EditableCard key={String(s.key ?? i)} index={i} item={s}
      isEditable={ep.isEditable} editingIndex={ep.editingIndex} onStartEdit={ep.onStartEdit}
      editForm={<SectionEditForm item={s} onSave={(v) => ep.onSaveItem(i, v)} onCancel={ep.onCancelEdit} isSaving={ep.isSaving} />}>
      <div style={{ fontSize: "13px", fontWeight: 600, color: "#e2e8f0" }}>
        {String(s.key ?? "")} — {String(s.title ?? "")}
      </div>
      {s.description ? <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>{String(s.description)}</div> : null}
    </EditableCard>
  ))
}

function renderResearchQuestions(data: unknown, ep: InlineEditProps): ReactNode {
  if (!Array.isArray(data)) return null
  return data.map((rq: Record<string, unknown>, i: number) => (
    <EditableCard key={String(rq.id ?? i)} index={i} item={rq}
      isEditable={ep.isEditable} editingIndex={ep.editingIndex} onStartEdit={ep.onStartEdit}
      editForm={<ResearchQuestionEditForm item={rq} onSave={(v) => ep.onSaveItem(i, v)} onCancel={ep.onCancelEdit} isSaving={ep.isSaving} />}>
      <div style={subValueStyle}>{String(rq.question ?? "")}</div>
      {rq.hypothesis ? (
        <div style={{ marginTop: "4px" }}>
          <span style={subLabelStyle}>假设：</span>
          <span style={{ fontSize: "12px", color: "#94a3b8" }}>{String(rq.hypothesis)}</span>
        </div>
      ) : null}
      {rq.rationale ? (
        <div style={{ marginTop: "4px" }}>
          <span style={subLabelStyle}>依据：</span>
          <span style={{ fontSize: "12px", color: "#94a3b8" }}>{String(rq.rationale)}</span>
        </div>
      ) : null}
      {Array.isArray(rq.related_sections) ? (
        <div style={{ marginTop: "6px" }}>
          {(rq.related_sections as string[]).map((s) => <span key={s} style={tagStyle}>{s}</span>)}
        </div>
      ) : null}
    </EditableCard>
  ))
}

function DataFlowEditor({ value, isEditable, isSaving, onSave }: {
  value: string; isEditable: boolean; isSaving: boolean; onSave: (v: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)

  useEffect(() => { setDraft(value) }, [value])

  if (editing) {
    return (
      <div style={{ padding: "8px 0", borderTop: "1px solid rgba(148,163,184,0.08)" }}>
        <div style={inlineFieldBlock}>
          <div style={inlineFieldLabel}>数据流</div>
          <textarea style={inlineTextareaStyle} value={draft} onChange={(e) => setDraft(e.target.value)} />
        </div>
        <div style={inlineActionRow}>
          <button type="button" style={inlineCancelBtnStyle} onClick={() => { setDraft(value); setEditing(false) }}>取消</button>
          <button type="button" style={isSaving ? { ...inlineSaveBtnStyle, ...btnDisabled } : inlineSaveBtnStyle}
            disabled={isSaving} onClick={() => { onSave(draft); setEditing(false) }}>
            {isSaving ? "保存中..." : "保存"}</button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ fontSize: "12px", color: "#94a3b8", padding: "8px 0", borderTop: "1px solid rgba(148,163,184,0.08)", display: "flex", alignItems: "flex-start", gap: "6px" }}>
      <div style={{ flex: 1 }}>
        <span style={subLabelStyle}>数据流：</span>{value}
      </div>
      {isEditable ? (
        <button type="button" style={{ background: "none", border: "none", color: "#60a5fa", cursor: "pointer", fontSize: "13px", padding: "0 2px", flexShrink: 0 }}
          onClick={() => setEditing(true)} title="编辑数据流">✎</button>
      ) : null}
    </div>
  )
}

function renderAnalysisStrategy(data: unknown, ep: InlineEditProps): ReactNode {
  if (!data || typeof data !== "object") return null
  const obj = data as Record<string, unknown>
  const methods = Array.isArray(obj.methods) ? obj.methods : []
  return (
    <>
      {methods.map((m: Record<string, unknown>, i: number) => (
        <EditableCard key={String(m.id ?? i)} index={i} item={m}
          isEditable={ep.isEditable} editingIndex={ep.editingIndex} onStartEdit={ep.onStartEdit}
          editForm={<AnalysisMethodEditForm item={m} onSave={(v) => ep.onSaveItem(i, v)} onCancel={ep.onCancelEdit} isSaving={ep.isSaving} />}>
          <div style={subValueStyle}>{String(m.name ?? "")}</div>
          {m.purpose ? <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>{String(m.purpose)}</div> : null}
          {m.data_requirements ? (
            <div style={{ marginTop: "4px" }}>
              <span style={subLabelStyle}>数据需求：</span>
              <span style={{ fontSize: "12px", color: "#94a3b8" }}>{String(m.data_requirements)}</span>
            </div>
          ) : null}
          {Array.isArray(m.addresses_questions) ? (
            <div style={{ marginTop: "6px" }}>
              {(m.addresses_questions as string[]).map((q) => <span key={q} style={tagStyle}>{q}</span>)}
            </div>
          ) : null}
        </EditableCard>
      ))}
      {obj.data_flow !== undefined ? (
        <DataFlowEditor
          value={String(obj.data_flow ?? "")}
          isEditable={ep.isEditable}
          isSaving={ep.isSaving}
          onSave={(v) => ep.onSaveTopLevelField?.("data_flow", v)}
        />
      ) : null}
    </>
  )
}

function renderFigureFramework(data: unknown, ep: InlineEditProps): ReactNode {
  if (!Array.isArray(data)) return null
  return data.map((f: Record<string, unknown>, i: number) => (
    <EditableCard key={String(f.figure_id ?? i)} index={i} item={f}
      isEditable={ep.isEditable} editingIndex={ep.editingIndex} onStartEdit={ep.onStartEdit}
      editForm={<FigureFrameworkEditForm item={f} onSave={(v) => ep.onSaveItem(i, v)} onCancel={ep.onCancelEdit} isSaving={ep.isSaving} />}>
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        <span style={subValueStyle}>{String(f.figure_id ?? "")}</span>
        {f.type ? <span style={tagStyle}>{String(f.type)}</span> : null}
        {f.importance ? <span style={importanceBadgeStyle(String(f.importance))}>{String(f.importance)}</span> : null}
      </div>
      <div style={{ fontSize: "13px", color: "#e2e8f0", marginTop: "2px" }}>{String(f.title ?? "")}</div>
      {f.purpose ? <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>{String(f.purpose)}</div> : null}
      {f.data_source ? (
        <div style={{ marginTop: "4px" }}>
          <span style={subLabelStyle}>数据来源：</span>
          <span style={{ fontSize: "12px", color: "#94a3b8" }}>{String(f.data_source)}</span>
        </div>
      ) : null}
      {f.data_preparation ? (
        <div style={{ marginTop: "4px" }}>
          <span style={subLabelStyle}>数据准备：</span>
          <span style={{ fontSize: "12px", color: "#a5b4fc" }}>{String(f.data_preparation)}</span>
        </div>
      ) : null}
      {f.data_question ? (
        <div style={{ marginTop: "4px" }}>
          <span style={subLabelStyle}>数据问题：</span>
          <span style={{ fontSize: "12px", color: "#fbbf24" }}>{String(f.data_question)}</span>
        </div>
      ) : null}
    </EditableCard>
  ))
}

function renderArgumentChains(data: unknown, ep: InlineEditProps): ReactNode {
  if (!Array.isArray(data)) return null
  return data.map((a: Record<string, unknown>, i: number) => (
    <EditableCard key={String(a.section_key ?? i)} index={i} item={a}
      isEditable={ep.isEditable} editingIndex={ep.editingIndex} onStartEdit={ep.onStartEdit}
      editForm={<ArgumentChainEditForm item={a} onSave={(v) => ep.onSaveItem(i, v)} onCancel={ep.onCancelEdit} isSaving={ep.isSaving} />}>
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        <span style={{ ...subValueStyle, fontWeight: 600 }}>{String(a.section_key ?? "")}</span>
        {a.reasoning_type ? <span style={tagStyle}>{String(a.reasoning_type)}</span> : null}
      </div>
      <div style={{ fontSize: "13px", color: "#e2e8f0", marginTop: "4px" }}>{String(a.claim ?? "")}</div>
      {Array.isArray(a.evidence_needed) && a.evidence_needed.length > 0 ? (
        <div style={{ marginTop: "6px" }}>
          <span style={subLabelStyle}>所需证据：</span>
          {(a.evidence_needed as string[]).map((e) => <span key={e} style={tagStyle}>{e}</span>)}
        </div>
      ) : null}
      {Array.isArray(a.depends_on) && a.depends_on.length > 0 ? (
        <div style={{ marginTop: "4px" }}>
          <span style={subLabelStyle}>依赖：</span>
          {(a.depends_on as string[]).map((d) => <span key={d} style={tagStyle}>{d}</span>)}
        </div>
      ) : null}
    </EditableCard>
  ))
}

function renderCrossExperimentLinks(data: unknown, ep: InlineEditProps): ReactNode {
  if (!Array.isArray(data)) return null
  return data.map((link: Record<string, unknown>, i: number) => (
    <EditableCard key={i} index={i} item={link}
      isEditable={ep.isEditable} editingIndex={ep.editingIndex} onStartEdit={ep.onStartEdit}
      editForm={<CrossLinkEditForm item={link} onSave={(v) => ep.onSaveItem(i, v)} onCancel={ep.onCancelEdit} isSaving={ep.isSaving} />}>
      <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontSize: "13px", color: "#60a5fa" }}>{String(link.from_section ?? "")}</span>
        <span style={{ fontSize: "11px", color: "#64748b" }}>→</span>
        <span style={{ fontSize: "13px", color: "#60a5fa" }}>{String(link.to_section ?? "")}</span>
        {link.relationship ? <span style={tagStyle}>{String(link.relationship)}</span> : null}
      </div>
      {link.description ? <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>{String(link.description)}</div> : null}
      {Array.isArray(link.shared_variables) && link.shared_variables.length > 0 ? (
        <div style={{ marginTop: "4px" }}>
          <span style={subLabelStyle}>共享变量：</span>
          {(link.shared_variables as string[]).map((v) => <span key={v} style={tagStyle}>{v}</span>)}
        </div>
      ) : null}
    </EditableCard>
  ))
}

function renderDimension(key: DimensionKey, json: Record<string, unknown>, ep: InlineEditProps): ReactNode {
  const data = json[key]
  if (data === undefined || data === null) return <div style={emptyDimStyle}>该维度暂无数据</div>
  try {
    switch (key) {
      case "sections": return renderSections(data, ep)
      case "research_questions": return renderResearchQuestions(data, ep)
      case "analysis_strategy": return renderAnalysisStrategy(data, ep)
      case "figure_framework": return renderFigureFramework(data, ep)
      case "argument_chains": return renderArgumentChains(data, ep)
      case "cross_experiment_links": return renderCrossExperimentLinks(data, ep)
      default: return <pre style={{ fontSize: "12px", color: "#94a3b8", whiteSpace: "pre-wrap" }}>{JSON.stringify(data, null, 2)}</pre>
    }
  } catch {
    return <pre style={{ fontSize: "12px", color: "#94a3b8", whiteSpace: "pre-wrap" }}>{JSON.stringify(data, null, 2)}</pre>
  }
}

// ---- Component ----

export function SkeletonOverlay({ systemId, isReadOnly, onClose, initialMode = "list" }: SkeletonOverlayProps) {
  const { data: skeletons, isLoading } = useSkeletons(systemId)
  const generateMut = useGenerateSkeleton(systemId)
  const confirmMut = useConfirmSkeleton(systemId)
  const deleteMut = useDeleteSkeleton(systemId)
  const patchMut = usePatchSkeleton(systemId)

  const [generationMode, setGenerationMode] = useState<"list" | "generating">(initialMode)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [activeDim, setActiveDim] = useState<DimensionKey>("sections")
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; msg: string } | null>(null)
  const [editJson, setEditJson] = useState("")
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [editingItemIndex, setEditingItemIndex] = useState<number | null>(null)

  const { data: expandedDetail } = useSkeleton(expandedId ?? "")

  // Escape key + body scroll lock
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        if (editingItemIndex !== null) { setEditingItemIndex(null); return }
        if (!isEditing) onClose()
      }
    }
    document.addEventListener("keydown", onKey)
    return () => {
      document.body.style.overflow = prev
      document.removeEventListener("keydown", onKey)
    }
  }, [onClose, isEditing, editingItemIndex])

  function showFeedback(type: "success" | "error", msg: string) {
    setFeedback({ type, msg })
    setTimeout(() => setFeedback(null), 3000)
  }

  function handleStartGeneration() {
    setGenerationMode("generating")
  }

  function handleConfirm(skeletonId: string) {
    confirmMut.mutate(skeletonId, {
      onSuccess: () => showFeedback("success", "骨架已确认，章节结构已更新"),
      onError: () => showFeedback("error", "确认失败，请重试"),
    })
  }

  function handleDelete(skeletonId: string) {
    if (!window.confirm("确定要删除这个骨架吗？同时会清理相关临时文件。")) return
    deleteMut.mutate(skeletonId, {
      onSuccess: () => {
        if (expandedId === skeletonId) setExpandedId(null)
        showFeedback("success", "骨架已删除")
      },
      onError: () => showFeedback("error", "删除失败，已确认的骨架不可删除"),
    })
  }

  function handleToggle(id: string) {
    if (expandedId === id) { setExpandedId(null); setIsEditing(false); setEditingItemIndex(null) }
    else { setExpandedId(id); setIsEditing(false); setEditingItemIndex(null); setActiveDim("sections") }
  }

  function handleStartEdit() {
    if (!expandedDetail) return
    setEditingItemIndex(null)
    setEditJson(JSON.stringify(expandedDetail.skeletonJson, null, 2))
    setJsonError(null)
    setIsEditing(true)
  }

  function handleStartInlineEdit(index: number) {
    setIsEditing(false)
    setJsonError(null)
    setEditingItemIndex(index)
  }

  const handleSaveInlineItem = useCallback((index: number, updated: Record<string, unknown>) => {
    if (!expandedId || !expandedDetail) return
    const json = structuredClone(expandedDetail.skeletonJson) as Record<string, unknown>

    if (activeDim === "analysis_strategy") {
      const strategy = (json.analysis_strategy ?? {}) as Record<string, unknown>
      const methods = Array.isArray(strategy.methods) ? [...strategy.methods] : []
      methods[index] = updated
      json.analysis_strategy = { ...strategy, methods }
    } else {
      const arr = Array.isArray(json[activeDim]) ? [...(json[activeDim] as unknown[])] : []
      arr[index] = updated
      json[activeDim] = arr
    }

    patchMut.mutate(
      { skeletonId: expandedId, input: { skeletonJson: json, changeSummary: "内联编辑" } },
      {
        onSuccess: () => { setEditingItemIndex(null); showFeedback("success", "已保存") },
        onError: () => showFeedback("error", "保存失败，请重试"),
      },
    )
  }, [expandedId, expandedDetail, activeDim, patchMut])

  const handleSaveTopLevelField = useCallback((field: string, value: unknown) => {
    if (!expandedId || !expandedDetail) return
    const json = structuredClone(expandedDetail.skeletonJson) as Record<string, unknown>

    if (activeDim === "analysis_strategy") {
      const strategy = (json.analysis_strategy ?? {}) as Record<string, unknown>
      json.analysis_strategy = { ...strategy, [field]: value }
    } else {
      json[field] = value
    }

    patchMut.mutate(
      { skeletonId: expandedId, input: { skeletonJson: json, changeSummary: "内联编辑" } },
      {
        onSuccess: () => showFeedback("success", "已保存"),
        onError: () => showFeedback("error", "保存失败，请重试"),
      },
    )
  }, [expandedId, expandedDetail, activeDim, patchMut])

  function handleSaveEdit() {
    if (!expandedId) return
    let parsed: Record<string, unknown>
    try { parsed = JSON.parse(editJson) } catch {
      setJsonError("JSON 格式错误，请检查语法"); return
    }
    setJsonError(null)
    patchMut.mutate(
      { skeletonId: expandedId, input: { skeletonJson: parsed, changeSummary: "手动编辑" } },
      {
        onSuccess: () => { setIsEditing(false); showFeedback("success", "骨架已保存") },
        onError: () => showFeedback("error", "保存失败，请重试"),
      },
    )
  }

  const canGenerate = !isReadOnly && !generateMut.isPending
  const isBusy = generateMut.isPending || confirmMut.isPending || patchMut.isPending || deleteMut.isPending

  return (
    <div style={backdropStyle} onClick={onClose}>
      <div style={panelStyle} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={headerStyle}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={titleStyle}>
              {generationMode === "generating" ? "AI 生成向导" : `结构骨架 (${skeletons?.length ?? 0})`}
            </div>
            {!isReadOnly && generationMode === "list" ? (
              <button type="button" onClick={handleStartGeneration} disabled={!canGenerate}
                style={canGenerate ? genBtnStyle : { ...genBtnStyle, ...btnDisabled }}>
                AI 生成
              </button>
            ) : null}
          </div>
          <button type="button" onClick={onClose} style={closeBtnStyle} aria-label="关闭">✕</button>
        </div>

        {/* Feedback */}
        {feedback ? (
          <div style={{
            ...feedbackStyle,
            color: feedback.type === "success" ? "#4ade80" : "#f87171",
            background: feedback.type === "success" ? "rgba(22,101,52,0.15)" : "rgba(127,29,29,0.15)",
          }}>{feedback.msg}</div>
        ) : null}

        {/* Body */}
        <div style={scrollAreaStyle}>
          {generationMode === "generating" ? (
            <GenerationPanel
              systemId={systemId}
              onComplete={() => {
                setGenerationMode("list")
                showFeedback("success", "骨架生成成功")
              }}
              onCancel={() => setGenerationMode("list")}
            />
          ) : (
            <>
              {isLoading ? (
                <div style={emptyStyle}>加载中...</div>
              ) : !skeletons || skeletons.length === 0 ? (
                <div style={emptyStyle}>暂无结构骨架，点击「AI 生成」创建</div>
              ) : (
                skeletons.map((sk: SkeletonSummary) => {
                  const isExp = expandedId === sk.id
                  const isDraft = sk.status === "draft"
                  return (
                    <div key={sk.id} style={isExp ? cardExpandedStyle : cardStyle}>
                      {/* Card header */}
                      <div style={cardHeaderStyle} onClick={() => handleToggle(sk.id)}
                        role="button" tabIndex={0}
                        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") handleToggle(sk.id) }}>
                        <div style={{ display: "flex", alignItems: "center" }}>
                          <span style={versionStyle}>v{sk.version}</span>
                          {sk.changeSummary ? <span style={summaryStyle}>{sk.changeSummary}</span> : null}
                        </div>
                        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                          <span style={timeStyle}>
                            {sk.createdAt ? new Date(sk.createdAt).toLocaleDateString() : ""}
                          </span>
                          <span style={statusBadge(sk.status)}>{sk.status}</span>
                          {!isReadOnly ? (
                            <>
                              {isDraft ? (
                                <button type="button"
                                  onClick={(e) => { e.stopPropagation(); handleConfirm(sk.id) }}
                                  disabled={isBusy}
                                  style={isBusy ? { ...confirmBtnStyle, ...btnDisabled } : confirmBtnStyle}>
                                  确认
                                </button>
                              ) : null}
                              <button type="button"
                                onClick={(e) => { e.stopPropagation(); handleDelete(sk.id) }}
                                disabled={isBusy}
                                style={isBusy ? { ...deleteBtnStyle, ...btnDisabled } : deleteBtnStyle}>
                                删除
                              </button>
                            </>
                          ) : null}
                        </div>
                      </div>

                      {/* Expanded body */}
                      {isExp ? (
                        <div onClick={(e) => e.stopPropagation()} style={{ marginTop: "8px" }}>
                          {isEditing ? (
                            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                              <textarea style={textareaStyle} value={editJson}
                                onChange={(e) => { setEditJson(e.target.value); setJsonError(null) }}
                                spellCheck={false} />
                              {jsonError ? <div style={{ fontSize: "11px", color: "#f87171" }}>{jsonError}</div> : null}
                              <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                                <button type="button" onClick={() => { setIsEditing(false); setJsonError(null) }}
                                  style={genBtnStyle}>取消</button>
                                <button type="button" onClick={handleSaveEdit}
                                  disabled={patchMut.isPending}
                                  style={patchMut.isPending ? { ...editBtnStyle, ...btnDisabled } : editBtnStyle}>
                                  {patchMut.isPending ? "保存中..." : "保存"}
                                </button>
                              </div>
                            </div>
                          ) : (
                            <>
                              {/* Dimension tabs */}
                              <div style={dimTabBarStyle}>
                                {DIMENSIONS.map((d) => (
                                  <button key={d.key} type="button"
                                    onClick={() => { setActiveDim(d.key); setEditingItemIndex(null) }}
                                    style={activeDim === d.key ? dimTabActiveStyle : dimTabStyle}>
                                    {d.label}
                                  </button>
                                ))}
                              </div>
                              {/* Dimension content */}
                              <div style={dimContentStyle}>
                                {expandedDetail
                                  ? renderDimension(activeDim, expandedDetail.skeletonJson, {
                                      isEditable: !isReadOnly,
                                      editingIndex: editingItemIndex,
                                      onStartEdit: handleStartInlineEdit,
                                      onSaveItem: handleSaveInlineItem,
                                      onCancelEdit: () => setEditingItemIndex(null),
                                      isSaving: patchMut.isPending,
                                      onSaveTopLevelField: handleSaveTopLevelField,
                                    })
                                  : <div style={emptyDimStyle}>加载中...</div>}
                              </div>
                              {/* Edit button */}
                              {!isReadOnly ? (
                                <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "8px" }}>
                                  <button type="button" onClick={handleStartEdit} style={editBtnStyle}>
                                    编辑 JSON
                                  </button>
                                </div>
                              ) : null}
                            </>
                          )}
                        </div>
                      ) : null}
                    </div>
                  )
                })
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
