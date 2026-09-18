import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { createElement } from "react";
import { useAuth } from "../../src/hooks/useAuth";
import { AuthContext } from "../../src/contexts/AuthContext";
import type { AuthContextValue } from "../../src/contexts/AuthContext";

function createWrapper(value: AuthContextValue) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return createElement(AuthContext.Provider, { value }, children);
  };
}

describe("useAuth", () => {
  it("returns context value", () => {
    const mockValue: AuthContextValue = {
      user: {
        id: 1,
        email: "test@example.com",
        display_name: "Test",
        avatar_url: null,
        auth_provider: "email",
        preferred_language: null,
        is_active: true,
        is_admin: false,
        role: "admin",
      },
      loading: false,
      error: null,
      isAuthenticated: true,
      hasBetaAccess: true,
      mustChangePassword: false,
      changePassword: async () => null,
      login: async () => null,
      register: async () => null,
      logout: async () => {},
    };

    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(mockValue),
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.email).toBe("test@example.com");
    expect(result.current.loading).toBe(false);
    expect(result.current.hasBetaAccess).toBe(true);
  });

  it("returns unauthenticated state", () => {
    const mockValue: AuthContextValue = {
      user: null,
      loading: false,
      error: null,
      isAuthenticated: false,
      hasBetaAccess: true,
      mustChangePassword: false,
      changePassword: async () => null,
      login: async () => null,
      register: async () => null,
      logout: async () => {},
    };

    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(mockValue),
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.hasBetaAccess).toBe(true);
  });

  it("hasBetaAccess is false for guest role", () => {
    const mockValue: AuthContextValue = {
      user: {
        id: 99,
        email: "guest@example.com",
        display_name: "Guest",
        avatar_url: null,
        auth_provider: "email",
        preferred_language: null,
        is_active: true,
        is_admin: false,
        role: "guest",
      },
      loading: false,
      error: null,
      isAuthenticated: true,
      hasBetaAccess: false,
      mustChangePassword: false,
      changePassword: async () => null,
      login: async () => null,
      register: async () => null,
      logout: async () => {},
    };

    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(mockValue),
    });

    expect(result.current.hasBetaAccess).toBe(false);
  });
});
