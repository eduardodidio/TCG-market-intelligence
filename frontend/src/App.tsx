import { lazy, Suspense, useEffect, useRef } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LoadingSpinner } from "./components/LoadingSpinner";
import { AdminRoute } from "./components/AdminRoute";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./contexts/AuthContext";
import { CurrencyProvider } from "./contexts/CurrencyContext";
import { LanguageProvider } from "./contexts/LanguageContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { PendingDeleteProvider } from "./hooks/usePendingDelete";
import type { SupportedLanguage } from "./contexts/LanguageContext";
import { useAuth } from "./hooks/useAuth";
import { useLanguage } from "./hooks/useLanguage";

const Dashboard = lazy(() =>
  import("./pages/Dashboard").then((m) => ({ default: m.Dashboard })),
);
const Cards = lazy(() =>
  import("./pages/Cards").then((m) => ({ default: m.Cards })),
);
const CardDetail = lazy(() =>
  import("./pages/CardDetail").then((m) => ({ default: m.CardDetail })),
);
const MarketMovers = lazy(() =>
  import("./pages/MarketMovers").then((m) => ({ default: m.MarketMovers })),
);
const MyCollection = lazy(() =>
  import("./pages/MyCollection").then((m) => ({ default: m.MyCollection })),
);
const CollectionCardDetail = lazy(() =>
  import("./pages/CollectionCardDetail").then((m) => ({
    default: m.CollectionCardDetail,
  })),
);
const DeckList = lazy(() =>
  import("./pages/DeckList").then((m) => ({ default: m.DeckList })),
);
const TopDecksPage = lazy(() =>
  import("./pages/TopDecksPage").then((m) => ({ default: m.TopDecksPage })),
);
const DeckView = lazy(() =>
  import("./pages/DeckView").then((m) => ({ default: m.DeckView })),
);
const BanList = lazy(() =>
  import("./pages/BanList").then((m) => ({ default: m.BanList })),
);
const BanHistory = lazy(() =>
  import("./pages/BanHistory").then((m) => ({ default: m.BanHistory })),
);
const Trending = lazy(() =>
  import("./pages/Trending").then((m) => ({ default: m.Trending })),
);
const MarketPage = lazy(() =>
  import("./pages/MarketPage").then((m) => ({ default: m.MarketPage })),
);
const Login = lazy(() =>
  import("./pages/Login").then((m) => ({ default: m.Login })),
);
const Settings = lazy(() =>
  import("./pages/Settings").then((m) => ({ default: m.Settings })),
);
const Marketplace = lazy(() =>
  import("./pages/Marketplace").then((m) => ({ default: m.Marketplace })),
);
const MyTrades = lazy(() =>
  import("./pages/MyTrades").then((m) => ({ default: m.MyTrades })),
);
const AdminPanel = lazy(() =>
  import("./pages/AdminPanel").then((m) => ({ default: m.AdminPanel })),
);
const ChangePassword = lazy(() =>
  import("./pages/ChangePassword").then((m) => ({
    default: m.ChangePassword,
  })),
);
const Evaluations = lazy(() =>
  import("./pages/Evaluations").then((m) => ({ default: m.Evaluations })),
);
const CatalogPage = lazy(() =>
  import("./pages/CatalogPage").then((m) => ({ default: m.CatalogPage })),
);
const AlertsPage = lazy(() =>
  import("./pages/AlertsPage").then((m) => ({ default: m.AlertsPage })),
);
const AchievementsPage = lazy(() =>
  import("./pages/AchievementsPage").then((m) => ({
    default: m.AchievementsPage,
  })),
);
const SharedCollectionPage = lazy(() =>
  import("./pages/SharedCollectionPage").then((m) => ({
    default: m.SharedCollectionPage,
  })),
);
const WishlistPage = lazy(() =>
  import("./pages/WishlistPage").then((m) => ({
    default: m.WishlistPage,
  })),
);
const TradeMatchesPage = lazy(() =>
  import("./pages/TradeMatchesPage").then((m) => ({
    default: m.TradeMatchesPage,
  })),
);
const NotFoundPage = lazy(() =>
  import("./pages/NotFoundPage").then((m) => ({ default: m.NotFoundPage })),
);

/**
 * Syncs user's preferred_language from their profile to the LanguageContext
 * whenever the user changes (login, session restore).
 */
