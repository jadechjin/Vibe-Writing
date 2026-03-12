import type { CSSProperties } from "react"

type ProjectStatsProps = Readonly<{
  completedSystemCount: number
  introductionUnlocked: boolean
  totalSystemCount: number
}>

const REQUIRED_COUNT = 3

const containerStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "12px",
}

const statCardStyle: CSSProperties = {
  padding: "16px 18px",
  borderRadius: "14px",
  border: "1px solid rgba(148, 163, 184, 0.14)",
  background: "rgba(15, 23, 42, 0.55)",
}

const labelStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  color: "#94a3b8",
  marginBottom: "8px",
}

const valueRowStyle: CSSProperties = {
  display: "flex",
  alignItems: "baseline",
  gap: "6px",
}

const valueStyle: CSSProperties = {
  fontSize: "28px",
  fontWeight: 700,
  lineHeight: 1,
}

const unitStyle: CSSProperties = {
  fontSize: "14px",
  color: "#94a3b8",
}

const progressTrackStyle: CSSProperties = {
  height: "6px",
  borderRadius: "3px",
  background: "rgba(51, 65, 85, 0.5)",
  overflow: "hidden",
  marginTop: "10px",
}

const progressFillStyle: CSSProperties = {
  height: "100%",
  borderRadius: "3px",
  transition: "width 0.3s ease",
}

const unlockBadgeBaseStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
  padding: "6px 12px",
  borderRadius: "8px",
  fontSize: "13px",
  fontWeight: 600,
  marginTop: "10px",
}

export function ProjectStats({
  completedSystemCount,
  introductionUnlocked,
  totalSystemCount,
}: ProjectStatsProps) {
  const pct = Math.min(Math.round((completedSystemCount / REQUIRED_COUNT) * 100), 100)
  const isComplete = completedSystemCount >= REQUIRED_COUNT

  return (
    <div style={containerStyle}>
      <div style={statCardStyle}>
        <div style={labelStyle}>体系完成度</div>
        <div style={valueRowStyle}>
          <span
            style={{
              ...valueStyle,
              color: isComplete ? "#4ade80" : "#60a5fa",
            }}
          >
            {completedSystemCount}
          </span>
          <span style={unitStyle}>/ {REQUIRED_COUNT} 个必需</span>
        </div>
        <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
          共创建 {totalSystemCount} 个实验体系
        </div>
        <div style={progressTrackStyle}>
          <div
            style={{
              ...progressFillStyle,
              width: `${pct}%`,
              background: isComplete
                ? "linear-gradient(90deg, #16a34a, #4ade80)"
                : "linear-gradient(90deg, #3b82f6, #60a5fa)",
            }}
          />
        </div>
      </div>

      <div style={statCardStyle}>
        <div style={labelStyle}>绪论与结论</div>
        <div
          style={{
            ...unlockBadgeBaseStyle,
            background: introductionUnlocked
              ? "rgba(20, 83, 45, 0.25)"
              : "rgba(51, 65, 85, 0.3)",
            border: introductionUnlocked
              ? "1px solid rgba(34, 197, 94, 0.4)"
              : "1px solid rgba(148, 163, 184, 0.2)",
            color: introductionUnlocked ? "#4ade80" : "#94a3b8",
          }}
        >
          {introductionUnlocked ? "已解锁" : "未解锁"}
        </div>
        <div style={{ fontSize: "12px", color: "#64748b", marginTop: "8px" }}>
          {introductionUnlocked
            ? "可以开始撰写绪论和结论章节。"
            : `还需完成 ${REQUIRED_COUNT - completedSystemCount} 个体系才能解锁。`}
        </div>
      </div>
    </div>
  )
}
