import type { CSSProperties, ReactNode } from "react"

import { GateNav, DEFAULT_GATE_PLACEHOLDERS, type GateNavItem } from "./GateNav"
import { ProjectWorkspace } from "./ProjectWorkspace"
import type { GateKey } from "../../lib/gateMapping"

type MainShellProps = Readonly<{
  children: ReactNode
  gates?: readonly GateNavItem[]
  evidencePanel?: ReactNode
  workbenchPanel?: ReactNode
  statusTray?: ReactNode
  onGateSelect?: (gateKey: GateKey) => void
  selectedGateKey?: GateKey | null
}>

const shellStyle: CSSProperties = {
  minHeight: "100vh",
  background:
    "radial-gradient(circle at top, rgba(30, 64, 175, 0.18), transparent 34%), linear-gradient(180deg, #020617 0%, #0f172a 56%, #111827 100%)",
  color: "#e2e8f0",
}

const contentStyle: CSSProperties = {
  maxWidth: "1440px",
  margin: "0 auto",
  padding: "24px 24px 28px",
}

export function MainShell({
  children,
  gates = DEFAULT_GATE_PLACEHOLDERS,
  evidencePanel,
  workbenchPanel,
  statusTray,
  onGateSelect,
  selectedGateKey,
}: MainShellProps) {
  return (
    <div style={shellStyle}>
      <GateNav gates={gates} onGateSelect={onGateSelect} selectedGateKey={selectedGateKey} />
      <main style={contentStyle}>
        {children}
        <ProjectWorkspace
          evidencePanel={evidencePanel}
          workbenchPanel={workbenchPanel}
          statusTray={statusTray}
        >
          {null}
        </ProjectWorkspace>
      </main>
    </div>
  )
}
