import { Button } from "@/components/ui/button";

interface SolutionFeedbackProps {
  onYes: () => void;
  onNo: () => void;
  disabled?: boolean;
}

export function SolutionFeedback({ onYes, onNo, disabled }: SolutionFeedbackProps) {
  return (
    <div className="flex items-center gap-2 my-2 p-3 rounded-lg border border-border bg-muted/30">
      <span className="text-sm text-muted-foreground mr-2">Did this resolve your issue?</span>
      <Button size="sm" onClick={onYes} disabled={disabled}>
        Yes
      </Button>
      <Button size="sm" variant="outline" onClick={onNo} disabled={disabled}>
        No, create ticket
      </Button>
    </div>
  );
}
