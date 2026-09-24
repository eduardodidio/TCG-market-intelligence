import { render, screen } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import i18n from "i18next";
import { describe, it, expect } from "vitest";
import { PriceHistoryMeta, formatHistoryDate } from "../PriceHistoryMeta";
import type { PriceHistoryMeta as PriceHistoryMetaData } from "../../types/api";
import en from "../../i18n/locales/en.json";
import ptBR from "../../i18n/locales/pt-BR.json";

function makeMeta(overrides: Partial<PriceHistoryMetaData> = {}): PriceHistoryMetaData {
  return {
    variant: "foil",
    sources: ["liga", "daily_snapshot"],
    first_observed_at: "2026-09-10",
    last_observed_at: "2026-09-24",
    real_points: 5,
    snapshot_points: 9,
    ...overrides,
  };
}

function renderWithMeta(meta: PriceHistoryMetaData) {
  return render(
    <I18nextProvider i18n={i18n}>
      <PriceHistoryMeta meta={meta} />
    </I18nextProvider>,
  );
}

describe("PriceHistoryMeta", () => {
  it("renders foil badge, translated sources and history-since date", () => {
    renderWithMeta(makeMeta());

    expect(screen.getByTestId("price-history-meta")).toBeInTheDocument();
    const badge = screen.getByTestId("price-history-variant");
    expect(badge).toHaveTextContent("Foil");
    expect(badge).toHaveAttribute("aria-label", expect.stringContaining("Foil"));
    const sources = screen.getByTestId("price-history-sources");
    expect(sources).toHaveTextContent("Liga");
    expect(sources).toHaveTextContent("Daily snapshot");
    expect(screen.getByTestId("price-history-since")).toHaveTextContent("History since 10/09");
    expect(screen.getByTestId("price-history-points")).toHaveTextContent("5 real collections · 9 repeated days");
  });

  it("renders normal badge", () => {
    renderWithMeta(makeMeta({ variant: "normal" }));
    expect(screen.getByTestId("price-history-variant")).toHaveTextContent("Normal");
    expect(screen.getByTestId("price-history-variant")).not.toHaveTextContent("Foil");
  });

  it("maps all known sources to labels", () => {
    renderWithMeta(makeMeta({ sources: ["myp", "manual", "jsonld_snapshot"] }));
    const sources = screen.getByTestId("price-history-sources");
    expect(sources).toHaveTextContent("MYP");
    expect(sources).toHaveTextContent("Manual");
    expect(sources).toHaveTextContent("JSON-LD");
  });

  it("deduplicates sources that share a label", () => {
    renderWithMeta(makeMeta({ sources: ["daily_snapshot", "daily_snapshot_backfill"] }));
    expect(screen.getAllByText("Daily snapshot")).toHaveLength(1);
  });

  it("shows unknown source raw without crashing", () => {
    renderWithMeta(makeMeta({ sources: ["foo"] }));
    expect(screen.getByTestId("price-history-sources")).toHaveTextContent("foo");
  });

  it("hides sources section when sources is empty", () => {
    renderWithMeta(makeMeta({ sources: [] }));
    expect(screen.queryByTestId("price-history-sources")).not.toBeInTheDocument();
  });

  it("hides since when first_observed_at is null", () => {
    renderWithMeta(makeMeta({ first_observed_at: null }));
    expect(screen.queryByTestId("price-history-since")).not.toBeInTheDocument();
  });

  it("renders real_points=0 correctly", () => {
    renderWithMeta(makeMeta({ real_points: 0, snapshot_points: 3 }));
    expect(screen.getByTestId("price-history-points")).toHaveTextContent("0 real collections · 3 repeated days");
  });

  it("hides points line when both counts are zero", () => {
    renderWithMeta(makeMeta({ real_points: 0, snapshot_points: 0 }));
    expect(screen.queryByTestId("price-history-points")).not.toBeInTheDocument();
  });

  it("renders pt-BR translations", async () => {
    i18n.addResourceBundle("pt-BR", "translation", ptBR, true, true);
    await i18n.changeLanguage("pt-BR");
    const { unmount } = renderWithMeta(makeMeta());
    try {
      expect(screen.getByTestId("price-history-sources")).toHaveTextContent("Snapshot diário");
      expect(screen.getByTestId("price-history-since")).toHaveTextContent("Histórico desde 10/09");
    } finally {
      unmount();
      await i18n.changeLanguage("en");
    }
  });
});

describe("formatHistoryDate", () => {
  it("formats date and datetime strings as dd/mm", () => {
    expect(formatHistoryDate("2026-09-10")).toBe("10/09");
    expect(formatHistoryDate("2026-01-02T12:00:00Z")).toBe("02/01");
  });
});

describe("priceHistory i18n keys", () => {
  const required = [
    "variantFoil", "variantNormal", "sources", "since", "sourceLiga", "sourceMyp",
    "sourceManual", "sourceJsonld", "sourceSnapshot", "emptyNeverCollected",
    "emptyPeriod", "snapshotPoint", "realVsSnapshot",
  ];

  it("en and pt-BR have identical priceHistory keys including all required ones", () => {
    const enKeys = Object.keys((en as Record<string, Record<string, string>>).priceHistory).sort();
    const ptKeys = Object.keys((ptBR as Record<string, Record<string, string>>).priceHistory).sort();
    expect(enKeys).toEqual(ptKeys);
    for (const key of required) expect(enKeys).toContain(key);
  });
});
