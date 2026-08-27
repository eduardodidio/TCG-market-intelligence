import { useContext } from 'react';
import { LanguageContext } from '../contexts/LanguageContext';
import treasureEn from '../assets/treasure.jpg';
import tesouroPt from '../assets/tesouro.png';

export function useTreasureImage(): string {
  const ctx = useContext(LanguageContext);
  const lang = ctx?.language ?? 'en';
  return lang === 'en' ? treasureEn : tesouroPt;
}
