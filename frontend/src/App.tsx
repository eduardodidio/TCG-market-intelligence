import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LoadingSpinner } from "./components/LoadingSpinner";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./contexts/AuthContext";
import { CurrencyProvider } from "./contexts/CurrencyContext";

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
const Scans = lazy(() =>
  import("./pages/Scans").then((m) => ({ default: m.Scans })),
);
const Login = lazy(() =>
  import("./pages/Login").then((m) => ({ default: m.Login })),
);

export default function App() {
  return (
    <AuthProvider>
      <CurrencyProvider>
        <BrowserRouter>
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

            {/* Main layout routes */}
            <Route element={<Layout />}>
              {/* Public routes */}
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

              {/* Protected routes */}
              <Route
                path="/collection"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <ProtectedRoute>
                      <MyCollection />
                    </ProtectedRoute>
                  </Suspense>
                }
              />
              <Route
                path="/collection/:id"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <ProtectedRoute>
                      <CollectionCardDetail />
                    </ProtectedRoute>
                  </Suspense>
                }
              />
              <Route
                path="/scans"
                element={
                  <Suspense
                    fallback={<LoadingSpinner message="Loading page..." />}
                  >
                    <ProtectedRoute>
                      <Scans />
                    </ProtectedRoute>
                  </Suspense>
                }
              />
            </Route>
          </Routes>
        </BrowserRouter>
      </CurrencyProvider>
    </AuthProvider>
  );
}
