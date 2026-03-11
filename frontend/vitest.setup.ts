import "@testing-library/jest-dom/vitest"
import { vi } from "vitest"

// Mock WebSocket for tests
vi.mock("./lib/websocket", () => ({
  createManagedSocket: vi.fn(() => vi.fn()),
  parseTaskEvent: vi.fn(),
}))
