import { Card } from "./primitives";
import { EmptyState } from "./EmptyState";
import { useRecEngine } from "@/context/RecEngineContext";

export function Signals() {
  const { dataSummary, hasResults, isRunning, pipeline } = useRecEngine();
  const s3 = dataSummary?.s3;

  const communityHardcoded = dataSummary?.config.community_source === "fixtures";
  const rows = [
    { label: "Interviews (S3)", count: s3?.interviews_json_count ?? 0, color: "bg-brand-blue" },
    {
      label: communityHardcoded ? "Community (curated)" : "Community (S3)",
      count: communityHardcoded ? 4 : (s3?.community_json_count ?? 0),
      color: "bg-brand-amber",
    },
    {
      label: "Market trends",
      count: s3?.gold_trend_signals_json_count ?? s3?.market_bronze_file_count ?? 0,
      color: "bg-brand-green",
    },
  ];

  return (
    <div className="space-y-4 animate-fade-in">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Signals</h1>
        <p className="text-xs text-text-secondary">
          S3 inventory for s3://{dataSummary?.bucket ?? "…"}. Community uses hardcoded fixture posts when configured.
        </p>
      </div>

      <Card className="p-4">
        <ul className="space-y-3">
          {rows.map((r) => (
            <li key={r.label} className="flex items-center justify-between border-b border-border pb-3 last:border-0 last:pb-0">
              <span className="text-sm text-foreground">{r.label}</span>
              <span className="font-mono text-sm tabular-nums text-text-secondary">{r.count} files</span>
            </li>
          ))}
        </ul>
        {pipeline.status === "completed" && (
          <p className="mt-4 text-xs text-text-secondary">
            Last run loaded {pipeline.interviews_loaded} interviews, {pipeline.community_loaded}{" "}
            community posts, {pipeline.trends_loaded} trends.
          </p>
        )}
      </Card>

      {!hasResults && (
        <EmptyState
          title={isRunning ? "Extracting signals…" : "Signal excerpts after ranking"}
          description="Individual quotes and themes appear in ranked mission writeups once the pipeline completes. Run Ranking to process live data."
          showRunButton={!isRunning}
        />
      )}
    </div>
  );
}
