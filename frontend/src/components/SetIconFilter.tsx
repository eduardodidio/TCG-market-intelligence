import { useTranslation } from "react-i18next";
import { scryfallSetIconUrl } from "../utils/scryfall";
import { useState, useRef, useCallback, useEffect } from "react";

interface SetIconFilterProps {
  options: { label: string; value: string }[];
  selected: string | null;
  onSelect: (value: string | null) => void;
}

export function SetIconFilter({ options, selected, onSelect }: SetIconFilterProps) {
  const { t } = useTranslation();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const updateScrollState = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 0);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1);
  }, []);

  useEffect(() => {
    updateScrollState();
  }, [options, updateScrollState]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const observer = new ResizeObserver(() => updateScrollState());
    observer.observe(el);
    return () => observer.disconnect();
  }, [updateScrollState]);

  const scrollBy = (delta: number) => {
    scrollRef.current?.scrollBy({ left: delta, behavior: "smooth" });
  };

  return (
    <div className="relative flex items-center gap-1" data-testid="set-icon-filter">
      {/* Left arrow */}
      {canScrollLeft && (
        <button
          className="absolute left-0 z-10 flex items-center justify-center w-7 h-7 rounded-full bg-slate-700 hover:bg-slate-600 text-slate-300 shadow-md transition-colors"
          onClick={() => scrollBy(-200)}
          aria-label="Scroll left"
          data-testid="scroll-left"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path fillRule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clipRule="evenodd" />
          </svg>
        </button>
      )}

      {/* Scrollable container */}
      <div
        ref={scrollRef}
        className="flex gap-2 overflow-x-auto pb-2 max-w-[520px] scrollbar-thin"
        onScroll={updateScrollState}
        data-testid="scroll-container"
        style={{
          scrollbarWidth: "thin",
          scrollbarColor: "#475569 #1e293b",
        }}
      >
        {/* "All" button */}
        <button
          className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors flex-shrink-0 ${
            selected === null
              ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/50"
              : "bg-slate-800 text-slate-400 hover:text-white border border-transparent"
          }`}
          onClick={() => onSelect(null)}
        >
          {t("common.all")}
        </button>
        {options.map((opt) => (
          <SetIconButton
            key={opt.value}
            option={opt}
            isSelected={selected === opt.value}
            onSelect={onSelect}
          />
        ))}
      </div>

      {/* Right gradient fade */}
      {canScrollRight && (
        <div
          className="absolute right-8 top-0 bottom-0 w-8 bg-gradient-to-l from-slate-900 to-transparent pointer-events-none"
          data-testid="scroll-fade"
        />
      )}

      {/* Right arrow */}
      {canScrollRight && (
        <button
          className="absolute right-0 z-10 flex items-center justify-center w-7 h-7 rounded-full bg-slate-700 hover:bg-slate-600 text-slate-300 shadow-md transition-colors"
          onClick={() => scrollBy(200)}
          aria-label="Scroll right"
          data-testid="scroll-right"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
          </svg>
        </button>
      )}
    </div>
  );
}

function SetIconButton({
  option,
  isSelected,
  onSelect,
}: {
  option: { label: string; value: string };
  isSelected: boolean;
  onSelect: (value: string | null) => void;
}) {
  const [imgError, setImgError] = useState(false);

  return (
    <button
      className={`flex items-center justify-center w-10 h-10 rounded-md transition-all flex-shrink-0 ${
        isSelected
          ? "bg-indigo-500/20 ring-2 ring-indigo-500 shadow-md"
          : "bg-slate-800 hover:bg-slate-700"
      }`}
      onClick={() => onSelect(isSelected ? null : option.value)}
      title={option.label}
      data-testid={`set-icon-${option.value}`}
    >
      {imgError ? (
        <span className="text-xs font-mono text-slate-400">{option.value.slice(0, 3).toUpperCase()}</span>
      ) : (
        <img
          src={scryfallSetIconUrl(option.value)}
          alt={option.label}
          className="w-6 h-6 invert brightness-200"
          onError={() => setImgError(true)}
        />
      )}
    </button>
  );
}
