import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CurrencyIndicator } from "../../src/components/CurrencyIndicator";

describe("CurrencyIndicator", () => {
  it("renders RS flag for PILA", () => {
    render(<CurrencyIndicator currency="PILA" />);
    const img = screen.getByTestId("currency-indicator-pila");
    expect(img).toBeDefined();
    expect(img.tagName).toBe("IMG");
    expect(img.getAttribute("alt")).toBe("RS flag");
  });

  it("renders R$ for BRL", () => {
    render(<CurrencyIndicator currency="BRL" />);
    const span = screen.getByTestId("currency-indicator-brl");
    expect(span).toBeDefined();
    expect(span.textContent).toBe("R$");
  });

  it("renders $ for USD", () => {
    render(<CurrencyIndicator currency="USD" />);
    const span = screen.getByTestId("currency-indicator-usd");
    expect(span).toBeDefined();
    expect(span.textContent).toBe("$");
  });

  it("uses custom size for PILA flag", () => {
    render(<CurrencyIndicator currency="PILA" size={24} />);
    const img = screen.getByTestId("currency-indicator-pila");
    expect(img.getAttribute("width")).toBe("24");
  });

  it("uses default size of 16", () => {
    render(<CurrencyIndicator currency="PILA" />);
    const img = screen.getByTestId("currency-indicator-pila");
    expect(img.getAttribute("width")).toBe("16");
  });

  it("renders R$ for unknown currency (fallback)", () => {
    render(<CurrencyIndicator currency="EUR" />);
    const span = screen.getByTestId("currency-indicator-eur");
    expect(span.textContent).toBe("R$");
  });
});
