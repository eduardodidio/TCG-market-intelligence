import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { BanList } from "../../src/pages/BanList";

function renderBanList() {
  return render(
    <MemoryRouter initialEntries={["/banlist"]}>
      <BanList />
    </MemoryRouter>,
  );
}

const MOCK_FORMATS = {
  data: ["standard", "modern", "legacy"],
  meta: { cursor: null, total: null, offset: null, request_id: "r1" },
  errors: [],
};

const MOCK_BANLIST = {
  data: [
    {
      card_id: 1,
      name_en: "Lightning Bolt",
      name_pt: "Raio",
      set_code: "lea",
      collector_number: "161",
      format: "standard",
      status: "banned",
      effective_date: "2026-01-01",
      image_url: null,
    },
    {
      card_id: 2,
      name_en: "Ancestral Recall",
      name_pt: null,
      set_code: "lea",
      collector_number: "47",
      format: "standard",
      status: "restricted",
      effective_date: null,
      image_url: null,
    },
  ],
  meta: { cursor: null, total: 2, offset: 0, request_id: "r2" },
  errors: [],
};

const MOCK_EMPTY_BANLIST = {
  data: [],
  meta: { cursor: null, total: 0, offset: 0, request_id: "r3" },
  errors: [],
};

describe("BanList page", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockFetch(formatResponse = MOCK_FORMATS, banlistResponse = MOCK_BANLIST) {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/banlist/formats")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(formatResponse),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(banlistResponse),
      });
    }) as unknown as typeof fetch;
  }

  it("renders format selector", async () => {
    mockFetch();
    renderBanList();
    await waitFor(() => {
      expect(screen.getByTestId("format-select")).toBeInTheDocument();
    });
  });

  it("renders ban list cards after loading", async () => {
    mockFetch();
    renderBanList();
    await waitFor(() => {
      const cards = screen.getAllByTestId("banlist-card");
      expect(cards.length).toBe(2);
    });
  });

  it("shows empty state when no results", async () => {
    mockFetch(MOCK_FORMATS, MOCK_EMPTY_BANLIST);
    renderBanList();
    await waitFor(() => {
      expect(screen.getByTestId("banlist-empty")).toBeInTheDocument();
    });
  });

  it("renders status filter buttons", async () => {
    mockFetch();
    renderBanList();
    await waitFor(() => {
      expect(screen.getByTestId("status-btn-all")).toBeInTheDocument();
      expect(screen.getByTestId("status-btn-banned")).toBeInTheDocument();
      expect(screen.getByTestId("status-btn-restricted")).toBeInTheDocument();
    });
  });

  it("renders search input", async () => {
    mockFetch();
    renderBanList();
    await waitFor(() => {
      expect(screen.getByTestId("banlist-search")).toBeInTheDocument();
    });
  });

  it("clicking status filter changes selection", async () => {
    mockFetch();
    renderBanList();
    await waitFor(() => {
      const bannedBtn = screen.getByTestId("status-btn-banned");
      fireEvent.click(bannedBtn);
      expect(bannedBtn.className).toContain("bg-indigo-500");
    });
  });
});
