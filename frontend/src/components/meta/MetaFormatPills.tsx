import { useTranslation } from "react-i18next";
import { META_FORMATS } from "../../types/metaDecks";
import type { MetaFormat, MetaFormatInfo } from "../../types/metaDecks";

interface MetaFormatPillsProps {
  value: MetaFormat;
  /** From `/meta-decks/formats`. Empty while loading (or on error) → all pills enabled. */
  formats: MetaFormatInfo[];
  onChange: (format: MetaFormat) => void;
}

export function MetaFormatPills({ value, formats, onChange }: MetaFormatPillsProps) {
  const { t } = useTranslation();
  const known = formats.length > 0;
  const byFormat = new Map(formats.map((f) => [f.format, f]));

  return (
    <div className="flex flex-wrap gap-1" data-testid="meta-format-pills">
      {META_FORMATS.map((fmt) => {
        const info = byFormat.get(fmt);
        const hasSnapshot = !known || Boolean(info?.latest_snapshot_date);
        const active = value === fmt;
        const disabled = !hasSnapshot && !active;
        return (
          <button
            key={fmt}
            type="button"
            onClick={() => {
              if (!disabled && !active) onChange(fmt);
            }}
            disabled={disabled}
            aria-pressed={active}
            title={
              disabled
                ? t("metaDecks.formatUnavailable", {
                    defaultValue: "Metagame ainda não coletado para este formato",
                  })
                : undefined
            }
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              active
                ? "bg-cyan-500 text-white"
                : "bg-slate-800 text-slate-400 hover:text-white"
            } disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:text-slate-400`}
            data-testid={`meta-format-${fmt}`}
          >
            {t(`metaDecks.format.${fmt}`, {
              defaultValue: fmt.charAt(0).toUpperCase() + fmt.slice(1),
            })}
          </button>
        );
      })}
    </div>
  );
}
