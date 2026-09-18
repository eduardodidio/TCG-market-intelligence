import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CatalogPage } from "../CatalogPage";
import type { ApiResponse } from "../../types/api";

function envelope<T>(data: T): ApiResponse<T> {
  return {
    data,
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [],
  };
}

function mockCatalogCards() {
  return {
    items: [
      {
        id: 1,
        name_en: "Test Card",
        name_pt: null,
        set_code: "mh3",
        collector_number: "001",
        rarity: "R",
        color_identity: null,
        mana_cost: null,
        type_line: null,
        image_uri: null,
        liga_price: 10.0,
        liga_price_date: "2026-09-01",
        owned: null,
      },
    ],
    total: 1,
    limit: 50,
    offset: 0,
  };
}

function createMockFetch() {
  return vi.fn().mockImplementation((url: string, options?: RequestInit) => {
    const urlStr = typeof url === "string" ? url : String(url);

    if (urlStr.includes("/catalog/import-liga") && options?.method === "POST") {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(
            envelope({
              status: "queued",
              card_id: 42,
              card_name: "Lightning Bolt",
              message: "Solicitacao enfileirada",
            }),
          ),
      });
    }

    if (urlStr.includes("/catalog/stats")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(
            envelope({
              total_cards: 100,
              total_sets: 5,
              cards_with_price: 50,
              cards_without_price: 50,
            }),
          ),
      });
    }

    if (urlStr.includes("/catalog/sets")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope([])),
      });
    }

    if (urlStr.includes("/catalog/cards")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope(mockCatalogCards())),
      });
    }

    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          data: null,
          meta: { cursor: null, total: null, offset: null, request_id: "" },
          errors: [],
        }),
    });
  });
}

// Mock useAuth to return authenticated user
vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: { id: 1, email: "test@test.com" },
    token: "fake-token",
    login: vi.fn(),
    logout: vi.fn(),
    isAdmin: false,
    isGuest: false,
  }),
}));

function renderCatalog() {
  return render(
    <MemoryRouter initialEntries={["/catalog"]}>
      <CatalogPage />
    </MemoryRouter>,
  );
}

describe("ImportLigaLink", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("renders the import section for authenticated users", async () => {
    renderCatalog();
    await waitFor(() => {
      expect(screen.getByTestId("import-liga-section")).toBeInTheDocument();
    });
  });

  it("renders input and button", async () => {
    renderCatalog();
    await waitFor(() => {
      expect(screen.getByTestId("import-liga-input")).toBeInTheDocument();
    });
    expect(screen.getByTestId("import-liga-btn")).toBeInTheDocument();
  });

  it("button is disabled when URL is invalid", async () => {
    renderCatalog();
    await waitFor(() => {
      expect(screen.getByTestId("import-liga-input")).toBeInTheDocument();
    });

    const input = screen.getByTestId("import-liga-input");
    fireEvent.change(input, { target: { value: "https://google.com" } });

    const btn = screen.getByTestId("import-liga-btn");
    expect(btn).toBeDisabled();
  });

  it("button is enabled when URL contains ligamagic.com.br", async () => {
    renderCatalog();
    await waitFor(() => {
      expect(screen.getByTestId("import-liga-input")).toBeInTheDocument();
    });

    const input = screen.getByTestId("import-liga-input");
    fireEvent.change(input, {
      target: { value: "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt" },
    });

    const btn = screen.getByTestId("import-liga-btn");
    expect(btn).not.toBeDisabled();
  });

  it("shows success feedback after successful import", async () => {
    renderCatalog();
    await waitFor(() => {
      expect(screen.getByTestId("import-liga-input")).toBeInTheDocument();
    });

    const input = screen.getByTestId("import-liga-input");
    fireEvent.change(input, {
      target: { value: "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt" },
    });

    const btn = screen.getByTestId("import-liga-btn");
    fireEvent.click(btn);

    await waitFor(() => {
      expect(screen.getByTestId("import-liga-feedback")).toBeInTheDocument();
    });
    expect(screen.getByTestId("import-liga-feedback")).toHaveClass("text-green-400");
  });
});
