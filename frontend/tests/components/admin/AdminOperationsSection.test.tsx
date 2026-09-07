import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AdminOperationsSection } from "../../../src/components/admin/AdminOperationsSection";

function makeApiResponse(data: unknown) {
  return {
    data,
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [],
  };
}

function makeErrorResponse(message: string) {
  return {
    data: null,
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [{ code: "ERROR", message }],
  };
}

function renderSection(isOpen = true) {
  return render(
    <MemoryRouter>
      <AdminOperationsSection isOpen={isOpen} />
    </MemoryRouter>,
  );
}

describe("AdminOperationsSection", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders nothing when closed", () => {
    renderSection(false);
    expect(screen.queryByTestId("operations-section")).not.toBeInTheDocument();
  });

  it("renders three action cards when open", () => {
    renderSection();
    expect(screen.getByTestId("liga-scan-title")).toBeInTheDocument();
    expect(screen.getByTestId("catalog-sweep-title")).toBeInTheDocument();
    expect(screen.getByTestId("db-backup-title")).toBeInTheDocument();
  });

  it("Run Liga Scan button calls API and shows scan_id", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeApiResponse({ scan_id: 42, status: "pending" })),
    });

    renderSection();
    fireEvent.click(screen.getByTestId("run-liga-scan-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("liga-scan-result")).toBeInTheDocument();
    });
    expect(screen.getByTestId("liga-scan-result").textContent).toContain("42");
  });

  it("Sweep Set button validates set_code is not empty", () => {
    renderSection();
    const btn = screen.getByTestId("sweep-set-btn");
    expect(btn).toBeDisabled();
  });

  it("Sweep Set calls API when set_code is provided", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve(
          makeApiResponse({ scan_id: 99, set_code: "mh3", status: "pending" }),
        ),
    });

    renderSection();
    fireEvent.change(screen.getByTestId("catalog-set-code-input"), {
      target: { value: "mh3" },
    });
    fireEvent.click(screen.getByTestId("sweep-set-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("catalog-scan-result")).toBeInTheDocument();
    });
    expect(screen.getByTestId("catalog-scan-result").textContent).toContain("99");
  });

  it("Download Backup button triggers window.open", () => {
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    renderSection();
    fireEvent.click(screen.getByTestId("download-backup-btn"));
    expect(openSpy).toHaveBeenCalledTimes(1);
    openSpy.mockRestore();
  });

  it("shows error messages on API failure", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve(makeErrorResponse("Server error")),
    });

    renderSection();
    fireEvent.click(screen.getByTestId("run-liga-scan-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("liga-scan-error")).toBeInTheDocument();
    });
  });
});
