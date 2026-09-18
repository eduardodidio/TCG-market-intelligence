interface PromoBadgeProps {
  className?: string;
}

/**
 * Silver "PROMO" stamp overlay, positioned at the bottom-center of the card
 * image to mimic the holofoil stamp location on real MTG cards.
 *
 * The parent must have `position: relative` for correct placement.
 */
export function PromoBadge({ className = "" }: PromoBadgeProps) {
  return (
    <span
      data-testid="promo-badge"
      className={`absolute bottom-2 left-1/2 -translate-x-1/2 pointer-events-none
        rounded-full px-3 py-0.5 text-[10px] font-bold uppercase tracking-widest
        select-none ${className}`}
      style={{
        background: "linear-gradient(135deg, #c0c0c0, #e8e8e8, #a0a0a0)",
        color: "#333",
        border: "1px solid rgba(255,255,255,0.5)",
        boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
        opacity: 0.85,
      }}
    >
      PROMO
    </span>
  );
}
