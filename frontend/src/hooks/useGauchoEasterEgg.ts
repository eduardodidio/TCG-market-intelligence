import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useCurrency } from "./useCurrency";
import type { GauchoOption } from "../components/GauchoDialog";

export interface GauchoDialogData {
  message: string;
  options?: GauchoOption[];
  autoDismissMs?: number;
}

interface GauchoEasterEggResult {
  showIcon: boolean;
  showDialog: boolean;
  dialogData: GauchoDialogData | null;
  openDialog: () => void;
  dismissDialog: () => void;
}

function getStorageKey(pagePath: string): string {
  return `gaucho_dismissed_${pagePath}`;
}

function getDialogueForPage(
  pagePath: string,
  t: (key: string) => string,
  context?: { isEmpty?: boolean },
): GauchoDialogData | null {
  switch (pagePath) {
    case "/":
      return {
        message: t("gaucho.dashboard.message"),
        options: [{ label: t("gaucho.dashboard.opt1") }],
      };
    case "/collection":
      return {
        message: t("gaucho.collection.message"),
        options: [
          { label: t("gaucho.collection.opt1"), reply: t("gaucho.collection.reply1") },
          { label: t("gaucho.collection.opt2"), reply: t("gaucho.collection.reply2") },
        ],
      };
    case "/banlist":
      return {
        message: t("gaucho.banlist.message"),
        options: [
          { label: t("gaucho.banlist.opt1"), reply: t("gaucho.banlist.reply1") },
          { label: t("gaucho.banlist.opt2"), reply: t("gaucho.banlist.reply2") },
        ],
      };
    case "/decks":
      if (context?.isEmpty) {
        return {
          message: t("gaucho.decksEmpty.message"),
          autoDismissMs: 4000,
        };
      }
      return {
        message: t("gaucho.decks.message"),
        options: [
          { label: t("gaucho.decks.opt1"), reply: t("gaucho.decks.reply1") },
          { label: t("gaucho.decks.opt2"), reply: t("gaucho.decks.reply2") },
        ],
      };
    default:
      return null;
  }
}

export function useGauchoEasterEgg(
  pagePath: string,
  context?: { isEmpty?: boolean },
): GauchoEasterEggResult {
  const { currency } = useCurrency();
  const { t } = useTranslation();
  const [iconVisible, setIconVisible] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  const isPila = currency === "PILA";
  const storageKey = getStorageKey(pagePath);
  const dialogData = isPila ? getDialogueForPage(pagePath, t, context) : null;

  // Show icon after 2-second delay, reset on page change
  useEffect(() => {
    setIconVisible(false);
    setDialogOpen(false);

    if (!isPila || !dialogData) return;

    // Check if already dismissed this session
    try {
      if (sessionStorage.getItem(storageKey)) return;
    } catch {
      // sessionStorage unavailable
    }

    const timer = setTimeout(() => {
      setIconVisible(true);
    }, 2000);

    return () => clearTimeout(timer);
  }, [pagePath, isPila, storageKey, dialogData !== null]); // eslint-disable-line react-hooks/exhaustive-deps

  const openDialog = useCallback(() => {
    setDialogOpen(true);
  }, []);

  const dismissDialog = useCallback(() => {
    setDialogOpen(false);
    setIconVisible(false);
    try {
      sessionStorage.setItem(storageKey, "1");
    } catch {
      // sessionStorage unavailable
    }
  }, [storageKey]);

  return {
    showIcon: isPila && iconVisible && dialogData !== null,
    showDialog: isPila && dialogOpen && dialogData !== null,
    dialogData,
    openDialog,
    dismissDialog,
  };
}
