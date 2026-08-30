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
  changePassword as apiChangePassword,
} from "../api/auth";

export interface AuthContextValue {
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  mustChangePassword: boolean;
  login: (email: string, password: string) => Promise<string | null>;
  register: (
    email: string,
    password: string,
    displayName?: string,
  ) => Promise<string | null>;
  logout: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<string | null>;
}

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  error: null,
  isAuthenticated: false,
  mustChangePassword: false,
  login: async () => null,
  register: async () => null,
  logout: async () => {},
  changePassword: async () => null,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mustChangePassword, setMustChangePassword] = useState(false);

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

  // Sync auth state across browser tabs via storage events
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key !== "tcg_access_token") return;

      if (e.newValue === null) {
        // Token was removed in another tab (logout)
        setUser(null);
        setError(null);
        setMustChangePassword(false);
      } else {
        // Token was added/changed in another tab (login)
        fetchMe().then((resp) => {
          if (resp.data) {
            setUser(resp.data);
          }
        });
      }
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    setMustChangePassword(false);
    const resp = await apiLogin(email, password);
    if (resp.errors.length > 0) {
      const msg = resp.errors[0].message;
      setError(msg);
      return msg;
    }
    // Check if password expired (admin-created user with temp password)
    const data = resp.data as Record<string, unknown> | null;
    if (data && data.password_expired) {
      // Store the temp token manually (apiLogin already stored it)
      setMustChangePassword(true);
      return null;
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

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      setError(null);
      const resp = await apiChangePassword(currentPassword, newPassword);
      if (resp.errors.length > 0) {
        const msg = resp.errors[0].message;
        setError(msg);
        return msg;
      }
      setMustChangePassword(false);
      // Fetch user profile with new tokens
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
    setMustChangePassword(false);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      error,
      isAuthenticated: user !== null,
      mustChangePassword,
      login,
      register,
      logout,
      changePassword,
    }),
    [user, loading, error, mustChangePassword, login, register, logout, changePassword],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
