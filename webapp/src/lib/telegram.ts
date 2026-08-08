/**
 * Telegram WebApp SDK wrapper — single access point for the Mini App API.
 * Safe to import in any environment; degrades to a no-op stub when the SDK
 * is absent (e.g. plain browser during dev).
 */

export interface TgThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
}

type HapticStyle = "light" | "medium" | "heavy" | "rigid" | "soft";
type NotificationType = "error" | "success" | "warning";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        initData: string;
        initDataUnsafe?: {
          user?: {
            id: number;
            first_name?: string;
            last_name?: string;
            username?: string;
            language_code?: string;
            photo_url?: string;
          };
        };
        colorScheme: "light" | "dark";
        themeParams: TgThemeParams;
        MainButton?: {
          show: () => void;
          hide: () => void;
          setText: (t: string) => void;
          setParams?: (p: Record<string, string>) => void;
          onClick: (cb: () => void) => void;
          offClick: (cb: () => void) => void;
        };
        BackButton?: {
          show: () => void;
          hide: () => void;
          onClick: (cb: () => void) => void;
          offClick: (cb: () => void) => void;
        };
        HapticFeedback?: {
          impactOccurred: (s: HapticStyle) => void;
          notificationOccurred: (t: NotificationType) => void;
          selectionChanged: () => void;
        };
        openLink: (url: string) => void;
        close: () => void;
      };
    };
  }
}

const tg = () => window.Telegram?.WebApp;

export const isTelegram = () => Boolean(tg());

export function initTelegram() {
  const webapp = tg();
  if (!webapp) return;
  webapp.ready();
  webapp.expand();
}

export function getInitData(): string {
  return tg()?.initData ?? "";
}

export function getTelegramUser() {
  return tg()?.initDataUnsafe?.user ?? null;
}

export function getColorScheme(): "light" | "dark" {
  return tg()?.colorScheme ?? "light";
}

export function getThemeParams(): TgThemeParams {
  return tg()?.themeParams ?? {};
}

/** Haptic feedback — free polish; no-op outside Telegram. */
export function haptic(
  style: HapticStyle = "light",
  notification?: NotificationType
) {
  const h = tg()?.HapticFeedback;
  h?.impactOccurred(style);
  if (notification) h?.notificationOccurred(notification);
}

export function mainButton(text: string, onClick: () => void) {
  const mb = tg()?.MainButton;
  if (!mb) return () => {};
  mb.setText(text);
  mb.onClick(onClick);
  mb.show();
  return () => {
    mb.offClick(onClick);
    mb.hide();
  };
}

export function backButton(onClick: () => void) {
  const bb = tg()?.BackButton;
  if (!bb) return () => {};
  bb.onClick(onClick);
  bb.show();
  return () => {
    bb.offClick(onClick);
    bb.hide();
  };
}
