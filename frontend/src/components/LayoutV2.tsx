import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";
import { ThemeToggle } from "./ThemeToggle";

interface V2NavItem {
  to: string;
  labelKey: string;
  icon: React.ReactNode;
  requiresAuth?: boolean;
  requiresAdmin?: boolean;
}

/* ── SVG icon helpers ──────────────────────────────────────────────── */
const iconHome = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1h-2z" />
  </svg>
);
const iconCollection = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
  </svg>
);
const iconSearch = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);
const iconCatalog = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
  </svg>
);
const iconAlerts = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
  </svg>
);
const iconWishlist = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
  </svg>
);
const iconSettings = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.573-1.066z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);
const iconAdmin = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);
const iconMarket = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
  </svg>
);
const iconTrending = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
  </svg>
);
const iconBan = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
  </svg>
);
const iconDecks = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
  </svg>
);
const iconMarketplace = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z" />
  </svg>
);
const iconTrade = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
  </svg>
);
const iconAchievements = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
  </svg>
);
const iconEvaluations = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
  </svg>
);

/* ── Nav item lists ────────────────────────────────────────────────── */
const PRIMARY_NAV_ITEMS: ReadonlyArray<V2NavItem> = [
  { to: "/v2", labelKey: "nav.dashboard", icon: iconHome },
  { to: "/v2/collection", labelKey: "nav.myCollection", icon: iconCollection, requiresAuth: true },
  { to: "/v2/wishlist", labelKey: "nav.wishlist", icon: iconWishlist, requiresAuth: true },
  { to: "/v2/cards", labelKey: "nav.exploreCards", icon: iconSearch },
  { to: "/v2/catalog", labelKey: "nav.catalog", icon: iconCatalog },
  { to: "/v2/alerts", labelKey: "nav.alerts", icon: iconAlerts, requiresAuth: true },
  { to: "/v2/settings", labelKey: "nav.settings", icon: iconSettings, requiresAuth: true },
  { to: "/v2/admin", labelKey: "nav.admin", icon: iconAdmin, requiresAuth: true, requiresAdmin: true },
];

const BETA_NAV_ITEMS: ReadonlyArray<V2NavItem> = [
  { to: "/v2/market", labelKey: "nav.market", icon: iconMarket },
  { to: "/v2/market/trending", labelKey: "nav.trending", icon: iconTrending },
  { to: "/v2/banlist", labelKey: "nav.banlist", icon: iconBan },
  { to: "/v2/banlist/history", labelKey: "nav.banHistory", icon: iconBan },
  { to: "/v2/decks", labelKey: "nav.myDecks", icon: iconDecks, requiresAuth: true },
  { to: "/v2/decks/ranking", labelKey: "nav.topDecks", icon: iconDecks, requiresAuth: true },
  { to: "/v2/marketplace", labelKey: "nav.marketplace", icon: iconMarketplace, requiresAuth: true },
  { to: "/v2/trade-matches", labelKey: "nav.tradeMatches", icon: iconTrade, requiresAuth: true },
  { to: "/v2/achievements", labelKey: "nav.achievements", icon: iconAchievements, requiresAuth: true },
  { to: "/v2/evaluations", labelKey: "nav.evaluations", icon: iconEvaluations, requiresAuth: true },
];

/** Mobile bottom tabs — only the 5 most important items */
const BOTTOM_TAB_ITEMS: ReadonlyArray<V2NavItem> = [
  PRIMARY_NAV_ITEMS[0], // Dashboard
  PRIMARY_NAV_ITEMS[1], // Collection
  PRIMARY_NAV_ITEMS[3], // Cards
  PRIMARY_NAV_ITEMS[4], // Catalog
  PRIMARY_NAV_ITEMS[5], // Alerts
];

const BETA_NAV_STORAGE_KEY = "tcg_v2_beta_nav_open";

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

function filterNavItems(
  items: ReadonlyArray<V2NavItem>,
  isAuthenticated: boolean,
  isAdmin: boolean,
): V2NavItem[] {
  return items.filter((item) => {
    if (item.requiresAdmin && !isAdmin) return false;
    if (item.requiresAuth && !isAuthenticated) return false;
    return true;
  });
}

