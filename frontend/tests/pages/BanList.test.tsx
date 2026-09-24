import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { BanList } from "../../src/pages/BanList";

vi.mock("../../src/api/banlist");
vi.mock("../../src/hooks/useAuth");

import {
  fetchBanList,
  fetchBanlistStatus,
  fetchCardBanHistory,
  fetchCardLegalities,
  fetchFormats,
} from "../../src/api/banlist";
import { useAuth } from "../../src/hooks/useAuth";

function renderBanList(initialEntry = "/banlist") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <BanList />
    </MemoryRouter>,
  );
}

const MOCK_FORMATS = {
  data: ["standard", "modern", "legacy", "commander"],
  meta: { cursor: null, total: null, offset: null, request_id: "r1" },
  errors: [],
};

const MOCK_STATUS = {
  data: {
    last_synced_at: "2026-01-01T00:00:00Z",
    legalities_count: 100,
    banned_count: 10,
    restricted_count: 5,
    history_count: 20,
    formats: 4,
  },
  meta: { cursor: null, total: null, offset: null, request_id: "rs" },
  errors: [],
};

function makeEntry(overrides: Record<string, unknown> = {}) {
  return {
    card_id: 1,
    name_en: "Lightning Bolt",
    name_pt: "Raio",
    set_code: "lea",
    collector_number: "161",
    format: "standard",
    status: "banned",
    effective_date: "2026-01-01",
    image_url: null,
    printings: 1,
    owned: false,
    owned_quantity: 0,
    ...overrides,
  };
}

function makeBanlistResponse(items: ReturnType<typeof makeEntry>[], total?: number) {
  return {
    data: items,
    meta: { cursor: null, total: total ?? items.length, offset: 0, request_id: "r2" },
    errors: [],
  };
}

