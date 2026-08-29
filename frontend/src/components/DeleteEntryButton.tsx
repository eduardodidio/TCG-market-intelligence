import { useState } from "react";
import { useTranslation } from "react-i18next";

interface DeleteEntryButtonProps {
  onConfirm: () => Promise<void>;
  entryName?: string;
}

/**
 * Delete button with inline confirmation dialog.
 */
export function DeleteEntryButton({ onConfirm, entryName }: DeleteEntryButtonProps) {
  const { t } = useTranslation();
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await onConfirm();
    } catch {
      // parent handles error
    } finally {
      setDeleting(false);
      setConfirming(false);
    }
  };

  if (confirming) {
    return (
      <div className="flex items-center gap-2 bg-red-900/30 border border-red-500/40 rounded-lg px-4 py-3" data-testid="delete-confirm-dialog">
        <p className="text-sm text-red-300 flex-1">
          {entryName
            ? t("inlineEdit.deleteConfirmNamed", { name: entryName })
            : t("inlineEdit.deleteConfirm")}
        </p>
        <button
          onClick={handleDelete}
          disabled={deleting}
          data-testid="delete-confirm-btn"
          className="rounded-md bg-red-600 hover:bg-red-500 px-3 py-1.5 text-sm font-medium text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
        >
          {deleting ? t("common.deleting") : t("common.delete")}
        </button>
        <button
          onClick={() => setConfirming(false)}
          disabled={deleting}
          data-testid="delete-cancel-btn"
          className="rounded-md border border-slate-500 px-3 py-1.5 text-sm font-medium text-slate-300 hover:bg-slate-700 transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          {t("common.cancel")}
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => setConfirming(true)}
      data-testid="delete-entry-btn"
      className="inline-flex items-center gap-1.5 rounded-md border border-red-500/50 px-3 py-1.5 text-sm font-medium text-red-400 hover:bg-red-900/30 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
    >
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
      </svg>
      {t("inlineEdit.deleteEntry")}
    </button>
  );
}
