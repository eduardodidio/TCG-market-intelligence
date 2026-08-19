import { useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard" },
  { to: "/cards", label: "Explore Cards" },
  { to: "/market/movers", label: "Market Movers" },
] as const;

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100">
      {/* Mobile overlay — close on outside click */}
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
          fixed inset-y-0 left-0 z-30 w-64 bg-slate-800 border-r border-slate-700
          transform transition-transform duration-200 ease-in-out
          md:relative md:translate-x-0
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}
        data-testid="sidebar"
      >
        <div className="flex items-center h-16 px-6 border-b border-slate-700">
          <h1 className="text-lg font-bold text-white">TCG Market</h1>
        </div>
        <nav className="mt-4 px-3" data-testid="sidebar-nav">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.to === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`
                  flex items-center px-3 py-2 mb-1 rounded-lg text-sm font-medium
                  transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400
                  ${
                    isActive
                      ? "bg-indigo-600 text-white"
                      : "text-slate-300 hover:bg-slate-700 hover:text-white"
                  }
                `}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar with hamburger */}
        <header className="flex items-center h-16 px-4 bg-slate-800 border-b border-slate-700 md:hidden">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-md text-slate-300 hover:bg-slate-700 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            aria-label="Toggle navigation"
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
          <span className="ml-3 text-lg font-bold text-white">TCG Market</span>
        </header>

        {/* Page content */}
        <main
          className="flex-1 overflow-y-auto p-6"
          data-testid="main-content"
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
