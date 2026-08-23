import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { type ReactNode } from "react";
import { CurrencyContext, type CurrencyCode } from "../../src/contexts/CurrencyContext";
import { useGauchoEasterEgg } from "../../src/hooks/useGauchoEasterEgg";

function createWrapper(currency: CurrencyCode = "PILA") {
  return ({ children }: { children: ReactNode }) => (
    <CurrencyContext.Provider
      value={{
        currency,
        setCurrency: vi.fn(),
        toggle: vi.fn(),
      }}
    >
      {children}
    </CurrencyContext.Provider>
  );
}

describe("useGauchoEasterEgg", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns correct dialogue for dashboard (/)", () => {
    const { result } = renderHook(
      () => useGauchoEasterEgg("/"),
      { wrapper: createWrapper() },
    );
    expect(result.current.dialogData).not.toBeNull();
    expect(result.current.dialogData?.message).toContain("Bah meu");
  });

  it("returns correct dialogue for collection", () => {
    const { result } = renderHook(
      () => useGauchoEasterEgg("/collection"),
      { wrapper: createWrapper() },
    );
    expect(result.current.dialogData?.message).toContain("luxo do gaúcho");
    expect(result.current.dialogData?.options).toHaveLength(2);
  });

  it("returns correct dialogue for banlist", () => {
    const { result } = renderHook(
      () => useGauchoEasterEgg("/banlist"),
      { wrapper: createWrapper() },
    );
    expect(result.current.dialogData?.message).toContain("bans recentes");
    expect(result.current.dialogData?.options).toHaveLength(2);
  });

  it("returns decks-empty variant when isEmpty=true", () => {
    const { result } = renderHook(
      () => useGauchoEasterEgg("/decks", { isEmpty: true }),
      { wrapper: createWrapper() },
    );
    expect(result.current.dialogData?.message).toContain("nenhum deckzinho");
    expect(result.current.dialogData?.options).toBeUndefined();
    expect(result.current.dialogData?.autoDismissMs).toBe(4000);
  });

  it("returns decks-with-data variant when isEmpty is not true", () => {
    const { result } = renderHook(
      () => useGauchoEasterEgg("/decks"),
      { wrapper: createWrapper() },
    );
    expect(result.current.dialogData?.message).toContain("deckzinho aí");
    expect(result.current.dialogData?.options).toHaveLength(2);
  });

  it("returns null dialogData for unknown pages", () => {
    const { result } = renderHook(
      () => useGauchoEasterEgg("/cards"),
      { wrapper: createWrapper() },
    );
    expect(result.current.dialogData).toBeNull();
    expect(result.current.showIcon).toBe(false);
  });

  it("shows icon after 2-second delay", () => {
    const { result } = renderHook(
      () => useGauchoEasterEgg("/"),
      { wrapper: createWrapper() },
    );
    expect(result.current.showIcon).toBe(false);
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(result.current.showIcon).toBe(true);
  });

  it("hides icon after dismiss", () => {
    const { result } = renderHook(
      () => useGauchoEasterEgg("/"),
      { wrapper: createWrapper() },
    );
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(result.current.showIcon).toBe(true);
    act(() => {
      result.current.openDialog();
    });
    act(() => {
      result.current.dismissDialog();
    });
    expect(result.current.showIcon).toBe(false);
    expect(result.current.showDialog).toBe(false);
  });

  it("does not show icon when currency is BRL", () => {
    const { result } = renderHook(
      () => useGauchoEasterEgg("/"),
      { wrapper: createWrapper("BRL") },
    );
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(result.current.showIcon).toBe(false);
  });

  it("does not show icon when currency is USD", () => {
    const { result } = renderHook(
      () => useGauchoEasterEgg("/"),
      { wrapper: createWrapper("USD") },
    );
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(result.current.showIcon).toBe(false);
  });

  it("persists dismissed state in sessionStorage", () => {
    const { result } = renderHook(
      () => useGauchoEasterEgg("/"),
      { wrapper: createWrapper() },
    );
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    act(() => {
      result.current.openDialog();
    });
    act(() => {
      result.current.dismissDialog();
    });
    expect(sessionStorage.getItem("gaucho_dismissed_/")).toBe("1");
  });
});
