import { useTranslation } from "react-i18next";
import { scryfallSetIconUrl } from "../utils/scryfall";
import { useState } from "react";

interface SetIconFilterProps {
  options: { label: string; value: string }[];
  selected: string | null;
  onSelect: (value: string | null) => void;
}

export function SetIconFilter({ options, selected, onSelect }: SetIconFilterProps) {
  const { t } = useTranslation();
  return (
    <div className="flex gap-2 overflow-x-auto pb-2" data-testid="set-icon-filter">
      {/* "All" button */}
      <button
        className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
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
      className={`flex items-center justify-center w-10 h-10 rounded-md transition-all ${
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
