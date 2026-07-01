import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  DEFAULT_UI_LANG,
  UI_LANG_STORAGE_KEY,
  translate,
  type UiLang,
} from "./index";

interface I18nContextValue {
  lang: UiLang;
  setLang: (lang: UiLang) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

function readStoredLang(): UiLang {
  try {
    const raw = localStorage.getItem(UI_LANG_STORAGE_KEY);
    if (raw === "zh" || raw === "en") return raw;
  } catch {
    // ignore storage errors (private mode, disabled storage)
  }
  return DEFAULT_UI_LANG;
}

interface LanguageProviderProps {
  children: ReactNode;
  initialLang?: UiLang;
}

export function LanguageProvider({
  children,
  initialLang,
}: LanguageProviderProps) {
  const [lang, setLangState] = useState<UiLang>(() => initialLang ?? readStoredLang());

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = lang;
    }
  }, [lang]);

  const setLang = useCallback((next: UiLang) => {
    setLangState(next);
    try {
      localStorage.setItem(UI_LANG_STORAGE_KEY, next);
    } catch {
      // ignore storage errors
    }
  }, []);

  const t = useCallback(
    (key: string, vars?: Record<string, string | number>) =>
      translate(lang, key, vars),
    [lang],
  );

  const value = useMemo<I18nContextValue>(
    () => ({ lang, setLang, t }),
    [lang, setLang, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within a LanguageProvider");
  }
  return ctx;
}
