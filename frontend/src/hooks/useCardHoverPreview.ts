import { useCallback, useEffect, useRef, useState } from "react";

interface PreviewState {
  visible: boolean;
  imageUrl: string | null;
  x: number;
  y: number;
}

/**
 * Hook that provides hover/long-press preview behavior.
 *
 * Desktop: 200ms delay on mouseenter shows a floating card preview.
 * Mobile: 500ms long-press shows the preview; short taps pass through.
 */
export function useCardHoverPreview() {
  const [preview, setPreview] = useState<PreviewState>({
    visible: false,
    imageUrl: null,
    x: 0,
    y: 0,
  });

  const showTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const touchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const touchStartPos = useRef<{ x: number; y: number } | null>(null);

  const clearTimers = useCallback(() => {
    if (showTimerRef.current) {
      clearTimeout(showTimerRef.current);
      showTimerRef.current = null;
    }
    if (touchTimerRef.current) {
      clearTimeout(touchTimerRef.current);
      touchTimerRef.current = null;
    }
  }, []);

  const hide = useCallback(() => {
    clearTimers();
    setPreview((p) => (p.visible ? { ...p, visible: false } : p));
  }, [clearTimers]);

  // Dismiss on scroll (mobile)
  useEffect(() => {
    const handler = () => hide();
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, [hide]);

  const getPreviewHandlers = useCallback(
    (imageUrl: string | null) => ({
      onMouseEnter: (e: React.MouseEvent) => {
        if (!imageUrl) return;
        const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
        showTimerRef.current = setTimeout(() => {
          // Position to the right of the element, or left if near right edge
          const x = rect.right + 10 + 310 > window.innerWidth
            ? rect.left - 310
            : rect.right + 10;
          const y = Math.min(rect.top, window.innerHeight - 440);
          setPreview({ visible: true, imageUrl, x: Math.max(0, x), y: Math.max(0, y) });
        }, 200);
      },
      onMouseLeave: () => {
        hide();
      },
      onTouchStart: (e: React.TouchEvent) => {
        if (!imageUrl) return;
        const touch = e.touches[0];
        touchStartPos.current = { x: touch.clientX, y: touch.clientY };
        touchTimerRef.current = setTimeout(() => {
          const x = Math.min(touch.clientX - 150, window.innerWidth - 310);
          const y = Math.min(touch.clientY - 220, window.innerHeight - 440);
          setPreview({ visible: true, imageUrl, x: Math.max(10, x), y: Math.max(10, y) });
        }, 500);
      },
      onTouchMove: (e: React.TouchEvent) => {
        if (!touchStartPos.current) return;
        const touch = e.touches[0];
        const dx = Math.abs(touch.clientX - touchStartPos.current.x);
        const dy = Math.abs(touch.clientY - touchStartPos.current.y);
        if (dx > 10 || dy > 10) {
          hide();
          touchStartPos.current = null;
        }
      },
      onTouchEnd: () => {
        hide();
        touchStartPos.current = null;
      },
    }),
    [hide],
  );

  return { preview, getPreviewHandlers, hidePreview: hide };
}
