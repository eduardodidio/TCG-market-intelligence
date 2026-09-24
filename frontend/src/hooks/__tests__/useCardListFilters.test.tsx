import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useCardListFilters } from "../useCardListFilters";

let capturedSearch = "";

function wrapperFactory(initialEntries: string[]) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter initialEntries={initialEntries}>
        <LocationCapture>{children}</LocationCapture>
      </MemoryRouter>
    );
  };
}

function LocationCapture({ children }: { children: ReactNode }) {
  const location = useLocation();
  capturedSearch = location.search;
  return <>{children}</>;
}

describe("useCardListFilters", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    capturedSearch = "";
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("initialises from ?name&set&sort&dir", () => {
    const { result } = renderHook(
      () => useCardListFilters({ defaultSortBy: "name", defaultSortDir: "asc" }),
      { wrapper: wrapperFactory(["/?name=bolt&set=lea&sort=price&dir=desc"]) },
    );
    expect(result.current.search).toBe("bolt");
    expect(result.current.selectedSet).toBe("lea");
    expect(result.current.sortBy).toBe("price");
    expect(result.current.sortDir).toBe("desc");
    expect(result.current.sortValue).toBe("price-desc");
  });

  it("falls back to defaults when no params are present", () => {
    const { result } = renderHook(
      () => useCardListFilters({ defaultSortBy: "name", defaultSortDir: "asc" }),
      { wrapper: wrapperFactory(["/"]) },
    );
    expect(result.current.search).toBe("");
    expect(result.current.selectedSet).toBeNull();
    expect(result.current.sortBy).toBe("name");
    expect(result.current.sortDir).toBe("asc");
  });

  it("falls back to the default dir on an invalid dir value", () => {
    const { result } = renderHook(
      () => useCardListFilters({ defaultSortBy: "name", defaultSortDir: "asc" }),
      { wrapper: wrapperFactory(["/?dir=sideways"]) },
    );
    expect(result.current.sortDir).toBe("asc");
  });

  it("writes search changes to the URL and preserves unrelated params like tab", () => {
    const { result } = renderHook(
      () => useCardListFilters({ defaultSortBy: "name", defaultSortDir: "asc" }),
      { wrapper: wrapperFactory(["/?tab=seller&name=x"]) },
    );

    act(() => {
      result.current.setSort("price", "desc");
    });

    const params = new URLSearchParams(capturedSearch);
    expect(params.get("tab")).toBe("seller");
    expect(params.get("sort")).toBe("price");
    expect(params.get("dir")).toBe("desc");
  });

  it("removes sort/dir from the URL when resetting to the defaults", () => {
    const { result } = renderHook(
      () => useCardListFilters({ defaultSortBy: "name", defaultSortDir: "asc" }),
      { wrapper: wrapperFactory(["/?sort=price&dir=desc"]) },
    );

    act(() => {
      result.current.setSort("name", "asc");
    });

    const params = new URLSearchParams(capturedSearch);
    expect(params.has("sort")).toBe(false);
    expect(params.has("dir")).toBe(false);
  });

  it("removes name from the URL when the search is cleared", () => {
    const { result } = renderHook(
      () => useCardListFilters({ defaultSortBy: "name", defaultSortDir: "asc" }),
      { wrapper: wrapperFactory(["/?name=bolt"]) },
    );

    act(() => {
      result.current.setSearch("");
    });

    const params = new URLSearchParams(capturedSearch);
    expect(params.has("name")).toBe(false);
  });

  it("updates debouncedSearch after 300ms", () => {
    const { result } = renderHook(
      () => useCardListFilters({ defaultSortBy: "name", defaultSortDir: "asc" }),
      { wrapper: wrapperFactory(["/"]) },
    );

    act(() => {
      result.current.setSearch("bolt");
    });
    expect(result.current.debouncedSearch).toBe("");

    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current.debouncedSearch).toBe("bolt");
  });

  it("removes the set param when selectedSet is cleared", () => {
    const { result } = renderHook(
      () => useCardListFilters({ defaultSortBy: "name", defaultSortDir: "asc" }),
      { wrapper: wrapperFactory(["/?set=lea"]) },
    );

    act(() => {
      result.current.setSelectedSet(null);
    });

    const params = new URLSearchParams(capturedSearch);
    expect(params.has("set")).toBe(false);
  });
});
