import { useEffect, useState } from "react";

export interface GauchoOption {
  label: string;
  reply?: string;
}

interface GauchoDialogProps {
  message: string;
  options?: GauchoOption[];
  autoDismissMs?: number;
  onDismiss: () => void;
}

export function GauchoDialog({
  message,
  options,
  autoDismissMs = 4000,
  onDismiss,
}: GauchoDialogProps) {
  const [replyText, setReplyText] = useState<string | null>(null);

  // Auto-dismiss when no options
  useEffect(() => {
    if (!options || options.length === 0) {
      const timer = setTimeout(onDismiss, autoDismissMs);
      return () => clearTimeout(timer);
    }
  }, [options, autoDismissMs, onDismiss]);

  // Dismiss after showing reply
  useEffect(() => {
    if (replyText !== null) {
      const timer = setTimeout(onDismiss, 2500);
      return () => clearTimeout(timer);
    }
  }, [replyText, onDismiss]);

  const handleOptionClick = (option: GauchoOption) => {
    if (option.reply) {
      setReplyText(option.reply);
    } else {
      onDismiss();
    }
  };

  return (
    <div
      className="fixed bottom-20 right-6 z-50 bg-slate-800/95 backdrop-blur border border-green-600/40 rounded-xl shadow-xl max-w-sm p-4 animate-fade-in-up"
      data-testid="gaucho-dialog"
    >
      {/* Close button */}
      <button
        onClick={onDismiss}
        className="absolute top-2 right-2 text-slate-400 hover:text-white transition-colors text-sm leading-none p-1"
        data-testid="gaucho-dialog-close"
        aria-label="Close"
        type="button"
      >
        &#x2715;
      </button>

      {replyText !== null ? (
        <p className="text-green-300 text-sm pr-6" data-testid="gaucho-reply">
          {replyText}
        </p>
      ) : (
        <>
          <p
            className="text-slate-200 text-sm mb-3 pr-6"
            data-testid="gaucho-message"
          >
            {message}
          </p>
          {options && options.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {options.map((opt) => (
                <button
                  key={opt.label}
                  onClick={() => handleOptionClick(opt)}
                  className="px-4 py-2 rounded-full bg-green-700/60 hover:bg-green-600 text-white text-sm transition-colors"
                  data-testid={`gaucho-option-${opt.label}`}
                  type="button"
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
