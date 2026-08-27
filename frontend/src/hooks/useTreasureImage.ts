import { useContext } from 'react';
import { CurrencyContext } from '../contexts/CurrencyContext';
import treasureDefault from '../assets/treasure.jpg';
import tesouroPila from '../assets/tesouro.png';

export function useTreasureImage(): string {
  const { currency } = useContext(CurrencyContext);
  return currency === 'PILA' ? tesouroPila : treasureDefault;
}
