import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";
import { useGauchoEasterEgg } from "../hooks/useGauchoEasterEgg";
import { usePendingDelete } from "../hooks/usePendingDelete";
import { AlertBell } from "./AlertBell";
import { ChimarraoIcon } from "./ChimarraoIcon";
import { CurrencyToggle } from "./CurrencyToggle";
import { ExchangeRateBanner } from "./ExchangeRateBanner";
import { GauchoDialog } from "./GauchoDialog";
import { InstallPrompt } from "./InstallPrompt";
import { LanguageSelector } from "./LanguageSelector";
import { MarketTicker } from "./MarketTicker";
import { OfflineBanner } from "./OfflineBanner";
import { ThemeToggle } from "./ThemeToggle";
import { TreasureBalance } from "./TreasureBalance";
import { UndoToast } from "./UndoToast";
import { UpdatePrompt } from "./UpdatePrompt";

interface NavItem {
  to: string;
  labelKey: string;
  requiresAuth: boolean;
  requiresAdmin?: boolean;
  icon: React.ReactNode;
}

/* ---- SVG icon helpers (Heroicons-style, 24x24 viewBox) ---- */
function NavIcon({ d }: { d: string }) {
  return (
    <svg className="h-5 w-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d={d} />
    </svg>
  );
}

const ICONS = {
  home: <NavIcon d="M2.25 12l8.954-8.955a1.126 1.126 0 011.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />,
  layers: <NavIcon d="M6.429 9.75L2.25 12l9.568 5.098a.75.75 0 00.364 0L21.75 12l-4.179-2.25m-7.142 0l-4.179 2.25L2.25 12l9.568-5.098a.75.75 0 01.364 0L21.75 12l-4.179-2.25m-7.142 0L6.429 9.75" />,
  heart: <NavIcon d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />,
  search: <NavIcon d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />,
  book: <NavIcon d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />,
  bell: <NavIcon d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />,
  cog: <NavIcon d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />,
  shield: <NavIcon d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />,
  chartBar: <NavIcon d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />,
  trendingUp: <NavIcon d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />,
  xCircle: <NavIcon d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />,
  clock: <NavIcon d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />,
  rectStack: <NavIcon d="M6 6.878V6a2.25 2.25 0 012.25-2.25h7.5A2.25 2.25 0 0118 6v.878m-12 0c.235-.083.487-.128.75-.128h10.5c.263 0 .515.045.75.128m-12 0A2.25 2.25 0 004.5 9v.878m13.5-3A2.25 2.25 0 0119.5 9v.878m0 0a2.246 2.246 0 00-.75-.128H5.25c-.263 0-.515.045-.75.128m15 0A2.25 2.25 0 0121 12v6a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 18v-6c0-1.018.675-1.878 1.601-2.159" />,
  star: <NavIcon d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />,
  shoppingBag: <NavIcon d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />,
  arrowsRightLeft: <NavIcon d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />,
  trophy: <NavIcon d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M18.75 4.236c.982.143 1.954.317 2.916.52A6.003 6.003 0 0116.27 9.728M18.75 4.236V4.5c0 2.108-.966 3.99-2.48 5.228m0 0a6.003 6.003 0 01-4.52 0" />,
  clipboardCheck: <NavIcon d="M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 011.65 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0118 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3l1.5 1.5 3-3.75" />,
};

const PRIMARY_NAV_ITEMS: ReadonlyArray<NavItem> = [
  { to: "/", labelKey: "nav.dashboard", requiresAuth: false, icon: ICONS.home },
  { to: "/collection", labelKey: "nav.myCollection", requiresAuth: true, icon: ICONS.layers },
  { to: "/wishlist", labelKey: "nav.wishlist", requiresAuth: true, icon: ICONS.heart },
  { to: "/cards", labelKey: "nav.exploreCards", requiresAuth: false, icon: ICONS.search },
  { to: "/catalog", labelKey: "nav.catalog", requiresAuth: false, icon: ICONS.book },
  { to: "/alerts", labelKey: "nav.alerts", requiresAuth: true, icon: ICONS.bell },
  { to: "/settings", labelKey: "nav.settings", requiresAuth: true, icon: ICONS.cog },
  { to: "/admin", labelKey: "nav.admin", requiresAuth: true, requiresAdmin: true, icon: ICONS.shield },
];

const BETA_NAV_ITEMS: ReadonlyArray<NavItem> = [
  { to: "/market", labelKey: "nav.market", requiresAuth: false, icon: ICONS.chartBar },
  { to: "/market/trending", labelKey: "nav.trending", requiresAuth: false, icon: ICONS.trendingUp },
  { to: "/banlist", labelKey: "nav.banlist", requiresAuth: false, icon: ICONS.xCircle },
  { to: "/banlist/history", labelKey: "nav.banHistory", requiresAuth: false, icon: ICONS.clock },
  { to: "/decks", labelKey: "nav.myDecks", requiresAuth: true, icon: ICONS.rectStack },
  { to: "/decks/ranking", labelKey: "nav.topDecks", requiresAuth: true, icon: ICONS.star },
  { to: "/marketplace", labelKey: "nav.marketplace", requiresAuth: true, icon: ICONS.shoppingBag },
  { to: "/trade-matches", labelKey: "nav.tradeMatches", requiresAuth: true, icon: ICONS.arrowsRightLeft },
  { to: "/achievements", labelKey: "nav.achievements", requiresAuth: true, icon: ICONS.trophy },
  { to: "/evaluations", labelKey: "nav.evaluations", requiresAuth: true, icon: ICONS.clipboardCheck },
];

