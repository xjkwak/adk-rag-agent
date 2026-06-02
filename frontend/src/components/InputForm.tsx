import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, Send } from "lucide-react";

export type DetailLevel = "low" | "high";

interface InputFormProps {
  onSubmit: (query: string, detailLevel?: DetailLevel) => void;
  isLoading: boolean;
  context?: "homepage" | "chat";
}

export function InputForm({
  onSubmit,
  isLoading,
  context = "homepage",
}: InputFormProps) {
  const [inputValue, setInputValue] = useState("");
  const [detailLevel, setDetailLevel] = useState<DetailLevel>("low");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading) {
      onSubmit(inputValue.trim(), detailLevel);
      setInputValue("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const placeholderText =
    context === "chat"
      ? "Ask about compliance gaps, line clearance, work orders..."
      : "Ask the Oracle about SOPs, rules, or production code";

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <div className="flex items-center gap-2 text-xs text-purple-700/80 dark:text-purple-300/80">
        <span className="shrink-0">Detail</span>
        <Select
          value={detailLevel}
          onValueChange={(v) => setDetailLevel(v as DetailLevel)}
          disabled={isLoading}
        >
          <SelectTrigger
            size="sm"
            className="h-8 w-[120px] border-purple-500/30 bg-background/80 dark:bg-neutral-800/50 text-foreground dark:text-purple-100"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="low">Low</SelectItem>
            <SelectItem value="high">High</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="flex items-end space-x-3">
        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholderText}
            rows={1}
            className="flex-1 resize-none pr-10 min-h-[40px] rounded-xl border-purple-500/30 
                       bg-background/80 dark:bg-neutral-800/50 text-foreground dark:text-purple-100
                       placeholder:text-muted-foreground dark:placeholder:text-purple-300/60
                       focus:border-purple-400/50 focus:ring-purple-400/20"
          />
        </div>
        <Button
          type="submit"
          size="icon"
          disabled={isLoading || !inputValue.trim()}
          className="w-10 h-10 rounded-full border border-purple-500/30 bg-background/80 dark:bg-neutral-800/50 
                     hover:bg-purple-100 dark:hover:bg-purple-900/20 hover:border-purple-400/50
                     disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all duration-200"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin text-purple-700 dark:text-purple-300" />
          ) : (
            <Send className="h-4 w-4 text-purple-700 dark:text-purple-300" />
          )}
        </Button>
      </div>
    </form>
  );
}
