import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { ProjectStats } from "./ProjectStats"

describe("ProjectStats", () => {
  it("renders zero completion state", () => {
    render(
      <ProjectStats
        completedSystemCount={0}
        introductionUnlocked={false}
        totalSystemCount={2}
      />,
    )

    expect(screen.getByText("0")).toBeDefined()
    expect(screen.getByText("/ 3 required")).toBeDefined()
    expect(screen.getByText("2 total systems created")).toBeDefined()
    expect(screen.getByText("Locked")).toBeDefined()
    expect(screen.getByText("Complete 3 more systems to unlock.")).toBeDefined()
  })

  it("renders partial completion state", () => {
    render(
      <ProjectStats
        completedSystemCount={1}
        introductionUnlocked={false}
        totalSystemCount={4}
      />,
    )

    expect(screen.getByText("1")).toBeDefined()
    expect(screen.getByText("Locked")).toBeDefined()
    expect(screen.getByText("Complete 2 more systems to unlock.")).toBeDefined()
  })

  it("renders threshold exact unlock state", () => {
    render(
      <ProjectStats
        completedSystemCount={3}
        introductionUnlocked={true}
        totalSystemCount={3}
      />,
    )

    expect(screen.getByText("3")).toBeDefined()
    expect(screen.getByText("Unlocked")).toBeDefined()
    expect(
      screen.getByText("You may begin writing the introduction and conclusion chapters."),
    ).toBeDefined()
  })

  it("renders above threshold state", () => {
    render(
      <ProjectStats
        completedSystemCount={5}
        introductionUnlocked={true}
        totalSystemCount={5}
      />,
    )

    expect(screen.getByText("5")).toBeDefined()
    expect(screen.getByText("Unlocked")).toBeDefined()
  })

  it("renders singular system text for 1 total", () => {
    render(
      <ProjectStats
        completedSystemCount={0}
        introductionUnlocked={false}
        totalSystemCount={1}
      />,
    )

    expect(screen.getByText("1 total system created")).toBeDefined()
  })
})
