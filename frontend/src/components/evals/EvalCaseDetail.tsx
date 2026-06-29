import { CollapsibleSection } from "@/components/CollapsibleSection";
import type { EvalCaseResult, EvalScenarioSummary } from "@/api/evals";
import { ROUTE_LABELS } from "@/api/evals";
import { cn } from "@/utils";

interface EvalCaseDetailProps {
  scenario: EvalScenarioSummary | null;
  detail: Record<string, unknown> | null;
  caseResult: EvalCaseResult | null;
}

export function EvalCaseDetail({
  scenario,
  detail,
  caseResult,
}: EvalCaseDetailProps) {
  if (!scenario) {
    return (
      <CollapsibleSection
        title="Scenario detail"
        description="Select a row to inspect checks and responses"
        defaultOpen
      >
        <p className="text-sm text-muted-foreground">
          No scenario selected.
        </p>
      </CollapsibleSection>
    );
  }

  const expected = (detail?.expected ?? {}) as Record<string, unknown>;
  const input = typeof detail?.input === "string" ? detail.input : "";
  const assistantMessage =
    typeof caseResult?.actual?.assistantMessage === "string"
      ? caseResult.actual.assistantMessage
      : null;

  return (
    <CollapsibleSection
      title={`Scenario ${scenario.id}`}
      description={scenario.title}
      defaultOpen
    >
      <div className="space-y-4 text-sm">
        <section>
          <h4 className="font-medium mb-1">User input</h4>
          <p className="rounded-md border border-border bg-muted/20 p-3 whitespace-pre-wrap">
            {input}
          </p>
        </section>

        <section className="grid gap-3 md:grid-cols-2">
          <FieldBlock
            title="Expected route"
            value={ROUTE_LABELS[scenario.expectedRoute] ?? scenario.expectedRoute}
          />
          <FieldBlock
            title="Actual route"
            value={
              typeof caseResult?.actual?.route === "string"
                ? ROUTE_LABELS[caseResult.actual.route] ?? caseResult.actual.route
                : "—"
            }
          />
        </section>

        <section>
          <h4 className="font-medium mb-2">Checks</h4>
          <ul className="space-y-1">
            {(caseResult?.checks ?? []).map((check) => (
              <li
                key={check.name}
                className={cn(
                  "rounded border px-2 py-1.5",
                  check.skipped && "border-border/60 text-muted-foreground",
                  !check.skipped && check.passed && "border-emerald-500/30",
                  !check.skipped && !check.passed && "border-red-500/30",
                )}
              >
                <span className="font-mono text-xs">{check.name}</span>
                <span className="mx-2 text-muted-foreground">→</span>
                <span>
                  {check.skipped
                    ? "skipped"
                    : check.passed
                      ? "pass"
                      : `fail (expected ${String(check.expected)}, got ${String(check.actual)})`}
                </span>
              </li>
            ))}
            {!caseResult && (
              <li className="text-muted-foreground">Run evals to see checks.</li>
            )}
          </ul>
        </section>

        {Boolean(expected.entities) && (
          <section>
            <h4 className="font-medium mb-2">Expected entities</h4>
            <pre className="rounded-md border border-border bg-muted/20 p-3 overflow-x-auto text-xs">
              {JSON.stringify(expected.entities, null, 2)}
            </pre>
          </section>
        )}

        {caseResult?.actual?.collectedFields != null && (
          <section>
            <h4 className="font-medium mb-2">Collected fields</h4>
            <pre className="rounded-md border border-border bg-muted/20 p-3 overflow-x-auto text-xs">
              {JSON.stringify(caseResult.actual.collectedFields, null, 2)}
            </pre>
          </section>
        )}

        {assistantMessage && (
          <section>
            <h4 className="font-medium mb-1">Assistant message</h4>
            <p className="rounded-md border border-border bg-muted/20 p-3 whitespace-pre-wrap max-h-64 overflow-y-auto">
              {assistantMessage}
            </p>
          </section>
        )}

        {caseResult?.error && (
          <p className="text-red-600 dark:text-red-400">{caseResult.error}</p>
        )}
      </div>
    </CollapsibleSection>
  );
}

function FieldBlock({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-md border border-border p-3">
      <p className="text-xs text-muted-foreground">{title}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}
