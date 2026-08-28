import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AdminScansSection } from "../../../src/components/admin/AdminScansSection";
import { mockScanListResponse } from "../../fixtures/scan-responses";

function renderSection(isOpen = true) {
  return render(
    <MemoryRouter>
      <AdminScansSection isOpen={isOpen} />
    </MemoryRouter>,
  );
}

describe("AdminScansSection", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockFetchSuccess() {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockScanListResponse()),
    }) as unknown as typeof fetch;
  }

  it("renders nothing when isOpen is false and never opened", () => {
    mockFetchSuccess();
    renderSection(false);
    expect(screen.queryByTestId("scans-section")).not.toBeInTheDocument();
  });

  it("renders section content when isOpen is true", async () => {
    mockFetchSuccess();
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("scans-section")).toBeInTheDocument();
    });
  });

  it("renders scan history table after loading", async () => {
    mockFetchSuccess();
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("scans-table")).toBeDefined();
    });

    expect(screen.getByTestId("scan-row-1")).toBeDefined();
    expect(screen.getByTestId("scan-row-2")).toBeDefined();
  });

  it("renders new scan toggle button", async () => {
    mockFetchSuccess();
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("new-scan-toggle")).toBeDefined();
    });
    expect(screen.getByText("New Scan")).toBeDefined();
  });

  it("toggle shows and hides the scan form", async () => {
    mockFetchSuccess();
    renderSection(true);

    await waitFor(() => {
      expect(screen.queryByTestId("scan-form-container")).toBeNull();
    });

    fireEvent.click(screen.getByTestId("new-scan-toggle"));
    expect(screen.getByTestId("scan-form-container")).toBeDefined();

    fireEvent.click(screen.getByTestId("new-scan-toggle"));
    expect(screen.queryByTestId("scan-form-container")).toBeNull();
  });

  it("shows empty state when no scans exist", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ scans: [], total: 0 }),
    }) as unknown as typeof fetch;

    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("scans-empty")).toBeDefined();
    });
  });
});
