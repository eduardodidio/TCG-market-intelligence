import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Card3DTilt } from "./Card3DTilt";
import { PromoBadge } from "./PromoBadge";

interface CardPreviewModalProps {
  imageUrl: string;
  cardName: string;
  isFoil?: boolean;
  isPromo?: boolean;
  onClose: () => void;
}

export function CardPreviewModal({
  imageUrl,
  cardName,
  isFoil = false,
  isPromo = false,
  onClose,
}: CardPreviewModalProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  useEffect(() => {
    const id = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(id);
  }, []);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return createPortal(
    <div
      className={`fixed inset-0 bg-black/60 z-[9999] flex items-center justify-center transition-opacity duration-200 ${visible ? "opacity-100" : "opacity-0"}`}
      onMouseDown={(e: React.MouseEvent) => e.stopPropagation()}
      onClick={(e: React.MouseEvent) => { e.stopPropagation(); e.preventDefault(); onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-label={cardName}
      data-testid="modal-backdrop"
    >
      <div
        className={`relative max-w-md mx-4 transition-transform duration-200 ${visible ? "scale-100" : "scale-95"}`}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={(e: React.MouseEvent) => { e.stopPropagation(); e.preventDefault(); onClose(); }}
          className="absolute -top-3 -right-3 z-10 w-8 h-8 rounded-full bg-black/70 text-white flex items-center justify-center hover:bg-black/90 transition-colors"
          aria-label="Close"
        >
          &#x2715;
        </button>

        <Card3DTilt tiltMaxAngle={18} scale={1.08} foil={isFoil} glowBorder={isFoil}>
          <div className="relative">
            <img
              src={imageUrl}
              alt={cardName}
              className="rounded-xl shadow-2xl w-full max-h-[80vh]"
              draggable={false}
            />
            {isPromo && <PromoBadge />}
          </div>
        </Card3DTilt>

        <p className="text-white text-center mt-3 text-lg font-medium drop-shadow-lg">
          {cardName}
        </p>
      </div>
    </div>,
    document.body,
  );
}
