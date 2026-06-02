import { Minus, Moon, Plus, RotateCcw, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useFontSize } from "@/hooks/use-font-size";
import { useTheme } from "@/hooks/use-theme";

const controlButtonClass =
  "h-9 border-border bg-background/80 backdrop-blur-sm shadow-sm";

export function AppControls() {
  const { theme, toggleTheme } = useTheme();
  const {
    percent,
    canDecrease,
    canIncrease,
    isDefault,
    increase,
    decrease,
    reset,
  } = useFontSize();

  return (
    <div
      className="fixed top-4 right-4 z-50 flex items-center gap-1"
      role="toolbar"
      aria-label="Display settings"
    >
      <div
        className="flex items-center gap-0.5 rounded-md border border-border bg-background/80 p-0.5 backdrop-blur-sm shadow-sm"
        role="group"
        aria-label="Font size"
      >
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={decrease}
          disabled={!canDecrease}
          className={`${controlButtonClass} w-9`}
          aria-label="Decrease font size"
          title="Decrease font size"
        >
          <Minus className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={reset}
          disabled={isDefault}
          className={`${controlButtonClass} h-9 min-w-[3.25rem] px-2 text-xs font-medium`}
          aria-label="Reset font size to default"
          title="Reset font size"
        >
          <RotateCcw className="h-3.5 w-3.5 shrink-0" />
          <span className="tabular-nums">{percent}%</span>
        </Button>
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={increase}
          disabled={!canIncrease}
          className={`${controlButtonClass} w-9`}
          aria-label="Increase font size"
          title="Increase font size"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      <Button
        type="button"
        variant="outline"
        size="icon"
        onClick={toggleTheme}
        className={`${controlButtonClass} w-9`}
        aria-label={
          theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
        }
        title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      >
        {theme === "dark" ? (
          <Sun className="h-4 w-4" />
        ) : (
          <Moon className="h-4 w-4" />
        )}
      </Button>
    </div>
  );
}
