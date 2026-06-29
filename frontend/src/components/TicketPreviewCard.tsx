import { Button } from "@/components/ui/button";
import type { IntakeState } from "@/api/intake";

interface TicketPreviewCardProps {
  preview: NonNullable<IntakeState["ticketPreview"]>;
  onConfirm: () => void;
  onCancel: () => void;
  disabled?: boolean;
}

export function TicketPreviewCard({
  preview,
  onConfirm,
  onCancel,
  disabled,
}: TicketPreviewCardProps) {
  return (
    <div className="rounded-lg border border-amber-500/40 bg-amber-50/50 dark:bg-amber-950/20 p-4 my-2">
      <p className="text-sm font-semibold text-amber-900 dark:text-amber-100 mb-3">
        Ticket Preview
      </p>
      <dl className="text-sm space-y-2 mb-4">
        <div>
          <dt className="text-muted-foreground text-xs">Summary</dt>
          <dd className="font-medium">{preview.summary}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground text-xs">Issue type</dt>
          <dd>{preview.issue_type}</dd>
        </div>
        {preview.time_estimate && (
          <div>
            <dt className="text-muted-foreground text-xs">Rough estimate</dt>
            <dd>{preview.time_estimate}</dd>
          </div>
        )}
        {preview.environment && (
          <div>
            <dt className="text-muted-foreground text-xs">Environment</dt>
            <dd>{preview.environment}</dd>
          </div>
        )}
        <div>
          <dt className="text-muted-foreground text-xs">Description</dt>
          <dd className="whitespace-pre-wrap text-xs max-h-40 overflow-y-auto">
            {preview.description}
          </dd>
        </div>
      </dl>
      <div className="flex gap-2">
        <Button size="sm" onClick={onConfirm} disabled={disabled}>
          Confirm & {preview.issue_type === "Story" ? "Create Story" : "Create Bug"}
        </Button>
        <Button size="sm" variant="outline" onClick={onCancel} disabled={disabled}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
