import type { CSSProperties, ReactNode } from "react"

type ProjectWorkspaceProps = Readonly<{
  children: ReactNode
  evidencePanel?: ReactNode
  workbenchPanel?: ReactNode
  statusTray?: ReactNode
}>

const workspaceStyle: CSSProperties = {
  display: "grid",
  gridTemplateRows: "minmax(0, 1fr) auto",
  gap: "18px",
  minHeight: "calc(100vh - 176px)",
}

const splitPaneStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "minmax(200px, 0.55fr) minmax(0, 1.85fr)",
  gap: "18px",
  minHeight: 0,
}

const panelStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  minHeight: 0,
  borderRadius: "24px",
  border: "1px solid rgba(148, 163, 184, 0.16)",
  background: "rgba(15, 23, 42, 0.74)",
  boxShadow: "0 18px 48px rgba(15, 23, 42, 0.22)",
  overflow: "hidden",
}

const panelHeaderStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
  padding: "18px 20px 0",
}

const panelEyebrowStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 700,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#60a5fa",
}

const panelTitleStyle: CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#f8fafc",
}

const panelSubtitleStyle: CSSProperties = {
  fontSize: "13px",
  lineHeight: 1.5,
  color: "#94a3b8",
}

const panelBodyStyle: CSSProperties = {
  flex: 1,
  minHeight: 0,
  padding: "20px",
}

const statusTrayWrapStyle: CSSProperties = {
  borderRadius: "20px",
  border: "1px solid rgba(148, 163, 184, 0.16)",
  background: "rgba(15, 23, 42, 0.82)",
  boxShadow: "0 12px 32px rgba(15, 23, 42, 0.18)",
  padding: "16px 20px",
}

const defaultEvidencePanel = (
  <div style={{ display: "grid", gap: "14px" }}>
    <section
      style={{
        borderRadius: "18px",
        border: "1px dashed rgba(96, 165, 250, 0.45)",
        background: "rgba(30, 41, 59, 0.45)",
        padding: "18px",
      }}
    >
      <strong style={{ display: "block", marginBottom: "8px", color: "#e2e8f0" }}>
        证据矩阵插槽
      </strong>
      <span style={{ color: "#94a3b8", fontSize: "14px", lineHeight: 1.5 }}>
        用于放置 claim、figure、analysis 与 asset 关联面板。
      </span>
    </section>
    <section
      style={{
        borderRadius: "18px",
        border: "1px dashed rgba(148, 163, 184, 0.3)",
        background: "rgba(15, 23, 42, 0.42)",
        padding: "18px",
        color: "#94a3b8",
        fontSize: "13px",
        lineHeight: 1.5,
      }}
    >
      左栏固定服务于证据浏览，不在布局层发起数据请求。
    </section>
  </div>
)

const defaultWorkbenchPanel = (
  <div style={{ display: "grid", gap: "16px", minHeight: "100%" }}>
    <section
      style={{
        borderRadius: "18px",
        border: "1px dashed rgba(249, 115, 22, 0.38)",
        background: "rgba(30, 41, 59, 0.45)",
        padding: "20px",
      }}
    >
      <strong style={{ display: "block", marginBottom: "8px", color: "#f8fafc" }}>
        Gate 工作台插槽
      </strong>
      <span style={{ color: "#94a3b8", fontSize: "14px", lineHeight: 1.6 }}>
        用于承载 Draft、Outline、Review 或 Gate 审批面板。
      </span>
    </section>
  </div>
)

function WorkspacePanel({
  eyebrow,
  title,
  subtitle,
  children,
}: Readonly<{
  eyebrow: string
  title: string
  subtitle: string
  children: ReactNode
}>) {
  return (
    <section style={panelStyle}>
      <div style={panelHeaderStyle}>
        <span style={panelEyebrowStyle}>{eyebrow}</span>
        <strong style={panelTitleStyle}>{title}</strong>
        <span style={panelSubtitleStyle}>{subtitle}</span>
      </div>
      <div style={panelBodyStyle}>{children}</div>
    </section>
  )
}

export function ProjectWorkspace({
  children,
  evidencePanel,
  workbenchPanel,
  statusTray,
}: ProjectWorkspaceProps) {
  return (
    <div style={workspaceStyle}>
      <div style={splitPaneStyle}>
        <WorkspacePanel
          eyebrow="证据中枢"
          title="证据中枢"
          subtitle="固定双栏中的左侧槽位，面向证据矩阵、图表计划与资产上下文。"
        >
          {evidencePanel ?? defaultEvidencePanel}
        </WorkspacePanel>

        <WorkspacePanel
          eyebrow="工作台"
          title="Gate 工作区"
          subtitle="右侧槽位承载 gate 对应的业务面板，布局层仅提供稳定容器。"
        >
          {workbenchPanel ?? children ?? defaultWorkbenchPanel}
        </WorkspacePanel>
      </div>

      {statusTray ? <section style={statusTrayWrapStyle}>{statusTray}</section> : null}
    </div>
  )
}
