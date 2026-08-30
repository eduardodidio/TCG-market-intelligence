import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, act, waitFor } from "@testing-library/react";
import { createElement, useContext } from "react";
import { AuthContext, AuthProvider } from "../../src/contexts/AuthContext";

// Mock the auth API module
vi.mock("../../src/api/auth", () => ({
  getStoredToken: vi.fn(() => null),
  getStoredRefreshToken: vi.fn(() => null),
  fetchMe: vi.fn(),
  clearTokens: vi.fn(),
  storeTokens: vi.fn(),
  refreshTokens: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  changePassword: vi.fn(),
}));

import {
  getStoredToken,
  fetchMe,
} from "../../src/api/auth";

const mockedGetStoredToken = vi.mocked(getStoredToken);
const mockedFetchMe = vi.mocked(fetchMe);

function AuthStateReader({ onState }: { onState: (state: { user: unknown; isAuthenticated: boolean }) => void }) {
  const ctx = useContext(AuthContext);
  onState({ user: ctx.user, isAuthenticated: ctx.isAuthenticated });
  return null;
}

function renderWithProvider(onState: (state: { user: unknown; isAuthenticated: boolean }) => void) {
  return render(
    createElement(AuthProvider, null,
      createElement(AuthStateReader, { onState }),
    ),
  );
}

describe("AuthContext storage sync", () => {
  let addSpy: ReturnType<typeof vi.spyOn>;
  let removeSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetStoredToken.mockReturnValue(null);
    addSpy = vi.spyOn(window, "addEventListener");
    removeSpy = vi.spyOn(window, "removeEventListener");
  });

  afterEach(() => {
    addSpy.mockRestore();
    removeSpy.mockRestore();
  });

  function fireStorageEvent(key: string, newValue: string | null) {
    const event = new StorageEvent("storage", { key, newValue });
    window.dispatchEvent(event);
  }

  it("clears auth state when token is removed in another tab (logout)", async () => {
    // Start with a logged-in user: mock getStoredToken to return a token on mount
    mockedGetStoredToken.mockReturnValue("valid-token");
    mockedFetchMe.mockResolvedValue({
      data: {
        id: 1,
        email: "user@test.com",
        display_name: "Test",
        avatar_url: null,
        auth_provider: "email",
        preferred_language: null,
        is_active: true,
        is_admin: false,
      },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    let latestState: { user: unknown; isAuthenticated: boolean } = { user: null, isAuthenticated: false };

    await act(async () => {
      renderWithProvider((s) => { latestState = s; });
    });

    // Verify user is logged in
    await waitFor(() => {
      expect(latestState.isAuthenticated).toBe(true);
    });

    // Simulate logout on another tab: storage event with newValue=null
    act(() => {
      fireStorageEvent("tcg_access_token", null);
    });

    await waitFor(() => {
      expect(latestState.isAuthenticated).toBe(false);
      expect(latestState.user).toBeNull();
    });
  });

  it("calls fetchMe when token is added in another tab (login)", async () => {
    // Start unauthenticated
    mockedGetStoredToken.mockReturnValue(null);

    let latestState: { user: unknown; isAuthenticated: boolean } = { user: null, isAuthenticated: false };

    await act(async () => {
      renderWithProvider((s) => { latestState = s; });
    });

    expect(latestState.isAuthenticated).toBe(false);

    // Now mock fetchMe to return a user for the cross-tab login
    mockedFetchMe.mockResolvedValue({
      data: {
        id: 2,
        email: "other@test.com",
        display_name: "Other",
        avatar_url: null,
        auth_provider: "email",
        preferred_language: null,
        is_active: true,
        is_admin: false,
      },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    // Simulate login on another tab: storage event with new token
    await act(async () => {
      fireStorageEvent("tcg_access_token", "new-token-from-other-tab");
    });

    await waitFor(() => {
      expect(mockedFetchMe).toHaveBeenCalled();
      expect(latestState.isAuthenticated).toBe(true);
      expect((latestState.user as { email: string }).email).toBe("other@test.com");
    });
  });

  it("ignores storage events for unrelated keys", async () => {
    mockedGetStoredToken.mockReturnValue(null);

    let latestState: { user: unknown; isAuthenticated: boolean } = { user: null, isAuthenticated: false };

    await act(async () => {
      renderWithProvider((s) => { latestState = s; });
    });

    // Fire storage event for a different key
    act(() => {
      fireStorageEvent("some_other_key", "some-value");
    });

    // fetchMe should NOT have been called (it was not called on mount either since no token)
    expect(mockedFetchMe).not.toHaveBeenCalled();
    expect(latestState.isAuthenticated).toBe(false);
  });

  it("removes event listener on unmount (cleanup)", async () => {
    mockedGetStoredToken.mockReturnValue(null);

    let result: ReturnType<typeof render>;

    await act(async () => {
      result = renderWithProvider(() => {});
    });

    // Verify listener was added
    const storageCalls = addSpy.mock.calls.filter(
      ([event]) => event === "storage",
    );
    expect(storageCalls.length).toBeGreaterThanOrEqual(1);

    // Unmount
    act(() => {
      result!.unmount();
    });

    // Verify listener was removed
    const removeStorageCalls = removeSpy.mock.calls.filter(
      ([event]) => event === "storage",
    );
    expect(removeStorageCalls.length).toBeGreaterThanOrEqual(1);
  });
});
