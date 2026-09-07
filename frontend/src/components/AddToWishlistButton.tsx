import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";
import { addToWishlist, checkWishlist, removeFromWishlist } from "../api/wishlist";

interface AddToWishlistButtonProps {
  cardId: number;
  className?: string;
}

export function AddToWishlistButton({
  cardId,
  className = "",
}: AddToWishlistButtonProps) {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const [wishlisted, setWishlisted] = useState(false);
  const [loading, setLoading] = useState(false);

  // Check initial state
  useEffect(() => {
    if (!isAuthenticated || !cardId) return;

    let cancelled = false;
    checkWishlist([cardId]).then((res) => {
      if (cancelled) return;
      if (res.data) {
        setWishlisted(res.data.wishlisted.includes(cardId));
      }
    });
    return () => {
      cancelled = true;
    };
  }, [cardId, isAuthenticated]);

  const handleToggle = useCallback(async () => {
    if (loading || !isAuthenticated) return;
    setLoading(true);

    try {
      if (wishlisted) {
        await removeFromWishlist(cardId);
        setWishlisted(false);
      } else {
        await addToWishlist(cardId);
        setWishlisted(true);
      }
    } catch {
      // Revert on error
    } finally {
      setLoading(false);
    }
  }, [cardId, wishlisted, loading, isAuthenticated]);

  if (!isAuthenticated) return null;

  return (
    <button
      onClick={handleToggle}
      disabled={loading}
      className={`inline-flex items-center justify-center rounded-md p-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
        wishlisted
          ? "text-red-500 hover:text-red-400"
          : "text-gray-400 dark:text-slate-500 hover:text-red-500 dark:hover:text-red-400"
      } ${loading ? "opacity-50 cursor-wait" : ""} ${className}`}
      title={
        wishlisted
          ? t("wishlist.removeFromWishlist")
          : t("wishlist.addToWishlist")
      }
      data-testid="wishlist-button"
      aria-label={
        wishlisted
          ? t("wishlist.removeFromWishlist")
          : t("wishlist.addToWishlist")
      }
    >
      <svg
        className="h-5 w-5"
        fill={wishlisted ? "currentColor" : "none"}
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
        />
      </svg>
    </button>
  );
}
