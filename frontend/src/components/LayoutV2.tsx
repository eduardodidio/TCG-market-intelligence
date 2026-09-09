import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";
import { ThemeToggle } from "./ThemeToggle";

interface V2NavItem {
  to: string;
  labelKey: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: ReadonlyArray<V2NavItem> = [
  {
    to: "/",
    labelKey: "nav.dashboard",
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1h-2z" />
      </svg>
    ),
  },
  {
    to: "/collection",
    labelKey: "nav.myCollection",
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    ),
  },
  {
    to: "/cards",
    labelKey: "nav.exploreCards",
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    ),
  },
  {
    to: "/catalog",
    labelKey: "nav.catalog",
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
    ),
  },
  {
    to: "/alerts",
    labelKey: "nav.alerts",
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    ),
  },
];

function getInitials(name: string | null | undefined): string {
  if (!name) return "?";
  return name
    .split(" ")
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function LayoutV2() {
  const { t } = useTranslation();
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const displayName = user?.display_name || user?.email?.split("@")[0] || null;
  const initials = getInitials(displayName);

  const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
    `relative px-3 py-2 text-sm font-medium font-figtree transition-colors duration-200 ${
      isActive
        ? "text-v2-accent after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-v2-accent after:rounded-full"
        : "text-v2-muted hover:text-white"
    }`;

  return (
    <div
      className="min-h-screen font-figtree"
      style={{
        backgroundColor: "#0a0e1a",
        backgroundImage:
          "radial-gradient(ellipse at 20% 50%, rgba(99,102,241,0.06) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(6,182,212,0.08) 0%, transparent 60%)",
      }}
    >
      {/* TopBar - Desktop */}
      <header
        className="sticky top-0 z-50 border-b"
        style={{
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          background: "rgba(10, 14, 26, 0.85)",
          borderColor: "rgba(255,255,255,0.06)",
        }}
        data-testid="v2-topbar"
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo */}
            <NavLink to="/" className="no-underline shrink-0" data-testid="v2-logo">
              <span className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-indigo-500 bg-clip-text text-transparent">
                TEDHC Market
              </span>
            </NavLink>

            {/* Desktop nav links */}
            <nav className="hidden md:flex items-center gap-1" data-testid="v2-nav">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={navLinkClasses}
                  data-testid={`v2-nav-${item.labelKey}`}
                >
                  {t(item.labelKey)}
                </NavLink>
              ))}
            </nav>

            {/* Right side: theme toggle + user menu */}
            <div className="hidden md:flex items-center gap-3">
              <ThemeToggle />

              {isAuthenticated ? (
                <div className="flex items-center gap-2" data-testid="v2-user-menu">
                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-500 text-white text-xs font-bold">
                    {initials}
                  </div>
                  <span className="text-sm text-white font-medium max-w-[120px] truncate">
                    {displayName}
                  </span>
                  <button
                    onClick={async () => {
                      await logout();
                      navigate("/");
                    }}
                    className="text-xs text-v2-muted hover:text-red-400 transition-colors ml-1"
                    data-testid="v2-logout"
                  >
                    {t("nav.signOut")}
                  </button>
                </div>
              ) : (
                <NavLink
                  to="/login"
                  className="text-sm font-medium text-v2-accent hover:text-white transition-colors"
                  data-testid="v2-sign-in"
                >
                  {t("nav.signIn")}
                </NavLink>
              )}
            </div>

            {/* Mobile: logo + hamburger */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-md text-v2-muted hover:text-white transition-colors"
              aria-label={t("nav.toggleNav")}
              data-testid="v2-hamburger"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                {mobileMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile dropdown menu */}
        {mobileMenuOpen && (
          <div
            className="md:hidden border-t px-4 py-3 space-y-1"
            style={{ borderColor: "rgba(255,255,255,0.06)" }}
            data-testid="v2-mobile-menu"
          >
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  `block px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? "text-v2-accent bg-v2-accent-soft"
                      : "text-v2-muted hover:text-white hover:bg-v2-surface"
                  }`
                }
              >
                <span className="flex items-center gap-2">
                  {item.icon}
                  {t(item.labelKey)}
                </span>
              </NavLink>
            ))}
            <div className="pt-2 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
              <ThemeToggle />
            </div>
          </div>
        )}
      </header>

      {/* Mobile bottom tab bar */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-50 md:hidden border-t flex justify-around py-1"
        style={{
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          background: "rgba(10, 14, 26, 0.95)",
          borderColor: "rgba(255,255,255,0.06)",
        }}
        data-testid="v2-bottom-tabs"
      >
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 px-2 py-1.5 text-[10px] font-medium transition-colors ${
                isActive ? "text-v2-accent" : "text-v2-muted"
              }`
            }
            data-testid={`v2-tab-${item.labelKey}`}
          >
            {item.icon}
            <span>{t(item.labelKey)}</span>
          </NavLink>
        ))}
      </nav>

      {/* Main content */}
      <main
        className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 pb-20 md:pb-6"
        data-testid="v2-main-content"
      >
        <Outlet />
      </main>
    </div>
  );
}
