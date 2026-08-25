import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { CollectionCardDetail } from "../../src/pages/CollectionCardDetail";
import type { ApiResponse, CollectionCardDetail as CollectionCardDetailType } from "../../src/types/api";

// Mock Recharts to avoid jsdom SVG rendering issues
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

function makeLinkedEntry(
  overrides?: Partial<CollectionCardDetailType>,
): ApiResponse<CollectionCardDetailType> {
  return {
    data: {
      id: 1,
      card_id: 42,
      set_code: "DMR",
      collector_number: "123",
      name_en: "Lightning Bolt",
      name_pt: "Raio",
      set_name_en: "Dominaria Remastered",
      quantity: 1,
      quality: "NM",
      language: "EN",
      rarity: "R",
      color: "R",
      extras: null,
      latest_price: 8.5,
      image_url: "https://api.scryfall.com/cards/dmr/123?format=image&version=normal",
      price_history: [],
      source_cards: [
        {
          source: "myp",
          external_id: "99999",
          sku: "magic_dmr_123",
          url: "https://mypcards.com/magic/99999/lightning-bolt",
        },
      ],
      scryfall_url: "https://scryfall.com/search?q=Lightning+Bolt+set:DMR",
      ligamagic_url: "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt",
      ...overrides,
    },
    meta: { cursor: null, total: null, offset: null, request_id: "test-liga-001" },
    errors: [],
  };
}

function renderDetail(id = "1") {
  return render(
    <MemoryRouter initialEntries={[`/collection/${id}`]}>
      <Routes>
        <Route path="/collection/:id" element={<CollectionCardDetail />} />
        <Route path="/collection" element={<div data-testid="collection-list">Collection</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function createMockFetch(
  response: unknown,
  postHandler?: (url: string, options?: RequestInit) => Promise<{ ok: boolean; json: () => Promise<unknown> }>,
) {
  return vi.fn().mockImplementation((url: string, options?: RequestInit) => {
    const urlStr = String(url);

    // POST handlers (refresh-liga, canonize, refresh)
    if (options?.method === "POST" && postHandler) {
      return postHandler(urlStr, options);
    }

    // Price chart history call
    if (urlStr.includes("/history")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: [],
            meta: { cursor: null, total: null, request_id: "" },
            errors: [],
          }),
      });
    }

    // Legality endpoint
    if (urlStr.includes("/legality")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: [],
            meta: { cursor: null, total: null, request_id: "" },
            errors: [],
          }),
      });
    }

    // Metrics endpoint
    if (urlStr.includes("/metrics")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: null,
            meta: { cursor: null, total: null, request_id: "" },
            errors: [],
          }),
      });
    }

    // Collection detail call
    if (urlStr.includes("/api/v1/collection/")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(response),
      });
    }

    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          data: null,
          meta: { cursor: null, total: null, request_id: "" },
          errors: [],
        }),
    });
  });
}

