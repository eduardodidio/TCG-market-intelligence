import { useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { fetchCardDetail } from "../api/cards";
import { useCardName } from "../hooks/useCardName";
import { useCurrency } from "../hooks/useCurrency";
import { formatCurrency, formatDate } from "../utils/format";
import { scryfallImageUrl } from "../utils/scryfall";
import { ErrorBanner } from "../components/ErrorBanner";
import { PriceChart } from "../components/PriceChart";
import { SkeletonChartPanel, SkeletonInfoPanel } from "../components/Skeleton";
import type { CardDetail as CardDetailType } from "../types/api";

function sourceLabel(source: string): string {
  const labels: Record<string, string> = {
    myp: "MYP Cards",
  };
  return labels[source] ?? source;
}

export function CardDetail() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const cardId = Number(id);

  const { currency } = useCurrency();
  const { getCardName, getSubtitleName } = useCardName();

  const detailFetcher = useCallback(
    () => fetchCardDetail(cardId, { currency }),
    [cardId, currency],
  );

  const { data: card, loading, error, refetch } = useApi<CardDetailType>(
    detailFetcher,
    [cardId, currency],
  );

  // Set page title
  useEffect(() => {
    if (card) {
      document.title = `${getCardName(card.name_en, card.name_pt, t("common.unknownCard"))} | TCG Market`;
    } else {
      document.title = t("cardDetail.pageTitle");
    }
  }, [card]);

  if (loading) {
    return (
      <div data-testid="page-card-detail">
        <div className="mb-6">
          <div className="animate-pulse bg-slate-700 rounded h-4 w-32" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonInfoPanel />
          <SkeletonChartPanel />
        </div>
      </div>
    );
  }

  if (error) {
    // Check if it's a 404-style error
    const is404 =
      error.toLowerCase().includes("not found") ||
      error.includes("HTTP_404") ||
      error.includes("404");

    if (is404) {
      return (
        <div data-testid="page-card-detail">
          <div data-testid="card-not-found" className="text-center py-12">
            <h2 className="text-2xl font-bold text-white mb-4">{t("cardDetail.notFoundTitle")}</h2>
            <p className="text-slate-400 mb-6">
              {t("cardDetail.notFoundMessage")}
            </p>
            <Link
              to="/cards"
              className="inline-block rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              {t("cardDetail.backToCards")}
            </Link>
          </div>
        </div>
      );
    }

    return (
      <div data-testid="page-card-detail">
        <ErrorBanner message={error} variant="full" onRetry={refetch} />
      </div>
    );
  }

  if (!card) {
    return (
      <div data-testid="page-card-detail">
        <div data-testid="card-not-found" className="text-center py-12">
          <h2 className="text-2xl font-bold text-white mb-4">{t("cardDetail.notFoundTitle")}</h2>
          <Link
            to="/cards"
            className="inline-block rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            {t("cardDetail.backToCards")}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="page-card-detail">
      {/* Breadcrumb */}
      <nav data-testid="breadcrumb" className="mb-6 text-sm text-slate-400" aria-label="Breadcrumb">
        <Link to="/cards" className="hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded">
          {t("cardDetail.breadcrumbCards")}
        </Link>
        <span className="mx-2" aria-hidden="true">&gt;</span>
        <span className="text-white">{getCardName(card.name_en, card.name_pt, t("common.unknownCard"))}</span>
      </nav>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left panel: Card info */}
        <div data-testid="card-info-panel" className="bg-slate-800 border border-slate-600 rounded-lg p-6">
          {/* Scryfall card image */}
          {card.set_code && card.collector_number && (
            <div className="mb-6 flex justify-center">
              <img
                src={scryfallImageUrl(card.set_code, card.collector_number, "normal")}
                alt={getCardName(card.name_en, card.name_pt, t("common.unknownCard"))}
                data-testid="card-image"
                className="rounded-lg shadow-lg max-w-[250px] w-full"
                loading="eager"
                onError={(e) => { e.currentTarget.style.display = 'none' }}
              />
            </div>
          )}

          {/* Card name */}
          <h1 className="text-2xl font-bold text-white mb-1">{getCardName(card.name_en, card.name_pt, t("common.unknownCard"))}</h1>
          {(() => {
            const subtitle = getSubtitleName(card.name_en, card.name_pt, t("common.unknownCard"));
            return subtitle ? (
              <p className="text-sm text-slate-400 mb-4" data-testid="card-name-subtitle">{subtitle}</p>
            ) : null;
          })()}

          {/* Set and collector number */}
          <div className="flex items-center gap-3 mb-4">
            {card.set_code && (
              <span className="rounded bg-slate-700 px-2 py-1 text-xs font-mono text-slate-400">
                {card.set_code}
              </span>
            )}
            {card.collector_number && (
              <span className="text-sm text-slate-400">
                #{card.collector_number}
              </span>
            )}
          </div>

          {/* Game badge */}
          <span className="inline-block rounded-full bg-indigo-500/20 px-3 py-1 text-xs font-medium text-indigo-400 mb-6">
            {card.game}
          </span>

          {/* Latest price */}
          <div className="mb-6">
            <p className="text-sm text-slate-400 mb-1">{t("cardDetail.latestPrice")}</p>
            <p data-testid="latest-price" className="text-3xl font-bold text-white">
              {formatCurrency(card.latest_price, currency)}
            </p>
          </div>

          {/* Source links */}
          {card.source_cards.length > 0 && (
            <div className="mb-6">
              <p className="text-sm text-slate-400 mb-2">{t("cardDetail.sources")}</p>
              <div className="flex flex-wrap gap-2">
                {card.source_cards.map((sc) => (
                  <a
                    key={sc.external_id}
                    href={sc.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    data-testid="source-link"
                    className="inline-flex items-center gap-1 rounded-md bg-slate-700 px-3 py-1.5 text-sm text-cyan-400 hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
                  >
                    {sourceLabel(sc.source)}
                    <svg
                      className="h-3 w-3"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                      />
                    </svg>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-slate-400">{t("cardDetail.firstTracked")}</p>
              <p className="text-white">{formatDate(card.created_at)}</p>
            </div>
            <div>
              <p className="text-slate-400">{t("cardDetail.lastUpdated")}</p>
              <p className="text-white">{formatDate(card.updated_at)}</p>
            </div>
          </div>

          {/* External Links */}
          <div className="mt-6" data-testid="external-links">
            <p className="text-sm text-slate-400 mb-2">{t("cardDetail.externalLinks")}</p>
            <div className="flex flex-wrap gap-2">
              <a
                href={`https://scryfall.com/search?q=${encodeURIComponent(card.name_en)}${card.set_code ? `+set:${card.set_code}` : ""}`}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="scryfall-link"
                className="inline-flex items-center gap-1.5 rounded-md bg-slate-700 px-3 py-1.5 text-sm text-cyan-400 hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              >
                {t("cardDetail.viewOnScryfall")}
                <svg
                  className="h-3 w-3"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
              <a
                href={`https://www.ligamagic.com.br/?view=cards/card&card=${encodeURIComponent(card.name_en)}`}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="ligamagic-link"
                className="inline-flex items-center gap-1.5 rounded-md bg-slate-700 px-3 py-1.5 text-sm text-cyan-400 hover:bg-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
              >
                {t("cardDetail.viewOnLigaMagic")}
                <svg
                  className="h-3 w-3"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
            </div>
          </div>
        </div>

        {/* Right panel: Price chart */}
        <div>
          <PriceChart cardId={cardId} currency={currency} />
        </div>
      </div>
    </div>
  );
}
