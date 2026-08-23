interface ChimarraoIconProps {
  onClick: () => void;
}

export function ChimarraoIcon({ onClick }: ChimarraoIconProps) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-6 right-6 z-50 flex items-center justify-center w-12 h-12 rounded-full bg-slate-800/90 border border-green-600/40 cursor-pointer animate-pulse shadow-lg shadow-green-500/30 hover:scale-110 transition-transform"
      data-testid="chimarrao-icon"
      aria-label="Chimarrao"
      type="button"
    >
      <span className="text-3xl leading-none" role="img" aria-hidden="true">
        🧉
      </span>
    </button>
  );
}
