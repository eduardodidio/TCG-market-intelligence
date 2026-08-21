import { createContext, useState, useCallback, type ReactNode } from 'react';
import i18n from '../i18n/i18n';

export type SupportedLanguage = 'en' | 'pt-BR';

export interface LanguageContextValue {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
}

export const LanguageContext = createContext<LanguageContextValue | null>(null);

const STORAGE_KEY = 'tcg_language';

function getInitialLanguage(): SupportedLanguage {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'en' || stored === 'pt-BR') return stored;
  return (i18n.language?.startsWith('pt') ? 'pt-BR' : 'en') as SupportedLanguage;
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<SupportedLanguage>(getInitialLanguage);

  const setLanguage = useCallback((lang: SupportedLanguage) => {
    i18n.changeLanguage(lang);
    localStorage.setItem(STORAGE_KEY, lang);
    setLanguageState(lang);
  }, []);

  return (
    <LanguageContext.Provider value={{ language, setLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
}
