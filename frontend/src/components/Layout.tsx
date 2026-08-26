import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";
import { useGauchoEasterEgg } from "../hooks/useGauchoEasterEgg";
import { ChimarraoIcon } from "./ChimarraoIcon";
import { CurrencyToggle } from "./CurrencyToggle";
import { ExchangeRateBanner } from "./ExchangeRateBanner";
import { GauchoDialog } from "./GauchoDialog";
import { LanguageSelector } from "./LanguageSelector";
import { MarketTicker } from "./MarketTicker";
import { TreasureBalance } from "./TreasureBalance";

const NAV_ITEMS = [
  { to: "/", labelKey: "nav.dashboard", requiresAuth: false },
  { to: "/collection", labelKey: "nav.myCollection", requiresAuth: true },
  { to: "/cards", labelKey: "nav.exploreCards", requiresAuth: false },
  { to: "/market", labelKey: "nav.market", requiresAuth: false },
  { to: "/market/trending", labelKey: "nav.trending", requiresAuth: false },
  { to: "/banlist", labelKey: "nav.banlist", requiresAuth: false },
  { to: "/banlist/history", labelKey: "nav.banHistory", requiresAuth: false },
  { to: "/decks", labelKey: "nav.myDecks", requiresAuth: true },
  { to: "/decks/ranking", labelKey: "nav.topDecks", requiresAuth: true },
  { to: "/scans", labelKey: "nav.priceScans", requiresAuth: true },
  { to: "/schedules", labelKey: "nav.schedules", requiresAuth: true },
  { to: "/settings", labelKey: "nav.settings", requiresAuth: true },
  { to: "/admin/liga-status", labelKey: "nav.ligaStatus", requiresAuth: true },
] as const;

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

export function Layout() {
  const { t } = useTranslation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  const displayName = user?.display_name || user?.email?.split("@")[0] || null;
  const initials = getInitials(displayName);

  // Filter nav items based on auth status
  const visibleNavItems = NAV_ITEMS.filter(
    (item) => !item.requiresAuth || isAuthenticated,
  );

  // Gaucho easter egg (PILA currency)
  const gaucho = useGauchoEasterEgg(location.pathname);

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100">
      {/* Mobile overlay -- close on outside click */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
          data-testid="sidebar-overlay"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-30 w-64 bg-slate-800 border-r border-slate-600
          transform transition-transform duration-200 ease-in-out
          md:relative md:translate-x-0
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}
        data-testid="sidebar"
      >
        <div className="flex items-center h-16 px-6 border-b border-slate-600">
          <Link to="/" className="no-underline">
            <h1 className="text-lg font-bold bg-gradient-to-r from-indigo-500 via-purple-400 to-cyan-400 bg-clip-text text-transparent cursor-pointer">TEDHC Market</h1>
          </Link>
        </div>
        {/* User avatar / sign-in */}
        <div
          className="flex items-center gap-3 px-6 py-4 border-b border-slate-600"
          data-testid="user-section"
        >
          {isAuthenticated ? (
            <>
              <div className="flex items-center justify-center w-9 h-9 rounded-full bg-indigo-500 text-white text-sm font-bold">
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">
                  {displayName}
                </p>
                <button
                  onClick={async () => {
                    await logout();
                    navigate("/");
                  }}
                  className="text-xs text-slate-400 hover:text-red-400 transition-colors"
                  data-testid="logout-button"
                >
                  {t("nav.signOut")}
                </button>
              </div>
            </>
          ) : (
            <Link
              to="/login"
              className="flex items-center gap-2 text-sm font-medium text-indigo-400 hover:text-purple-400 transition-colors"
              data-testid="sign-in-link"
            >
              <div className="flex items-center justify-center w-9 h-9 rounded-full bg-slate-700 text-slate-400 text-sm font-bold">
                ?
              </div>
              <span>{t("nav.signIn")}</span>
            </Link>
          )}
        </div>
        {/* Treasure token balance */}
        {isAuthenticated && (
          <div className="border-b border-slate-600 py-1" data-testid="treasure-balance-section">
            <TreasureBalance />
          </div>
        )}
        {/* Currency toggle */}
        <div className="flex items-center gap-2 px-6 py-3 border-b border-slate-600">
          <CurrencyToggle />
        </div>
        {/* Language selector */}
        <div className="flex items-center gap-2 px-6 py-3 border-b border-slate-600" data-testid="sidebar-language-selector">
          <LanguageSelector variant="compact" />
        </div>
        <nav className="mt-4 px-3" data-testid="sidebar-nav">
          {visibleNavItems.map((item) => {
            const isActive = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`
                  flex items-center px-3 py-2 mb-1 rounded-md text-sm font-medium
                  transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400
                  ${
                    isActive
                      ? "bg-indigo-500 text-white shadow-md"
                      : "text-slate-400 hover:bg-slate-800 hover:text-white"
                  }
                `}
              >
                {t(item.labelKey)}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar with hamburger */}
        <header className="flex items-center h-16 px-4 bg-slate-800 border-b border-slate-600 md:hidden">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-md text-slate-400 hover:bg-slate-800 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            aria-label={t("nav.toggleNav")}
            data-testid="hamburger-button"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
          <Link to="/" className="ml-3 no-underline">
            <span className="text-lg font-bold bg-gradient-to-r from-indigo-500 via-purple-400 to-cyan-400 bg-clip-text text-transparent">TEDHC Market</span>
          </Link>
        </header>

        {/* Exchange rate banner */}
        <ExchangeRateBanner />
        <MarketTicker />

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6" data-testid="main-content">
          <Outlet />
        </main>
      </div>

      {/* Gaucho easter egg (PILA currency) */}
      {gaucho.showIcon && (
        <ChimarraoIcon onClick={gaucho.openDialog} />
      )}
      {gaucho.showDialog && gaucho.dialogData && (
        <GauchoDialog
          message={gaucho.dialogData.message}
          options={gaucho.dialogData.options}
          autoDismissMs={gaucho.dialogData.autoDismissMs}
          onDismiss={gaucho.dismissDialog}
        />
      )}
    </div>
  );
}
