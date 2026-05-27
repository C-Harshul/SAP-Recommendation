import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRecEngine } from "@/context/RecEngineContext";

interface Props {
  title: string;
  description: string;
  showRunButton?: boolean;
}

export function EmptyState({ title, description, showRunButton = true }: Props) {
  const { runRanking, isRunning } = useRecEngine();

  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card/50 px-6 py-16 text-center">
      <h2 className="text-base font-semibold text-foreground">{title}</h2>
      <p className="mt-2 max-w-md text-sm text-text-secondary">{description}</p>
      {showRunButton && (
        <Button
          className="mt-6 gap-2 bg-sap-amber text-sap-navy hover:bg-sap-amber/90"
          onClick={() => void runRanking()}
          disabled={isRunning}
        >
          <Play className="h-4 w-4" />
          {isRunning ? "Ranking in progress…" : "Run Ranking"}
        </Button>
      )}
    </div>
  );
}
