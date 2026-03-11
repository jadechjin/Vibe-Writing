import { fireEvent, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { EvidenceMatrixPanel } from "./EvidenceMatrixPanel"
import {
  buildAsset,
  buildClaim,
  buildOutline,
  buildOutlineBinding,
  buildSystemDetail,
  buildWorkflowSnapshot,
} from "./testFixtures"
import { createMutationHookResult, createQueryHookResult, renderWithQueryClient } from "./testUtils"
import * as analysisHooks from "../../hooks/useAnalysis"
import * as evidenceHooks from "../../hooks/useEvidence"

vi.mock("../../hooks/useEvidence", () => ({
  useApproveClaim: vi.fn(),
  useClaims: vi.fn(),
  useCreateClaimEvidenceLink: vi.fn(),
  useCreateOutlineBinding: vi.fn(),
  useGenerateEvidenceMatrix: vi.fn(),
  useGenerateOutline: vi.fn(),
  useConfirmOutline: vi.fn(),
  useOutlines: vi.fn(),
}))

vi.mock("../../hooks/useAnalysis", () => ({
  useAssets: vi.fn(),
}))

const mockedUseClaims = vi.mocked(evidenceHooks.useClaims)
const mockedUseOutlines = vi.mocked(evidenceHooks.useOutlines)
const mockedUseGenerateEvidenceMatrix = vi.mocked(evidenceHooks.useGenerateEvidenceMatrix)
const mockedUseApproveClaim = vi.mocked(evidenceHooks.useApproveClaim)
const mockedUseCreateClaimEvidenceLink = vi.mocked(evidenceHooks.useCreateClaimEvidenceLink)
const mockedUseGenerateOutline = vi.mocked(evidenceHooks.useGenerateOutline)
const mockedUseConfirmOutline = vi.mocked(evidenceHooks.useConfirmOutline)
const mockedUseCreateOutlineBinding = vi.mocked(evidenceHooks.useCreateOutlineBinding)
const mockedUseAssets = vi.mocked(analysisHooks.useAssets)

describe("EvidenceMatrixPanel smoke coverage", () => {
  const systemDetail = buildSystemDetail()
  const baseSnapshot = buildWorkflowSnapshot({
    currentState: "Evidence_Matrix_Ready",
    currentGate: "G4",
  })

  beforeEach(() => {
    vi.clearAllMocks()

    mockedUseClaims.mockReturnValue(createQueryHookResult([]) as unknown as ReturnType<typeof evidenceHooks.useClaims>)
    mockedUseOutlines.mockReturnValue(createQueryHookResult([]) as unknown as ReturnType<typeof evidenceHooks.useOutlines>)
    mockedUseAssets.mockReturnValue(createQueryHookResult([]) as unknown as ReturnType<typeof analysisHooks.useAssets>)
    mockedUseGenerateEvidenceMatrix.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useGenerateEvidenceMatrix>,
    )
    mockedUseApproveClaim.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useApproveClaim>,
    )
    mockedUseCreateClaimEvidenceLink.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useCreateClaimEvidenceLink>,
    )
    mockedUseGenerateOutline.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useGenerateOutline>,
    )
    mockedUseConfirmOutline.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useConfirmOutline>,
    )
    mockedUseCreateOutlineBinding.mockReturnValue(
      createMutationHookResult() as unknown as ReturnType<typeof evidenceHooks.useCreateOutlineBinding>,
    )
  })

  it("renders G4 regions, splits approved/pending latest claims, and uses latest outline binding truth", () => {
    const olderClaimVersion = buildClaim({
      id: "claim-alpha-v1",
      claimId: "claim-alpha",
      statement: "Older alpha statement",
      status: "approved",
      version: 1,
      updatedAt: "2026-03-10T10:00:00Z",
    })
    const latestClaimVersion = buildClaim({
      id: "claim-alpha-v2",
      claimId: "claim-alpha",
      statement: "Latest alpha statement",
      status: "pending",
      version: 2,
      updatedAt: "2026-03-11T10:00:00Z",
    })
    const latestApprovedClaim = buildClaim({
      id: "claim-beta-v1",
      claimId: "claim-beta",
      statement: "Approved beta statement",
      status: "approved",
      sectionRef: "intro",
      version: 1,
      approvedAt: "2026-03-11T08:30:00Z",
    })

    const oldAsset = buildAsset({ id: "asset-old", fileName: "old-binding.png" })
    const latestAsset = buildAsset({ id: "asset-latest", fileName: "latest-binding.png" })
    const authoritativeOutline = buildOutline({
      id: "outline-authoritative",
      version: 3,
      status: "confirmed",
      approvedAt: "2026-03-11T09:00:00Z",
      updatedAt: "2026-03-11T09:00:00Z",
      bindings: [
        buildOutlineBinding({
          id: "binding-latest",
          outlineId: "outline-authoritative",
          assetId: latestAsset.id,
          sectionKey: "intro",
        }),
      ],
    })
    const tailOrderOnlyOutline = buildOutline({
      id: "outline-tail-only",
      version: 2,
      status: "confirmed",
      approvedAt: "2026-03-11T09:30:00Z",
      updatedAt: "2026-03-11T09:45:00Z",
      bindings: [
        buildOutlineBinding({
          id: "binding-old",
          outlineId: "outline-tail-only",
          assetId: oldAsset.id,
          sectionKey: "intro",
        }),
      ],
    })

    mockedUseClaims.mockReturnValue(
      createQueryHookResult([latestClaimVersion, latestApprovedClaim, olderClaimVersion]) as unknown as ReturnType<
        typeof evidenceHooks.useClaims
      >,
    )
    mockedUseOutlines.mockReturnValue(
      createQueryHookResult([tailOrderOnlyOutline, authoritativeOutline]) as unknown as ReturnType<
        typeof evidenceHooks.useOutlines
      >,
    )
    mockedUseAssets.mockReturnValue(
      createQueryHookResult([oldAsset, latestAsset]) as unknown as ReturnType<typeof analysisHooks.useAssets>,
    )

    renderWithQueryClient(
      <EvidenceMatrixPanel
        snapshot={baseSnapshot}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    expect(screen.getByText("Evidence & Outline")).toBeInTheDocument()
    expect(screen.getByText("Claims Review Queue")).toBeInTheDocument()
    expect(screen.getByText("Outline Strategy")).toBeInTheDocument()
    expect(screen.getByText("Approved (1)")).toBeInTheDocument()
    expect(screen.getByText("Pending (1)")).toBeInTheDocument()
    expect(screen.getByText(/Latest alpha statement/)).toBeInTheDocument()
    expect(screen.queryByText(/Older alpha statement/)).not.toBeInTheDocument()
    expect(screen.getAllByText(/Known section binding is available\./).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/latest-binding\.png/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("Outline v3")).toBeInTheDocument()
    expect(screen.getByLabelText(/Outline binding asset/i)).toBeInTheDocument()
  })

  it("keeps artifact UI pending after accepted G4 action until refreshed outline resources arrive", () => {
    const generateOutlineMutate = vi.fn((_variables, callbacks) => {
      callbacks?.onSuccess?.({
        handle: {
          workflow_id: "workflow-outline-queued",
          job_id: "job-outline-queued",
          status: "queued",
        },
      })
      callbacks?.onSettled?.()
    })

    mockedUseGenerateOutline.mockReturnValue(
      createMutationHookResult({ mutate: generateOutlineMutate }) as unknown as ReturnType<
        typeof evidenceHooks.useGenerateOutline
      >,
    )

    const { rerender } = renderWithQueryClient(
      <EvidenceMatrixPanel
        snapshot={baseSnapshot}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    fireEvent.click(screen.getByRole("button", { name: "Generate Outline" }))

    expect(generateOutlineMutate).toHaveBeenCalledTimes(1)
    expect(screen.getByText(/No outline generated yet\./)).toBeInTheDocument()

    rerender(
      <EvidenceMatrixPanel
        snapshot={buildWorkflowSnapshot({
          currentState: "Outline_Ready",
          currentGate: "G5",
          latestEvent: null,
          events: [],
        })}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    expect(screen.getByText(/当前状态：Outline_Ready/)).toBeInTheDocument()
    expect(screen.getByText(/No outline generated yet\./)).toBeInTheDocument()

    mockedUseOutlines.mockReturnValue(
      createQueryHookResult([
        buildOutline({
          id: "outline-arrived",
          version: 3,
          status: "confirmed",
          approvedAt: "2026-03-11T11:30:00Z",
          updatedAt: "2026-03-11T11:30:00Z",
        }),
      ]) as unknown as ReturnType<typeof evidenceHooks.useOutlines>,
    )

    rerender(
      <EvidenceMatrixPanel
        snapshot={buildWorkflowSnapshot({
          currentState: "Outline_Ready",
          currentGate: "G5",
          latestEvent: null,
          events: [],
        })}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    expect(screen.getByText("Outline v3")).toBeInTheDocument()
    expect(screen.getByText(/Current bindings: 0/)).toBeInTheDocument()
  })

  it("clears local binding success after authoritative outline refresh updates the latest resource", () => {
    const claim = buildClaim({
      id: "claim-bound",
      claimId: "claim-bound",
      statement: "Claim waiting for outline binding",
      sectionRef: "intro",
      status: "approved",
    })
    const asset = buildAsset({ id: "asset-1", fileName: "bound-asset.png" })
    const initialOutline = buildOutline({
      id: "outline-1",
      version: 1,
      status: "draft",
      updatedAt: "2026-03-11T09:00:00Z",
    })

    const createBindingMutate = vi.fn((_variables, callbacks) => {
      callbacks?.onSuccess?.(
        buildOutlineBinding({
          id: "binding-new",
          outlineId: "outline-1",
          assetId: asset.id,
          sectionKey: "intro",
        }),
      )
    })

    mockedUseClaims.mockReturnValue(
      createQueryHookResult([claim]) as unknown as ReturnType<typeof evidenceHooks.useClaims>,
    )
    mockedUseOutlines.mockReturnValue(
      createQueryHookResult([initialOutline]) as unknown as ReturnType<typeof evidenceHooks.useOutlines>,
    )
    mockedUseAssets.mockReturnValue(
      createQueryHookResult([asset]) as unknown as ReturnType<typeof analysisHooks.useAssets>,
    )
    mockedUseCreateOutlineBinding.mockReturnValue(
      createMutationHookResult({ mutate: createBindingMutate }) as unknown as ReturnType<
        typeof evidenceHooks.useCreateOutlineBinding
      >,
    )

    const { rerender } = renderWithQueryClient(
      <EvidenceMatrixPanel
        snapshot={baseSnapshot}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    fireEvent.change(screen.getByLabelText(/Outline binding asset/i), {
      target: { value: asset.id },
    })
    fireEvent.change(screen.getByLabelText(/Target section/i), {
      target: { value: "intro" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Add Outline Binding" }))

    expect(createBindingMutate).toHaveBeenCalledTimes(1)

    mockedUseOutlines.mockReturnValue(
      createQueryHookResult([
        buildOutline({
          id: "outline-1",
          version: 1,
          status: "draft",
          updatedAt: "2026-03-11T09:05:00Z",
          bindings: [
            buildOutlineBinding({
              id: "binding-new",
              outlineId: "outline-1",
              assetId: asset.id,
              sectionKey: "intro",
            }),
          ],
        }),
      ]) as unknown as ReturnType<typeof evidenceHooks.useOutlines>,
    )

    rerender(
      <EvidenceMatrixPanel
        snapshot={baseSnapshot}
        blockers={[]}
        systemId="system-1"
        systemDetail={systemDetail}
      />,
    )

    expect(screen.getByText(/Asset: bound-asset\.png/)).toBeInTheDocument()
    expect(screen.getAllByText(/Known section binding is available\./).length).toBeGreaterThanOrEqual(1)
  })
})
