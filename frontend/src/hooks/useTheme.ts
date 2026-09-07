import { useContext } from "react";
import { ThemeContext, type ThemeContextValue } from "../contexts/ThemeContext";

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}
