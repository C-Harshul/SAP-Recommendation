import {
  AlertCircle,
  CheckCircle2,
  Circle,
  Loader2,
  Play,
  SkipForward,
} from "lucide-react";
import { useRecEngine } from "@/context/RecEngineContext";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import {
  GRAPH_STEP_IDS,
  PREP_STEP_IDS,
  stepStatusColor,
  type PipelineStep,
  type StepStatus,
} from "@/lib/pipeline-graph";
import type { PipelineState } from "@/lib/api";

function StepIcon({ status }: { status: StepStatus }) {
  const cls = "h-4 w-4 shrink-0";
  switch (status) {
    case "running":
      return <Loader2 className={cn(cls, "animate-spin text-sap-amber")} />;
    case "completed":
      return <CheckCircle2 className={cn(cls, "text-emerald-600")} />;
    case "failed":
      return <AlertCircle className={cn(cls, "text-destructive")} />;
    case "skipped":
      return <SkipForward className={cn(cls, "text-text-tertiary")} />;
    default:
      return <Circle className={cn(cls, "text-text-tertiary")} />;
  }
}

function StepNode({ step, compact }: { step: PipelineStep; compact?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-lg border px-3 py-2 transition-all",
        stepStatusColor(step.status),
        compact ? "min-w-[120px]" : "min-w-[140px]",
        step.status === "running" && "ring-2 ring-sap-amber/40 shadow-sm",
      )}
    >
      <div className="flex items-start gap-2">
        <StepIcon status={step.status} />
        <div className="min-w-0">
          <div className="text-xs font-semibold leading-tight">{step.label}</div>
          {!compact && step.detail && (
            <p className="mt-0.5 text-[10px] leading-snug text-text-secondary">{step.detail}</p>
          )}
        </div>
      </div>
    </div>
  );
}

function Arrow() {
  return (
    <div className="flex shrink-0 items-center px-1 text-text-tertiary" aria-hidden>
      <svg width="28" height="12" viewBox="0 0 28 12" className="opacity-60">
        <path d="M0 6h20M20 6l-6-5M20 6l-6 5" stroke="currentColor" strokeWidth="1.5" fill="none" />
      </svg>
    </div>
  );
}

function GraphFlow({ steps }: { steps: PipelineStep[] }) {
  const byId = Object.fromEntries(steps.map((s) => [s.id, s]));
  const graphSteps = GRAPH_STEP_IDS.map((id) => byId[id]).filter(Boolean) as PipelineStep[];

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex min-w-max items-center">
        {graphSteps.map((step, i) => (
          <div key={step.id} className="flex items-center">
            <StepNode step={step} />
            {i < graphSteps.length - 1 && <Arrow />}
          </div>
        ))}
      </div>
    </div>
  );
}

function PrepColumn({ steps }: { steps: PipelineStep[] }) {
  const byId = Object.fromEntries(steps.map((s) => [s.id, s]));
  const prep = PREP_STEP_IDS.map((id) => byId[id]).filter(Boolean) as PipelineStep[];

  return (
    <div className="flex flex-col gap-2">
      {prep.map((step, i) => (
        <div key={step.id} className="flex items-center gap-2">
          {i > 0 && (
            <div className="absolute left-[27px] hidden h-4 w-px bg-border md:block" />
          )}
          <StepNode step={step} compact />
        </div>
      ))}
    </div>
  );
}

function statusBanner(pipeline: PipelineState) {
  if (pipeline.status === "running") {
    return {
      label: "Ranking in progress",
      tone: "text-sap-amber",
    };
  }
  if (pipeline.status === "completed") {
    return { label: "Last run completed", tone: "text-emerald-600" };
  }
  if (pipeline.status === "failed") {
    return { label: "Last run failed", tone: "text-destructive" };
  }
  return { label: "Ready to run", tone: "text-text-secondary" };
}

export function RankingRun() {
  const { pipeline, isRunning, runRanking, apiConnected } = useRecEngine();
  const steps = pipeline.steps ?? [];
  const percent = pipeline.progress_percent ?? 0;
  const banner = statusBanner(pipeline);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Ranking Run</h1>
          <p className="text-xs text-text-secondary">
            Live LangGraph pipeline — prep steps, then extract through persist.
          </p>
        </div>
        <Button
          size="sm"
          className="gap-1.5 bg-sap-amber text-sap-navy hover:bg-sap-amber/90"
          onClick={() => void runRanking()}
          disabled={isRunning || !apiConnected}
        >
          {isRunning ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          {isRunning ? "Running…" : "Run Ranking"}
        </Button>
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className={cn("text-sm font-medium", banner.tone)}>{banner.label}</span>
          <span className="font-mono text-xs text-text-secondary">{percent}%</span>
        </div>
        <Progress value={percent} className="mt-3 h-2" />
        <p className="mt-2 text-xs text-text-secondary">{pipeline.message}</p>
        {pipeline.error && (
          <p className="mt-2 rounded border border-destructive/30 bg-destructive/5 px-2 py-1.5 text-xs text-destructive">
            {pipeline.error}
          </p>
        )}
        {(pipeline.interviews_loaded > 0 || pipeline.trends_loaded > 0) && (
          <p className="mt-2 font-mono text-[11px] text-text-tertiary">
            {pipeline.interviews_loaded} interviews · {pipeline.community_loaded} community ·{" "}
            {pipeline.trends_loaded} trends
            {pipeline.missions_count > 0 ? ` · ${pipeline.missions_count} missions` : ""}
          </p>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[200px_1fr]">
        <div>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-secondary">
            Preparation
          </h2>
          <PrepColumn steps={steps} />
        </div>

        <div className="min-w-0">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-secondary">
            LangGraph workflow
          </h2>
          <div className="rounded-lg border border-dashed border-border bg-muted/20 p-4">
            <div className="mb-3 flex items-center gap-2 text-[10px] text-text-tertiary">
              <span className="rounded bg-background px-1.5 py-0.5 font-mono">START</span>
              <Arrow />
              <span className="text-text-secondary">linear graph (7 nodes)</span>
              <Arrow />
              <span className="rounded bg-background px-1.5 py-0.5 font-mono">END</span>
            </div>
            <GraphFlow steps={steps} />
          </div>

          <div className="mt-4 hidden md:block">
            <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-text-tertiary">
              Topology
            </h3>
            <pre className="overflow-x-auto rounded border border-border bg-background p-3 font-mono text-[10px] leading-relaxed text-text-secondary">
{`START → extract → synthesize → cluster → match_trends → rank → writeup → persist → END`}
            </pre>
          </div>
        </div>
      </div>

      <div>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-secondary">
          Step log
        </h2>
        <ul className="divide-y divide-border rounded-lg border border-border bg-card">
          {steps.length === 0 ? (
            <li className="px-4 py-6 text-center text-xs text-text-tertiary">
              Start a ranking run to see step-by-step progress.
            </li>
          ) : (
            steps.map((step) => (
              <li
                key={step.id}
                className={cn(
                  "flex items-center gap-3 px-4 py-2.5 text-sm",
                  step.status === "running" && "bg-sap-amber/5",
                )}
              >
                <StepIcon status={step.status} />
                <span className="flex-1 font-medium">{step.label}</span>
                <span className="font-mono text-[10px] uppercase text-text-tertiary">
                  {step.phase}
                </span>
                <span className="w-20 text-right text-xs capitalize text-text-secondary">
                  {step.status}
                </span>
                {step.detail && (
                  <span className="hidden max-w-[240px] truncate text-xs text-text-tertiary lg:inline">
                    {step.detail}
                  </span>
                )}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
