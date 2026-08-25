import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AdminLigaStatus } from "../../src/pages/AdminLigaStatus";
import type { ApiResponse, LigaStatusResponse, CollectionCard } from "../../src/types/api";

function envelope<T>(data: T, total?: number): ApiResponse<T> {
  return {
    data,
    meta: { cursor: null, total: total ?? null, offset: null, request_id: "test" },
    errors: [],
  };
}

function mockStatus(): LigaStatusResponse {
  return {
    total_cards: 100,
    liga_priced: 60,
    liga_stale: 10,
    liga_missing: 30,
    unlinked: 5,
    coverage_pct: 60.0,
    last_liga_scan: "2026-08-25",
  };
}

function mockMissingCards(): CollectionCard[] {
  return [
    {
      id: 1,
      card_id: 42,
      set_code: "DMR",
      collector_number: "123",
      name_en: "Lightning Bolt",
      name_pt: null,
      set_name_en: "Dominaria Remastered",
      quantity: 2,
      quality: "NM",
      language: "EN",
      rarity: "R",
      color: "R",
      extras: null,
      latest_price: null,
      image_url: null,
    },
    {
      id: 2,
      card_id: 43,
      set_code: "LEA",
      collector_number: "1",
      name_en: "Dark Ritual",
      name_pt: null,
      set_name_en: null,
      quantity: 1,
      quality: null,
      language: null,
      rarity: null,
      color: null,
      extras: null,
      latest_price: null,
      image_url: null,
    },
  ];
}

function mockFetch() {
  return vi.fn().mockImplementation((url: string, init?: RequestInit) => {
    if (typeof url === "string" && url.includes("/collection/liga-status")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope(mockStatus())),
      });
    }
    if (typeof url === "string" && url.includes("/collection/liga-missing")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope(mockMissingCards(), 2)),
      });
    }
    if (typeof url === "string" && url.includes("/scans") && init?.method === "POST") {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(envelope({ scan_id: 99, status: "pending" })),
      });
    }
    if (typeof url === "string" && url.includes("/scans/99")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(
            envelope({
              id: 99,
              scan_type: "collection",
              status: "completed",
              cards_total: 30,
              cards_processed: 30,
              cards_failed: 0,
              observations_saved: 30,
              error_summary: null,
              started_at: null,
              finished_at: null,
              created_at: "2026-08-25T00:00:00",
              filters_json: "{}",
            }),
          ),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(envelope(null)),
    });
  });
}

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminLigaStatus />
    </MemoryRouter>,
  );
}

describe("AdminLigaStatus", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    globalThis.fetch = mockFetch() as unknown as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders the page title", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Liga Price Coverage")).toBeInTheDocument();
    });
  });

  it("renders KPI cards with correct values", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("100")).toBeInTheDocument(); // total_cards
      expect(screen.getByText("60")).toBeInTheDocument(); // liga_priced
      expect(screen.getByText("30")).toBeInTheDocument(); // liga_missing
      expect(screen.getByText("10")).toBeInTheDocument(); // liga_stale
    });
  });

  it("renders coverage progress bar", async () => {
    renderPage();
    await waitFor(() => {
      const bar = screen.getByTestId("coverage-bar");
      expect(bar).toBeInTheDocument();
      expect(bar.textContent).toContain("60.0%");
    });
  });

  it("renders missing cards table", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("missing-table")).toBeInTheDocument();
      expect(screen.getByText("Lightning Bolt")).toBeInTheDocument();
      expect(screen.getByText("Dark Ritual")).toBeInTheDocument();
    });
  });

  it("renders the Scan All Missing button", async () => {
    renderPage();
    await waitFor(() => {
      const btn = screen.getByTestId("scan-all-missing");
      expect(btn).toBeInTheDocument();
      expect(btn.textContent).toContain("Scan All Missing");
    });
  });

  it("triggers scan on button click", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("scan-all-missing")).toBeInTheDocument();
    });

    const btn = screen.getByTestId("scan-all-missing");
    fireEvent.click(btn);

    await waitFor(() => {
      // Button should show loading state
      expect(btn.textContent).toContain("Please wait");
    });
  });

  it("shows last scan date", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/2026-08-25/)).toBeInTheDocument();
    });
  });

  it("shows unlinked count when > 0", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Unlinked.*5/)).toBeInTheDocument();
    });
  });

  it("renders page container with correct testid", async () => {
    renderPage();
    expect(screen.getByTestId("page-admin-liga-status")).toBeInTheDocument();
  });
});
