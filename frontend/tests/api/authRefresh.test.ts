import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  tryRefreshToken,
  forceLogout,
  _resetForTest,
} from "../../src/api/authRefresh";
import { apiGet } from "../../src/api/client";

describe("authRefresh", () => {
  const originalFetch = globalThis.fetch;
  const originalLocation = window.location;

  beforeEach(() => {
    localStorage.clear();
    _resetForTest();

    // Mock window.location so forceLogout can be observed without
    // triggering real navigation.
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...originalLocation, href: "", pathname: "/collection" },
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    Object.defineProperty(window, "location", {
      writable: true,
      value: originalLocation,
    });
  });

  // --- tryRefreshToken ---

  it("calls refresh endpoint and stores new tokens on success", async () => {
    localStorage.setItem("tcg_refresh_token", "old-refresh");

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: {
            access_token: "new-access",
            refresh_token: "new-refresh",
            token_type: "bearer",
          },
        }),
    });

    const result = await tryRefreshToken();

    expect(result).toBe(true);
    expect(localStorage.getItem("tcg_access_token")).toBe("new-access");
    expect(localStorage.getItem("tcg_refresh_token")).toBe("new-refresh");

    // Verify correct endpoint was called
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toContain("/api/v1/auth/refresh");
  });

  it("returns false and does NOT store tokens when refresh fails", async () => {
    localStorage.setItem("tcg_refresh_token", "old-refresh");
    localStorage.setItem("tcg_access_token", "old-access");

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Invalid refresh token" }),
    });

    const result = await tryRefreshToken();

    expect(result).toBe(false);
    // Tokens should NOT be cleared by tryRefreshToken — only forceLogout does that
    expect(localStorage.getItem("tcg_access_token")).toBe("old-access");
  });

  it("returns false when no refresh token is stored", async () => {
    globalThis.fetch = vi.fn();

    const result = await tryRefreshToken();

    expect(result).toBe(false);
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("deduplicates concurrent refresh calls to a single request", async () => {
    localStorage.setItem("tcg_refresh_token", "old-refresh");

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: {
            access_token: "new-access",
            refresh_token: "new-refresh",
            token_type: "bearer",
          },
        }),
    });
    globalThis.fetch = fetchMock;

    // Fire 3 concurrent refresh attempts
    const [r1, r2, r3] = await Promise.all([
      tryRefreshToken(),
      tryRefreshToken(),
      tryRefreshToken(),
    ]);

    expect(r1).toBe(true);
    expect(r2).toBe(true);
    expect(r3).toBe(true);

    // Only ONE fetch call should have been made
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  // --- forceLogout ---

  it("clears tokens and redirects to /login", () => {
    localStorage.setItem("tcg_access_token", "tok");
    localStorage.setItem("tcg_refresh_token", "ref");

    forceLogout();

    expect(localStorage.getItem("tcg_access_token")).toBeNull();
    expect(localStorage.getItem("tcg_refresh_token")).toBeNull();
    expect(window.location.href).toBe(
      "/login?returnTo=%2Fcollection&expired=1",
    );
  });

  it("does not redirect when already on /login", () => {
    (window.location as { pathname: string }).pathname = "/login";
    window.location.href = "/login";

    forceLogout();

    // href should not have changed
    expect(window.location.href).toBe("/login");
  });
});

describe("apiGet with silent token refresh", () => {
  const originalFetch = globalThis.fetch;
  const originalLocation = window.location;

  beforeEach(() => {
    localStorage.clear();
    _resetForTest();

    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...originalLocation, href: "", pathname: "/collection" },
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    Object.defineProperty(window, "location", {
      writable: true,
      value: originalLocation,
    });
  });

  it("retries once on 401 after successful token refresh", async () => {
    localStorage.setItem("tcg_access_token", "expired-token");
    localStorage.setItem("tcg_refresh_token", "valid-refresh");

    const successData = {
      data: [{ id: 1, name: "Card" }],
      meta: { cursor: null, total: 1, offset: null, request_id: "r1" },
      errors: [],
    };

    let callCount = 0;
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if ((url as string).includes("/api/v1/auth/refresh")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              data: {
                access_token: "fresh-token",
                refresh_token: "fresh-refresh",
                token_type: "bearer",
              },
            }),
        });
      }

      callCount++;
      if (callCount === 1) {
        // First call: 401 (expired)
        return Promise.resolve({
          ok: false,
          status: 401,
          statusText: "Unauthorized",
          json: () => Promise.resolve({ detail: "Token expired" }),
        });
      }
      // Retry: success
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(successData),
      });
    });

    const result = await apiGet("/api/v1/collection");

    expect(result.data).toEqual(successData.data);
    expect(result.errors).toHaveLength(0);
    // fetch called 3 times: original 401, refresh, retry
    expect(globalThis.fetch).toHaveBeenCalledTimes(3);
  });

  it("redirects to login on 401 when refresh also fails", async () => {
    localStorage.setItem("tcg_access_token", "expired-token");
    localStorage.setItem("tcg_refresh_token", "expired-refresh");

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if ((url as string).includes("/api/v1/auth/refresh")) {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({ detail: "Refresh token expired" }),
        });
      }
      return Promise.resolve({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        json: () => Promise.resolve({ detail: "Token expired" }),
      });
    });

    const result = await apiGet("/api/v1/collection");

    expect(result.errors[0].code).toBe("HTTP_401");
    expect(window.location.href).toBe(
      "/login?returnTo=%2Fcollection&expired=1",
    );
    expect(localStorage.getItem("tcg_access_token")).toBeNull();
  });

  it("does NOT retry when the failing request IS the refresh endpoint", async () => {
    localStorage.setItem("tcg_access_token", "some-token");
    localStorage.setItem("tcg_refresh_token", "some-refresh");

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: () => Promise.resolve({ detail: "Bad token" }),
    });

    const result = await apiGet("/api/v1/auth/refresh");

    expect(result.errors[0].code).toBe("HTTP_401");
    // Should have called fetch exactly once — no retry loop
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    // forceLogout should have fired
    expect(window.location.href).toBe(
      "/login?returnTo=%2Fcollection&expired=1",
    );
  });
});
