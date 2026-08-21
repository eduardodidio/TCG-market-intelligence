import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CurrencyToggle } from "../../src/components/CurrencyToggle";
import { CurrencyProvider } from "../../src/contexts/CurrencyContext";

function renderWithProvider() {
  return render(
    <CurrencyProvider>
      <CurrencyToggle />
    </CurrencyProvider>,
  );
}

describe("CurrencyToggle", () => {
  it("renders BRL, USD, and Pila buttons", () => {
    renderWithProvider();
    expect(screen.getByTestId("currency-btn-BRL")).toBeDefined();
    expect(screen.getByTestId("currency-btn-USD")).toBeDefined();
    expect(screen.getByTestId("currency-btn-PILA")).toBeDefined();
  });

  it("BRL is selected by default", () => {
    renderWithProvider();
    expect(screen.getByTestId("currency-btn-BRL").getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByTestId("currency-btn-USD").getAttribute("aria-pressed")).toBe("false");
    expect(screen.getByTestId("currency-btn-PILA").getAttribute("aria-pressed")).toBe("false");
  });

  it("clicking PILA selects it", () => {
    renderWithProvider();
    fireEvent.click(screen.getByTestId("currency-btn-PILA"));
    expect(screen.getByTestId("currency-btn-PILA").getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByTestId("currency-btn-BRL").getAttribute("aria-pressed")).toBe("false");
  });

  it("clicking USD selects it", () => {
    renderWithProvider();
    fireEvent.click(screen.getByTestId("currency-btn-USD"));
    expect(screen.getByTestId("currency-btn-USD").getAttribute("aria-pressed")).toBe("true");
  });

  it("Pila button label contains 'Pila'", () => {
    renderWithProvider();
    expect(screen.getByTestId("currency-btn-PILA").textContent).toContain("Pila");
  });

  it("renders RS flag image in Pila button", () => {
    renderWithProvider();
    const pilaBtn = screen.getByTestId("currency-btn-PILA");
    const img = pilaBtn.querySelector("img");
    expect(img).toBeDefined();
    expect(img).not.toBeNull();
  });
});
