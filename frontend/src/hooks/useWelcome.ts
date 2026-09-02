import { useCallback, useState } from "react";

const STORAGE_KEY = "tcg_welcomed";

export function useWelcome() {
  const [showWelcome, setShowWelcome] = useState(
    () => localStorage.getItem(STORAGE_KEY) !== "1",
  );

  const dismiss = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, "1");
    setShowWelcome(false);
  }, []);

  return { showWelcome, dismiss };
}
