import { describe, it, expect } from "vitest";
import { formatPila, formatCurrency, formatBRL, formatPercent, formatDate } from "../format";

describe("formatPila", () => {
  it("returns '--' for null", () => {
    expect(formatPila(null)).toBe("--");
  });

  it("returns '--' for undefined", () => {
    expect(formatPila(undefined)).toBe("--");
  });

  it("returns '--' for NaN string", () => {
    expect(formatPila("abc")).toBe("--");
  });

  it("formats zero as '0 pilas'", () => {
    expect(formatPila(0)).toBe("0 pilas");
  });

  it("formats 1 as singular '1 pila'", () => {
    expect(formatPila(1.0)).toBe("1 pila");
  });

  it("formats 2 as plural '2 pilas'", () => {
    expect(formatPila(2.0)).toBe("2 pilas");
  });

  it("formats 1.01 with singular centavo", () => {
    expect(formatPila(1.01)).toBe("1 pila e 1 centavo");
  });

  it("formats 1.50 with plural centavos", () => {
    expect(formatPila(1.50)).toBe("1 pila e 50 centavos");
  });

  it("formats 230.21 correctly", () => {
    expect(formatPila(230.21)).toBe("230 pilas e 21 centavos");
  });

  it("formats 1000 with thousands separator", () => {
    expect(formatPila(1000.0)).toBe("1.000 pilas");
  });

  it("formats large numbers with thousands separator", () => {
    expect(formatPila(1000000.0)).toBe("1.000.000 pilas");
  });

  it("omits centavos when zero", () => {
    expect(formatPila(500.0)).toBe("500 pilas");
  });

  it("formats 0.01 as '0 pilas e 1 centavo'", () => {
    expect(formatPila(0.01)).toBe("0 pilas e 1 centavo");
  });

  it("formats 0.99 correctly", () => {
    expect(formatPila(0.99)).toBe("0 pilas e 99 centavos");
  });

  it("handles string input", () => {
    expect(formatPila("230.21")).toBe("230 pilas e 21 centavos");
  });

  it("handles negative values", () => {
    expect(formatPila(-5.50)).toBe("-5 pilas e 50 centavos");
  });

  it("rounds to 2 decimal places", () => {
    // 1.005 rounds to 1.01 (note: JS floating point)
    expect(formatPila(1.006)).toBe("1 pila e 1 centavo");
  });

  it("formats 1234.56 with separator and centavos", () => {
    expect(formatPila(1234.56)).toBe("1.234 pilas e 56 centavos");
  });
});

describe("formatCurrency with PILA", () => {
  it("dispatches PILA to formatPila", () => {
    expect(formatCurrency(230.21, "PILA")).toBe("230 pilas e 21 centavos");
  });

  it("dispatches PILA null to '--'", () => {
    expect(formatCurrency(null, "PILA")).toBe("--");
  });

  it("dispatches PILA 1.0 to singular", () => {
    expect(formatCurrency(1.0, "PILA")).toBe("1 pila");
  });

  it("still formats BRL correctly", () => {
    const result = formatCurrency(100.0, "BRL");
    expect(result).toContain("100");
  });

  it("still formats USD correctly", () => {
    const result = formatCurrency(100.0, "USD");
    expect(result).toContain("100");
  });
});

describe("formatBRL", () => {
  it("returns '--' for null", () => {
    expect(formatBRL(null)).toBe("--");
  });

  it("formats a number as BRL", () => {
    const result = formatBRL(100.5);
    expect(result).toContain("100");
  });
});

describe("formatPercent", () => {
  it("formats positive with +", () => {
    expect(formatPercent(12.3)).toMatch(/\+12/);
  });

  it("formats negative with -", () => {
    expect(formatPercent(-5.7)).toMatch(/-5/);
  });
});

describe("formatDate", () => {
  it("formats ISO date as DD/MM/YYYY", () => {
    expect(formatDate("2026-08-21")).toBe("21/08/2026");
  });
});
