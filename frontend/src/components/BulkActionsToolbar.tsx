import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";

const QUALITY_OPTIONS = ["M", "NM", "SP", "MP", "HP", "D"] as const;
const LANGUAGE_OPTIONS = ["BR", "EN", "DE", "ES", "FR", "IT", "JP", "KO", "RU", "TW"] as const;

interface BulkActionsToolbarProps {
  selectedIds: Set<number>;
  onUpdate: (ids: number[], updates: { quality?: string; language?: string; extras?: string }) => Promise<void>;
  onDelete: (ids: number[]) => Promise<void>;
  onCancel: () => void;
}

type PopoverKind = "quality" | "language" | "extras" | null;

export function BulkActionsToolbar({ selectedIds, onUpdate, onDelete, onCancel }: BulkActionsToolbarProps) {
  const { t } = useTranslation();
  const [popover, setPopover] = useState<PopoverKind>(null);
  const [extrasValue, setExtrasValue] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [loading, setLoading] = useState(false);

  const ids = Array.from(selectedIds);
  const count = selectedIds.size;

  const handleUpdate = useCallback(
    async (updates: { quality?: string; language?: string; extras?: string }) => {
      setLoading(true);
      try {
        await onUpdate(ids, updates);
      } finally {
        setLoading(false);
        setPopover(null);
        setExtrasValue("");
      }
    },
    [ids, onUpdate],
  );

  const handleDelete = useCallback(async () => {
    setLoading(true);
    try {
      await onDelete(ids);
    } finally {
      setLoading(false);
      setConfirmDelete(false);
    }
  }, [ids, onDelete]);

  if (count === 0) return null;

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-50 bg-slate-800 border-t border-slate-600 shadow-2xl px-4 py-3"
      data-testid="bulk-actions-toolbar"
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 flex-wrap">
        {/* Left: selected count */}
        <span className="text-sm font-medium text-white" data-testid="selected-count">
          {t("bulk.selectedCount", { count })}
        </span>

        {/* Center: action buttons */}
        <div className="flex items-center gap-2 relative">
          {/* Set Condition */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setPopover(popover === "quality" ? null : "quality")}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors disabled:opacity-50"
              data-testid="bulk-set-condition"
            >
              {t("bulk.setCondition")}
            </button>
            {popover === "quality" && (
              <div className="absolute bottom-full mb-2 left-0 bg-slate-700 border border-slate-500 rounded-lg shadow-xl p-2 min-w-[120px]" data-testid="quality-popover">
                {QUALITY_OPTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => handleUpdate({ quality: q })}
                    className="block w-full text-left px-3 py-1.5 text-sm text-white hover:bg-slate-600 rounded transition-colors"
                    data-testid={`quality-option-${q}`}
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Set Language */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setPopover(popover === "language" ? null : "language")}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors disabled:opacity-50"
              data-testid="bulk-set-language"
            >
              {t("bulk.setLanguage")}
            </button>
            {popover === "language" && (
              <div className="absolute bottom-full mb-2 left-0 bg-slate-700 border border-slate-500 rounded-lg shadow-xl p-2 min-w-[120px] max-h-60 overflow-y-auto" data-testid="language-popover">
                {LANGUAGE_OPTIONS.map((lang) => (
                  <button
                    key={lang}
                    type="button"
                    onClick={() => handleUpdate({ language: lang })}
                    className="block w-full text-left px-3 py-1.5 text-sm text-white hover:bg-slate-600 rounded transition-colors"
                    data-testid={`language-option-${lang}`}
                  >
                    {lang}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Set Extras */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setPopover(popover === "extras" ? null : "extras")}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors disabled:opacity-50"
              data-testid="bulk-set-extras"
            >
              {t("bulk.setExtras")}
            </button>
            {popover === "extras" && (
              <div className="absolute bottom-full mb-2 left-0 bg-slate-700 border border-slate-500 rounded-lg shadow-xl p-3 min-w-[200px]" data-testid="extras-popover">
                <input
                  type="text"
                  value={extrasValue}
                  onChange={(e) => setExtrasValue(e.target.value)}
                  placeholder={t("bulk.extrasPlaceholder")}
                  className="w-full px-2 py-1.5 text-sm bg-slate-800 text-white border border-slate-500 rounded focus:border-cyan-400 focus:outline-none"
                  data-testid="extras-input"
                />
                <button
                  type="button"
                  onClick={() => handleUpdate({ extras: extrasValue })}
                  disabled={loading}
                  className="mt-2 w-full px-3 py-1.5 text-sm bg-cyan-600 hover:bg-cyan-500 text-white rounded transition-colors disabled:opacity-50"
                  data-testid="extras-apply"
                >
                  {t("bulk.apply")}
                </button>
              </div>
            )}
          </div>

          {/* Delete */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-red-700 hover:bg-red-600 text-white rounded-lg transition-colors disabled:opacity-50"
              data-testid="bulk-delete"
            >
              {t("common.delete")}
            </button>
          </div>
        </div>

        {/* Right: cancel */}
        <button
          type="button"
          onClick={onCancel}
          disabled={loading}
          className="px-3 py-1.5 text-sm text-slate-300 hover:text-white transition-colors disabled:opacity-50"
          data-testid="bulk-cancel"
        >
          {t("common.cancel")}
        </button>
      </div>

      {/* Delete confirmation dialog */}
      {confirmDelete && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60" data-testid="delete-confirm-dialog">
          <div className="bg-slate-800 border border-slate-600 rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-semibold text-white mb-2">{t("bulk.deleteTitle")}</h3>
            <p className="text-sm text-slate-300 mb-4">
              {t("bulk.deleteMessage", { count })}
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="px-4 py-2 text-sm text-slate-300 hover:text-white transition-colors"
                data-testid="delete-cancel"
              >
                {t("common.cancel")}
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={loading}
                className="px-4 py-2 text-sm bg-red-600 hover:bg-red-500 text-white rounded-lg transition-colors disabled:opacity-50"
                data-testid="delete-confirm"
              >
                {loading ? t("common.deleting") : t("common.delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
