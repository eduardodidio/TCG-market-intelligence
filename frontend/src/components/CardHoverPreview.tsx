import { createPortal } from "react-dom";

interface CardHoverPreviewProps {
  visible: boolean;
  imageUrl: string | null;
  x: number;
  y: number;
}

/**
 * Floating card image preview rendered via portal.
 * Shows an enlarged card image near the cursor/touch position.
 */
export function CardHoverPreview({ visible, imageUrl, x, y }: CardHoverPreviewProps) {
  if (!visible || !imageUrl) return null;

  return createPortal(
    <div
      className="fixed z-50 pointer-events-none"
      style={{ left: x, top: y }}
      data-testid="card-hover-preview"
    >
      {/* Mobile backdrop */}
      <div className="sm:hidden fixed inset-0 bg-black/30" />
      <img
        src={imageUrl}
        alt=""
        className="w-[300px] rounded-lg shadow-2xl border border-slate-600"
        loading="eager"
      />
    </div>,
    document.body,
  );
}
