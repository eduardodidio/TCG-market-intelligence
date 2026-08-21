import { describe, it, expect } from 'vitest';
import i18n from '../i18n';

describe('i18n initialization', () => {
  it('initializes without errors', () => {
    expect(i18n.isInitialized).toBe(true);
  });

  it('has "en" as fallback language', () => {
    expect(i18n.options.fallbackLng).toEqual(['en']);
  });

  it('has en and pt-BR resources loaded', () => {
    expect(i18n.hasResourceBundle('en', 'translation')).toBe(true);
    expect(i18n.hasResourceBundle('pt-BR', 'translation')).toBe(true);
  });

  it('defaults to "en" when no localStorage value is set', () => {
    localStorage.removeItem('tcg_language');
    // fallback should be en
    expect(i18n.options.fallbackLng).toEqual(['en']);
  });

  it('switching language persists to localStorage', async () => {
    localStorage.removeItem('tcg_language');
    await i18n.changeLanguage('pt-BR');
    // i18next detection caches to localStorage with key tcg_language
    expect(localStorage.getItem('tcg_language')).toBe('pt-BR');
    // reset
    await i18n.changeLanguage('en');
  });

  it('interpolation escapeValue is false', () => {
    expect(i18n.options.interpolation?.escapeValue).toBe(false);
  });
});
