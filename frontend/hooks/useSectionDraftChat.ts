"use client"

import { useCallback, useRef, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"
import type { DraftChatMessageDetail, DraftContextPack } from "../types/g5"

const draftChatKeys = {
  messages: (systemId: string, sectionKey: string) =>
    ["draftChat", systemId, sectionKey] as const,
  context: (systemId: string, sectionKey: string) =>
    ["draftContext", systemId, sectionKey] as const,
}

export function useDraftChatMessages(
  systemId: string,
  sectionKey: string,
  provider = "claude",
) {
  return useQuery({
    queryKey: draftChatKeys.messages(systemId, sectionKey),
    queryFn: () =>
      apiRequest<DraftChatMessageDetail[]>(
        `/systems/${systemId}/sections/${sectionKey}/draft/chat/messages`,
        { query: { provider } },
      ),
    enabled: !!systemId && !!sectionKey,
  })
}

export function useDraftContext(systemId: string, sectionKey: string) {
  return useQuery({
    queryKey: draftChatKeys.context(systemId, sectionKey),
    queryFn: () =>
      apiRequest<DraftContextPack>(
        `/systems/${systemId}/sections/${sectionKey}/draft/context`,
      ),
    enabled: !!systemId && !!sectionKey,
  })
}

export function useSendDraftChatStream(
  systemId: string,
  sectionKey: string,
) {
  const queryClient = useQueryClient()
  const [streaming, setStreaming] = useState(false)
  const [streamContent, setStreamContent] = useState("")
  const [skillAssets, setSkillAssets] = useState<unknown[]>([])
  const [skillReview, setSkillReview] = useState<unknown[]>([])
  const [skillRevisions, setSkillRevisions] = useState<unknown[]>([])
  const abortRef = useRef<AbortController | null>(null)

  const send = useCallback(
    async (content: string, provider = "claude") => {
      setStreaming(true)
      setStreamContent("")
      setSkillAssets([])
      setSkillReview([])
      setSkillRevisions([])
      const controller = new AbortController()
      abortRef.current = controller

      const baseUrl =
        process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api"
      const url = `${baseUrl}/systems/${systemId}/sections/${sectionKey}/draft/chat`

      try {
        const resp = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content, provider }),
          signal: controller.signal,
        })

        if (!resp.ok || !resp.body) {
          setStreaming(false)
          return
        }

        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let accumulated = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          const text = decoder.decode(value, { stream: true })
          for (const line of text.split("\n")) {
            if (!line.startsWith("data: ")) continue
            try {
              const evt = JSON.parse(line.slice(6))
              if (evt.type === "delta") {
                accumulated += evt.content
                setStreamContent(accumulated)
              } else if (evt.type === "skill_assets") {
                try { setSkillAssets(JSON.parse(evt.content)) } catch { /* skip */ }
              } else if (evt.type === "skill_review") {
                try { setSkillReview(JSON.parse(evt.content)) } catch { /* skip */ }
              } else if (evt.type === "skill_revisions") {
                try { setSkillRevisions(JSON.parse(evt.content)) } catch { /* skip */ }
              }
            } catch {
              // ignore parse errors
            }
          }
        }
      } finally {
        setStreaming(false)
        abortRef.current = null
        queryClient.invalidateQueries({
          queryKey: draftChatKeys.messages(systemId, sectionKey),
        })
      }
    },
    [systemId, sectionKey, queryClient],
  )

  const abort = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return { send, abort, streaming, streamContent, skillAssets, skillReview, skillRevisions }
}