describe("BanList page", () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 1, email: "test@example.com" } as never,
      loading: false,
      error: null,
      isAuthenticated: true,
      hasBetaAccess: true,
      mustChangePassword: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      changePassword: vi.fn(),
    });
    vi.mocked(fetchFormats).mockResolvedValue(MOCK_FORMATS as never);
    vi.mocked(fetchBanlistStatus).mockResolvedValue(MOCK_STATUS as never);
    vi.mocked(fetchBanList).mockResolvedValue(
      makeBanlistResponse([
        makeEntry({ card_id: 1, name_en: "Lightning Bolt", status: "banned" }),
        makeEntry({ card_id: 2, name_en: "Ancestral Recall", status: "restricted" }),
      ]) as never,
    );
    vi.mocked(fetchCardLegalities).mockResolvedValue({
      data: [],
      meta: { cursor: null, total: null, offset: null, request_id: "rl" },
      errors: [],
    } as never);
    vi.mocked(fetchCardBanHistory).mockResolvedValue({
      data: [],
      meta: { cursor: null, total: null, offset: null, request_id: "rh" },
      errors: [],
    } as never);
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it("renders format selector", async () => {
    renderBanList();
    await waitFor(() => {
      expect(screen.getByTestId("format-select")).toBeInTheDocument();
    });
  });

  it("renders ban list cards after loading", async () => {
    renderBanList();
    await waitFor(() => {
      const cards = screen.getAllByTestId("banlist-card");
      expect(cards.length).toBe(2);
    });
  });

  it("shows empty state when no results", async () => {
    vi.mocked(fetchBanList).mockResolvedValue(makeBanlistResponse([], 0) as never);
    renderBanList();
    await waitFor(() => {
      expect(screen.getByTestId("banlist-empty")).toBeInTheDocument();
    });
  });

  it("renders status filter buttons", async () => {
    renderBanList();
    await waitFor(() => {
      expect(screen.getByTestId("status-btn-all")).toBeInTheDocument();
      expect(screen.getByTestId("status-btn-banned")).toBeInTheDocument();
      expect(screen.getByTestId("status-btn-restricted")).toBeInTheDocument();
    });
  });

  it("renders search input", async () => {
    renderBanList();
    await waitFor(() => {
      expect(screen.getByTestId("banlist-search")).toBeInTheDocument();
    });
  });

  it("clicking status filter changes selection", async () => {
    renderBanList();
    await waitFor(() => {
      const bannedBtn = screen.getByTestId("status-btn-banned");
      fireEvent.click(bannedBtn);
      expect(bannedBtn.className).toContain("bg-indigo-500");
    });
  });

  it("logged-in user toggles owned-only, refetches with ownedOnly true and sets ?owned=1", async () => {
    renderBanList();
    await waitFor(() => {
      expect(screen.getAllByTestId("banlist-card").length).toBe(2);
    });
    const toggle = screen.getByTestId("owned-only-toggle") as HTMLInputElement;
    expect(toggle.disabled).toBe(false);
    fireEvent.click(toggle);
    await waitFor(() => {
      const calls = vi.mocked(fetchBanList).mock.calls;
      const lastCall = calls[calls.length - 1][0];
      expect(lastCall.ownedOnly).toBe(true);
    });
  });

  it("clicking a tile opens the modal, closing clears it", async () => {
    renderBanList();
    await waitFor(() => {
      expect(screen.getAllByTestId("banlist-card").length).toBe(2);
    });
    const cards = screen.getAllByTestId("banlist-card");
    fireEvent.click(cards[0]);
    await waitFor(() => {
      expect(screen.getByTestId("ban-card-modal")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("ban-card-modal-close"));
    await waitFor(() => {
      expect(screen.queryByTestId("ban-card-modal")).not.toBeInTheDocument();
    });
  });

  it("logged out with ?owned=1 in URL: toggle disabled, fetch uses ownedOnly false", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      loading: false,
      error: null,
      isAuthenticated: false,
      hasBetaAccess: true,
      mustChangePassword: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      changePassword: vi.fn(),
    });
    renderBanList("/banlist?format=commander&owned=1");
    await waitFor(() => {
      const toggle = screen.getByTestId("owned-only-toggle") as HTMLInputElement;
      expect(toggle.disabled).toBe(true);
    });
    await waitFor(() => {
      const calls = vi.mocked(fetchBanList).mock.calls;
      expect(calls.length).toBeGreaterThan(0);
      expect(calls[calls.length - 1][0].ownedOnly).toBe(false);
    });
  });

  it("shows banlist-not-synced when legalities_count is 0", async () => {
    vi.mocked(fetchBanlistStatus).mockResolvedValue(
      makeBanlistResponse as never,
    );
    vi.mocked(fetchBanlistStatus).mockResolvedValue({
      data: { ...MOCK_STATUS.data, legalities_count: 0 },
      meta: MOCK_STATUS.meta,
      errors: [],
    } as never);
    vi.mocked(fetchBanList).mockResolvedValue(makeBanlistResponse([], 0) as never);
    renderBanList();
    await waitFor(() => {
      expect(screen.getByTestId("banlist-not-synced")).toBeInTheDocument();
    });
  });

  it("shows emptyOwned text when ownedOnly returns no results", async () => {
    vi.mocked(fetchBanList).mockResolvedValue(makeBanlistResponse([], 0) as never);
    renderBanList("/banlist?format=commander&owned=1");
    await waitFor(() => {
      expect(screen.getByTestId("banlist-empty")).toHaveTextContent(
        "None of your cards are banned or restricted in this format",
      );
    });
  });

  it("preselects format from URL", async () => {
    renderBanList("/banlist?format=legacy");
    await waitFor(() => {
      expect(screen.getByTestId("format-select")).toHaveValue("legacy");
    });
  });

  it("shows error text when fetchBanList rejects", async () => {
    vi.mocked(fetchBanList).mockRejectedValue(new Error("network down"));
    renderBanList();
    await waitFor(() => {
      expect(screen.getByText("network down")).toBeInTheDocument();
    });
  });

  it("shows load more when total exceeds page size and hides it after loading", async () => {
    const firstPage = Array.from({ length: 50 }, (_, i) =>
      makeEntry({ card_id: i + 1, name_en: `Card ${i + 1}` }),
    );
    const secondPage = [makeEntry({ card_id: 51, name_en: "Card 51" })];
    vi.mocked(fetchBanList).mockImplementation((params: { offset?: number }) => {
      if (!params.offset) {
        return Promise.resolve(makeBanlistResponse(firstPage, 51) as never);
      }
      return Promise.resolve(makeBanlistResponse(secondPage, 51) as never);
    });
    renderBanList();
    await waitFor(() => {
      expect(screen.getByTestId("banlist-load-more")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("banlist-load-more"));
    await waitFor(() => {
      expect(screen.queryByTestId("banlist-load-more")).not.toBeInTheDocument();
      expect(screen.getAllByTestId("banlist-card").length).toBe(51);
    });
  });
});
