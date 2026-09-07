import { useEffect, useRef, useState } from "react";

interface AchievementToastProps {
  title: string;
  description: string;
  icon: string;
  durationMs?: number;
  onDismiss: () => void;
}

const ICON_MAP: Record<string, string> = {
  card: "M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z",
  deck: "M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z",
  scan: "M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z",
  collection: "M20 2H4c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM8 20H4v-4h4v4zm0-6H4v-4h4v4zm0-6H4V4h4v4zm6 12h-4v-4h4v4zm0-6h-4v-4h4v4zm0-6h-4V4h4v4zm6 12h-4v-4h4v4zm0-6h-4v-4h4v4zm0-6h-4V4h4v4z",
  trophy: "M19 5h-2V3H7v2H5c-1.1 0-2 .9-2 2v1c0 2.55 1.92 4.63 4.39 4.94.63 1.5 1.98 2.63 3.61 2.96V19H7v2h10v-2h-4v-3.1c1.63-.33 2.98-1.46 3.61-2.96C19.08 12.63 21 10.55 21 8V7c0-1.1-.9-2-2-2z",
  alert: "M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z",
  treasure: "M12 2L6 8h12L12 2zm0 4L9.5 8h5L12 6zm-6 4v8h12v-8H6zm2 2h8v4H8v-4z",
  star: "M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z",
};

function AchievementIcon({ icon }: { icon: string }) {
  const path = ICON_MAP[icon] || ICON_MAP.star;
  return (
    <svg
      className="w-8 h-8 text-amber-400 flex-shrink-0"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}

export function AchievementToast({
  title,
  description,
  icon,
  durationMs = 5000,
  onDismiss,
}: AchievementToastProps) {
  const [visible, setVisible] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onDismissRef = useRef(onDismiss);
  onDismissRef.current = onDismiss;

  useEffect(() => {
    // Trigger entrance animation
    const enterTimer = setTimeout(() => setVisible(true), 50);

    // Auto-dismiss
    timerRef.current = setTimeout(() => {
      setVisible(false);
      setTimeout(() => onDismissRef.current(), 300);
    }, durationMs);

    return () => {
      clearTimeout(enterTimer);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [durationMs]);

  return (
    <div
      className={`
        fixed top-4 left-1/2 -translate-x-1/2 z-[60]
        bg-gradient-to-r from-amber-900/90 to-yellow-900/90
        border border-amber-500/50 rounded-lg shadow-lg shadow-amber-500/20
        px-4 py-3 flex items-center gap-3
        min-w-[300px] max-w-[420px]
        transition-all duration-300 ease-out
        ${visible ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-4"}
      `}
      data-testid="achievement-toast"
      role="alert"
    >
      <AchievementIcon icon={icon} />
      <div className="flex-1 min-w-0">
        <p
          className="text-sm font-bold text-amber-300"
          data-testid="achievement-toast-title"
        >
          {title}
        </p>
        <p className="text-xs text-amber-100/80 truncate">{description}</p>
      </div>
      <button
        onClick={() => {
          if (timerRef.current) clearTimeout(timerRef.current);
          setVisible(false);
          setTimeout(() => onDismissRef.current(), 300);
        }}
        className="text-amber-400/60 hover:text-amber-300 transition-colors flex-shrink-0"
        aria-label="Dismiss"
        data-testid="achievement-toast-dismiss"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
        </svg>
      </button>
      {/* Progress bar */}
      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-amber-900/50 rounded-b-lg overflow-hidden">
        <div
          className="h-full bg-amber-400"
          data-testid="achievement-toast-progress"
          style={{
            animation: `achievement-shrink ${durationMs}ms linear forwards`,
          }}
        />
      </div>
      <style>{`
        @keyframes achievement-shrink {
          from { width: 100%; }
          to { width: 0%; }
        }
      `}</style>
    </div>
  );
}
