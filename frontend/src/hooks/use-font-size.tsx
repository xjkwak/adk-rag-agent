import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export const DEFAULT_FONT_SCALE = 1;
const STORAGE_KEY = "knowledge-hub-font-scale";
const STEP = 0.0625;
const MIN_SCALE = 0.75;
const MAX_SCALE = 1.5;

function clampScale(scale: number): number {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
}

function getStoredScale(): number {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return DEFAULT_FONT_SCALE;
  const parsed = Number.parseFloat(stored);
  return Number.isFinite(parsed) ? clampScale(parsed) : DEFAULT_FONT_SCALE;
}

export function applyFontScale(scale: number) {
  document.documentElement.style.setProperty(
    "--font-size-scale",
    String(clampScale(scale)),
  );
}

interface FontSizeContextValue {
  scale: number;
  percent: number;
  canDecrease: boolean;
  canIncrease: boolean;
  isDefault: boolean;
  increase: () => void;
  decrease: () => void;
  reset: () => void;
}

const FontSizeContext = createContext<FontSizeContextValue | null>(null);

export function FontSizeProvider({ children }: { children: ReactNode }) {
  const [scale, setScale] = useState<number>(getStoredScale);

  useEffect(() => {
    const clamped = clampScale(scale);
    applyFontScale(clamped);
    localStorage.setItem(STORAGE_KEY, String(clamped));
  }, [scale]);

  const increase = useCallback(() => {
    setScale((current) => clampScale(current + STEP));
  }, []);

  const decrease = useCallback(() => {
    setScale((current) => clampScale(current - STEP));
  }, []);

  const reset = useCallback(() => {
    setScale(DEFAULT_FONT_SCALE);
  }, []);

  const clamped = clampScale(scale);

  return (
    <FontSizeContext.Provider
      value={{
        scale: clamped,
        percent: Math.round(clamped * 100),
        canDecrease: clamped > MIN_SCALE,
        canIncrease: clamped < MAX_SCALE,
        isDefault: clamped === DEFAULT_FONT_SCALE,
        increase,
        decrease,
        reset,
      }}
    >
      {children}
    </FontSizeContext.Provider>
  );
}

export function useFontSize() {
  const context = useContext(FontSizeContext);
  if (!context) {
    throw new Error("useFontSize must be used within a FontSizeProvider");
  }
  return context;
}
