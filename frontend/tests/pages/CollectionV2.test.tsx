import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import CollectionV2 from "../../src/pages/CollectionV2";

// Mock auth
vi.mock("../../src/hooks/useAuth", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: { id: 1, email: "test@example.com" },
  }),
}));

// Mock currency
vi.mock("../../src/hooks/useCurrency", () => ({
  useCurrency: () => ({ currency: "BRL", setCurrency: vi.fn() }),
}));

// Mock language context for useCardName
vi.mock("../../src/contexts/LanguageContext", () => ({
  LanguageContext: { _currentValue: { language: "en" }, Provider: ({ children }: { children: React.ReactNode }) => children },
}));

// Mock collection API
vi.mock("../../src/api/collection", () => ({
  fetchCollection: vi.fn(),
  fetchCollectionSummary: vi.fn(),
  fetchCollectionSets: vi.fn(),
  fetchSetCompletion: vi.fn(),
}));

// Mock Card3DTilt (react-parallax-tilt needs DOM)
vi.mock("../../src/components/Card3DTilt", () => ({
  Card3DTilt: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card-3d-tilt">{children}</div>
  ),
}));

import { fetchCollection, fetchCollectionSummary } from "../../src/api/collection";

const mockFetchCollection = vi.mocked(fetchCollection);
const mockFetchSummary = vi.mocked(fetchCollectionSummary);

const MOCK_CARDS = [
  {
    id: 1,
    card_id: 10,
    set_code: "mh3",
    collector_number: "100",
    name_en: "Lightning Bolt",
    name_pt: "Raio",
    set_name_en: "Modern Horizons 3",
    set_name_pt: null,
    notes: null,
    quantity: 1,
    quality: "NM",
    language: "EN",
    rarity: "C",
    color: "R",
    extras: null,
    is_foil: false,
    latest_price: 5.5,
    price_source: "liga",
    currency: "BRL",
    image_url: null,
    acquisition_price: null,
    acquired_at: null,
  },
  {
    id: 2,
    card_id: 20,
    set_code: "fdn",
    collector_number: "200",
    name_en: "Sol Ring",
    name_pt: "Anel de Sol",
    set_name_en: "Foundations",
    set_name_pt: null,
    notes: null,
    quantity: 2,
    quality: null,
    language: null,
    rarity: "U",
    color: null,
    extras: null,
    is_foil: false,
    latest_price: null,
    price_source: null,
    currency: "BRL",
    image_url: null,
    acquisition_price: null,
    acquired_at: null,
  },
];

const MOCK_SUMMARY = {
  total_unique: 42,
  total_cards: 100,
  total_value: 1234.56,
  linked_count: 40,
  priced_count: 38,
  sets_count: 5,
  currency: "BRL",
  banned_count: 0,
  recently_changed_count: 0,
};

function renderPage() {
  return render(
    <MemoryRouter>
      <CollectionV2 />
    </MemoryRouter>,
  );
}

describe("CollectionV2", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetchCollection.mockResolvedValue({
      data: MOCK_CARDS,
      meta: { cursor: null, total: 2, offset: null, request_id: "" },
      errors: [],
    });

    mockFetchSummary.mockResolvedValue({
      data: MOCK_SUMMARY,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });
  });

  it("renders page header with title", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("My Collection")).toBeDefined();
    });
  });

  it("renders summary stats", async () => {
    renderPage();
    await waitFor(() => {
      const summary = screen.getByTestId("collection-summary");
      expect(summary.textContent).toContain("42");
      expect(summary.textContent).toContain("5");
    });
  });

  it("renders card grid with cards from API", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("v2-collection-grid")).toBeDefined();
    });
    expect(screen.getByText("Lightning Bolt")).toBeDefined();
    expect(screen.getByText("Sol Ring")).toBeDefined();
  });

  it("shows empty state when no cards", async () => {
    mockFetchCollection.mockResolvedValueOnce({
      data: [],
      meta: { cursor: null, total: 0, offset: null, request_id: "" },
      errors: [],
    });

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeDefined();
    });
  });

  it("search input filters cards", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("v2-search-input")).toBeDefined();
    });

    const input = screen.getByTestId("v2-search-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Lightning" } });
    expect(input.value).toBe("Lightning");
  });

  it("uses v2-card styling classes", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("v2-collection-grid")).toBeDefined();
    });
    const grid = screen.getByTestId("v2-collection-grid");
    const v2Cards = grid.querySelectorAll(".v2-card");
    expect(v2Cards.length).toBe(2);
  });

  it("renders filter bar with sort select", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("v2-filter-bar")).toBeDefined();
      expect(screen.getByTestId("sort-select")).toBeDefined();
    });
  });

  it("shows skeleton loading state", () => {
    // Don't resolve the fetch yet
    mockFetchCollection.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByTestId("v2-skeleton-grid")).toBeDefined();
  });

  it("displays card prices with correct formatting", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("v2-collection-grid")).toBeDefined();
    });
    const prices = screen.getAllByTestId("v2-card-price");
    // First card has price 5.50
    expect(prices[0].textContent).toContain("5");
    // Second card has no price, shows em dash
    expect(prices[1].textContent).toBe("\u2014");
  });

  it("links cards to collection detail page", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("v2-collection-grid")).toBeDefined();
    });
    const link = screen.getByTestId("v2-card-1");
    expect(link.getAttribute("href")).toBe("/collection/1");
  });
});
