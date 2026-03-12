import { render, screen, fireEvent } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { ActionButton } from "../ActionButton"

describe("ActionButton", () => {
  it("renders label", () => {
    render(<ActionButton label="Click me" onClick={vi.fn()} />)
    expect(screen.getByText("Click me")).toBeTruthy()
  })

  it("calls onClick when clicked", () => {
    const onClick = vi.fn()
    render(<ActionButton label="Click me" onClick={onClick} />)
    fireEvent.click(screen.getByText("Click me"))
    expect(onClick).toHaveBeenCalledOnce()
  })

  it("shows '...' when isPending", () => {
    render(<ActionButton label="Click me" onClick={vi.fn()} isPending />)
    expect(screen.getByText("...")).toBeTruthy()
  })

  it("is disabled when disabled prop is true", () => {
    render(<ActionButton label="Click me" onClick={vi.fn()} disabled />)
    expect(screen.getByRole("button")).toBeDisabled()
  })

  it("is disabled when isPending is true", () => {
    render(<ActionButton label="Click me" onClick={vi.fn()} isPending />)
    expect(screen.getByRole("button")).toBeDisabled()
  })
})
