import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useState } from "react";

// Mock the virtual module
const mockUpdateServiceWorker = vi.fn().mockResolvedValue(undefined);
let mockNeedRefresh = false;
let mockSetNeedRefresh: (v: boolean) => void = vi.fn();

vi.mock("virtual:pwa-register/react", () => ({
  useRegisterSW: () => {
    const [needRefresh, setNeedRefresh] = useState(mockNeedRefresh);
    mockSetNeedRefresh = setNeedRefresh;
    return {
      needRefresh: [needRefresh, setNeedRefresh],
      offlineReady: [false, vi.fn()],
      updateServiceWorker: mockUpdateServiceWorker,
    };
  },
}));

// Import after mock
import { UpdatePrompt } from "../../src/components/UpdatePrompt";

describe("UpdatePrompt", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNeedRefresh = false;
  });

  it("does not render when no update needed", () => {
    mockNeedRefresh = false;
    render(<UpdatePrompt />);
    expect(screen.queryByTestId("update-prompt")).toBeNull();
  });

  it("renders when needRefresh is true", () => {
    mockNeedRefresh = true;
    render(<UpdatePrompt />);
    expect(screen.getByTestId("update-prompt")).toBeInTheDocument();
    expect(screen.getByText("A new version is available!")).toBeInTheDocument();
  });

  it("calls updateServiceWorker when update button is clicked", () => {
    mockNeedRefresh = true;
    render(<UpdatePrompt />);
    fireEvent.click(screen.getByTestId("update-prompt-update"));
    expect(mockUpdateServiceWorker).toHaveBeenCalledWith(true);
  });

  it("dismisses when dismiss button is clicked", () => {
    mockNeedRefresh = true;
    render(<UpdatePrompt />);
    expect(screen.getByTestId("update-prompt")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("update-prompt-dismiss"));
    expect(screen.queryByTestId("update-prompt")).toBeNull();
  });

  it("has role=alert for accessibility", () => {
    mockNeedRefresh = true;
    render(<UpdatePrompt />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
