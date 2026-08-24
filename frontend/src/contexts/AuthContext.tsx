import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";
import type { UserProfile } from "../api/auth";
import {
  clearTokens,
  fetchMe,
  getStoredToken,
  getStoredRefreshToken,
  refreshTokens,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
} from "../api/auth";

export interface AuthContextValue {
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<string | null>;
  register: (
    email: string,
    password: string,
    displayName?: string,
  ) => Promise<string | null>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  error: null,
  isAuthenticated: false,
  login: async () => null,
  register: async () => null,
  logout: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Try to restore session on mount
  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }

    fetchMe()
      .then(async (resp) => {
        if (resp.data) {
          setUser(resp.data);
          return;
        }
        // If fetchMe failed (e.g. expired token), try refreshing
        const hasRefresh = getStoredRefreshToken();
        if (!hasRefresh) {
          clearTokens();
          return;
        }
        const refreshResp = await refreshTokens();
        if (!refreshResp.data) {
          clearTokens();
          return;
        }
        // Retry fetchMe with new access token
        const retryResp = await fetchMe();
        if (retryResp.data) {
          setUser(retryResp.data);
        } else {
          clearTokens();
        }
      })
      .catch(() => {
        clearTokens();
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    const resp = await apiLogin(email, password);
    if (resp.errors.length > 0) {
      const msg = resp.errors[0].message;
      setError(msg);
      return msg;
    }
    // Fetch user profile after login
    const meResp = await fetchMe();
    if (meResp.data) {
      setUser(meResp.data);
    }
    return null;
  }, []);

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      setError(null);
      const resp = await apiRegister(email, password, displayName);
      if (resp.errors.length > 0) {
        const msg = resp.errors[0].message;
        setError(msg);
        return msg;
      }
      const meResp = await fetchMe();
      if (meResp.data) {
        setUser(meResp.data);
      }
      return null;
    },
    [],
  );

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
    setError(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      error,
      isAuthenticated: user !== null,
      login,
      register,
      logout,
    }),
    [user, loading, error, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
