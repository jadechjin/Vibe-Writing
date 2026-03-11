import type { CSSProperties } from "react"

import { Providers } from "../lib/providers"

const bodyStyle: CSSProperties = {
  margin: 0,
  minHeight: "100vh",
  background: "#020617",
  fontFamily:
    '"Inter", "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="zh-CN">
      <body style={bodyStyle}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
