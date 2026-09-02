import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

interface InlineEditFieldProps {
  value: string;
  onSave: (newValue: string) => Promise<void>;
  type: "text" | "number" | "select";
  options?: { label: string; value: string }[];
  label: string;
  min?: number;
}

/**
 * Reusable inline edit component.
 * Display mode: shows value + pencil icon.
 * Edit mode: input/select + save(check)/cancel(X) buttons.
 * Enter saves, Escape cancels.
 */
export function InlineEditField({ value, onSave, type, options, label, min }: InlineEditFieldProps) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | HTMLSelectElement>(null);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [editing]);

  const handleSave = async () => {
    if (draft === value) {
      setEditing(false);
      return;
    }
    if (type === "number" && min != null) {
      const num = Number(draft);
      if (isNaN(num) || num < min) {
        setError(t("inlineEdit.invalidValue"));
        return;
      }
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(draft);
      setEditing(false);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 1500);
    } catch {
      setError(t("inlineEdit.saveError"));
      setDraft(value);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setDraft(value);
    setEditing(false);
    setError(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSave();
    } else if (e.key === "Escape") {
      handleCancel();
    }
  };

  const displayValue = type === "select" && options
    ? options.find((o) => o.value === value)?.label ?? value
    : value;

  if (!editing) {
    return (
      <div className="flex items-center gap-2" data-testid={`inline-edit-${label}`}>
        <span className="text-sm text-slate-300" data-testid="inline-edit-display">
          {displayValue || t("inlineEdit.empty")}
        </span>
        {success && (
          <svg
            className="h-4 w-4 text-emerald-400 animate-fade-in-out"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
            data-testid="save-checkmark"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )}
        <button
          onClick={() => setEditing(true)}
          title={t("inlineEdit.edit")}
          data-testid="inline-edit-pencil"
          className="text-slate-400 hover:text-cyan-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div data-testid={`inline-edit-${label}`}>
      <div className="flex items-center gap-2">
        {type === "select" && options ? (
          <select
            ref={inputRef as React.RefObject<HTMLSelectElement>}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={saving}
            data-testid="inline-edit-select"
            className="rounded-md bg-slate-700 border border-slate-600 px-2 py-1 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-transparent"
          >
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        ) : (
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type={type}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={saving}
            min={min}
            data-testid="inline-edit-input"
            className="rounded-md bg-slate-700 border border-slate-600 px-2 py-1 text-sm text-white w-32 focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-transparent"
          />
        )}

        {/* Save button */}
        <button
          onClick={handleSave}
          disabled={saving}
          title={t("inlineEdit.save")}
          data-testid="inline-edit-save"
          className="text-green-400 hover:text-green-300 disabled:opacity-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded"
        >
          {saving ? (
            <svg className="h-4 w-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          ) : (
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          )}
        </button>

        {/* Cancel button */}
        <button
          onClick={handleCancel}
          disabled={saving}
          title={t("common.cancel")}
          data-testid="inline-edit-cancel"
          className="text-slate-400 hover:text-red-400 disabled:opacity-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      {error && (
        <p className="text-xs text-red-400 mt-1" data-testid="inline-edit-error">{error}</p>
      )}
    </div>
  );
}
