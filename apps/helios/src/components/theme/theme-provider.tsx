"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
} from "react";

const STORAGE_KEY = "localstock-theme";
const DEFAULT_THEME = "light";
const THEMES = ["light", "dark"] as const;

interface ThemeContextValue {
  theme: string;
  setTheme: (theme: string) => void;
  resolvedTheme: string;
  themes: readonly string[];
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: DEFAULT_THEME,
  setTheme: () => {},
  resolvedTheme: DEFAULT_THEME,
  themes: THEMES,
});

export const useTheme = () => useContext(ThemeContext);

// Subscribe to storage events (cross-tab sync)
function subscribeToStorage(callback: () => void) {
  const handler = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) callback();
  };
  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
}

function getThemeSnapshot(): string {
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_THEME;
}

function getServerSnapshot(): string {
  return DEFAULT_THEME;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useSyncExternalStore(
    subscribeToStorage,
    getThemeSnapshot,
    getServerSnapshot,
  );

  const setTheme = useCallback((newTheme: string) => {
    localStorage.setItem(STORAGE_KEY, newTheme);
    const el = document.documentElement;
    el.classList.remove(...THEMES);
    el.classList.add(newTheme);
    // Trigger re-render via storage event emulation
    window.dispatchEvent(
      new StorageEvent("storage", { key: STORAGE_KEY, newValue: newTheme }),
    );
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, setTheme, resolvedTheme: theme, themes: THEMES }),
    [theme, setTheme],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}
