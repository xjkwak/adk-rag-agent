import { Button } from "@/components/ui/button";
import { InputForm } from "@/components/InputForm";

interface WelcomeScreenProps {
  handleSubmit: (query: string) => void;
  isLoading: boolean;
  onCancel: () => void;
}

export function WelcomeScreen({
  handleSubmit,
  isLoading,
  onCancel,
}: WelcomeScreenProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-4 overflow-hidden relative">
      
      {/* Main card container with purple border */}
      <div className="w-full max-w-2xl z-10
                      bg-neutral-900/50 backdrop-blur-md 
                      p-8 rounded-2xl border border-purple-500/30 
                      shadow-2xl shadow-black/60 
                      transition-all duration-300">
        
        {/* Header section with Knowledge HUB title and star icons */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-purple-300 flex items-center justify-center gap-3">
          🧠 Knowledge HUB 1.0 🚀
          </h1>
          <p className="text-lg text-purple-200 max-w-md mx-auto">
            Turns your questions into comprehensive reports!
          </p>
        </div>

        {/* Input form section */}
        <div className="mt-8">
          <InputForm onSubmit={handleSubmit} isLoading={isLoading} context="homepage" />
          {isLoading && (
            <div className="mt-4 flex justify-center">
              <Button
                variant="outline"
                onClick={onCancel}
                className="text-red-400 hover:text-red-300 hover:bg-red-900/20 border-red-700/50"
              >
                Cancel
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}