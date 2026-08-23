import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BulkCanonizeButton } from "../../src/components/BulkCanonizeButton";

// Mock the collection API module
vi.mock("../../src/api/collection", () => ({
  canonizeAll: vi.fn(),
}));

import { canonizeAll } from "../../src/api/collection";
const mockCanonizeAll = vi.mocked(canonizeAll);

const mockBulkCanonizeResult = {
  total: 10,
  canonized: 8,
  failed: 2,
  skipped: 0,
  rate_limited: 0,
};

const emptyMeta = { cursor: null, total: null, offset: null, request_id: "" };

describe("BulkCanonizeButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("is hidden when unlinkedCount is 0", () => {
    const { container } = render(
      <BulkCanonizeButton unlinkedCount={0} />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("is hidden when unlinkedCount is negative", () => {
    const { container } = render(
      <BulkCanonizeButton unlinkedCount={-1} />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders when unlinkedCount > 0", () => {
    render(<BulkCanonizeButton unlinkedCount={5} />);
    expect(screen.getByTestId("bulk-canonize-btn")).toBeInTheDocument();
    expect(screen.getByText(/5 unlinked/)).toBeInTheDocument();
  });

  it("shows Canonize All text", () => {
    render(<BulkCanonizeButton unlinkedCount={3} />);
    expect(screen.getByText(/Canonize All/)).toBeInTheDocument();
  });

  it("calls canonizeAll API on click", async () => {
    mockCanonizeAll.mockResolvedValue({
      data: mockBulkCanonizeResult,
      meta: emptyMeta,
      errors: [],
    });

    render(<BulkCanonizeButton unlinkedCount={5} />);
    fireEvent.click(screen.getByTestId("bulk-canonize-btn"));

    await waitFor(() => {
      expect(mockCanonizeAll).toHaveBeenCalledTimes(1);
    });
  });

  it("shows loading state while request is in-flight", async () => {
    let resolvePromise: (value: unknown) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    mockCanonizeAll.mockReturnValue(promise as ReturnType<typeof canonizeAll>);

    render(<BulkCanonizeButton unlinkedCount={5} />);
    fireEvent.click(screen.getByTestId("bulk-canonize-btn"));

    await waitFor(() => {
      // The button should show the canonizing/loading text
      expect(screen.getByText(/Linking\.\.\./)).toBeInTheDocument();
    });

    // Button should be disabled during loading
    expect(screen.getByTestId("bulk-canonize-btn")).toBeDisabled();

    // Resolve the promise to clean up
    resolvePromise!({
      data: mockBulkCanonizeResult,
      meta: emptyMeta,
      errors: [],
    });
  });

  it("is disabled during loading", async () => {
    let resolvePromise: (value: unknown) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    mockCanonizeAll.mockReturnValue(promise as ReturnType<typeof canonizeAll>);

    render(<BulkCanonizeButton unlinkedCount={5} />);
    fireEvent.click(screen.getByTestId("bulk-canonize-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("bulk-canonize-btn")).toBeDisabled();
    });

    resolvePromise!({
      data: mockBulkCanonizeResult,
      meta: emptyMeta,
      errors: [],
    });
  });

  it("shows result banner after completion", async () => {
    mockCanonizeAll.mockResolvedValue({
      data: mockBulkCanonizeResult,
      meta: emptyMeta,
      errors: [],
    });

    render(<BulkCanonizeButton unlinkedCount={5} />);
    fireEvent.click(screen.getByTestId("bulk-canonize-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("bulk-canonize-result")).toBeInTheDocument();
    });

    // Shows canonized count
    expect(screen.getByText(/Canonized 8 of 10 cards/)).toBeInTheDocument();
    // Shows failed count
    expect(screen.getByText(/2 cards failed/)).toBeInTheDocument();
  });

  it("shows result without failed text when failed is 0", async () => {
    mockCanonizeAll.mockResolvedValue({
      data: { ...mockBulkCanonizeResult, failed: 0 },
      meta: emptyMeta,
      errors: [],
    });

    render(<BulkCanonizeButton unlinkedCount={5} />);
    fireEvent.click(screen.getByTestId("bulk-canonize-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("bulk-canonize-result")).toBeInTheDocument();
    });

    expect(screen.queryByText(/cards failed/)).not.toBeInTheDocument();
  });

  it("triggers onComplete callback after successful canonize", async () => {
    const onComplete = vi.fn();
    mockCanonizeAll.mockResolvedValue({
      data: mockBulkCanonizeResult,
      meta: emptyMeta,
      errors: [],
    });

    render(<BulkCanonizeButton unlinkedCount={5} onComplete={onComplete} />);
    fireEvent.click(screen.getByTestId("bulk-canonize-btn"));

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledTimes(1);
    });
  });

  it("does not call onComplete on error", async () => {
    const onComplete = vi.fn();
    mockCanonizeAll.mockResolvedValue({
      data: null,
      meta: emptyMeta,
      errors: [{ code: "ERROR", message: "Something went wrong" }],
    });

    render(<BulkCanonizeButton unlinkedCount={5} onComplete={onComplete} />);
    fireEvent.click(screen.getByTestId("bulk-canonize-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("bulk-canonize-error")).toBeInTheDocument();
    });

    expect(onComplete).not.toHaveBeenCalled();
  });

  it("shows error banner on API error", async () => {
    mockCanonizeAll.mockResolvedValue({
      data: null,
      meta: emptyMeta,
      errors: [{ code: "ERROR", message: "Server error" }],
    });

    render(<BulkCanonizeButton unlinkedCount={5} />);
    fireEvent.click(screen.getByTestId("bulk-canonize-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("bulk-canonize-error")).toBeInTheDocument();
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
  });

  it("shows error banner on network exception", async () => {
    mockCanonizeAll.mockRejectedValue(new Error("Network failure"));

    render(<BulkCanonizeButton unlinkedCount={5} />);
    fireEvent.click(screen.getByTestId("bulk-canonize-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("bulk-canonize-error")).toBeInTheDocument();
    });
  });
});
