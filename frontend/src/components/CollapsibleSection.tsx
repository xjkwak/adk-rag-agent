import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/utils";

interface CollapsibleSectionProps {
  title: string;
  description?: string;
  defaultOpen?: boolean;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function CollapsibleSection({
  title,
  description,
  defaultOpen = true,
  actions,
  children,
  className,
}: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const sectionId = title.toLowerCase().replace(/\s+/g, "-");

  return (
    <section
      className={cn(
        "rounded-xl border border-border bg-card/50 overflow-hidden",
        className,
      )}
    >
      <div className="flex items-start gap-2 p-4 md:px-6 md:py-4 border-b border-border/60">
        <button
          type="button"
          className="flex flex-1 min-w-0 items-start gap-3 text-left"
          aria-expanded={open}
          aria-controls={`${sectionId}-content`}
          onClick={() => setOpen((value) => !value)}
        >
          <ChevronDown
            className={cn(
              "h-5 w-5 shrink-0 mt-0.5 text-muted-foreground transition-transform",
              open && "rotate-180",
            )}
          />
          <span className="min-w-0">
            <span className="block text-lg font-semibold">{title}</span>
            {description && (
              <span className="block text-sm text-muted-foreground mt-1">
                {description}
              </span>
            )}
          </span>
        </button>
        {actions && (
          <div
            className="flex shrink-0 flex-wrap items-center gap-2"
            onClick={(e) => e.stopPropagation()}
          >
            {actions}
          </div>
        )}
      </div>
      {open && (
        <div
          id={`${sectionId}-content`}
          className="space-y-4 p-4 md:p-6 pt-4"
        >
          {children}
        </div>
      )}
    </section>
  );
}
