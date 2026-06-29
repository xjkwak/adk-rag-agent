const API_BASE = "/api/hub/intake";

export type EvalMode = "fast" | "integration" | "live";

export interface EvalScenarioSummary {
  id: string;
  role: string;
  title: string;
  expectedRoute: string;
  modality: string;
}

export interface EvalCheck {
  name: string;
  expected: unknown;
  actual: unknown;
  passed: boolean;
  skipped: boolean;
  message?: string | null;
}

export interface EvalCaseResult {
  id: string;
  passed: boolean;
  skipped: boolean;
  error?: string | null;
  checks: EvalCheck[];
  actual: Record<string, unknown>;
}

export interface EvalRunResult {
  runId: string;
  mode: EvalMode;
  startedAt: string;
  durationMs: number;
  summary: {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
  };
  cases: EvalCaseResult[];
}

export async function fetchEvalScenarios(): Promise<{
  total: number;
  scenarios: EvalScenarioSummary[];
}> {
  const res = await fetch(`${API_BASE}/evals/scenarios`);
  if (!res.ok) {
    throw new Error(`Failed to load scenarios (${res.status})`);
  }
  return res.json();
}

export async function fetchEvalScenario(id: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/evals/scenarios/${encodeURIComponent(id)}`);
  if (!res.ok) {
    throw new Error(`Failed to load scenario ${id}`);
  }
  return res.json();
}

export async function runEvals(
  mode: EvalMode,
  scenarioIds?: string[],
): Promise<EvalRunResult> {
  const res = await fetch(`${API_BASE}/evals/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, scenario_ids: scenarioIds }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Eval run failed (${res.status})`);
  }
  return res.json();
}

export const ROLE_LABELS: Record<string, string> = {
  plant_operator: "Plant Operator",
  billing_clerk: "Billing Clerk",
  logistics_manager: "Logistics Manager",
  it_administrator: "IT Administrator",
  sales_manager: "Sales Manager",
};

export const ROUTE_LABELS: Record<string, string> = {
  route_a: "Route A (KB)",
  route_b: "Route B (Ticket)",
  ask_missing: "Ask (Missing Info)",
};
