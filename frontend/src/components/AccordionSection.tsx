import type { ReactNode } from "react";

export interface AccordionSectionProps {
  title: string;
  icon?: ReactNode;
  isOpen: boolean;
  onToggle: () => void;
  children: ReactNode;
}

export function AccordionSection({
  title,
  icon,
  isOpen,
  onToggle,
  children,
}: AccordionSectionProps) {
  return (
    <div
      className="bg-slate-800 border border-slate-700 rounded-lg mb-2"
      data-testid={`accordion-${title.toLowerCase().replace(/[^a-z0-9]/g, "-")}`}
    >
      <button
        type="button"
        onClick={onToggle}
        className="w-full px-4 py-3 flex justify-between items-center cursor-pointer hover:bg-slate-700/50 rounded-lg"
        data-testid={`accordion-toggle-${title.toLowerCase().replace(/[^a-z0-9]/g, "-")}`}
      >
        <span className="flex items-center gap-2 text-white font-medium">
          {icon}
          {title}
        </span>
        <svg
          className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          data-testid="accordion-chevron"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {isOpen && (
        <div className="px-4 pb-4" data-testid="accordion-content">
          {children}
        </div>
      )}
    </div>
  );
}