const BETA_NAV_STORAGE_KEY = "tcg_beta_nav_open";

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
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem("sidebar-collapsed") === "true";
    } catch {
      return false;
    }
  });
  const [betaOpen, setBetaOpen] = useState(() => {
    try {
      return localStorage.getItem(BETA_NAV_STORAGE_KEY) === "true";
    } catch {
      return false;
    }
  });
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();

  // Persist collapsed state
  useEffect(() => {
    try {
      localStorage.setItem("sidebar-collapsed", String(collapsed));
    } catch {
      // ignore
    }
  }, [collapsed]);

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  const displayName = user?.display_name || user?.email?.split("@")[0] || null;
  const initials = getInitials(displayName);

  // Filter nav items based on auth status and admin role
  const filterNavItems = (items: ReadonlyArray<NavItem>) =>
    items.filter((item) => {
      if (item.requiresAuth && !isAuthenticated) return false;
      if (item.requiresAdmin && !user?.is_admin) return false;
      return true;
    });

  const visiblePrimaryItems = filterNavItems(PRIMARY_NAV_ITEMS);
  const visibleBetaItems = filterNavItems(BETA_NAV_ITEMS);

  const toggleBeta = () => {
    setBetaOpen((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(BETA_NAV_STORAGE_KEY, String(next));
      } catch {
        // ignore
      }
      return next;
    });
  };

  // Pending delete (undo toast)
  const { pendingDelete, clearPendingDelete, executeDelete } = usePendingDelete();

  // Gaucho easter egg (PILA currency)
  const gaucho = useGauchoEasterEgg(location.pathname);

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-slate-900 text-gray-900 dark:text-slate-100">
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
          fixed inset-y-0 left-0 z-30 bg-white dark:bg-slate-800 border-r border-gray-200 dark:border-slate-600
          transform transition-all duration-200 ease-in-out
          md:relative md:translate-x-0
          ${sidebarOpen ? "translate-x-0 w-64" : "-translate-x-full"}
          ${!sidebarOpen ? (collapsed ? "md:w-16" : "md:w-64") : ""}
        `}
        data-testid="sidebar"
      >
        <div className="flex items-center h-16 px-4 border-b border-gray-200 dark:border-slate-600 justify-between">
          <Link to="/" className="no-underline overflow-hidden">
            {collapsed ? (
              <span className="text-lg font-bold bg-gradient-to-r from-indigo-500 via-purple-400 to-cyan-400 bg-clip-text text-transparent cursor-pointer" data-testid="logo-collapsed">TM</span>
            ) : (
              <h1 className="text-lg font-bold bg-gradient-to-r from-indigo-500 via-purple-400 to-cyan-400 bg-clip-text text-transparent cursor-pointer whitespace-nowrap" data-testid="logo-expanded">TEDHC Market</h1>
            )}
          </Link>
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="hidden md:flex items-center justify-center w-7 h-7 rounded-md text-gray-400 dark:text-slate-500 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-600 dark:hover:text-slate-300 transition-colors"
            aria-label="Toggle sidebar"
            data-testid="sidebar-collapse-toggle"
          >
            <svg className={`h-4 w-4 transition-transform duration-200 ${collapsed ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
            </svg>
          </button>
        </div>
        {/* User avatar / sign-in */}
        <div
          className={`flex items-center gap-3 py-4 border-b border-gray-200 dark:border-slate-600 ${collapsed ? "px-3 justify-center" : "px-6"}`}
          data-testid="user-section"
        >
          {isAuthenticated ? (
            <>
              <div className="flex items-center justify-center w-9 h-9 rounded-full bg-indigo-500 text-white text-sm font-bold flex-shrink-0" title={collapsed ? displayName || "" : undefined}>
                {initials}
              </div>
              {!collapsed && (
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {displayName}
                  </p>
                  <button
                    onClick={async () => {
                      await logout();
                      navigate("/");
                    }}
                    className="text-xs text-gray-500 dark:text-slate-400 hover:text-red-400 transition-colors"
                    data-testid="logout-button"
                  >
                    {t("nav.signOut")}
                  </button>
                </div>
              )}
            </>
          ) : (
            <Link
              to="/login"
              className="flex items-center gap-2 text-sm font-medium text-indigo-500 dark:text-indigo-400 hover:text-purple-500 dark:hover:text-purple-400 transition-colors"
              data-testid="sign-in-link"
              title={collapsed ? t("nav.signIn") : undefined}
            >
              <div className="flex items-center justify-center w-9 h-9 rounded-full bg-gray-200 dark:bg-slate-700 text-gray-500 dark:text-slate-400 text-sm font-bold flex-shrink-0">
                ?
              </div>
              {!collapsed && <span>{t("nav.signIn")}</span>}
            </Link>
          )}
        </div>
        {/* Treasure token balance */}
        {isAuthenticated && (
          <div className={`border-b border-gray-200 dark:border-slate-600 py-1 ${collapsed ? "px-1" : ""}`} data-testid="treasure-balance-section">
            <TreasureBalance />
          </div>
        )}
        {/* Alert bell */}
        {isAuthenticated && (
          <div className={`flex items-center gap-2 py-2 border-b border-gray-200 dark:border-slate-600 ${collapsed ? "px-3 justify-center" : "px-6"}`} data-testid="alert-bell-section">
            <AlertBell />
            {!collapsed && <span className="text-sm text-gray-500 dark:text-slate-400">{t("alerts.priceAlerts")}</span>}
          </div>
        )}
        {/* Currency toggle */}
        <div className={`flex items-center gap-2 py-3 border-b border-gray-200 dark:border-slate-600 ${collapsed ? "px-2 justify-center" : "px-6"}`}>
          <CurrencyToggle />
        </div>
        {/* Language selector */}
        <div className={`flex items-center gap-2 py-3 border-b border-gray-200 dark:border-slate-600 ${collapsed ? "px-2 justify-center" : "px-6"}`} data-testid="sidebar-language-selector">
          <LanguageSelector variant="compact" />
        </div>
        {/* Theme toggle */}
        <div className={`flex items-center gap-2 py-3 border-b border-gray-200 dark:border-slate-600 ${collapsed ? "px-1 justify-center" : "px-6"}`} data-testid="sidebar-theme-toggle">
          <ThemeToggle />
        </div>
        <nav className={`mt-4 ${collapsed ? "px-1" : "px-3"}`} data-testid="sidebar-nav">
          {visiblePrimaryItems.map((item) => {
            const isActive = location.pathname === item.to;
            const label = t(item.labelKey);
            return (
              <Link
                key={item.to}
                to={item.to}
                title={collapsed ? label : undefined}
                className={`
                  flex items-center ${collapsed ? "justify-center px-2" : "px-3 gap-3"} py-2 mb-1 rounded-md text-sm font-medium
                  transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400
                  ${
                    isActive
                      ? "bg-indigo-500 text-white shadow-md"
                      : "text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800 hover:text-gray-900 dark:hover:text-white"
                  }
                `}
              >
                {item.icon}
                {!collapsed && <span className="whitespace-nowrap overflow-hidden">{label}</span>}
              </Link>
            );
          })}

          {/* Beta Test disclosure section */}
          {visibleBetaItems.length > 0 && (
            <div className="mt-2">
              <button
                onClick={toggleBeta}
                className={`flex items-center w-full ${collapsed ? "justify-center px-2" : "px-3"} py-2 mb-1 rounded-md text-sm font-medium text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800 hover:text-gray-900 dark:hover:text-white transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400`}
                data-testid="beta-nav-toggle"
                aria-expanded={betaOpen}
                title={collapsed ? t("nav.betaTest") : undefined}
              >
                <svg
                  className={`h-4 w-4 ${collapsed ? "" : "mr-2"} transition-transform duration-200 ${betaOpen ? "rotate-90" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                  aria-hidden="true"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
                {!collapsed && t("nav.betaTest")}
              </button>
              {betaOpen && (
                <div data-testid="beta-nav-items">
                  {visibleBetaItems.map((item) => {
                    const isActive = location.pathname === item.to;
                    const label = t(item.labelKey);
                    return (
                      <Link
                        key={item.to}
                        to={item.to}
                        title={collapsed ? label : undefined}
                        className={`
                          flex items-center ${collapsed ? "justify-center px-2" : "px-6 gap-3"} py-2 mb-1 rounded-md text-sm font-medium
                          transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400
                          ${
                            isActive
                              ? "bg-indigo-500 text-white shadow-md"
                              : "text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800 hover:text-gray-900 dark:hover:text-white"
                          }
                        `}
                      >
                        {item.icon}
                        {!collapsed && <span className="whitespace-nowrap overflow-hidden">{label}</span>}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </nav>
        {/* Install PWA prompt — hidden when collapsed */}
        {!collapsed && (
          <div className="mt-auto">
            <InstallPrompt />
          </div>
        )}
      </aside>

      {/* Main content area */}
      <div className={`flex flex-1 flex-col overflow-hidden transition-all duration-200`}>
        {/* Top bar with hamburger */}
        <header className="flex items-center h-16 px-4 bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-600 md:hidden">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-md text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800 hover:text-gray-900 dark:hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
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

        {/* Offline banner */}
        <OfflineBanner />
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

      {/* PWA update prompt */}
      <UpdatePrompt />

      {/* Undo delete toast -- survives page navigation */}
      {pendingDelete && (
        <UndoToast
          message={t("collection.deleteUndoMessage", { name: pendingDelete.entryName })}
          onUndo={() => {
            clearPendingDelete();
            navigate(`/collection/${pendingDelete.entryId}`);
          }}
          onExpire={async () => {
            await executeDelete();
          }}
        />
      )}

    </div>
  );
}
