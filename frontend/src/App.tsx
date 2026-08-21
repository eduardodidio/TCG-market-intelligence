import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LoadingSpinner } from "./components/LoadingSpinner";

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
  import("./pages/CollectionCardDetail").then((m) => ({ default: m.CollectionCardDetail })),
);
const Scans = lazy(() =>
  import("./pages/Scans").then((m) => ({ default: m.Scans })),
);

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route
            path="/"
            element={
              <Suspense fallback={<LoadingSpinner message="Loading page..." />}>
                <Dashboard />
              </Suspense>
            }
          />
          <Route
            path="/collection"
            element={
              <Suspense fallback={<LoadingSpinner message="Loading page..." />}>
                <MyCollection />
              </Suspense>
            }
          />
          <Route
            path="/collection/:id"
            element={
              <Suspense fallback={<LoadingSpinner message="Loading page..." />}>
                <CollectionCardDetail />
              </Suspense>
            }
          />
          <Route
            path="/cards"
            element={
              <Suspense fallback={<LoadingSpinner message="Loading page..." />}>
                <Cards />
              </Suspense>
            }
          />
          <Route
            path="/cards/:id"
            element={
              <Suspense fallback={<LoadingSpinner message="Loading page..." />}>
                <CardDetail />
              </Suspense>
            }
          />
          <Route
            path="/market/movers"
            element={
              <Suspense fallback={<LoadingSpinner message="Loading page..." />}>
                <MarketMovers />
              </Suspense>
            }
          />
          <Route
            path="/scans"
            element={
              <Suspense fallback={<LoadingSpinner message="Loading page..." />}>
                <Scans />
              </Suspense>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
