import { createContext, useCallback, useEffect, useState, type ReactNode } from "react";

export type Theme = "dark" | "light" | "system";
export type ResolvedTheme = "dark" | "light";

export interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
}

const STORAGE_KEY = "tcg_theme";

function getSystemPreference(): ResolvedTheme {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function loadTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "dark" || stored === "light" || stored === "system") return stored;
  } catch {
    // localStorage unavailable
  }
  return "dark";
}

function resolveTheme(theme: Theme): ResolvedTheme {
  if (theme === "system") return getSystemPreference();
  return theme;
}

function applyThemeClass(resolved: ResolvedTheme) {
  const root = document.documentElement;
  if (resolved === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}

export const ThemeContext = createContext<ThemeContextValue>({
  theme: "dark",
  resolvedTheme: "dark",
  setTheme: () => {},
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(loadTheme);
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() =>
    resolveTheme(loadTheme()),
  );

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    const resolved = resolveTheme(t);
    setResolvedTheme(resolved);
    applyThemeClass(resolved);
    try {
      localStorage.setItem(STORAGE_KEY, t);
    } catch {
      // ignore
    }
  }, []);

  // Apply theme class on mount
  useEffect(() => {
    applyThemeClass(resolvedTheme);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for system preference changes when theme is 'system'
  useEffect(() => {
    if (theme !== "system") return;
    if (typeof window.matchMedia !== "function") return;

    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => {
      const resolved = e.matches ? "dark" : "light";
      setResolvedTheme(resolved);
      applyThemeClass(resolved);
    };

    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [theme]);

  // Sync if localStorage changes in another tab
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (
        e.key === STORAGE_KEY &&
        (e.newValue === "dark" || e.newValue === "light" || e.newValue === "system")
      ) {
        setThemeState(e.newValue);
        const resolved = resolveTheme(e.newValue);
        setResolvedTheme(resolved);
        applyThemeClass(resolved);
      }
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
