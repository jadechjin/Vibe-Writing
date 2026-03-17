import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiError, apiRequest } from "./api"

describe("apiRequest", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("preserves structured code and details from ApiResponse errors", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: false,
          error: "Cannot regenerate evidence matrix because latest approved claims or confirmed outline already exists",
          data: {
            code: "evidence_matrix_regeneration_conflict",
            details: {
              approved_latest_claim_count: 2,
              confirmed_outline_count: 1,
              sections_affected: ["intro", "results"],
            },
          },
        }),
        {
          status: 409,
          headers: { "Content-Type": "application/json" },
        },
      ),
    )

    await expect(apiRequest("/systems/system-1/evidence-matrix/generate")).rejects.toMatchObject({
      status: 409,
      message: "Cannot regenerate evidence matrix because latest approved claims or confirmed outline already exists",
      code: "evidence_matrix_regeneration_conflict",
      details: {
        approved_latest_claim_count: 2,
        confirmed_outline_count: 1,
        sections_affected: ["intro", "results"],
      },
    })
  })
})
