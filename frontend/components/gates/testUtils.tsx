import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, type RenderOptions } from "@testing-library/react"
import type { PropsWithChildren, ReactElement } from "react"
import { vi } from "vitest"
import { WebSocketProvider } from "../../contexts/WebSocketContext"

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

type ProviderProps = PropsWithChildren<{
  client: QueryClient
  projectId?: string
  systemId?: string
}>

function TestQueryProvider({ client, projectId, systemId, children }: ProviderProps) {
  return (
    <QueryClientProvider client={client}>
      <WebSocketProvider projectId={projectId} systemId={systemId}>
        {children}
      </WebSocketProvider>
    </QueryClientProvider>
  )
}

export function renderWithQueryClient(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper"> & { projectId?: string; systemId?: string },
) {
  const client = createTestQueryClient()
  const { projectId, systemId, ...renderOptions } = options ?? {}

  return {
    client,
    ...render(ui, {
      wrapper: ({ children }) => (
        <TestQueryProvider client={client} projectId={projectId} systemId={systemId}>
          {children}
        </TestQueryProvider>
      ),
      ...renderOptions,
    }),
  }
}

export function createQueryHookResult<T>(data: T, overrides: Record<string, unknown> = {}) {
  return {
    data,
    isLoading: false,
    isError: false,
    isPending: false,
    isSuccess: true,
    isFetching: false,
    isRefetching: false,
    isLoadingError: false,
    isRefetchError: false,
    isPlaceholderData: false,
    status: "success",
    fetchStatus: "idle",
    error: null,
    refetch: vi.fn(),
    failureCount: 0,
    failureReason: null,
    errorUpdateCount: 0,
    dataUpdatedAt: 0,
    errorUpdatedAt: 0,
    isFetched: true,
    isFetchedAfterMount: true,
    isInitialLoading: false,
    isPaused: false,
    isStale: false,
    promise: Promise.resolve(data),
    ...overrides,
  } as const
}

export function createMutationHookResult(overrides: Record<string, unknown> = {}) {
  return {
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    reset: vi.fn(),
    data: undefined,
    error: null,
    variables: undefined,
    context: undefined,
    failureCount: 0,
    failureReason: null,
    isError: false,
    isIdle: true,
    isPaused: false,
    isPending: false,
    isSuccess: false,
    status: "idle",
    submittedAt: 0,
    ...overrides,
  } as const
}
