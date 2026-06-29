import { CollapsibleSection } from "@/components/CollapsibleSection";
import type { EvalRunResult } from "@/api/evals";

interface EvalRunSummaryProps {
  result: EvalRunResult | null;
  running: boolean;
}

export function EvalRunSummary({ result, running }: EvalRunSummaryProps) {
  const summary = result?.summary;
  const passRate =
    summary && summary.total > 0
      ? Math.round((summary.passed / summary.total) * 100)
      : null;

  return (
    <CollapsibleSection
      title="Run summary"
      description="Latest eval results across all scenarios"
      defaultOpen
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard label="Total" value={summary?.total ?? "—"} />
        <StatCard
          label="Passed"
          value={summary?.passed ?? "—"}
          tone="success"
        />
        <StatCard label="Failed" value={summary?.failed ?? "—"} tone="danger" />
        <StatCard label="Skipped" value={summary?.skipped ?? "—"} />
        <StatCard
          label="Duration"
          value={
            running
              ? "Running…"
              : result
                ? `${(result.durationMs / 1000).toFixed(1)}s`
                : "—"
          }
          hint={passRate !== null ? `${passRate}% pass rate` : undefined}
        />
      </div>
    </CollapsibleSection>
  );
}

function StatCard({
  label,
  value,
  tone,
  hint,
}: {
  label: string;
  value: string | number;
  tone?: "success" | "danger";
  hint?: string;
}) {
  const toneClass =
    tone === "success"
      ? "text-emerald-600 dark:text-emerald-400"
      : tone === "danger"
        ? "text-red-600 dark:text-red-400"
        : "text-foreground";

  return (
    <div className="rounded-lg border border-border bg-background/60 p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className={`mt-1 text-2xl font-semibold ${toneClass}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
