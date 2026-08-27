import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { createElement } from "react";
import {
  CurrencyContext,
  type CurrencyContextValue,
} from "../../src/contexts/CurrencyContext";
import type { CurrencyCode } from "../../src/types/currency";
import { useTreasureImage } from "../../src/hooks/useTreasureImage";

function renderWithCurrency(currency: CurrencyCode) {
  const value: CurrencyContextValue = {
    currency,
    setCurrency: vi.fn(),
    toggle: vi.fn(),
  };
  return renderHook(() => useTreasureImage(), {
    wrapper: ({ children }) =>
      createElement(CurrencyContext.Provider, { value }, children),
  });
}

describe("useTreasureImage", () => {
  it("returns tesouro image when currency is PILA", () => {
    const { result } = renderWithCurrency("PILA");
    expect(result.current).toContain("tesouro");
  });

  it("returns default treasure image when currency is BRL", () => {
    const { result } = renderWithCurrency("BRL");
    expect(result.current).toContain("treasure");
    expect(result.current).not.toContain("tesouro");
  });

  it("returns default treasure image when currency is USD", () => {
    const { result } = renderWithCurrency("USD");
    expect(result.current).toContain("treasure");
    expect(result.current).not.toContain("tesouro");
  });

  it("defaults to treasure image when no context provided", () => {
    const { result } = renderHook(() => useTreasureImage());
    // CurrencyContext defaults to BRL
    expect(result.current).toContain("treasure");
  });
});