export function LayoutV2() {
  const { t } = useTranslation();
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [betaOpen, setBetaOpen] = useState(() => {
    try {
      return localStorage.getItem(BETA_NAV_STORAGE_KEY) === "true";
    } catch {
      return false;
    }
  });

  const displayName = user?.display_name || user?.email?.split("@")[0] || null;
  const initials = getInitials(displayName);

  const primaryItems = filterNavItems(PRIMARY_NAV_ITEMS, isAuthenticated, !!user?.is_admin);
  const betaItems = filterNavItems(BETA_NAV_ITEMS, isAuthenticated, !!user?.is_admin);

  const toggleBeta = () => {
    setBetaOpen((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(BETA_NAV_STORAGE_KEY, String(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  };

  const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
    `relative px-3 py-2 text-sm font-medium font-figtree transition-colors duration-200 ${
      isActive
        ? "text-v2-accent after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-v2-accent after:rounded-full"
        : "text-v2-muted hover:text-white"
    }`;

  const sidebarLinkClasses = ({ isActive }: { isActive: boolean }) =>
    `block px-3 py-2 text-sm font-medium rounded-md transition-colors ${
      isActive
        ? "text-v2-accent bg-v2-accent-soft"
        : "text-v2-muted hover:text-white hover:bg-v2-surface"
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
            <NavLink to="/v2" className="no-underline shrink-0" data-testid="v2-logo">
              <span className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-indigo-500 bg-clip-text text-transparent">
                TEDHC Market
              </span>
            </NavLink>

            {/* Desktop nav links — primary items */}
            <nav className="hidden md:flex items-center gap-1" data-testid="v2-nav">
              {primaryItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/v2"}
                  className={navLinkClasses}
                  data-testid={`v2-nav-${item.labelKey}`}
                >
                  {t(item.labelKey)}
                </NavLink>
              ))}
              {/* Beta toggle in topbar */}
              {betaItems.length > 0 && (
                <button
                  onClick={toggleBeta}
                  className="relative px-3 py-2 text-sm font-medium font-figtree transition-colors duration-200 text-v2-muted hover:text-white flex items-center gap-1"
                  aria-expanded={betaOpen}
                  data-testid="v2-beta-toggle"
                >
                  <svg
                    className={`h-4 w-4 transition-transform duration-200 ${betaOpen ? "rotate-90" : ""}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                    aria-hidden="true"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                  {t("nav.betaTest")}
                </button>
              )}
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

            {/* Mobile: hamburger */}
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

        {/* Desktop beta dropdown — slides below topbar */}
        {betaOpen && betaItems.length > 0 && (
          <div
            className="hidden md:block border-t px-4 py-2"
            style={{ borderColor: "rgba(255,255,255,0.06)" }}
            data-testid="v2-beta-bar"
          >
            <div className="mx-auto max-w-7xl flex items-center gap-1 flex-wrap">
              <span className="text-xs text-v2-muted mr-2 uppercase tracking-wider">{t("nav.betaTest")}</span>
              {betaItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={navLinkClasses}
                  data-testid={`v2-beta-nav-${item.labelKey}`}
                >
                  {t(item.labelKey)}
                </NavLink>
              ))}
            </div>
          </div>
        )}

        {/* Mobile dropdown menu */}
        {mobileMenuOpen && (
          <div
            className="md:hidden border-t px-4 py-3 space-y-1 max-h-[70vh] overflow-y-auto"
            style={{ borderColor: "rgba(255,255,255,0.06)" }}
            data-testid="v2-mobile-menu"
          >
            {/* Primary nav */}
            {primaryItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/v2"}
                onClick={() => setMobileMenuOpen(false)}
                className={sidebarLinkClasses}
              >
                <span className="flex items-center gap-2">
                  {item.icon}
                  {t(item.labelKey)}
                </span>
              </NavLink>
            ))}

            {/* Beta section */}
            {betaItems.length > 0 && (
              <>
                <button
                  onClick={toggleBeta}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-v2-muted hover:text-white transition-colors mt-2"
                  aria-expanded={betaOpen}
                  data-testid="v2-mobile-beta-toggle"
                >
                  <svg
                    className={`h-4 w-4 transition-transform duration-200 ${betaOpen ? "rotate-90" : ""}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                    aria-hidden="true"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                  {t("nav.betaTest")}
                </button>
                {betaOpen &&
                  betaItems.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={() => setMobileMenuOpen(false)}
                      className={sidebarLinkClasses}
                    >
                      <span className="flex items-center gap-2 pl-4">
                        {item.icon}
                        {t(item.labelKey)}
                      </span>
                    </NavLink>
                  ))}
              </>
            )}

            <div className="pt-2 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
              <ThemeToggle />
            </div>
          </div>
        )}
      </header>

      {/* Mobile bottom tab bar — top 5 items only */}
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
        {BOTTOM_TAB_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/v2"}
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

      {/* Version toggle — back to classic UI */}
      <Link
        to="/"
        className="fixed bottom-16 right-4 md:bottom-4 z-50 bg-v2-surface border border-v2-border rounded-v2 px-3 py-2 text-sm text-v2-muted hover:text-white hover:bg-v2-surface-hover shadow-v2-card transition-all"
        data-testid="v2-back-to-classic"
      >
        &larr; Back to Classic
      </Link>
    </div>
  );
}
