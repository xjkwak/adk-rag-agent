import { ExternalLink } from "lucide-react";

interface JiraCreatedBannerProps {
  issueKey: string;
  issueUrl: string;
}

export function JiraCreatedBanner({ issueKey, issueUrl }: JiraCreatedBannerProps) {
  return (
    <div className="rounded-lg border border-blue-500/40 bg-blue-50/50 dark:bg-blue-950/20 p-4 my-2">
      <p className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-1">
        Ticket Created
      </p>
      <a
        href={issueUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-blue-600 hover:underline font-medium"
      >
        {issueKey}
        <ExternalLink className="h-3 w-3" />
      </a>
    </div>
  );
}
