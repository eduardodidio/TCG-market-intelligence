import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { BanHistory } from "../../src/pages/BanHistory";

const MOCK_FORMATS = {
  data: ["standard", "modern", "legacy"],
  meta: { cursor: null, total: null, offset: null, request_id: "r1" },
  errors: [],
};

const MOCK_HISTORY = {
  data: {
    items: [
      {
        card_id: 1,
        name_en: "Lightning Bolt",
        name_pt: "Raio",
        set_code: "lea",
        collector_number: "161",
        format: "standard",
        old_status: "legal",
        new_status: "banned",
        changed_at: "2026-08-01T12:00:00",
        image_url: null,
      },
      {
        card_id: 2,
        name_en: "Ancestral Recall",
        name_pt: null,
        set_code: "lea",
        collector_number: "47",
        format: "vintage",
        old_status: null,
        new_status: "restricted",
        changed_at: "2026-08-01T10:00:00",
        image_url: null,
      },
    ],
    total: 2,
    limit: 30,
    offset: 0,
  },
  meta: { cursor: null, total: null, offset: null, request_id: "r2" },
  errors: [],
};

const MOCK_EMPTY_HISTORY = {
  data: { items: [], total: 0, limit: 30, offset: 0 },
  meta: { cursor: null, total: null, offset: null, request_id: "r3" },
  errors: [],
};

const MOCK_LARGE_HISTORY = {
  data: {
    items: Array.from({ length: 30 }, (_, i) => ({
      card_id: i + 1,
      name_en: `Card ${i + 1}`,
      name_pt: null,
      set_code: "lea",
      collector_number: String(i + 1),
      format: "standard",
      old_status: "legal",
      new_status: "banned",
      changed_at: "2026-08-01T12:00:00",
      image_url: null,
    })),
    total: 50,
    limit: 30,
    offset: 0,
  },
  meta: { cursor: null, total: null, offset: null, request_id: "r4" },
  errors: [],
};

function createMockFetch(historyResponse: unknown = MOCK_EMPTY_HISTORY) {
  return vi.fn().mockImplementation((url: string) => {
    const urlStr = String(url);
    if (urlStr.includes("/banlist/formats")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(MOCK_FORMATS),
      });
    }
    if (urlStr.includes("/banlist/history")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(historyResponse),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          data: null,
          meta: { cursor: null, total: null, request_id: "" },
          errors: [],
        }),
    });
  });
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/banlist/history"]}>
      <BanHistory />
    </MemoryRouter>,
  );
}

describe("BanHistory page", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders filter controls", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("ban-history-filters")).toBeInTheDocument();
    });
    expect(screen.getByTestId("bh-format-select")).toBeInTheDocument();
    expect(screen.getByTestId("bh-date-from")).toBeInTheDocument();
    expect(screen.getByTestId("bh-date-to")).toBeInTheDocument();
  });

  it("populates format dropdown", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderPage();

    await waitFor(() => {
      const select = screen.getByTestId("bh-format-select");
      expect(select).toBeInTheDocument();
      // Should have "All Formats" + 3 format options
      expect(select.querySelectorAll("option").length).toBeGreaterThanOrEqual(4);
    });
  });

  it("shows empty state when no events", async () => {
    globalThis.fetch = createMockFetch(MOCK_EMPTY_HISTORY) as unknown as typeof fetch;
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("ban-history-empty")).toBeInTheDocument();
    });
  });

  it("renders events grouped by month", async () => {
    globalThis.fetch = createMockFetch(MOCK_HISTORY) as unknown as typeof fetch;
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("ban-history-timeline")).toBeInTheDocument();
    });
    expect(screen.getAllByTestId("month-group-header")).toHaveLength(1);
    expect(screen.getAllByTestId("ban-event-card")).toHaveLength(2);
  });

  it("shows load more button when total > loaded", async () => {
    globalThis.fetch = createMockFetch(MOCK_LARGE_HISTORY) as unknown as typeof fetch;
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("ban-history-load-more")).toBeInTheDocument();
    });
    expect(screen.getByTestId("ban-history-count")).toHaveTextContent("30");
  });

  it("shows loading skeleton while fetching", async () => {
    let resolveHistory: (value: unknown) => void;
    const historyPromise = new Promise((resolve) => {
      resolveHistory = resolve;
    });

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      const urlStr = String(url);
      if (urlStr.includes("/banlist/formats")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(MOCK_FORMATS),
        });
      }
      if (urlStr.includes("/banlist/history")) {
        return historyPromise.then(() => ({
          ok: true,
          json: () => Promise.resolve(MOCK_EMPTY_HISTORY),
        }));
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: null,
            meta: { cursor: null, total: null, request_id: "" },
            errors: [],
          }),
      });
    }) as unknown as typeof fetch;

    renderPage();
    expect(screen.getByTestId("ban-history-loading")).toBeInTheDocument();

    resolveHistory!(null);
    await waitFor(() => {
      expect(screen.queryByTestId("ban-history-loading")).toBeNull();
    });
  });
});
