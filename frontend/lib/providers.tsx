"use client"

import type { ReactNode } from "react"
import { QueryClientProvider } from "@tanstack/react-query"

import { queryClient } from "./query"

export function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
