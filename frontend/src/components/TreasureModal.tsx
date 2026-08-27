import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { useTreasureImage } from "../hooks/useTreasureImage";

interface TreasureModalProps {
  count: number;
  onClose: () => void;
  /** Rect of the thumbnail that triggered the modal (for fly-back animation) */
  originRect?: DOMRect | null;
}

const ANIM_DURATION = 500; // ms
const SPARKLE_COUNT = 18;

interface Sparkle {
  id: number;
  x: number;
  y: number;
  size: number;
  delay: number;
  angle: number;
  distance: number;
}

function generateSparkles(
  cx: number,
  cy: number,
  spread: number,
): Sparkle[] {
  return Array.from({ length: SPARKLE_COUNT }, (_, i) => {
    const angle = (360 / SPARKLE_COUNT) * i + Math.random() * 20 - 10;
    const distance = spread * 0.4 + Math.random() * spread * 0.6;
    return {
      id: i,
      x: cx,
      y: cy,
      size: 3 + Math.random() * 5,
      delay: Math.random() * 200,
      angle,
      distance,
    };
  });
}

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
  const [sparkles, setSparkles] = useState<Sparkle[]>([]);

  // Trigger enter animation on mount
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      setPhase("open");
      // Spawn sparkles from viewport center
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      setSparkles(generateSparkles(cx, cy, 220));
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  // Keyboard escape
  const handleClose = useCallback(() => {
    // Spawn sparkles toward origin on close
    if (originRect) {
      const ox = originRect.left + originRect.width / 2;
      const oy = originRect.top + originRect.height / 2;
      setSparkles(generateSparkles(ox, oy, 120));
    }
    setPhase("leaving");
    setTimeout(() => onClose(), ANIM_DURATION);
  }, [onClose, originRect]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleClose]);

  // Compute transform for the "origin" position (thumbnail location)
  const getOriginTransform = (): React.CSSProperties => {
    if (!originRect) {
      return {
        transform: "scale(0.15) translateY(60vh)",
        opacity: 0,
      };
    }
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
    transition: `transform ${ANIM_DURATION}ms cubic-bezier(0.34, 1.56, 0.64, 1), opacity ${ANIM_DURATION}ms ease`,
    ...(isOpen
      ? {
          transform: "scale(1) translate(0, 0)",
          opacity: 1,
        }
      : getOriginTransform()),
  };

  const modal = (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center"
      style={backdropStyle}
      onClick={handleClose}
      data-testid="treasure-modal-backdrop"
    >
      {/* Golden sparkle particles */}
      {sparkles.map((s) => (
        <span
          key={s.id}
          className="treasure-sparkle"
          style={{
            position: "fixed",
            left: s.x,
            top: s.y,
            width: s.size,
            height: s.size,
            borderRadius: "50%",
            background:
              "radial-gradient(circle, #fbbf24 0%, #f59e0b 40%, transparent 70%)",
            boxShadow: "0 0 6px 2px rgba(251, 191, 36, 0.6)",
            pointerEvents: "none",
            zIndex: 10000,
            animationName: "sparkle-burst",
            animationDuration: `${ANIM_DURATION}ms`,
            animationDelay: `${s.delay}ms`,
            animationTimingFunction: "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
            animationFillMode: "forwards",
            opacity: 0,
            // CSS custom properties for the keyframe destination
            "--sparkle-tx": `${Math.cos((s.angle * Math.PI) / 180) * s.distance}px`,
            "--sparkle-ty": `${Math.sin((s.angle * Math.PI) / 180) * s.distance}px`,
          } as React.CSSProperties}
        />
      ))}

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
              ? "0 0 80px 20px rgba(245, 158, 11, 0.4), 0 0 120px 40px rgba(245, 158, 11, 0.15), 0 25px 50px -12px rgba(0, 0, 0, 0.6)"
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

      {/* Sparkle keyframes (injected once) */}
      <style>{`
        @keyframes sparkle-burst {
          0% {
            opacity: 1;
            transform: translate(0, 0) scale(1);
          }
          60% {
            opacity: 0.8;
            transform: translate(
              var(--sparkle-tx),
              var(--sparkle-ty)
            ) scale(1.2);
          }
          100% {
            opacity: 0;
            transform: translate(
              var(--sparkle-tx),
              var(--sparkle-ty)
            ) scale(0);
          }
        }
      `}</style>
    </div>
  );

  // Portal to document.body so the modal escapes any parent transform context
  return createPortal(modal, document.body);
}
