import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { type ReactNode } from 'react';
import { LanguageProvider } from '../../contexts/LanguageContext';
import { useLanguage } from '../useLanguage';

function wrapper({ children }: { children: ReactNode }) {
  return <LanguageProvider>{children}</LanguageProvider>;
}

describe('useLanguage hook', () => {
  it('returns language and setLanguage from context', () => {
    const { result } = renderHook(() => useLanguage(), { wrapper });
    expect(result.current.language).toBeDefined();
    expect(typeof result.current.setLanguage).toBe('function');
  });

  it('throws when used outside LanguageProvider', () => {
    expect(() => {
      renderHook(() => useLanguage());
    }).toThrow('useLanguage must be used within a LanguageProvider');
  });
});
