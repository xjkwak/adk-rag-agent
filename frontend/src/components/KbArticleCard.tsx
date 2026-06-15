import type { KbArticle } from "@/api/intake";
import { Badge } from "@/components/ui/badge";

interface KbArticleCardProps {
  articles: KbArticle[];
  kbAnswer?: string;
}

export function KbArticleCard({ articles, kbAnswer }: KbArticleCardProps) {
  if (!articles.length && !kbAnswer) return null;

  return (
    <div className="rounded-lg border border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/20 p-4 my-2">
      <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-200 mb-2">
        Knowledge Hub Solution
      </p>
      {articles.length > 0 && (
        <ul className="space-y-2 mb-2">
          {articles.map((a, i) => (
            <li key={i} className="text-xs">
              <Badge variant="outline" className="mr-2">
                {(a.score * 100).toFixed(0)}% match
              </Badge>
              <span className="font-medium">{a.sourceName}</span>
              {a.sourceUri && (
                <a
                  href={a.sourceUri}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-2 text-blue-600 hover:underline"
                >
                  View
                </a>
              )}
              <p className="text-muted-foreground mt-1 line-clamp-2">{a.excerpt}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
