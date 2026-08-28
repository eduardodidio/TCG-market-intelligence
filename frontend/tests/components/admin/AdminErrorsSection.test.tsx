import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AdminErrorsSection } from "../../../src/components/admin/AdminErrorsSection";

function makeErrorEntry(overrides: Record<string, unknown> = {}) {
  return {
    id: "err-1",
    timestamp: "2026-08-28T10:00:00Z",
    level: "ERROR",
    error_type: "ValueError",
    message: "Something went wrong in the application",
    module: "src.api.routers.collection",
    function: "get_collection",
    ...overrides,
  };
}

function makeErrorDetail(overrides: Record<string, unknown> = {}) {
  return {
    ...makeErrorEntry(),
    traceback: 'Traceback (most recent call last):\n  File "app.py", line 42\nValueError: bad value',
    line: 42,
    request_method: "GET",
    request_path: "/api/v1/collection",
    request_user_id: 1,
    request_id: "req-abc-123",
    request_params: { limit: 50 },
    extra: { card_id: 999 },
    ...overrides,
  };
}

function makeApiResponse(data: unknown, total: number | null = null) {
  return {
    data,
    meta: { cursor: null, total, offset: null, request_id: "test" },
    errors: [],
  };
}

function renderSection(isOpen = true) {
  return render(
    <MemoryRouter>
      <AdminErrorsSection isOpen={isOpen} />
    </MemoryRouter>,
  );
}

describe("AdminErrorsSection", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockFetchErrors(entries: unknown[] = [makeErrorEntry()], total?: number) {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeApiResponse(entries, total ?? entries.length)),
    }) as unknown as typeof fetch;
  }

  function mockFetchWithDetail() {
    const entry = makeErrorEntry();
    const detail = makeErrorDetail();

    globalThis.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(makeApiResponse([entry], 1)),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(makeApiResponse(detail)),
      }) as unknown as typeof fetch;
  }

  it("renders nothing when isOpen is false and never opened", () => {
    mockFetchErrors();
    renderSection(false);
    expect(screen.queryByTestId("errors-section")).not.toBeInTheDocument();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("renders section content when isOpen is true", async () => {
    mockFetchErrors();
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("errors-section")).toBeInTheDocument();
    });
  });

  it("shows loading state", () => {
    // Never resolves fetch
    globalThis.fetch = vi.fn().mockReturnValue(new Promise(() => {})) as unknown as typeof fetch;
    renderSection(true);

    expect(screen.getByTestId("errors-loading")).toBeInTheDocument();
  });

  it("renders error list with correct columns", async () => {
    mockFetchErrors([
      makeErrorEntry({ id: "err-1", level: "ERROR" }),
      makeErrorEntry({ id: "err-2", level: "CRITICAL", error_type: "RuntimeError" }),
    ], 2);
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("errors-table")).toBeInTheDocument();
    });

    expect(screen.getByTestId("error-row-err-1")).toBeInTheDocument();
    expect(screen.getByTestId("error-row-err-2")).toBeInTheDocument();
  });

  it("renders CRITICAL badge with red styling", async () => {
    mockFetchErrors([makeErrorEntry({ id: "err-1", level: "CRITICAL" })]);
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("level-badge-CRITICAL")).toBeInTheDocument();
    });

    const badge = screen.getByTestId("level-badge-CRITICAL");
    expect(badge.className).toContain("bg-red-900");
    expect(badge.className).toContain("text-red-300");
  });

  it("renders ERROR badge with amber styling", async () => {
    mockFetchErrors([makeErrorEntry({ id: "err-1", level: "ERROR" })]);
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("level-badge-ERROR")).toBeInTheDocument();
    });

    const badge = screen.getByTestId("level-badge-ERROR");
    expect(badge.className).toContain("bg-amber-900");
    expect(badge.className).toContain("text-amber-300");
  });

  it("renders WARNING badge with yellow styling", async () => {
    mockFetchErrors([makeErrorEntry({ id: "err-1", level: "WARNING" })]);
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("level-badge-WARNING")).toBeInTheDocument();
    });

    const badge = screen.getByTestId("level-badge-WARNING");
    expect(badge.className).toContain("bg-yellow-900");
  });

  it("shows empty state when no errors exist", async () => {
    mockFetchErrors([], 0);
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("errors-empty")).toBeInTheDocument();
    });

    expect(screen.getByText("No errors recorded")).toBeInTheDocument();
  });

  it("selecting level filter calls API with level param", async () => {
    mockFetchErrors();
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("errors-level-filter")).toBeInTheDocument();
    });

    // Reset mock to track new calls
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeApiResponse([], 0)),
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    fireEvent.change(screen.getByTestId("errors-level-filter"), {
      target: { value: "CRITICAL" },
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const callUrl = fetchMock.mock.calls[0][0] as string;
    expect(callUrl).toContain("level=CRITICAL");
  });

  it("clicking row expands detail with traceback and request context", async () => {
    mockFetchWithDetail();
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("error-row-err-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("error-row-err-1"));

    await waitFor(() => {
      expect(screen.getByTestId("error-detail-err-1")).toBeInTheDocument();
    });

    expect(screen.getByTestId("error-traceback")).toBeInTheDocument();
    expect(screen.getByTestId("error-traceback").textContent).toContain("Traceback");
    expect(screen.getByText("GET")).toBeInTheDocument();
    expect(screen.getByText("/api/v1/collection")).toBeInTheDocument();
  });

  it("pagination next button updates offset", async () => {
    // 25 total items, showing 20
    const entries = Array.from({ length: 20 }, (_, i) =>
      makeErrorEntry({ id: `err-${i}` }),
    );
    mockFetchErrors(entries, 25);
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("errors-next")).toBeInTheDocument();
    });

    expect(screen.getByTestId("errors-next")).not.toBeDisabled();
    expect(screen.getByTestId("errors-prev")).toBeDisabled();

    // Click next
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve(
          makeApiResponse(
            Array.from({ length: 5 }, (_, i) =>
              makeErrorEntry({ id: `err-${20 + i}` }),
            ),
            25,
          ),
        ),
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    fireEvent.click(screen.getByTestId("errors-next"));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const callUrl = fetchMock.mock.calls[0][0] as string;
    expect(callUrl).toContain("offset=20");
  });

  it("pagination prev button navigates back", async () => {
    // Simulate being on page 2
    const entries = Array.from({ length: 20 }, (_, i) =>
      makeErrorEntry({ id: `err-${i}` }),
    );
    mockFetchErrors(entries, 45);
    renderSection(true);

    await waitFor(() => {
      expect(screen.getByTestId("errors-next")).toBeInTheDocument();
    });

    // Go to page 2
    const fetchMock2 = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve(
          makeApiResponse(
            Array.from({ length: 20 }, (_, i) =>
              makeErrorEntry({ id: `err-p2-${i}` }),
            ),
            45,
          ),
        ),
    });
    globalThis.fetch = fetchMock2 as unknown as typeof fetch;

    fireEvent.click(screen.getByTestId("errors-next"));

    await waitFor(() => {
      expect(fetchMock2).toHaveBeenCalled();
    });

    // Now prev should be enabled
    await waitFor(() => {
      expect(screen.getByTestId("errors-prev")).not.toBeDisabled();
    });
  });

  it("lazy loads data only when accordion opens", async () => {
    mockFetchErrors();
    const { rerender } = renderSection(false);

    // API should not be called when closed
    expect(globalThis.fetch).not.toHaveBeenCalled();

    // Now open
    rerender(
      <MemoryRouter>
        <AdminErrorsSection isOpen={true} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalled();
    });
  });
});
