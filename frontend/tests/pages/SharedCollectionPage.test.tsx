import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { SharedCollectionPage } from "../../src/pages/SharedCollectionPage";

function mockListing(overrides: Record<string, unknown> = {}) {
  return {
    share_code: "abc123def456gh",
    entry_id: 1,
    card_name_en: "Lightning Bolt",
    card_name_pt: "Relampago",
    set_code: "lea",
    collector_number: "161",
    rarity: "C",
    quantity: 1,
    latest_price: 25.5,
    estimated_fee: 3,
    ...overrides,
  };
}

function mockCollectionInfo(overrides: Record<string, unknown> = {}) {
  return {
    total_cards: 42,
    sets: ["lea", "mh3"],
    shared_at: "2026-09-01T12:00:00",
    ...overrides,
  };
}

function mockFetchSuccess(
  listings = [mockListing()],
  collection_info = mockCollectionInfo(),
) {
  return vi.fn().mockImplementation(() => {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          share_code: "abc123def456gh",
          collection_info,
          listings,
          count: listings.length,
        }),
    });
  });
}

function mockFetch404() {
  return vi.fn().mockImplementation(() => {
    return Promise.resolve({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: () => Promise.resolve({ detail: "Shared collection not found" }),
    });
  });
}

function mockFetchError() {
  return vi.fn().mockRejectedValue(new Error("Network error"));
}

function renderPage(
  code = "abc123def456gh",
  fetchImpl?: ReturnType<typeof vi.fn>,
) {
  if (fetchImpl) {
    vi.stubGlobal("fetch", fetchImpl);
  }
  return render(
    <MemoryRouter initialEntries={[`/marketplace/share/${code}`]}>
      <Routes>
        <Route path="/marketplace/share/:code" element={<SharedCollectionPage />} />
        <Route path="/login" element={<div data-testid="login-page">Login</div>} />
        <Route path="/marketplace" element={<div data-testid="marketplace-page">Marketplace</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("SharedCollectionPage", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders page with shared collection data", async () => {
    renderPage("abc123def456gh", mockFetchSuccess());

    await waitFor(() => {
      expect(screen.getByTestId("page-shared-collection")).toBeInTheDocument();
    });
  });

  it("shows collection stats", async () => {
    renderPage("abc123def456gh", mockFetchSuccess());

    await waitFor(() => {
      expect(screen.getByTestId("collection-stats")).toBeInTheDocument();
      expect(screen.getByTestId("total-cards")).toHaveTextContent("42 cards");
    });
  });

  it("shows set codes in stats", async () => {
    renderPage("abc123def456gh", mockFetchSuccess());

    await waitFor(() => {
      expect(screen.getByTestId("collection-sets")).toHaveTextContent("LEA, MH3");
    });
  });

  it("shows shared_at date", async () => {
    renderPage("abc123def456gh", mockFetchSuccess());

    await waitFor(() => {
      expect(screen.getByTestId("shared-at")).toBeInTheDocument();
    });
  });

  it("renders card tiles from API data", async () => {
    const listings = [
      mockListing({ entry_id: 1, card_name_en: "Lightning Bolt" }),
      mockListing({ entry_id: 2, card_name_en: "Dark Ritual" }),
    ];
    renderPage("abc123def456gh", mockFetchSuccess(listings));

    await waitFor(() => {
      expect(screen.getByTestId("shared-card-1")).toBeInTheDocument();
      expect(screen.getByTestId("shared-card-2")).toBeInTheDocument();
    });
  });

  it("shows empty state for invalid share code (404)", async () => {
    renderPage("nonexistent", mockFetch404());

    await waitFor(() => {
      expect(screen.getByText("Collection not found")).toBeInTheDocument();
    });
  });

  it("shows empty collection state when no listings", async () => {
    renderPage(
      "abc123def456gh",
      mockFetchSuccess([], mockCollectionInfo({ total_cards: 0, sets: [] })),
    );

    await waitFor(() => {
      expect(screen.getByText("This collection has no cards")).toBeInTheDocument();
    });
  });

  it("shows error banner on network error", async () => {
    renderPage("abc123def456gh", mockFetchError());

    await waitFor(() => {
      expect(screen.getByText("Retry")).toBeInTheDocument();
    });
  });

  it("renders breadcrumb with share code", async () => {
    renderPage("abc123def456gh", mockFetchSuccess());

    await waitFor(() => {
      expect(screen.getByText("abc123de...")).toBeInTheDocument();
    });
  });

  it("renders search bar", async () => {
    renderPage("abc123def456gh", mockFetchSuccess());

    await waitFor(() => {
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });
  });

  it("shows I'm Interested button on each card", async () => {
    renderPage("abc123def456gh", mockFetchSuccess());

    await waitFor(() => {
      expect(screen.getByTestId("interest-btn-1")).toBeInTheDocument();
    });
  });
});
