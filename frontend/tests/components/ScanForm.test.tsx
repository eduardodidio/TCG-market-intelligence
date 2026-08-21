import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ScanForm } from "../../src/components/ScanForm";
import type { ScanTriggerResponse } from "../../src/types/api";

describe("ScanForm", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders all form elements", () => {
    render(<ScanForm onSuccess={vi.fn()} />);

    expect(screen.getByTestId("scan-form")).toBeDefined();
    expect(screen.getByTestId("scan-type-select")).toBeDefined();
    expect(screen.getByTestId("scan-limit-input")).toBeDefined();
    expect(screen.getByTestId("scan-submit-button")).toBeDefined();
    expect(screen.getByText("Start Scan")).toBeDefined();
  });

  it("shows set code input when type is set", () => {
    render(<ScanForm onSuccess={vi.fn()} />);

    // Initially no set code input (collection type)
    expect(screen.queryByTestId("set-code-input")).toBeNull();

    // Change to set
    fireEvent.change(screen.getByTestId("scan-type-select"), {
      target: { value: "set" },
    });

    expect(screen.getByTestId("set-code-input")).toBeDefined();
  });

  it("shows format name input when type is format", () => {
    render(<ScanForm onSuccess={vi.fn()} />);

    fireEvent.change(screen.getByTestId("scan-type-select"), {
      target: { value: "format" },
    });

    expect(screen.getByTestId("format-name-input")).toBeDefined();
  });

  it("shows card IDs textarea when type is custom", () => {
    render(<ScanForm onSuccess={vi.fn()} />);

    fireEvent.change(screen.getByTestId("scan-type-select"), {
      target: { value: "custom" },
    });

    expect(screen.getByTestId("card-ids-input")).toBeDefined();
  });

  it("submits form and calls onSuccess on API success", async () => {
    const mockResponse: ScanTriggerResponse = { scan_id: 1, status: "pending" };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    }) as unknown as typeof fetch;

    const onSuccess = vi.fn();
    render(<ScanForm onSuccess={onSuccess} />);

    fireEvent.click(screen.getByTestId("scan-submit-button"));

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledTimes(1);
    });

    // Verify POST was sent
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    const fetchCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const requestInit = fetchCall[1] as RequestInit;
    expect(requestInit.method).toBe("POST");
  });
});
