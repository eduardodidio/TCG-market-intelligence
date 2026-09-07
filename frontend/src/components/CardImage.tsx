import { useState } from "react";

interface CardImageProps {
  src: string | null;
  fallbackSrc?: string | null;
  alt: string;
  className?: string;
}

/**
 * Shared card image component with skeleton loading and fade-in transition.
 * Shows an animate-pulse skeleton while the image loads.
 * Falls back to a placeholder SVG on error.
 */
export function CardImage({ src, fallbackSrc, alt, className = "" }: CardImageProps) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const [fallbackError, setFallbackError] = useState(false);

  const currentSrc = error && fallbackSrc ? fallbackSrc : src;
  const showImage = currentSrc && !(error && (fallbackError || !fallbackSrc));

  return (
    <div className={`relative ${className}`} data-testid="card-image-container">
      {showImage ? (
        <>
          {/* Skeleton overlay while loading */}
          {!loaded && (
            <div
              className="absolute inset-0 animate-pulse bg-slate-700 rounded"
              data-testid="card-image-skeleton"
            />
          )}
          <img
            src={currentSrc}
            alt={alt}
            className={`w-full h-full object-cover transition-opacity duration-200 ${
              loaded ? "opacity-100" : "opacity-0"
            }`}
            loading="lazy"
            onLoad={() => setLoaded(true)}
            onError={() => {
              if (!error) {
                setError(true);
              } else {
                setFallbackError(true);
              }
            }}
            data-testid="card-image"
          />
        </>
      ) : (
        <div className="w-full h-full flex items-center justify-center" data-testid="card-image-fallback">
          <svg
            className="h-12 w-12 text-slate-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
        </div>
      )}
    </div>
  );
}
