import { describe, it, expect } from 'vitest';
import en from '../locales/en.json';
import ptBR from '../locales/pt-BR.json';

type Tree = { [key: string]: string | Tree };

const NAMESPACES = ['deckBuild', 'deckSuggest', 'deckSuggestions'] as const;

// Keys referenced by the deck builder / suggestion UI (F172).
const USED_KEYS = [
  'deckBuild.title',
  'deckBuild.selectFormat',
  'deckBuild.selectCommander',
  'deckBuild.selectColors',
  'deckBuild.pickColors',
  'deckBuild.searchCommander',
  'deckBuild.commanderSearchError',
  'deckBuild.noCommandersFound',
  'deckBuild.archetypeBudget',
  'deckBuild.selectArchetype',
  'deckBuild.budgetLabel',
  'deckBuild.prioritizeOwned',
  'deckBuild.generate',
  'deckBuild.generating',
  'deckBuild.regenerate',
  'deckBuild.reviewDeck',
  'deckBuild.totalCards',
  'deckBuild.lands',
  'deckBuild.nonlands',
  'deckBuild.totalValue',
  'deckBuild.deckName',
  'deckBuild.saveDeck',
  'deckSuggest.mode.manualTitle',
  'deckSuggest.mode.manualDesc',
  'deckSuggest.mode.suggestionTitle',
  'deckSuggest.mode.suggestionDesc',
  'deckSuggest.mode.switchBack',
  'deckSuggest.form.format',
  'deckSuggest.form.commander',
  'deckSuggest.form.colors',
  'deckSuggest.form.archetype',
  'deckSuggest.form.notes',
  'deckSuggest.form.notesPlaceholder',
  'deckSuggest.form.submit',
  'deckSuggest.form.submitting',
  'deckSuggest.form.success',
  'deckSuggest.form.genericError',
  'deckSuggest.panel.selectPrompt',
  'deckSuggest.result.pending',
  'deckSuggest.result.processing',
  'deckSuggest.result.failed',
  'deckSuggest.result.saveFailed',
  'deckSuggest.result.totalCards',
  'deckSuggest.result.ownedCards',
  'deckSuggest.result.missingCards',
  'deckSuggest.result.missingCost',
  'deckSuggest.result.commander',
  'deckSuggest.result.owned',
  'deckSuggest.result.missing',
  'deckSuggest.result.unresolved',
  'deckSuggest.result.viewDeck',
  'deckSuggest.result.save',
  'deckSuggest.result.saving',
  'deckSuggestions.list.title',
  'deckSuggestions.list.loading',
  'deckSuggestions.list.refresh',
  'deckSuggestions.list.emptyTitle',
  'deckSuggestions.list.emptyDescription',
  'deckSuggestions.list.ownedOfTotal',
  'deckSuggestions.list.delete',
  'deckSuggestions.list.confirmDelete',
  'deckSuggestions.status.pending',
  'deckSuggestions.status.processing',
  'deckSuggestions.status.done',
  'deckSuggestions.status.failed',
];

function flatten(tree: Tree, prefix: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(tree)) {
    const path = `${prefix}.${key}`;
    if (typeof value === 'string') out[path] = value;
    else Object.assign(out, flatten(value, path));
  }
  return out;
}

function namespaceKeys(locale: Record<string, unknown>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const ns of NAMESPACES) {
    const tree = locale[ns];
    if (tree && typeof tree === 'object') Object.assign(out, flatten(tree as Tree, ns));
  }
  return out;
}

function placeholders(value: string): string[] {
  return (value.match(/\{\{\s*\w+\s*\}\}/g) ?? []).map((p) => p.replace(/\s/g, '')).sort();
}

const enKeys = namespaceKeys(en as Record<string, unknown>);
const ptKeys = namespaceKeys(ptBR as Record<string, unknown>);

describe('deckBuild / deckSuggest i18n keys', () => {
  it('namespaces exist and are non-empty in both locales', () => {
    for (const ns of NAMESPACES) {
      expect(Object.keys(flatten((en as Record<string, Tree>)[ns] ?? {}, ns)).length).toBeGreaterThan(0);
      expect(Object.keys(flatten((ptBR as Record<string, Tree>)[ns] ?? {}, ns)).length).toBeGreaterThan(0);
    }
  });

  it('en and pt-BR have identical key sets', () => {
    expect(Object.keys(ptKeys).sort()).toEqual(Object.keys(enKeys).sort());
  });

  it('every key used by the UI exists in both locales', () => {
    const missingEn = USED_KEYS.filter((k) => !(k in enKeys));
    const missingPt = USED_KEYS.filter((k) => !(k in ptKeys));
    expect(missingEn).toEqual([]);
    expect(missingPt).toEqual([]);
  });

  it('nested keys are present', () => {
    expect(ptKeys['deckSuggest.result.pending']).toBeTruthy();
    expect(ptKeys['deckSuggestions.status.pending']).toBeTruthy();
    expect(enKeys['deckSuggest.mode.switchBack']).toBeTruthy();
  });

  it('no value is empty', () => {
    for (const [k, v] of [...Object.entries(enKeys), ...Object.entries(ptKeys)]) {
      expect(v.trim(), k).not.toBe('');
    }
  });

  it('interpolation placeholders match across languages', () => {
    for (const [k, v] of Object.entries(enKeys)) {
      expect(placeholders(ptKeys[k] ?? ''), k).toEqual(placeholders(v));
    }
    expect(placeholders(enKeys['deckSuggestions.list.ownedOfTotal'])).toEqual(['{{owned}}', '{{total}}']);
  });

  it('does not rename the legacy deckBuilder namespace', () => {
    expect((en as Record<string, unknown>).deckBuilder).toBeDefined();
    expect((ptBR as Record<string, unknown>).deckBuilder).toBeDefined();
  });
});
