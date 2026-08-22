import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CollectionCardDetail } from "../../src/pages/CollectionCardDetail";

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
    { format: "standard", status: "banned", effective_date: "2026-01-01" },
    { format: "modern", status: "legal", effective_date: null },
    { format: "legacy", status: "restricted", effective_date: null },
    { format: "vintage", status: "legal", effective_date: null },
    { format: "commander", status: "legal", effective_date: null },
    { format: "pioneer", status: "not_legal", effective_date: null },
    { format: "pauper", status: "legal", effective_date: null },
    { format: "historic", status: "legal", effective_date: null },
  ],
  meta: { cursor: null, total: null, offset: null, request_id: "r2" },
  errors: [],
};

const MOCK_HISTORY = {
  data: { observations: [], summary: null },
  meta: { cursor: null, total: null, offset: null, request_id: "rh" },
  errors: [],
};

describe("LegalitySection in CollectionCardDetail", () => {
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
      if (typeof url === "string" && url.includes("/banlist/card/")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(legalities),
        });
      }
      if (typeof url === "string" && url.includes("/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(MOCK_HISTORY),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(entry),
      });
    }) as unknown as typeof fetch;
  }

  it("shows legality section when card_id present", async () => {
    mockFetch();
    render(
      <MemoryRouter initialEntries={["/collection/1"]}>
        <CollectionCardDetail />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("legality-section")).toBeInTheDocument();
    });
  });

  it("shows 'unavailable' message when card_id is null", async () => {
    mockFetch(MOCK_ENTRY_UNLINKED);
    render(
      <MemoryRouter initialEntries={["/collection/1"]}>
        <CollectionCardDetail />
      </MemoryRouter>,
    );
    await waitFor(() => {
      const section = screen.getByTestId("legality-section");
      expect(section.textContent).toContain("Legality data not available");
    });
  });

  it("shows expand button when more than 6 formats", async () => {
    mockFetch();
    render(
      <MemoryRouter initialEntries={["/collection/1"]}>
        <CollectionCardDetail />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("legality-expand")).toBeInTheDocument();
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
      expect(screen.getByTestId("legality-expand")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("legality-expand"));
    await waitFor(() => {
      // All 8 badges should now be visible
      const badges = screen.getAllByTestId(/^legality-badge-/);
      expect(badges.length).toBe(8);
    });
  });
});
