import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";

interface CopyCodeButtonProps {
  code: string;
  truncateAt?: number;
  className?: string;
}

export function CopyCodeButton({ code, truncateAt = 8, className = "" }: CopyCodeButtonProps) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation();
      try {
        await navigator.clipboard.writeText(code);
      } catch {
        // Fallback for older browsers
        const textarea = document.createElement("textarea");
        textarea.value = code;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    },
    [code],
  );

  const truncated = code.length > truncateAt ? `${code.slice(0, truncateAt)}...` : code;

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={code}
      className={`text-[10px] text-slate-500 dark:text-slate-400 hover:text-cyan-400 dark:hover:text-cyan-300 transition-colors cursor-pointer ${className}`}
      data-testid="copy-code-button"
    >
      {copied ? (
        <span className="text-green-400" data-testid="copy-feedback">
          {t("marketplace.codeCopied")}
        </span>
      ) : (
        <span>{truncated}</span>
      )}
    </button>
  );
}
