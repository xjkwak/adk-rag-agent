import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  ROUTE_LABELS,
  ROLE_LABELS,
  type EvalCaseResult,
  type EvalScenarioSummary,
} from "@/api/evals";
import { cn } from "@/utils";

interface EvalScenarioTableProps {
  scenarios: EvalScenarioSummary[];
  cases: EvalCaseResult[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onRunOne: (id: string) => void;
  runningId: string | null;
  filterRole: string;
  filterRoute: string;
  filterStatus: string;
}

export function EvalScenarioTable({
  scenarios,
  cases,
  selectedId,
  onSelect,
  onRunOne,
  runningId,
  filterRole,
  filterRoute,
  filterStatus,
}: EvalScenarioTableProps) {
  const caseMap = new Map(cases.map((item) => [item.id, item]));

  const rows = scenarios.filter((scenario) => {
    if (filterRole !== "all" && scenario.role !== filterRole) return false;
    if (filterRoute !== "all" && scenario.expectedRoute !== filterRoute) {
      return false;
    }
    const result = caseMap.get(scenario.id);
    if (filterStatus === "passed" && !result?.passed) return false;
    if (filterStatus === "failed" && (!result || result.passed)) return false;
    if (filterStatus === "pending" && result) return false;
    return true;
  });

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-left">
          <tr>
            <th className="px-3 py-2 font-medium">ID</th>
            <th className="px-3 py-2 font-medium">Role</th>
            <th className="px-3 py-2 font-medium">Scenario</th>
            <th className="px-3 py-2 font-medium">Expected</th>
            <th className="px-3 py-2 font-medium">Actual</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 font-medium w-24" />
          </tr>
        </thead>
        <tbody>
          {rows.map((scenario) => {
            const result = caseMap.get(scenario.id);
            const actualRoute =
              typeof result?.actual?.route === "string"
                ? result.actual.route
                : "—";
            return (
              <tr
                key={scenario.id}
                className={cn(
                  "border-t border-border/60 cursor-pointer hover:bg-muted/30",
                  selectedId === scenario.id && "bg-muted/50",
                )}
                onClick={() => onSelect(scenario.id)}
              >
                <td className="px-3 py-2 font-mono">{scenario.id}</td>
                <td className="px-3 py-2">
                  {ROLE_LABELS[scenario.role] ?? scenario.role}
                </td>
                <td className="px-3 py-2">{scenario.title}</td>
                <td className="px-3 py-2">
                  {ROUTE_LABELS[scenario.expectedRoute] ?? scenario.expectedRoute}
                </td>
                <td className="px-3 py-2">
                  {ROUTE_LABELS[actualRoute] ?? actualRoute}
                </td>
                <td className="px-3 py-2">
                  <StatusBadge result={result} />
                </td>
                <td className="px-3 py-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={runningId !== null}
                    onClick={(event) => {
                      event.stopPropagation();
                      onRunOne(scenario.id);
                    }}
                  >
                    <Play className="h-3.5 w-3.5 mr-1" />
                    Run
                  </Button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function StatusBadge({ result }: { result?: EvalCaseResult }) {
  if (!result) {
    return (
      <span className="inline-flex rounded-full bg-muted px-2 py-0.5 text-xs">
        Pending
      </span>
    );
  }
  if (result.skipped) {
    return (
      <span className="inline-flex rounded-full bg-amber-500/15 text-amber-700 dark:text-amber-300 px-2 py-0.5 text-xs">
        Skipped
      </span>
    );
  }
  if (result.passed) {
    return (
      <span className="inline-flex rounded-full bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 px-2 py-0.5 text-xs">
        Pass
      </span>
    );
  }
  return (
    <span className="inline-flex rounded-full bg-red-500/15 text-red-700 dark:text-red-300 px-2 py-0.5 text-xs">
      Fail
    </span>
  );
}
