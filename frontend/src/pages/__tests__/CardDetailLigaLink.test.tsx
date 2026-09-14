import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CardDetail } from "../CardDetail";
import type { CardDetail as CardDetailType } from "../../types/api";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "en" },
  }),
}));

vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => ({ isAuthenticated: false, user: null }),
}));

vi.mock("../../hooks/useCurrency", () => ({
  useCurrency: () => ({ currency: "BRL", setCurrency: vi.fn() }),
}));

vi.mock("../../hooks/useCardName", () => ({
  useCardName: () => ({
    getCardName: (en: string) => en,
    getSubtitleName: () => null,
  }),
}));

vi.mock("../../api/wishlist", () => ({
  checkWishlist: vi.fn().mockResolvedValue({ data: { in_wishlist: false } }),
  addToWishlist: vi.fn(),
  removeFromWishlist: vi.fn(),
}));

const { fetchCardDetailMock, fetchCardHistoryMock } = vi.hoisted(() => ({
  fetchCardDetailMock: vi.fn(),
  fetchCardHistoryMock: vi.fn(),
}));

vi.mock("../../api/cards", () => ({
  fetchCardDetail: fetchCardDetailMock,
  fetchCardHistory: fetchCardHistoryMock,
}));

function baseCard(overrides: Partial<CardDetailType> = {}): CardDetailType {
  return {
    id: 1,
    game: "magic",
    name_en: "Lightning Bolt",
    name_pt: "Raio",
    set_code: "2XM",
    collector_number: "1",
    latest_price: 5,
    currency: "BRL",
    source_cards: [],
    collection_entry_id: null,
    ligamagic_url: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function renderCardDetail() {
  return render(
    <MemoryRouter initialEntries={["/cards/1"]}>
      <Routes>
        <Route path="/cards/:id" element={<CardDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CardDetail LigaMagic link", () => {
  beforeEach(() => {
    fetchCardHistoryMock.mockResolvedValue({ data: { observations: [] }, errors: [] });
  });

  it("uses ligamagic_url from the API when present", async () => {
    fetchCardDetailMock.mockResolvedValue({
      data: baseCard({
        ligamagic_url: "https://www.ligamagic.com.br/?view=cards/card&card=1&show=1",
      }),
      errors: [],
    });

    renderCardDetail();

    const link = await screen.findByTestId("ligamagic-link");
    await waitFor(() =>
      expect(link).toHaveAttribute(
        "href",
        "https://www.ligamagic.com.br/?view=cards/card&card=1&show=1",
      ),
    );
  });

  it("falls back to the encoded name URL when ligamagic_url is null", async () => {
    fetchCardDetailMock.mockResolvedValue({
      data: baseCard({ name_en: "Dain, Dwarven King", ligamagic_url: null }),
      errors: [],
    });

    renderCardDetail();

    const link = await screen.findByTestId("ligamagic-link");
    await waitFor(() =>
      expect(link.getAttribute("href")).toContain(
        `card=${encodeURIComponent("Dain, Dwarven King")}`,
      ),
    );
  });
});
