import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useCardName } from "../hooks/useCardName";
import { LegalityBadge } from "./LegalityBadge";
import { StatusTransition } from "./StatusTransition";

export interface BanEventCardEvent {
  cardId?: number;
  collectionEntryId?: number;
  nameEn?: string;
  namePt?: string;
  setCode?: string;
  collectorNumber?: string;
  format: string;
  oldStatus: string | null;
  newStatus: string;
  changedAt: string;
  imageUrl?: string;
}

interface BanEventCardProps {
  event: BanEventCardEvent;
  showCardInfo?: boolean;
}

function formatDate(isoDate: string, locale: string): string {
  try {
    return new Date(isoDate).toLocaleDateString(locale, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return isoDate;
  }
}

export function BanEventCard({
  event,
  showCardInfo = true,
}: BanEventCardProps) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { getCardName } = useCardName();

  const displayName = getCardName(
    event.nameEn ?? null,
    event.namePt ?? null,
    t("common.unknownCard"),
  );

  const handleClick = () => {
    if (event.collectionEntryId) {
      navigate(`/collection/${event.collectionEntryId}`);
    }
  };

  const isClickable = !!event.collectionEntryId;

  return (
    <div
      data-testid="ban-event-card"
      className={`flex items-start gap-3 bg-slate-800 border border-slate-700 rounded-lg p-3 transition-colors ${
        isClickable
          ? "cursor-pointer hover:bg-slate-700/70 hover:border-slate-600"
          : ""
      }`}
      onClick={isClickable ? handleClick : undefined}
      role={isClickable ? "button" : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") handleClick();
            }
          : undefined
      }
    >
      {/* Card thumbnail */}
      {showCardInfo && event.imageUrl && (
        <img
          src={event.imageUrl}
          alt={displayName}
          className="w-12 h-[67px] rounded object-cover flex-shrink-0"
          loading="lazy"
          data-testid="ban-event-image"
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
      )}

      {/* Event info */}
      <div className="flex-1 min-w-0">
        {showCardInfo && (
          <p
            className="text-sm font-medium text-white truncate mb-1"
            data-testid="ban-event-name"
          >
            {displayName}
          </p>
        )}
        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
          <LegalityBadge format={event.format} status={event.newStatus} size="sm" />
        </div>
        <StatusTransition
          oldStatus={event.oldStatus}
          newStatus={event.newStatus}
          size="sm"
        />
        <p
          className="text-xs text-slate-500 mt-1.5"
          data-testid="ban-event-date"
        >
          {formatDate(event.changedAt, i18n.language === "pt-BR" ? "pt-BR" : "en-US")}
        </p>
      </div>
    </div>
  );
}
