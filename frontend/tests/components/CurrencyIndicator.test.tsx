import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CurrencyIndicator } from "../../src/components/CurrencyIndicator";

describe("CurrencyIndicator", () => {
  it("renders RS flag for PILA", () => {
    render(<CurrencyIndicator currency="PILA" />);
    const container = screen.getByTestId("currency-indicator-pila");
    expect(container).toBeDefined();
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img!.getAttribute("alt")).toBe("RS flag");
  });

  it("renders Brazil flag + R$ for BRL", () => {
    render(<CurrencyIndicator currency="BRL" />);
    const container = screen.getByTestId("currency-indicator-brl");
    expect(container).toBeDefined();
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img!.getAttribute("alt")).toBe("Brazil flag");
    expect(container.textContent).toBe("R$");
  });

  it("renders US flag + $ for USD", () => {
    render(<CurrencyIndicator currency="USD" />);
    const container = screen.getByTestId("currency-indicator-usd");
    expect(container).toBeDefined();
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img!.getAttribute("alt")).toBe("US flag");
    expect(container.textContent).toBe("$");
  });

  it("uses custom size for PILA flag", () => {
    render(<CurrencyIndicator currency="PILA" size={24} />);
    const container = screen.getByTestId("currency-indicator-pila");
    const img = container.querySelector("img");
    expect(img!.getAttribute("width")).toBe("24");
  });

  it("uses default size of 16", () => {
    render(<CurrencyIndicator currency="PILA" />);
    const container = screen.getByTestId("currency-indicator-pila");
    const img = container.querySelector("img");
    expect(img!.getAttribute("width")).toBe("16");
  });

  it("renders currency code for unknown currency (fallback)", () => {
    render(<CurrencyIndicator currency="EUR" />);
    const span = screen.getByTestId("currency-indicator-eur");
    expect(span.textContent).toBe("EUR");
  });

  it("PILA does not render a text symbol", () => {
    render(<CurrencyIndicator currency="PILA" />);
    const container = screen.getByTestId("currency-indicator-pila");
    // PILA only has the flag, no text symbol
    expect(container.textContent).toBe("");
  });
});
