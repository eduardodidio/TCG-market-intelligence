import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CollectionCardDetail } from "../../src/pages/CollectionCardDetail";

// Mock Recharts
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container" style={{ width: 500, height: 300 }}>
        {children}
      </div>
    ),
  };
});

const MOCK_ENTRY = {
  data: {
    id: 1,
    card_id: 42 as number | null,
    set_code: "lea",
    collector_number: "161",
    name_en: "Lightning Bolt",
    name_pt: "Raio",
    set_name_en: "Alpha",
    quantity: 1,
    quality: "NM",
    language: "EN",
    rarity: "C",
    color: null,
    extras: null,
    latest_price: 10.5,
    image_url: null,
    price_history: [],
    source_cards: [],
    scryfall_url: null,
    ligamagic_url: null,
  },
  meta: { cursor: null, total: null, offset: null, request_id: "r1" },
  errors: [],
};

const MOCK_ENTRY_UNLINKED = {
  ...MOCK_ENTRY,
  data: { ...MOCK_ENTRY.data, card_id: null },
};

const MOCK_LEGALITIES = {
  data: [
    { format: "standard", status: "banned", effective_date: "2026-01-01", recently_changed: true, change_date: "2026-08-20T00:00:00", old_status: "legal" },
    { format: "modern", status: "legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
    { format: "legacy", status: "restricted", effective_date: null, recently_changed: false, change_date: null, old_status: null },
    { format: "vintage", status: "legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
    { format: "commander", status: "legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
    { format: "pioneer", status: "not_legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
    { format: "pauper", status: "legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
    { format: "historic", status: "legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
    { format: "brawl", status: "not_legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
    { format: "alchemy", status: "not_legal", effective_date: null, recently_changed: false, change_date: null, old_status: null },
  ],
  meta: { cursor: null, total: null, offset: null, request_id: "r2" },
  errors: [],
};

const MOCK_HISTORY = {
  data: { observations: [], summary: null },
  meta: { cursor: null, total: null, offset: null, request_id: "rh" },
  errors: [],
};

const MOCK_EMPTY = {
  data: null,
  meta: { cursor: null, total: null, offset: null, request_id: "re" },
  errors: [],
};

describe("LegalityPanel in CollectionCardDetail", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockFetch(entry = MOCK_ENTRY, legalities = MOCK_LEGALITIES) {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      const urlStr = String(url);
      if (urlStr.includes("/legality")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(legalities),
        });
      }
      if (urlStr.includes("/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(MOCK_HISTORY),
        });
      }
      if (urlStr.includes("/metrics")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(MOCK_EMPTY),
        });
      }
      // banlist/card fallback
      if (urlStr.includes("/banlist/")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [], meta: { cursor: null, total: null, offset: null, request_id: "bl" }, errors: [] }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(entry),
      });
    }) as unknown as typeof fetch;
  }

  it("shows legality panel when card_id present", async () => {
    mockFetch();
    render(
      <MemoryRouter initialEntries={["/collection/1"]}>
        <CollectionCardDetail />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("legality-panel")).toBeInTheDocument();
    });
  });

  it("shows unavailable message when card_id is null", async () => {
    mockFetch(MOCK_ENTRY_UNLINKED);
    render(
      <MemoryRouter initialEntries={["/collection/1"]}>
        <CollectionCardDetail />
      </MemoryRouter>,
    );
    await waitFor(() => {
      const panel = screen.getByTestId("legality-panel");
      expect(panel.textContent).toContain("not available");
    });
  });

  it("shows expand button when more than 8 formats", async () => {
    mockFetch();
    render(
      <MemoryRouter initialEntries={["/collection/1"]}>
        <CollectionCardDetail />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("legality-panel-expand")).toBeInTheDocument();
    });
  });

  it("expands to show all formats when clicking expand", async () => {
    mockFetch();
    render(
      <MemoryRouter initialEntries={["/collection/1"]}>
        <CollectionCardDetail />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("legality-panel-expand")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("legality-panel-expand"));
    await waitFor(() => {
      // All 10 badges should now be visible
      const badges = screen.getAllByTestId(/^legality-badge-/);
      expect(badges.length).toBe(10);
    });
  });

  it("shows NEW chip for recently changed legality", async () => {
    mockFetch();
    render(
      <MemoryRouter initialEntries={["/collection/1"]}>
        <CollectionCardDetail />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("legality-new-standard")).toBeInTheDocument();
    });
  });

  it("shows empty message when card has no ban history", async () => {
    const emptyLegalities = {
      data: [],
      meta: { cursor: null, total: null, offset: null, request_id: "r2" },
      errors: [],
    };
    mockFetch(MOCK_ENTRY, emptyLegalities);
    render(
      <MemoryRouter initialEntries={["/collection/1"]}>
        <CollectionCardDetail />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/no legality data/i)).toBeInTheDocument();
    });
  });
});
