"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"
import type { DraftValidateResponse } from "../types/g5"

export function useValidateAndSaveDraft(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      sectionKey,
      contentMd,
      outlineId,
    }: {
      sectionKey: string
      contentMd: string
      outlineId?: string
    }) =>
      apiRequest<DraftValidateResponse>(
        `/systems/${systemId}/sections/${sectionKey}/draft/validate-and-save`,
        {
          method: "POST",
          body: JSON.stringify({ contentMd, outlineId }),
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drafts", systemId] })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}
