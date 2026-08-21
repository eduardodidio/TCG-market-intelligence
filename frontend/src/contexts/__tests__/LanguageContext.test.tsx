import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { LanguageProvider } from '../LanguageContext';
import { useLanguage } from '../../hooks/useLanguage';

function TestConsumer() {
  const { language, setLanguage } = useLanguage();
  return (
    <div>
      <span data-testid="lang">{language}</span>
      <button onClick={() => setLanguage('pt-BR')}>Switch to PT</button>
      <button onClick={() => setLanguage('en')}>Switch to EN</button>
    </div>
  );
}

describe('LanguageContext', () => {
  beforeEach(() => {
    localStorage.removeItem('tcg_language');
  });

  it('provides language value', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>,
    );
    expect(screen.getByTestId('lang')).toHaveTextContent('en');
  });

  it('setLanguage updates context and persists to localStorage', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>,
    );

    act(() => {
      screen.getByText('Switch to PT').click();
    });

    expect(screen.getByTestId('lang')).toHaveTextContent('pt-BR');
    expect(localStorage.getItem('tcg_language')).toBe('pt-BR');
  });

  it('setLanguage can switch back to EN', () => {
    localStorage.setItem('tcg_language', 'pt-BR');
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>,
    );

    expect(screen.getByTestId('lang')).toHaveTextContent('pt-BR');

    act(() => {
      screen.getByText('Switch to EN').click();
    });

    expect(screen.getByTestId('lang')).toHaveTextContent('en');
    expect(localStorage.getItem('tcg_language')).toBe('en');
  });
});
