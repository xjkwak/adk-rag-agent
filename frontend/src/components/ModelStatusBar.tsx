import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchAgentConfig } from "@/api/hubConfig";

interface ModelStatus {
  provider: string;
  model: string;
}

const PROVIDER_LABELS: Record<string, string> = {
  gemini: "Gemini",
  openai: "OpenAI",
};

export function ModelStatusBar() {
  const [status, setStatus] = useState<ModelStatus | null>(null);

  const refresh = useCallback(async () => {
    try {
      const cfg = await fetchAgentConfig();
      setStatus({ provider: cfg.provider ?? "gemini", model: cfg.model });
    } catch {
      // Silent — status bar is informational only.
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Re-fetch when the window regains focus so a Config page save is
  // reflected immediately when the user switches back to another tab.
  useEffect(() => {
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, [refresh]);

  if (!status) return null;

  const providerLabel =
    PROVIDER_LABELS[status.provider] ?? status.provider;

  return (
    <Link
      to="/config"
      className={[
        "shrink-0 w-full",
        "flex items-center gap-2 px-3 h-7",
        "border-t border-border bg-muted/80 backdrop-blur-sm",
        "text-xs text-muted-foreground hover:text-foreground",
        "transition-colors select-none",
      ].join(" ")}
      title="Click to open Configuration"
    >
      <span
        className={[
          "rounded px-1.5 py-0.5 font-medium text-[11px]",
          status.provider === "openai"
            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
            : "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
        ].join(" ")}
      >
        {providerLabel}
      </span>
      <span className="font-mono">{status.model}</span>
    </Link>
  );
}