describe("CollectionCardDetail — Liga/MYP button hierarchy", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders Liga as primary button (emerald) and MYP as secondary (gray outline)", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("refresh-buttons")).toBeDefined();
    });

    const ligaBtn = screen.getByTestId("refresh-liga-btn");
    const mypBtn = screen.getByTestId("refresh-price-btn");

    // Liga button should be emerald (primary)
    expect(ligaBtn.className).toContain("bg-emerald-600");
    expect(ligaBtn.className).toContain("text-sm");
    expect(ligaBtn.textContent).toContain("Refresh Liga");

    // MYP button should be gray outline (secondary)
    expect(mypBtn.className).toContain("border-slate-500");
    expect(mypBtn.className).toContain("bg-transparent");
    expect(mypBtn.className).toContain("text-xs");
    expect(mypBtn.textContent).toContain("Refresh MYP");
  });

  it("Liga button appears before MYP button in DOM (primary first)", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("refresh-buttons")).toBeDefined();
    });

    const container = screen.getByTestId("refresh-buttons");
    const buttons = container.querySelectorAll("button");
    expect(buttons.length).toBe(2);
    expect(buttons[0].getAttribute("data-testid")).toBe("refresh-liga-btn");
    expect(buttons[1].getAttribute("data-testid")).toBe("refresh-price-btn");
  });

  it("does NOT render LigaMagic button when both name_en and name_pt are null", async () => {
    globalThis.fetch = createMockFetch(
      makeLinkedEntry({ name_en: null, name_pt: null }),
    ) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-info-panel")).toBeDefined();
    });

    expect(screen.queryByTestId("refresh-liga-btn")).toBeNull();
  });

  it("renders LigaMagic button when only name_pt is present", async () => {
    globalThis.fetch = createMockFetch(
      makeLinkedEntry({ name_en: null, name_pt: "Raio" }),
    ) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("refresh-liga-btn")).toBeDefined();
    });
  });

  it("Liga click triggers API call to /refresh-liga endpoint", async () => {
    const updatedEntry = makeLinkedEntry({ latest_price: 12.0 });

    const postHandler = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes("/refresh-liga")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(updatedEntry),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: null,
            meta: { cursor: null, total: null, request_id: "" },
            errors: [],
          }),
      });
    });

    globalThis.fetch = createMockFetch(
      makeLinkedEntry(),
      postHandler,
    ) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("refresh-liga-btn")).toBeDefined();
    });

    screen.getByTestId("refresh-liga-btn").click();

    await waitFor(() => {
      expect(postHandler).toHaveBeenCalled();
    });

    const ligaCall = postHandler.mock.calls.find(
      ([u]: [string]) => String(u).includes("/refresh-liga"),
    );
    expect(ligaCall).toBeDefined();
    expect(String(ligaCall[0])).toContain("/collection/1/refresh-liga");
  });

  it("MYP click triggers API call to /refresh endpoint (not /refresh-liga)", async () => {
    const updatedEntry = makeLinkedEntry({ latest_price: 10.0 });

    const postHandler = vi.fn().mockImplementation((url: string) => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(updatedEntry),
      });
    });

    globalThis.fetch = createMockFetch(
      makeLinkedEntry(),
      postHandler,
    ) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("refresh-price-btn")).toBeDefined();
    });

    screen.getByTestId("refresh-price-btn").click();

    await waitFor(() => {
      expect(postHandler).toHaveBeenCalled();
    });

    const mypCall = postHandler.mock.calls.find(
      ([u]: [string]) => String(u).includes("/refresh") && !String(u).includes("/refresh-liga"),
    );
    expect(mypCall).toBeDefined();
  });

  it("shows loading state during Liga fetch (button disabled)", async () => {
    let resolvePost!: (v: unknown) => void;
    const pendingPromise = new Promise((resolve) => {
      resolvePost = resolve;
    });

    const postHandler = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes("/refresh-liga")) {
        return pendingPromise;
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: null,
            meta: { cursor: null, total: null, request_id: "" },
            errors: [],
          }),
      });
    });

    globalThis.fetch = createMockFetch(
      makeLinkedEntry(),
      postHandler,
    ) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("refresh-liga-btn")).toBeDefined();
    });

    expect(screen.getByTestId("refresh-liga-btn").hasAttribute("disabled")).toBe(false);

    screen.getByTestId("refresh-liga-btn").click();

    await waitFor(() => {
      expect(screen.getByTestId("refresh-liga-btn").hasAttribute("disabled")).toBe(true);
    });

    resolvePost({
      ok: true,
      json: () => Promise.resolve(makeLinkedEntry({ latest_price: 12.0 })),
    });
  });

  it("shows success message on successful Liga price fetch", async () => {
    const updatedEntry = makeLinkedEntry({ latest_price: 15.0 });

    const postHandler = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes("/refresh-liga")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(updatedEntry),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: null,
            meta: { cursor: null, total: null, request_id: "" },
            errors: [],
          }),
      });
    });

    globalThis.fetch = createMockFetch(
      makeLinkedEntry(),
      postHandler,
    ) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("refresh-liga-btn")).toBeDefined();
    });

    screen.getByTestId("refresh-liga-btn").click();

    await waitFor(() => {
      const msg = screen.getByTestId("refresh-message");
      expect(msg).toBeDefined();
      expect(msg.className).toContain("text-green-400");
    });
  });

  it("shows error message on Liga failure", async () => {
    const postHandler = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes("/refresh-liga")) {
        return Promise.reject(new Error("Network error"));
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: null,
            meta: { cursor: null, total: null, request_id: "" },
            errors: [],
          }),
      });
    });

    globalThis.fetch = createMockFetch(
      makeLinkedEntry(),
      postHandler,
    ) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("refresh-liga-btn")).toBeDefined();
    });

    screen.getByTestId("refresh-liga-btn").click();

    await waitFor(() => {
      const msg = screen.getByTestId("refresh-message");
      expect(msg).toBeDefined();
      expect(msg.className).toContain("text-red-400");
    });
  });

  it("existing MYP refresh button still works independently", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-info-panel")).toBeDefined();
    });

    // Both buttons should be present
    expect(screen.getByTestId("refresh-price-btn")).toBeDefined();
    expect(screen.getByTestId("refresh-liga-btn")).toBeDefined();

    // They should be different elements
    expect(screen.getByTestId("refresh-price-btn")).not.toBe(
      screen.getByTestId("refresh-liga-btn"),
    );
  });
});
