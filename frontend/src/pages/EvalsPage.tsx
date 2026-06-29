import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, Play, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CollapsibleSection } from "@/components/CollapsibleSection";
import { EvalRunSummary } from "@/components/evals/EvalRunSummary";
import { EvalScenarioTable } from "@/components/evals/EvalScenarioTable";
import { EvalCaseDetail } from "@/components/evals/EvalCaseDetail";
import {
  fetchEvalScenario,
  fetchEvalScenarios,
  runEvals,
  ROLE_LABELS,
  ROUTE_LABELS,
  type EvalMode,
  type EvalRunResult,
  type EvalScenarioSummary,
} from "@/api/evals";

export default function EvalsPage() {
  const [scenarios, setScenarios] = useState<EvalScenarioSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<EvalMode>("integration");
  const [result, setResult] = useState<EvalRunResult | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [filterRole, setFilterRole] = useState("all");
  const [filterRoute, setFilterRoute] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");

  const loadScenarios = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEvalScenarios();
      setScenarios(data.scenarios);
      if (!selectedId && data.scenarios.length > 0) {
        setSelectedId(data.scenarios[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load scenarios");
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    void loadScenarios();
  }, [loadScenarios]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    void fetchEvalScenario(selectedId)
      .then(setDetail)
      .catch(() => setDetail(null));
  }, [selectedId]);

  const selectedScenario = useMemo(
    () => scenarios.find((item) => item.id === selectedId) ?? null,
    [scenarios, selectedId],
  );

  const selectedCase = useMemo(
    () => result?.cases.find((item) => item.id === selectedId) ?? null,
    [result, selectedId],
  );

  const handleRunAll = async () => {
    setRunning(true);
    setError(null);
    try {
      const run = await runEvals(mode);
      setResult(run);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eval run failed");
    } finally {
      setRunning(false);
    }
  };

  const handleRunOne = async (id: string) => {
    setRunningId(id);
    setError(null);
    try {
      const run = await runEvals(mode, [id]);
      setResult((prev) => {
        if (!prev) return run;
        const merged = new Map(prev.cases.map((item) => [item.id, item]));
        for (const item of run.cases) {
          merged.set(item.id, item);
        }
        return {
          ...run,
          cases: scenarios
            .map((scenario) => merged.get(scenario.id))
            .filter((item): item is NonNullable<typeof item> => Boolean(item)),
          summary: {
            total: scenarios.length,
            passed: [...merged.values()].filter((item) => item.passed).length,
            failed: [...merged.values()].filter(
              (item) => !item.passed && !item.skipped,
            ).length,
            skipped: [...merged.values()].filter((item) => item.skipped).length,
          },
        };
      });
      setSelectedId(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eval run failed");
    } finally {
      setRunningId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />
        Loading eval scenarios…
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6 space-y-4">
      <CollapsibleSection
        title="Support Intake Evals"
        description="Amtech Testing Framework — 25 scenarios across entity extraction, routing, and response quality"
        defaultOpen
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Select
              value={mode}
              onValueChange={(value) => setMode(value as EvalMode)}
            >
              <SelectTrigger className="w-[160px] h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fast">Fast (heuristics)</SelectItem>
                <SelectItem value="integration">Integration (mocked KB)</SelectItem>
                <SelectItem value="live">Live (LLM + KB)</SelectItem>
              </SelectContent>
            </Select>
            <Button
              type="button"
              size="sm"
              onClick={() => void handleRunAll()}
              disabled={running || runningId !== null}
            >
              {running ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1" />
              ) : (
                <Play className="h-4 w-4 mr-1" />
              )}
              Run all
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => void loadScenarios()}
            >
              <RefreshCw className="h-4 w-4 mr-1" />
              Refresh
            </Button>
          </div>
        }
      >
        <div className="flex flex-wrap gap-2">
          <FilterSelect
            label="Role"
            value={filterRole}
            onChange={setFilterRole}
            options={[
              { value: "all", label: "All roles" },
              ...Object.entries(ROLE_LABELS).map(([value, label]) => ({
                value,
                label,
              })),
            ]}
          />
          <FilterSelect
            label="Route"
            value={filterRoute}
            onChange={setFilterRoute}
            options={[
              { value: "all", label: "All routes" },
              ...Object.entries(ROUTE_LABELS).map(([value, label]) => ({
                value,
                label,
              })),
            ]}
          />
          <FilterSelect
            label="Status"
            value={filterStatus}
            onChange={setFilterStatus}
            options={[
              { value: "all", label: "All statuses" },
              { value: "passed", label: "Passed" },
              { value: "failed", label: "Failed" },
              { value: "pending", label: "Pending" },
            ]}
          />
        </div>
      </CollapsibleSection>

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400 rounded-md border border-red-500/30 bg-red-500/5 p-3">
          {error}
        </p>
      )}

      <EvalRunSummary result={result} running={running} />

      <CollapsibleSection
        title="Scenarios"
        description={`${scenarios.length} cases from the CoderoadERP Testing Framework`}
        defaultOpen
      >
        <EvalScenarioTable
          scenarios={scenarios}
          cases={result?.cases ?? []}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onRunOne={(id) => void handleRunOne(id)}
          runningId={runningId}
          filterRole={filterRole}
          filterRoute={filterRoute}
          filterStatus={filterStatus}
        />
      </CollapsibleSection>

      <EvalCaseDetail
        scenario={selectedScenario}
        detail={detail}
        caseResult={selectedCase}
      />
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-[180px] h-8">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
