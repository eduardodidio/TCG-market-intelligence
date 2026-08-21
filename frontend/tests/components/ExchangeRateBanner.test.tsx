import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { ExchangeRateBanner } from "../../src/components/ExchangeRateBanner";
import {
  CurrencyContext,
  type CurrencyCode,
} from "../../src/contexts/CurrencyContext";

// Helper: wrap in CurrencyContext with a specific currency
function renderWithCurrency(currency: CurrencyCode) {
  return render(
    <CurrencyContext.Provider
      value={{
        currency,
        setCurrency: vi.fn(),
        toggle: vi.fn(),
      }}
    >
      <ExchangeRateBanner />
    </CurrencyContext.Provider>,
  );
}

function mockFetchSuccess(rate = 5.42, rateDate = "2026-08-21") {
  return vi.fn().mockResolvedValue({
    ok: true,
    json: () =>
      Promise.resolve({
        data: {
          rate_date: rateDate,
          from_currency: "USD",
          to_currency: "BRL",
          rate,
          source: "BCB_PTAX",
        },
        meta: { cursor: null, total: null, offset: null, request_id: "r1" },
        errors: [],
      }),
  });
}

function mockFetchNoData() {
  return vi.fn().mockResolvedValue({
    ok: true,
    json: () =>
      Promise.resolve({
        data: null,
        meta: { cursor: null, total: null, offset: null, request_id: "r1" },
        errors: [],
      }),
  });
}

function mockFetchNetworkError() {
  return vi.fn().mockRejectedValue(new Error("Network error"));
}

beforeEach(() => {
  vi.stubGlobal("localStorage", {
    getItem: vi.fn().mockReturnValue(null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
});

describe("ExchangeRateBanner", () => {
  it("renders nothing when currency is BRL", () => {
    globalThis.fetch = mockFetchSuccess();
    const { container } = renderWithCurrency("BRL");
    expect(container.innerHTML).toBe("");
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("renders nothing when currency is PILA", () => {
    globalThis.fetch = mockFetchSuccess();
    const { container } = renderWithCurrency("PILA");
    expect(container.innerHTML).toBe("");
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("fetches and displays rate when currency is USD", async () => {
    globalThis.fetch = mockFetchSuccess(5.42, "2026-08-21");
    await act(async () => {
      renderWithCurrency("USD");
    });

    await waitFor(() => {
      const banner = screen.getByTestId("exchange-rate-banner");
      expect(banner).toBeDefined();
      expect(banner.textContent).toContain("5.42");
      expect(banner.textContent).toContain("2026-08-21");
    });
  });

  it("shows unavailable message when no rate data", async () => {
    globalThis.fetch = mockFetchNoData();
    await act(async () => {
      renderWithCurrency("USD");
    });

    await waitFor(() => {
      const banner = screen.getByTestId("exchange-rate-banner");
      expect(banner).toBeDefined();
      expect(banner.textContent).toContain("Exchange rate unavailable");
    });
  });

  it("shows unavailable message on network error", async () => {
    globalThis.fetch = mockFetchNetworkError();
    await act(async () => {
      renderWithCurrency("USD");
    });

    await waitFor(() => {
      const banner = screen.getByTestId("exchange-rate-banner");
      expect(banner).toBeDefined();
      expect(banner.textContent).toContain("Exchange rate unavailable");
    });
  });

  it("calls the exchange rate API endpoint", async () => {
    globalThis.fetch = mockFetchSuccess();
    await act(async () => {
      renderWithCurrency("USD");
    });

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    });

    const callUrl = String((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0]);
    expect(callUrl).toContain("/api/v1/exchange-rates/current");
  });

  it("applies the correct styling classes", async () => {
    globalThis.fetch = mockFetchSuccess();
    await act(async () => {
      renderWithCurrency("USD");
    });

    await waitFor(() => {
      const banner = screen.getByTestId("exchange-rate-banner");
      expect(banner.className).toContain("bg-slate-700/50");
      expect(banner.className).toContain("text-slate-300");
      expect(banner.className).toContain("text-xs");
      expect(banner.className).toContain("text-center");
    });
  });

  it("formats rate with two decimal places", async () => {
    globalThis.fetch = mockFetchSuccess(5.4, "2026-08-21");
    await act(async () => {
      renderWithCurrency("USD");
    });

    await waitFor(() => {
      const banner = screen.getByTestId("exchange-rate-banner");
      expect(banner.textContent).toContain("5.40");
    });
  });
});
