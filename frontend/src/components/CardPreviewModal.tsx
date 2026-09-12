import { useEffect } from "react";
import { Card3DTilt } from "./Card3DTilt";

interface CardPreviewModalProps {
  imageUrl: string;
  cardName: string;
  isFoil?: boolean;
  onClose: () => void;
}

export function CardPreviewModal({
  imageUrl,
  cardName,
  isFoil = false,
  onClose,
}: CardPreviewModalProps) {
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
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

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={cardName}
      data-testid="modal-backdrop"
    >
      <div
        className="relative max-w-sm mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute -top-3 -right-3 z-10 w-8 h-8 rounded-full bg-black/70 text-white flex items-center justify-center hover:bg-black/90 transition-colors"
          aria-label="Close"
        >
          &#x2715;
        </button>

        <Card3DTilt tiltMaxAngle={18} scale={1.08} foil={isFoil}>
          <img
            src={imageUrl}
            alt={cardName}
            className="rounded-lg shadow-2xl w-full"
            draggable={false}
          />
        </Card3DTilt>

        <p className="text-white text-center mt-3 text-lg font-medium drop-shadow-lg">
          {cardName}
        </p>
      </div>
    </div>
  );
}
