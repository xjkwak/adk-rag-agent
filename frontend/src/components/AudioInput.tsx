import { useState, useRef, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Mic, Square, Upload, Loader2 } from "lucide-react";
import { transcribeAudio } from "@/api/intake";

interface AudioInputProps {
  onTranscriptConfirmed: (transcript: string) => void;
  disabled?: boolean;
}

export function AudioInput({ onTranscriptConfirmed, disabled }: AudioInputProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const transcriptRef = useRef<HTMLTextAreaElement>(null);
  const wasTranscribingRef = useRef(false);

  useEffect(() => {
    if (wasTranscribingRef.current && !isTranscribing && transcript) {
      requestAnimationFrame(() => {
        transcriptRef.current?.focus();
        const len = transcript.length;
        transcriptRef.current?.setSelectionRange(len, len);
      });
    }
    wasTranscribingRef.current = isTranscribing;
  }, [isTranscribing, transcript]);

  const processBlob = useCallback(async (blob: Blob, mimeType: string) => {
    setIsTranscribing(true);
    setError(null);
    try {
      const text = await transcribeAudio(blob, mimeType);
      setTranscript(text);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Transcription failed");
    } finally {
      setIsTranscribing(false);
    }
  }, []);

  const startRecording = async () => {
    setError(null);
    setTranscript(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/mp4";
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: mimeType });
        void processBlob(blob, mimeType);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      setError("Microphone access denied or not available.");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setTranscript(null);
    setError(null);
    void processBlob(file, file.type || "audio/mpeg");
    e.target.value = "";
  };

  const confirmTranscript = () => {
    if (transcript?.trim()) {
      onTranscriptConfirmed(transcript.trim());
      setTranscript(null);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        {!isRecording ? (
          <Button
            type="button"
            variant="outline"
            size="icon"
            disabled={disabled || isTranscribing}
            onClick={() => void startRecording()}
            title="Record audio"
            className="h-9 w-9 shrink-0"
          >
            <Mic className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            type="button"
            variant="destructive"
            size="icon"
            onClick={stopRecording}
            title="Stop recording"
            className="h-9 w-9 shrink-0"
          >
            <Square className="h-4 w-4" />
          </Button>
        )}
        <Button
          type="button"
          variant="outline"
          size="icon"
          disabled={disabled || isTranscribing}
          onClick={() => fileInputRef.current?.click()}
          title="Upload audio file"
          className="h-9 w-9 shrink-0"
        >
          <Upload className="h-4 w-4" />
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          className="hidden"
          onChange={handleFileUpload}
        />
        {isTranscribing && (
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Loader2 className="h-3 w-3 animate-spin" /> Transcribing…
          </span>
        )}
        {isRecording && (
          <span className="text-xs text-red-500 animate-pulse">Recording…</span>
        )}
      </div>

      {error && <p className="text-xs text-destructive">{error}</p>}

      {transcript !== null && (
        <div className="rounded-lg border border-border bg-muted/40 p-3 text-sm">
          <p className="font-medium text-xs text-muted-foreground mb-1">
            Transcript — edit if needed before sending
          </p>
          <Textarea
            ref={transcriptRef}
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            rows={3}
            disabled={disabled}
            className="mb-2 min-h-[72px] resize-y bg-background/80 text-sm"
            aria-label="Edit transcript"
          />
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              onClick={confirmTranscript}
              disabled={disabled || !transcript.trim()}
            >
              Send
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setTranscript(null)}
              disabled={disabled}
            >
              Discard
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
