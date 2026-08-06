/**
 * Theme management hook for the Mini App.
 * - Defaults to Telegram's colorScheme on first launch
 * - Allows manual override (light/dark/system) persisted in localStorage
 * - Toggles `dark` class on document.documentElement for Tailwind's darkMode: 'class'
 */

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { getColorScheme, isTelegram } from "./telegram";

type ThemeMode = "light" | "dark" | "system";

interface ThemeContextValue {
  theme: ThemeMode;
  resolvedTheme: "light" | "dark";
  setTheme: (t: ThemeMode) => void;
  toggleTheme: () => void;
}

const THEME_KEY = "theme-preference";
const DARK_CLASS = "dark";

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    if (typeof window === "undefined") return "system";
    const stored = localStorage.getItem(THEME_KEY) as ThemeMode | null;
    return stored ?? "system";
  });
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light");

  // Compute resolved theme from Telegram or stored preference
  const computeResolved = (t: ThemeMode): "light" | "dark" => {
    if (t === "system") {
      if (isTelegram()) {
        return getColorScheme() === "dark" ? "dark" : "light";
      }
      return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }
    return t;
  };

  // Apply theme to document
  const applyTheme = (t: "light" | "dark") => {
    const html = document.documentElement;
    if (t === "dark") {
      html.classList.add(DARK_CLASS);
    } else {
      html.classList.remove(DARK_CLASS);
    }
    setResolvedTheme(t);
  };

  // Initial load + whenever theme preference changes
  useEffect(() => {
    const resolved = computeResolved(theme);
    applyTheme(resolved);
  }, [theme]);

  // Listen to Telegram colorScheme changes when in "system" mode
  useEffect(() => {
    if (!isTelegram() || theme !== "system") return;

    // Telegram WebApp doesn't have a standard event for theme change,
    // but we can poll or use the themeParams change if available.
    // Simple approach: listen for storage changes from other tabs (not applicable here)
    // and rely on the user re-opening the Mini App.
    // For now, we'll just respect the initial Telegram theme.
    // If user wants live updates, they'd need to re-open the app.
  }, [theme]);

  // Also listen to system prefers-color-scheme when in "system" mode (outside Telegram)
  useEffect(() => {
    if (theme !== "system" || isTelegram()) return;

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => applyTheme(computeResolved("system"));
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  const setTheme = (t: ThemeMode) => {
    localStorage.setItem(THEME_KEY, t);
    setThemeState(t);
  };

  const toggleTheme = () => {
    if (theme === "system") {
      setTheme(resolvedTheme === "dark" ? "light" : "dark");
    } else if (theme === "light") {
      setTheme("dark");
    } else {
      setTheme("light");
    }
  };

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return ctx;
}