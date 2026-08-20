import { describe, it, expect } from "vitest";
import { formatBRL, formatPercent, formatDate } from "../../src/utils/format";

describe("formatBRL", () => {
  it("formats a positive number as BRL currency", () => {
    const result = formatBRL(1234.56);
    // toLocaleString output may vary by environment; check key parts
    expect(result).toContain("R$");
    expect(result).toContain("1.234,56");
  });

  it("formats zero as R$ 0,00", () => {
    const result = formatBRL(0);
    expect(result).toContain("R$");
    expect(result).toContain("0,00");
  });

  it("formats small values correctly", () => {
    const result = formatBRL(0.5);
    expect(result).toContain("R$");
    expect(result).toContain("0,50");
  });

  it("returns '--' for null", () => {
    expect(formatBRL(null)).toBe("--");
  });

  it("returns '--' for undefined", () => {
    expect(formatBRL(undefined)).toBe("--");
  });

  it("coerces string value to number and formats", () => {
    const result = formatBRL("40.00" as unknown as number);
    expect(result).toContain("R$");
    expect(result).toContain("40,00");
  });

  it("returns '--' for non-numeric string", () => {
    expect(formatBRL("abc" as unknown as number)).toBe("--");
  });

  it("formats very large numbers with thousand separators", () => {
    const result = formatBRL(999999.99);
    expect(result).toContain("R$");
    expect(result).toContain("999.999,99");
  });

  it("returns '--' for NaN", () => {
    expect(formatBRL(NaN)).toBe("--");
  });
});

describe("formatPercent", () => {
  it("formats positive percentage with + sign", () => {
    expect(formatPercent(12.3)).toBe("+12,3%");
  });

  it("formats negative percentage with - sign", () => {
    expect(formatPercent(-5.7)).toBe("-5,7%");
  });

  it("formats zero without sign", () => {
    expect(formatPercent(0)).toBe("0,0%");
  });

  it("formats large positive percentage", () => {
    expect(formatPercent(150.0)).toBe("+150,0%");
  });

  it("formats small negative percentage", () => {
    expect(formatPercent(-0.3)).toBe("-0,3%");
  });
});

describe("formatDate", () => {
  it("formats ISO date as DD/MM/YYYY", () => {
    expect(formatDate("2026-01-15")).toBe("15/01/2026");
  });

  it("formats ISO datetime by extracting date part", () => {
    expect(formatDate("2026-08-18T12:30:00Z")).toBe("18/08/2026");
  });

  it("handles end-of-year date", () => {
    expect(formatDate("2025-12-31")).toBe("31/12/2025");
  });

  it("handles beginning-of-year date", () => {
    expect(formatDate("2026-01-01")).toBe("01/01/2026");
  });
});
