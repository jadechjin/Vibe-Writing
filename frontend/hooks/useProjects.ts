"use client"

import { useCallback } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"

// ---- Domain types (matching backend camelCase responses) ----

export type ProjectSystemSummary = {
  id: string
  systemNo: number
  title: string
  status: string
  sectionCount: number
  createdAt: string
  updatedAt: string
}

export type ProjectListItem = {
  id: string
  name: string
  ownerId: string
  status: string
  templateAssetId: string | null
  systemCount: number
  createdAt: string
  updatedAt: string
}

export type ProjectDetail = ProjectListItem & {
  thesisSchemaJson: Record<string, unknown>
  systems: ProjectSystemSummary[]
  completedSystemCount: number
  introductionUnlocked: boolean
}

export type CreateProjectInput = {
  name: string
  ownerId: string
  templateAssetId?: string | null
  thesisSchemaJson?: Record<string, unknown>
}

export type CreateSystemInput = {
  title: string
}

export type SystemDetail = {
  id: string
  projectId: string
  systemNo: number
  title: string
  status: string
  sections: { id: string; sectionKey: string; title: string; orderNo: number }[]
  createdAt: string
  updatedAt: string
}

// ---- Query keys ----

const projectKeys = {
  all: ["projects"] as const,
  detail: (id: string) => ["projects", id] as const,
}

// ---- Hooks ----

export function useProjectList() {
  return useQuery({
    queryKey: projectKeys.all,
    queryFn: () => apiRequest<ProjectListItem[]>("/projects"),
  })
}

export function useProjectDetail(projectId: string) {
  return useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => apiRequest<ProjectDetail>(`/projects/${projectId}`),
    enabled: !!projectId,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: CreateProjectInput) =>
      apiRequest<ProjectDetail>("/projects", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.all })
    },
  })
}

export function useCreateSystem(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: CreateSystemInput) =>
      apiRequest<SystemDetail>(`/projects/${projectId}/systems`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}

export function useDeleteSystem(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (systemId: string) =>
      apiRequest<void>(`/systems/${systemId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
    },
  })
}

export function useProjectInvalidation(projectId: string) {
  const queryClient = useQueryClient()

  return useCallback(() => {
    queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectId) })
  }, [queryClient, projectId])
}
