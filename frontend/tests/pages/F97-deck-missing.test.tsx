import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { LanguageProvider } from "../../src/contexts/LanguageContext";
import { DeckView } from "../../src/pages/DeckView";
import type { DeckDetail } from "../../src/types/api";

// Mock recharts
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  };
});

function makeDeck(overrides?: Partial<DeckDetail>): DeckDetail {
  return {
    id: 1,
    name: "Test Deck",
    description: null,
    total_cards: 5,
    unique_cards: 5,
    owned_cards: 3,
    ownership_pct: 60,
    created_at: "2026-01-01T00:00:00",
    updated_at: "2026-01-01T00:00:00",
    cards: [
      { id: 1, name_en: "Lightning Bolt", name_pt: null, set_code: "lea", collector_number: "161", quantity: 4, card_id: 10, in_collection: true, owned_quantity: 4, collection_entry_id: 100, image_url: null, latest_price: 10 },
      { id: 2, name_en: "Counterspell", name_pt: null, set_code: "mh2", collector_number: "267", quantity: 2, card_id: 20, in_collection: true, owned_quantity: 2, collection_entry_id: 101, image_url: null, latest_price: 5 },
      { id: 3, name_en: "Dark Ritual", name_pt: null, set_code: "lea", collector_number: "98", quantity: 3, card_id: 30, in_collection: false, owned_quantity: 1, collection_entry_id: null, image_url: null, latest_price: 8 },
      { id: 4, name_en: "Swords to Plowshares", name_pt: null, set_code: null, collector_number: null, quantity: 1, card_id: 40, in_collection: false, owned_quantity: 0, collection_entry_id: null, image_url: null, latest_price: 12 },
      { id: 5, name_en: "Sol Ring", name_pt: null, set_code: "cmr", collector_number: "472", quantity: 1, card_id: 50, in_collection: true, owned_quantity: 1, collection_entry_id: 102, image_url: null, latest_price: 3 },
    ],
    ...overrides,
  };
}

function createMockFetch(deck: DeckDetail) {
  return vi.fn().mockImplementation((url: string) => {
    const u = String(url);
    if (u.includes("/decks/") && u.includes("/value")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          data: { total_value: 100, value_change_pct: 5, priced_cards: 3, unpriced_cards: 2, value_series: [] },
          meta: { request_id: "t" },
          errors: [],
        }),
      });
    }
    if (u.includes("/decks/")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          data: deck,
          meta: { request_id: "t" },
          errors: [],
        }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ data: null, meta: { request_id: "t" }, errors: [] }),
    });
  });
}

function wrap(deckData: DeckDetail) {
  return render(
    <LanguageProvider>
      <MemoryRouter initialEntries={["/decks/1"]}>
        <Routes>
          <Route path="/decks/:id" element={<DeckView />} />
        </Routes>
      </MemoryRouter>
    </LanguageProvider>,
  );
}

describe("F97-T05: Add Missing Cards on DeckView", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("shows add-missing-cards button when ownership_pct < 100", async () => {
    const deck = makeDeck({ ownership_pct: 60 });
    globalThis.fetch = createMockFetch(deck) as unknown as typeof fetch;
    wrap(deck);
    const btn = await screen.findByTestId("add-missing-cards-btn");
    expect(btn).toBeDefined();
  });

  it("does not show add-missing-cards button when ownership_pct is 100", async () => {
    const deck = makeDeck({
      ownership_pct: 100,
      owned_cards: 5,
      cards: makeDeck().cards.map((c) => ({ ...c, in_collection: true, owned_quantity: c.quantity })),
    });
    globalThis.fetch = createMockFetch(deck) as unknown as typeof fetch;
    wrap(deck);
    await screen.findByTestId("deck-title");
    expect(screen.queryByTestId("add-missing-cards-btn")).toBeNull();
  });

  it("opens BatchAddModal with missing cards text when button is clicked", async () => {
    const deck = makeDeck({ ownership_pct: 60 });
    globalThis.fetch = createMockFetch(deck) as unknown as typeof fetch;
    wrap(deck);
    const btn = await screen.findByTestId("add-missing-cards-btn");
    fireEvent.click(btn);

    const modal = await screen.findByTestId("batch-add-modal");
    expect(modal).toBeDefined();

    const textarea = screen.getByTestId("batch-textarea") as HTMLTextAreaElement;
    // Dark Ritual: qty=3, owned=1 => need 2; set_code=lea
    expect(textarea.value).toContain("2 Dark Ritual [lea]");
    // Swords to Plowshares: qty=1, owned=0 => need 1; no set_code
    expect(textarea.value).toContain("1 Swords to Plowshares");
    // Should NOT contain owned cards
    expect(textarea.value).not.toContain("Lightning Bolt");
    expect(textarea.value).not.toContain("Sol Ring");
  });
});
