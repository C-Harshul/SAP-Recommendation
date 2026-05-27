export type StepStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export interface PipelineStep {
  id: string;
  label: string;
  phase: "prep" | "graph";
  status: StepStatus;
  detail?: string | null;
}

export interface PipelineGraphEdge {
  from: string;
  to: string;
}

export interface PipelineGraphMeta {
  nodes: { id: string; label: string }[];
  edges: PipelineGraphEdge[];
}

export const PREP_STEP_IDS = ["validate", "load", "embed"] as const;

export const GRAPH_STEP_IDS = [
  "extract",
  "synthesize",
  "cluster",
  "match_trends",
  "rank",
  "writeup",
  "persist",
] as const;

export function stepStatusColor(status: StepStatus): string {
  switch (status) {
    case "running":
      return "border-sap-amber bg-sap-amber/10 text-foreground";
    case "completed":
      return "border-emerald-500/60 bg-emerald-500/10 text-foreground";
    case "failed":
      return "border-destructive bg-destructive/10 text-destructive";
    case "skipped":
      return "border-border bg-muted/50 text-text-tertiary";
    default:
      return "border-border bg-card text-text-secondary";
  }
}
