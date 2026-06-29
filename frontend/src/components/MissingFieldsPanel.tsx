import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export interface FieldOption {
  value: string;
  label: string;
}

export interface MissingFieldsPanelProps {
  awaitingFields: string[];
  fieldOptions?: Record<string, FieldOption[]>;
  onSubmit: (message: string) => void;
  disabled?: boolean;
}

const FIELD_LABELS: Record<string, string> = {
  system: "System / module",
  module: "Module",
  environment: "Environment",
  identifier: "Invoice / record ID",
  actual_behavior: "What is happening",
  description: "Description",
  business_impact: "Business impact",
  summary: "Summary",
};

/** Labels used when submitting — must match backend parser aliases. */
const FIELD_SUBMIT_LABELS: Record<string, string> = {
  system: "System",
  module: "Module",
  environment: "Environment",
  identifier: "Invoice",
  actual_behavior: "Actual behavior",
  description: "Description",
  business_impact: "Business impact",
  summary: "Summary",
};

export function MissingFieldsPanel({
  awaitingFields,
  fieldOptions = {},
  onSubmit,
  disabled,
}: MissingFieldsPanelProps) {
  const [draft, setDraft] = useState<Record<string, string>>({});

  if (!awaitingFields.length) return null;

  const setDraftField = (field: string, value: string) => {
    setDraft((prev) => ({ ...prev, [field]: value }));
  };

  const handleQuickPick = (field: string, value: string) => {
    setDraftField(field, value);
  };

  const handleSubmitAll = () => {
    const lines: string[] = [];
    for (const field of awaitingFields) {
      const val = draft[field]?.trim();
      if (val) {
        const label = FIELD_SUBMIT_LABELS[field] ?? field;
        lines.push(`${label}: ${val}`);
      }
    }
    if (lines.length === 0) return;
    onSubmit(lines.join("\n"));
    setDraft({});
  };

  const canSubmit = awaitingFields.some((field) => draft[field]?.trim());

  return (
    <div className="my-2 rounded-lg border border-border bg-muted/30 p-4 space-y-4">
      <p className="text-sm font-medium">Provide missing details</p>
      <p className="text-xs text-muted-foreground">
        Fill in all fields below, or type everything in one message in the chat box.
      </p>

      {awaitingFields.map((field) => (
        <div key={field} className="space-y-2">
          <label className="text-xs text-muted-foreground">
            {FIELD_LABELS[field] ?? field}
          </label>

          {fieldOptions[field] && fieldOptions[field].length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {fieldOptions[field].map((opt) => (
                <Button
                  key={opt.value}
                  type="button"
                  size="sm"
                  variant={draft[field] === opt.value ? "default" : "outline"}
                  disabled={disabled}
                  onClick={() => handleQuickPick(field, opt.value)}
                >
                  {opt.label}
                </Button>
              ))}
            </div>
          ) : (
            <Input
              value={draft[field] ?? ""}
              onChange={(e) => setDraftField(field, e.target.value)}
              disabled={disabled}
              placeholder={`Enter ${(FIELD_LABELS[field] ?? field).toLowerCase()}…`}
              className="h-9"
            />
          )}

          {fieldOptions[field] && fieldOptions[field].length > 0 && (
            <Input
              value={draft[field] ?? ""}
              onChange={(e) => setDraftField(field, e.target.value)}
              disabled={disabled}
              placeholder="Or type a custom value…"
              className="h-9"
            />
          )}
        </div>
      ))}

      <Button
        type="button"
        size="sm"
        disabled={disabled || !canSubmit}
        onClick={handleSubmitAll}
      >
        Submit all details
      </Button>
    </div>
  );
}
