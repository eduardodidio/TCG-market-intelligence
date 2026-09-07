import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AdminAuditLogSection } from "../../../src/components/admin/AdminAuditLogSection";

function makeEntry(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    timestamp: "2026-09-07T14:32:00Z",
    actor_id: 1,
    actor_email: "admin@example.com",
    action: "credit_adjust",
    target_type: "user",
    target_id: "5",
    details_json: '{"amount": 100, "reason": "bonus"}',
    ip_address: "127.0.0.1",
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
      <AdminAuditLogSection isOpen={isOpen} />
    </MemoryRouter>,
  );
}

describe("AdminAuditLogSection", () => {
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
    expect(screen.queryByTestId("audit-log-section")).not.toBeInTheDocument();
  });

  it("renders empty state when no entries", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeApiResponse([], 0)),
    });

    renderSection();

    await waitFor(() => {
      expect(screen.getByTestId("audit-empty")).toBeInTheDocument();
    });
  });

  it("renders table with entries", async () => {
    const entries = [
      makeEntry({ id: 1 }),
      makeEntry({ id: 2, action: "user_create" }),
    ];
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeApiResponse(entries, 2)),
    });

    renderSection();

    await waitFor(() => {
      expect(screen.getByTestId("audit-table")).toBeInTheDocument();
    });
    expect(screen.getByTestId("audit-row-1")).toBeInTheDocument();
    expect(screen.getByTestId("audit-row-2")).toBeInTheDocument();
  });

  it("action filter dropdown changes filter state", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeApiResponse([], 0)),
    });

    renderSection();

    await waitFor(() => {
      expect(screen.getByTestId("audit-action-filter")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("audit-action-filter"), {
      target: { value: "user_create" },
    });

    // Should re-fetch with the filter (verified by the mock being called again)
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(2);
    });
  });

  it("details cell click expands to show full JSON", async () => {
    const entry = makeEntry({ id: 1, details_json: '{"amount": 100}' });
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeApiResponse([entry], 1)),
    });

    renderSection();

    await waitFor(() => {
      expect(screen.getByTestId("audit-row-1")).toBeInTheDocument();
    });

    // Click to expand
    fireEvent.click(screen.getByTestId("audit-row-1"));

    await waitFor(() => {
      expect(screen.getByTestId("audit-detail-row-1")).toBeInTheDocument();
    });
    expect(screen.getByTestId("audit-detail-1")).toBeInTheDocument();
  });

  it("shows loading spinner while fetching", () => {
    // Never resolve the fetch
    globalThis.fetch = vi.fn().mockReturnValue(new Promise(() => {}));

    renderSection();
    expect(screen.getByTestId("audit-loading")).toBeInTheDocument();
  });

  it("pagination buttons update offset", async () => {
    const entries = Array.from({ length: 50 }, (_, i) =>
      makeEntry({ id: i + 1 }),
    );
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeApiResponse(entries, 75)),
    });

    renderSection();

    await waitFor(() => {
      expect(screen.getByTestId("audit-table")).toBeInTheDocument();
    });

    // Next should be enabled, prev disabled
    expect(screen.getByTestId("audit-next")).not.toBeDisabled();
    expect(screen.getByTestId("audit-prev")).toBeDisabled();

    fireEvent.click(screen.getByTestId("audit-next"));

    // Should refetch
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(2);
    });
  });
});
