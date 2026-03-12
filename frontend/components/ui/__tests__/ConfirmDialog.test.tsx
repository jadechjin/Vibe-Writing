import { render, screen, fireEvent } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { ConfirmDialog } from "../ConfirmDialog"

describe("ConfirmDialog", () => {
  it("renders nothing when isOpen is false", () => {
    const { container } = render(
      <ConfirmDialog
        isOpen={false}
        title="Confirm"
        message="Are you sure?"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )
    expect(container.firstChild).toBeNull()
  })

  it("renders title and message when open", () => {
    render(
      <ConfirmDialog
        isOpen
        title="Delete Item"
        message="This cannot be undone."
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )
    expect(screen.getByText("Delete Item")).toBeTruthy()
    expect(screen.getByText("This cannot be undone.")).toBeTruthy()
  })

  it("calls onConfirm when confirm button clicked", () => {
    const onConfirm = vi.fn()
    render(
      <ConfirmDialog
        isOpen
        title="Confirm"
        message="Sure?"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
        confirmLabel="Yes"
      />,
    )
    fireEvent.click(screen.getByText("Yes"))
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  it("calls onCancel when cancel button clicked", () => {
    const onCancel = vi.fn()
    render(
      <ConfirmDialog
        isOpen
        title="Confirm"
        message="Sure?"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    )
    fireEvent.click(screen.getByText("Cancel"))
    expect(onCancel).toHaveBeenCalledOnce()
  })

  it("shows '...' and disables buttons when isPending", () => {
    render(
      <ConfirmDialog
        isOpen
        title="Confirm"
        message="Sure?"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        isPending
        confirmLabel="Yes"
      />,
    )
    expect(screen.getByText("...")).toBeTruthy()
    const buttons = screen.getAllByRole("button")
    for (const btn of buttons) {
      expect(btn).toBeDisabled()
    }
  })
})
