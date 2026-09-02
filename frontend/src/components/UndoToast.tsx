import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

interface UndoToastProps {
  message: string;
  durationMs?: number;
  onUndo: () => void;
  onExpire: () => void;
}

export function UndoToast({
  message,
  durationMs = 5000,
  onUndo,
  onExpire,
}: UndoToastProps) {
  const { t } = useTranslation();
  const [dismissed, setDismissed] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onExpireRef = useRef(onExpire);
  onExpireRef.current = onExpire;

  useEffect(() => {
    timerRef.current = setTimeout(() => {
      setDismissed(true);
      onExpireRef.current();
    }, durationMs);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [durationMs]);

  const handleUndo = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setDismissed(true);
    onUndo();
  };

  if (dismissed) return null;

  return (
    <div
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-slate-700 border border-slate-500 rounded-lg shadow-lg px-4 py-3 flex items-center gap-3 min-w-[280px] max-w-[400px]"
      data-testid="undo-toast"
    >
      <span className="text-sm text-white flex-1">{message}</span>
      <button
        onClick={handleUndo}
        className="text-sm font-medium text-cyan-400 hover:text-cyan-300 transition-colors whitespace-nowrap"
        data-testid="undo-toast-btn"
      >
        {t("collection.deleteUndo")}
      </button>
      {/* Progress bar */}
      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-slate-600 rounded-b-lg overflow-hidden">
        <div
          className="h-full bg-cyan-400"
          data-testid="undo-toast-progress"
          style={{
            animation: `undo-shrink ${durationMs}ms linear forwards`,
          }}
        />
      </div>
      <style>{`
        @keyframes undo-shrink {
          from { width: 100%; }
          to { width: 0%; }
        }
      `}</style>
    </div>
  );
}
