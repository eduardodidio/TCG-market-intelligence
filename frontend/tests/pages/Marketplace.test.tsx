import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Marketplace } from "../../src/pages/Marketplace";

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

function mockFetch(listings = [mockListing()]) {
  return vi.fn().mockImplementation((url: string) => {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ listings, count: listings.length }),
    });
  });
}

function renderPage(fetchImpl?: ReturnType<typeof vi.fn>) {
  if (fetchImpl) {
    vi.stubGlobal("fetch", fetchImpl);
  }
  return render(
    <MemoryRouter>
      <Marketplace />
    </MemoryRouter>,
  );
}

describe("Marketplace", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders page title", async () => {
    renderPage(mockFetch());
    expect(screen.getByText("Card Marketplace")).toBeInTheDocument();
  });

  it("renders card grid from API data", async () => {
    const listings = [
      mockListing({ entry_id: 1, card_name_en: "Lightning Bolt" }),
      mockListing({ entry_id: 2, card_name_en: "Dark Ritual", share_code: "xyz789" }),
    ];
    renderPage(mockFetch(listings));

    await waitFor(() => {
      expect(screen.getByTestId("marketplace-card-1")).toBeInTheDocument();
      expect(screen.getByTestId("marketplace-card-2")).toBeInTheDocument();
    });
  });

  it("shows card name in listing", async () => {
    renderPage(mockFetch());

    await waitFor(() => {
      expect(screen.getByText("Lightning Bolt")).toBeInTheDocument();
    });
  });

  it("shows estimated fee per card", async () => {
    renderPage(mockFetch());

    await waitFor(() => {
      expect(screen.getByText("3 tokens")).toBeInTheDocument();
    });
  });

  it("shows share code (truncated) per card", async () => {
    renderPage(mockFetch());

    await waitFor(() => {
      expect(screen.getByText("abc123de...")).toBeInTheDocument();
    });
  });

  it("does not show user info in listings", async () => {
    renderPage(mockFetch());

    await waitFor(() => {
      expect(screen.getByTestId("marketplace-card-1")).toBeInTheDocument();
    });

    // No user email or name should appear
    expect(screen.queryByText(/@/)).not.toBeInTheDocument();
  });

  it("shows 'I'm Interested' button per card", async () => {
    renderPage(mockFetch());

    await waitFor(() => {
      expect(screen.getByTestId("interest-btn-1")).toBeInTheDocument();
      expect(screen.getByTestId("interest-btn-1")).toHaveTextContent("I'm Interested");
    });
  });

  it("shows empty state when no listings", async () => {
    renderPage(mockFetch([]));

    await waitFor(() => {
      expect(screen.getByText("No cards available for trade")).toBeInTheDocument();
    });
  });

  it("renders search bar", async () => {
    renderPage(mockFetch());

    await waitFor(() => {
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });
  });

  it("shows My Trades link", async () => {
    renderPage(mockFetch());

    expect(screen.getByText("My Trades")).toBeInTheDocument();
  });

  it("shows set code and collector number", async () => {
    renderPage(mockFetch());

    await waitFor(() => {
      expect(screen.getByText("LEA #161")).toBeInTheDocument();
    });
  });

  it("shows quantity badge when > 1", async () => {
    renderPage(mockFetch([mockListing({ quantity: 3 })]));

    await waitFor(() => {
      expect(screen.getByText("x3")).toBeInTheDocument();
    });
  });

  it("handles API error gracefully", async () => {
    const failFetch = vi.fn().mockRejectedValue(new Error("Network error"));
    renderPage(failFetch);

    await waitFor(() => {
      // ErrorBanner renders a Retry button on failure
      expect(screen.getByText("Retry")).toBeInTheDocument();
    });
  });
});
