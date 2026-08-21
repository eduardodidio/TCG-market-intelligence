import { useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { fetchCollectionEntry } from "../api/collection";
import { useCurrency } from "../hooks/useCurrency";
import { formatCurrency } from "../utils/format";
import { scryfallImageUrl } from "../utils/scryfall";
import { CurrencyIndicator } from "../components/CurrencyIndicator";
import { ErrorBanner } from "../components/ErrorBanner";
import { PriceChart } from "../components/PriceChart";
import { SkeletonChartPanel, SkeletonInfoPanel } from "../components/Skeleton";
import type { CollectionCardDetail as CollectionCardDetailType } from "../types/api";

const RARITY_LABEL_KEYS: Record<string, string> = {
  M: "rarity.mythic",
  R: "rarity.rare",
  U: "rarity.uncommon",
  C: "rarity.common",
};

function sourceLabel(source: string): string {
  const labels: Record<string, string> = {
    myp: "MYP Cards",
  };
  return labels[source] ?? source;
}

export function CollectionCardDetail() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const entryId = Number(id);

  const { currency } = useCurrency();

  const detailFetcher = useCallback(
    () => fetchCollectionEntry(entryId, { currency }),
    [entryId, currency],
  );

  const { data: entry, loading, error, refetch } = useApi<CollectionCardDetailType>(
    detailFetcher,
    [entryId, currency],
  );

  useEffect(() => {
    if (entry) {
      document.title = `${entry.name_en || entry.name_pt || t("common.unknownCard")} | TCG Market`;
    } else {
      document.title = `${t("collection.breadcrumbCollection")} | TCG Market`;
    }
  }, [entry]);

  if (loading) {
    return (
      <div data-testid="page-collection-detail">
        <div className="mb-6">
          <div className="animate-pulse bg-tcg-card-alt rounded h-4 w-32" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonInfoPanel />
          <SkeletonChartPanel />
        </div>
      </div>
    );
  }

  if (error) {
    const is404 =
      error.toLowerCase().includes("not found") ||
      error.includes("HTTP_404") ||
      error.includes("404");

    if (is404) {
      return (
        <div data-testid="page-collection-detail">
          <div data-testid="entry-not-found" className="text-center py-12">
            <h2 className="text-2xl font-bold text-white mb-4">{t("collection.entryNotFound")}</h2>
            <p className="text-tcg-muted mb-6">
              {t("collection.entryNotFoundMessage")}
            </p>
            <Link
              to="/collection"
              className="inline-block rounded-tcg-md bg-tcg-primary px-4 py-2 text-sm font-medium text-white hover:bg-tcg-primary-hover transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tcg-secondary"
            >
              {t("collection.backToCollection")}
            </Link>
          </div>
        </div>
      );
    }

    return (
      <div data-testid="page-collection-detail">
        <ErrorBanner message={error} variant="full" onRetry={refetch} />
      </div>
    );
  }

  if (!entry) {
    return (
      <div data-testid="page-collection-detail">
        <div data-testid="entry-not-found" className="text-center py-12">
          <h2 className="text-2xl font-bold text-white mb-4">Collection entry not found</h2>
          <Link
            to="/collection"
            className="inline-block rounded-tcg-md bg-tcg-primary px-4 py-2 text-sm font-medium text-white hover:bg-tcg-primary-hover transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tcg-secondary"
          >
            Back to Collection
          </Link>
        </div>
      </div>
    );
  }

  const displayName = entry.name_en || entry.name_pt || t("common.unknownCard");
  const imageUrl = entry.image_url || scryfallImageUrl(entry.set_code, entry.collector_number);

  return (
    <div data-testid="page-collection-detail">
      {/* Breadcrumb */}
      <nav data-testid="breadcrumb" className="mb-6 text-sm text-tcg-muted" aria-label="Breadcrumb">
        <Link to="/collection" className="hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tcg-secondary rounded">
          {t("collection.breadcrumbCollection")}
        </Link>
        <span className="mx-2" aria-hidden="true">&gt;</span>
        <span className="text-white">{displayName}</span>
      </nav>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left panel: Card info */}
        <div data-testid="card-info-panel" className="bg-tcg-card border border-tcg-border rounded-tcg-lg p-6">
          {/* Card image */}
          <div className="mb-6 flex justify-center">
            <img
              src={imageUrl}
              alt={displayName}
              data-testid="card-image"
              className="rounded-tcg-lg shadow-tcg-lg max-w-[250px] w-full"
              loading="eager"
              onError={(e) => { e.currentTarget.style.display = "none"; }}
            />
          </div>

          {/* Card name */}
          <h1 className="text-2xl font-bold text-white mb-1">{entry.name_en || t("common.unknownCard")}</h1>
          {entry.name_pt && entry.name_pt !== entry.name_en && (
            <p className="text-sm text-tcg-muted mb-4" data-testid="name-pt">{entry.name_pt}</p>
          )}

          {/* Set and collector number */}
          <div className="flex items-center gap-3 mb-4">
            {entry.set_code && (
              <span className="rounded-tcg-sm bg-tcg-card-alt px-2 py-1 text-xs font-mono text-tcg-muted" data-testid="set-code">
                {entry.set_code}
              </span>
            )}
            {entry.collector_number && (
              <span className="text-sm text-tcg-muted" data-testid="collector-number">
                #{entry.collector_number}
              </span>
            )}
          </div>

          {/* Collection metadata */}
          <div className="mb-6" data-testid="collection-metadata">
            <p className="text-sm text-tcg-muted mb-2">{t("collection.collectionInfo")}</p>
            <div className="flex flex-wrap gap-2">
              {entry.quantity > 1 && (
                <span className="inline-block rounded-full bg-tcg-primary px-3 py-1 text-xs font-bold text-white" data-testid="quantity-badge">
                  x{entry.quantity}
                </span>
              )}
              {entry.quality && (
                <span className="inline-block rounded-full bg-tcg-card-alt px-3 py-1 text-xs font-medium text-tcg-muted" data-testid="quality-badge">
                  {entry.quality}
                </span>
              )}
              {entry.language && (
                <span className="inline-block rounded-full bg-tcg-card-alt px-3 py-1 text-xs font-medium text-tcg-muted" data-testid="language-badge">
                  {entry.language}
                </span>
              )}
              {entry.rarity && (
                <span className="inline-block rounded-full bg-tcg-card-alt px-3 py-1 text-xs font-medium text-tcg-muted" data-testid="rarity-badge">
                  {RARITY_LABEL_KEYS[entry.rarity] ? t(RARITY_LABEL_KEYS[entry.rarity]) : entry.rarity}
                </span>
              )}
              {entry.extras && (
                <span className="inline-block rounded-full bg-amber-600/90 px-3 py-1 text-xs font-bold text-white" data-testid="extras-badge">
                  {entry.extras}
                </span>
              )}
            </div>
          </div>

          {/* Latest price */}
          <div className="mb-6">
            <p className="text-sm text-tcg-muted mb-1">{t("cardDetail.latestPrice")}</p>
            <p data-testid="latest-price" className="text-3xl font-bold text-white flex items-center gap-2">
              <CurrencyIndicator currency={currency} size={24} />
              {formatCurrency(entry.latest_price, currency)}
            </p>
          </div>

          {/* Linked status */}
          {entry.card_id == null && (
            <div className="mb-6 rounded-tcg-md bg-tcg-card-alt/50 p-4" data-testid="unlinked-notice">
              <p className="text-sm text-tcg-warning">
                {t("collection.notLinked")}
              </p>
              <p className="text-xs text-tcg-muted mt-1">
                {t("collection.notLinkedDescription")}
              </p>
            </div>
          )}

          {/* Source links */}
          {entry.source_cards.length > 0 && (
            <div className="mb-6">
              <p className="text-sm text-tcg-muted mb-2">{t("cardDetail.sources")}</p>
              <div className="flex flex-wrap gap-2">
                {entry.source_cards.map((sc) => (
                  <a
                    key={sc.external_id}
                    href={sc.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    data-testid="source-link"
                    className="inline-flex items-center gap-1 rounded-tcg-md bg-tcg-card-alt px-3 py-1.5 text-sm text-tcg-secondary hover:bg-tcg-ring transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tcg-secondary"
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

          {/* External Links */}
          <div className="mt-6" data-testid="external-links">
            <p className="text-sm text-tcg-muted mb-2">{t("cardDetail.externalLinks")}</p>
            <div className="flex flex-wrap gap-2">
              {entry.scryfall_url && (
                <a
                  href={entry.scryfall_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="scryfall-link"
                  className="inline-flex items-center gap-1.5 rounded-tcg-md bg-tcg-card-alt px-3 py-1.5 text-sm text-tcg-secondary hover:bg-tcg-ring transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tcg-secondary"
                >
                  {t("cardDetail.viewOnScryfall")}
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              )}
              {entry.ligamagic_url && (
                <a
                  href={entry.ligamagic_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="ligamagic-link"
                  className="inline-flex items-center gap-1.5 rounded-tcg-md bg-tcg-card-alt px-3 py-1.5 text-sm text-tcg-secondary hover:bg-tcg-ring transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tcg-secondary"
                >
                  {t("cardDetail.viewOnLigaMagic")}
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Right panel: Price chart */}
        <div>
          {entry.card_id != null ? (
            <PriceChart cardId={entry.card_id} currency={currency} />
          ) : (
            <div data-testid="no-price-chart" className="bg-tcg-card border border-tcg-border rounded-tcg-lg p-8 text-center">
              <p className="text-tcg-muted">
                {t("collection.noPriceChart")}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