function LanguageSyncEffect() {
  const { user } = useAuth();
  const { setLanguage } = useLanguage();
  const syncedRef = useRef<number | null>(null);

  useEffect(() => {
    if (user && user.preferred_language && syncedRef.current !== user.id) {
      const lang = user.preferred_language;
      if (lang === "en" || lang === "pt-BR") {
        setLanguage(lang as SupportedLanguage);
      }
      syncedRef.current = user.id;
    }
    if (!user) {
      syncedRef.current = null;
    }
  }, [user, setLanguage]);

  return null;
}

export default function App() {
  return (
    <LanguageProvider>
    <ThemeProvider>
    <AuthProvider>
      <LanguageSyncEffect />
      <CurrencyProvider>
        <BrowserRouter>
        <PendingDeleteProvider>
          <Routes>
            {/* Login page — no layout */}
            <Route
              path="/login"
              element={
                <Suspense
                  fallback={<LoadingSpinner message="Loading page..." />}
                >
                  <Login />
                </Suspense>
              }
            />

            {/* Change password — no layout (first-access flow) */}
            <Route
              path="/change-password"
              element={
                <Suspense
                  fallback={<LoadingSpinner message="Loading page..." />}
                >
                  <ChangePassword />
                </Suspense>
              }
            />

            {/* Shared collection — public route with Layout (no auth required) */}
            <Route
              path="/marketplace/share/:code"
              element={<Layout />}
            >
              <Route
                index
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <SharedCollectionPage />
                  </Suspense>
                }
              />
            </Route>

            {/* Main layout routes — all require authentication */}
            <Route
              element={
                <ProtectedRoute>
                    <Layout />
                </ProtectedRoute>
              }
            >
              <Route
                path="/"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <Dashboard />
                  </Suspense>
                }
              />
              <Route
                path="/cards"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <Cards />
                  </Suspense>
                }
              />
              <Route
                path="/cards/:id"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <CardDetail />
                  </Suspense>
                }
              />
              <Route
                path="/market/movers"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <MarketMovers />
                  </Suspense>
                }
              />
              <Route
                path="/market/trending"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <Trending />
                  </Suspense>
                }
              />
              <Route
                path="/market"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <MarketPage />
                  </Suspense>
                }
              />
              <Route
                path="/banlist"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <BanList />
                  </Suspense>
                }
              />
              <Route
                path="/banlist/history"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <BanHistory />
                  </Suspense>
                }
              />
              <Route
                path="/catalog"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <CatalogPage />
                  </Suspense>
                }
              />
              <Route
                path="/collection"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <MyCollection />
                  </Suspense>
                }
              />
              <Route
                path="/collection/:id"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <CollectionCardDetail />
                  </Suspense>
                }
              />
              <Route
                path="/decks"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <DeckList />
                  </Suspense>
                }
              />
              <Route
                path="/decks/ranking"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <TopDecksPage />
                  </Suspense>
                }
              />
              <Route
                path="/decks/:id"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <DeckView />
                  </Suspense>
                }
              />
              <Route
                path="/scans"
                element={<Navigate to="/admin" replace />}
              />
              <Route
                path="/settings"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <Settings />
                  </Suspense>
                }
              />
              <Route
                path="/schedules"
                element={<Navigate to="/admin" replace />}
              />
              <Route
                path="/marketplace/my-trades"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <MyTrades />
                  </Suspense>
                }
              />
              <Route
                path="/marketplace"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <Marketplace />
                  </Suspense>
                }
              />
              <Route
                path="/wishlist"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <WishlistPage />
                  </Suspense>
                }
              />
              <Route
                path="/trade-matches"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <TradeMatchesPage />
                  </Suspense>
                }
              />
              <Route
                path="/evaluations"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <Evaluations />
                  </Suspense>
                }
              />
              <Route
                path="/alerts"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <AlertsPage />
                  </Suspense>
                }
              />
              <Route
                path="/achievements"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <AchievementsPage />
                  </Suspense>
                }
              />
              <Route
                path="/admin"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <AdminRoute>
                      <AdminPanel />
                    </AdminRoute>
                  </Suspense>
                }
              />
              <Route
                path="/admin/liga-status"
                element={<Navigate to="/admin" replace />}
              />
            </Route>

            {/* 404 catch-all */}
            <Route
              path="*"
              element={
                <Suspense
                  fallback={<LoadingSpinner message="Loading page..." />}
                >
                  <NotFoundPage />
                </Suspense>
              }
            />
          </Routes>
        </PendingDeleteProvider>
        </BrowserRouter>
      </CurrencyProvider>
    </AuthProvider>
    </ThemeProvider>
    </LanguageProvider>
  );
}
