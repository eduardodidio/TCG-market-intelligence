import { useContext } from "react";
import { LanguageContext } from "../contexts/LanguageContext";

export function useCardName() {
  const ctx = useContext(LanguageContext);
  const language = ctx?.language ?? "en";

  function getCardName(
    name_en?: string | null,
    name_pt?: string | null,
    fallback?: string,
  ): string {
    if (language === "pt-BR" && name_pt) return name_pt;
    return name_en || name_pt || fallback || "Unknown Card";
  }

  /** Returns the "other language" name for use as a subtitle, or null if not applicable. */
  function getSubtitleName(
    name_en?: string | null,
    name_pt?: string | null,
    fallback?: string,
  ): string | null {
    const mainName = getCardName(name_en, name_pt, fallback);
    if (language === "pt-BR") {
      return name_en && name_en !== mainName ? name_en : null;
    }
    return name_pt && name_pt !== mainName ? name_pt : null;
  }

  return { getCardName, getSubtitleName };
}
