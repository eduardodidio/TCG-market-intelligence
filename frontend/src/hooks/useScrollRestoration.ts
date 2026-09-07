import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

/**
 * Save and restore scroll position per route using sessionStorage.
 * Only restores on browser back/forward navigation (popstate),
 * not on fresh navigation.
 */
export function useScrollRestoration(key?: string) {
  const location = useLocation();
  const storageKey = `scroll_${key || location.pathname}`;
  const isPopState = useRef(false);

  // Track popstate (back/forward) navigation
  useEffect(() => {
    const handler = () => {
      isPopState.current = true;
    };
    window.addEventListener("popstate", handler);
    return () => window.removeEventListener("popstate", handler);
  }, []);

  // Save scroll position on unmount
  useEffect(() => {
    return () => {
      const scrollY = window.scrollY;
      if (scrollY > 0) {
        sessionStorage.setItem(storageKey, String(scrollY));
      }
    };
  }, [storageKey]);

  // Restore scroll position on mount (only for back/forward)
  useEffect(() => {
    if (!isPopState.current) {
      isPopState.current = false;
      return;
    }

    isPopState.current = false;
    const saved = sessionStorage.getItem(storageKey);
    if (saved) {
      const scrollY = parseInt(saved, 10);
      if (!isNaN(scrollY)) {
        // Wait for content to render
        requestAnimationFrame(() => {
          window.scrollTo(0, scrollY);
        });
      }
    }
  }, [storageKey]);
}
