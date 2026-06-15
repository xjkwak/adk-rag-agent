import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Send } from "lucide-react";
import { AudioInput } from "@/components/AudioInput";

interface IntakeInputFormProps {
  onSubmit: (message: string) => void;
  isLoading: boolean;
}

export function IntakeInputForm({ onSubmit, isLoading }: IntakeInputFormProps) {
  const [inputValue, setInputValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading) {
      onSubmit(inputValue.trim());
      setInputValue("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleTranscript = useCallback(
    (transcript: string) => {
      onSubmit(transcript);
    },
    [onSubmit],
  );

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <AudioInput onTranscriptConfirmed={handleTranscript} disabled={isLoading} />
      <div className="flex items-end space-x-3">
        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your issue or question…"
            rows={2}
            disabled={isLoading}
            className="flex-1 resize-none min-h-[48px] rounded-xl border-border bg-background/80"
          />
        </div>
        <Button
          type="submit"
          size="icon"
          disabled={isLoading || !inputValue.trim()}
          className="w-10 h-10 rounded-full shrink-0"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    </form>
  );
}
