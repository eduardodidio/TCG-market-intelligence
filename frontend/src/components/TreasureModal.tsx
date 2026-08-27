import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useTreasureImage } from "../hooks/useTreasureImage";

interface TreasureModalProps {
  count: number;
  onClose: () => void;
  /** Rect of the thumbnail that triggered the modal (for fly-back animation) */
  originRect?: DOMRect | null;
}

const ANIM_DURATION = 400; // ms

export function TreasureModal({
  count,
  onClose,
  originRect,
}: TreasureModalProps) {
  const { t } = useTranslation();
  const treasureImage = useTreasureImage();
  const [phase, setPhase] = useState<"entering" | "open" | "leaving">(
    "entering",
  );
  const contentRef = useRef<HTMLDivElement>(null);

  // Trigger enter animation on mount
  useEffect(() => {
    const frame = requestAnimationFrame(() => setPhase("open"));
    return () => cancelAnimationFrame(frame);
  }, []);

  // Keyboard escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleClose = () => {
    setPhase("leaving");
    setTimeout(() => onClose(), ANIM_DURATION);
  };

  // Compute transform for the "origin" position (thumbnail location)
  const getOriginTransform = (): React.CSSProperties => {
    if (!originRect) {
      // Fallback: shrink toward bottom-left (sidebar area)
      return {
        transform: "scale(0.15) translateY(60vh)",
        opacity: 0,
      };
    }
    // Calculate offset from viewport center to origin center
    const cx = window.innerWidth / 2;
    const cy = window.innerHeight / 2;
    const ox = originRect.left + originRect.width / 2;
    const oy = originRect.top + originRect.height / 2;
    return {
      transform: `translate(${ox - cx}px, ${oy - cy}px) scale(0.12)`,
      opacity: 0.4,
    };
  };

  const isOpen = phase === "open";

  const backdropStyle: React.CSSProperties = {
    backgroundColor: isOpen ? "rgba(0,0,0,0.7)" : "rgba(0,0,0,0)",
    transition: `background-color ${ANIM_DURATION}ms ease`,
  };

  const contentStyle: React.CSSProperties = {
    transition: `transform ${ANIM_DURATION}ms cubic-bezier(0.34, 1.56, 0.64, 1), opacity ${ANIM_DURATION}ms ease, box-shadow ${ANIM_DURATION}ms ease`,
    ...(isOpen
      ? {
          transform: "scale(1) translate(0, 0)",
          opacity: 1,
        }
      : getOriginTransform()),
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={backdropStyle}
      onClick={handleClose}
      data-testid="treasure-modal-backdrop"
    >
      <div
        ref={contentRef}
        className="flex flex-col items-center gap-4"
        style={contentStyle}
        onClick={(e) => e.stopPropagation()}
        data-testid="treasure-modal-content"
      >
        <img
          src={treasureImage}
          alt={t("credits.balance")}
          className="max-h-[70vh] max-w-[90vw] rounded-lg"
          style={{
            boxShadow: isOpen
              ? "0 0 60px 15px rgba(245, 158, 11, 0.35), 0 25px 50px -12px rgba(0, 0, 0, 0.6)"
              : "0 4px 6px rgba(0, 0, 0, 0.3)",
            transition: `box-shadow ${ANIM_DURATION}ms ease`,
          }}
          data-testid="treasure-modal-image"
        />
        <div
          className="flex items-center gap-2 bg-slate-800/90 px-4 py-2 rounded-lg"
          style={{
            opacity: isOpen ? 1 : 0,
            transition: `opacity ${ANIM_DURATION * 0.6}ms ease`,
          }}
        >
          <span
            className="text-2xl font-bold text-amber-400"
            data-testid="treasure-modal-count"
          >
            {count}
          </span>
          <span className="text-sm text-slate-300">
            {t("credits.balance")}
          </span>
        </div>
      </div>
    </div>
  );
}
