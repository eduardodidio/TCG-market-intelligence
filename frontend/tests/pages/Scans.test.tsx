import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Scans } from "../../src/pages/Scans";
import { mockScanListResponse } from "../fixtures/scan-responses";

function renderScans() {
  return render(
    <MemoryRouter initialEntries={["/scans"]}>
      <Scans />
    </MemoryRouter>,
  );
}

describe("Scans page", () => {
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

  it("renders page title and toggle button", async () => {
    mockFetchSuccess();
    renderScans();

    await waitFor(() => {
      expect(screen.getByTestId("page-scans")).toBeDefined();
    });

    expect(screen.getByText("Price Scans")).toBeDefined();
    expect(screen.getByTestId("new-scan-toggle")).toBeDefined();
    expect(screen.getByText("New Scan")).toBeDefined();
  });

  it("toggle shows and hides the scan form", async () => {
    mockFetchSuccess();
    renderScans();

    await waitFor(() => {
      expect(screen.queryByTestId("scan-form-container")).toBeNull();
    });

    // Click to show form
    fireEvent.click(screen.getByTestId("new-scan-toggle"));
    expect(screen.getByTestId("scan-form-container")).toBeDefined();
    expect(screen.getByText("Cancel")).toBeDefined();

    // Click to hide form
    fireEvent.click(screen.getByTestId("new-scan-toggle"));
    expect(screen.queryByTestId("scan-form-container")).toBeNull();
    expect(screen.getByText("New Scan")).toBeDefined();
  });

  it("renders scan history table after loading", async () => {
    mockFetchSuccess();
    renderScans();

    await waitFor(() => {
      expect(screen.getByTestId("scans-table")).toBeDefined();
    });

    // Two scan rows from the fixture
    expect(screen.getByTestId("scan-row-1")).toBeDefined();
    expect(screen.getByTestId("scan-row-2")).toBeDefined();
  });

  it("shows empty state when no scans exist", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ scans: [], total: 0 }),
    }) as unknown as typeof fetch;

    renderScans();

    await waitFor(() => {
      expect(screen.getByTestId("scans-empty")).toBeDefined();
    });

    expect(screen.getByText("No scan runs yet.")).toBeDefined();
  });
});
