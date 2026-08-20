import { useEffect, useRef } from "react";

export function useInfiniteScroll(
  onLoadMore: () => void,
  options: { enabled: boolean; rootMargin?: string },
) {
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!options.enabled) return;
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) onLoadMore();
      },
      { rootMargin: options.rootMargin ?? "200px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [onLoadMore, options.enabled, options.rootMargin]);

  return sentinelRef;
}
