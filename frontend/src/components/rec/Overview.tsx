import { Bar, Card, Dot, Label, Square } from "./primitives";
import { EmptyState } from "./EmptyState";
import { useRecEngine } from "@/context/RecEngineContext";
import { statusMeta } from "@/lib/rec-data";

function Metric({ label, value, subtitle }: { label: string; value: string; subtitle?: string }) {
  return (
    <Card className="p-4">
      <Label>{label}</Label>
      <div className="mt-3 font-mono text-3xl font-semibold tracking-tight text-foreground">{value}</div>
      {subtitle && <div className="mt-1 text-xs text-text-tertiary">{subtitle}</div>}
    </Card>
  );
}

export function Overview() {
  const { ideas, hasResults, pipeline, dataSummary, isRunning } = useRecEngine();

  const s3 = dataSummary?.s3;
  const interviewsS3 = s3?.interviews_json_count ?? 0;
  const communityHardcoded = dataSummary?.config.community_source === "fixtures";
  const communityS3 = s3?.community_json_count ?? 0;
  const marketS3 = s3?.market_bronze_file_count ?? s3?.gold_trend_signals_json_count ?? 0;

  const interviews =
    pipeline.interviews_loaded > 0 ? pipeline.interviews_loaded : interviewsS3;
  const community = pipeline.community_loaded > 0
    ? pipeline.community_loaded
    : communityHardcoded
      ? 4
      : communityS3;
  const trends = pipeline.trends_loaded > 0 ? pipeline.trends_loaded : marketS3;
  const totalSignals = interviews + community + trends;

  const ranked = [...ideas].map((i) => ({ ...i, score: i.score ?? 0 })).sort((a, b) => b.score - a.score);
  const top3 = ranked.slice(0, 3);
  const avg = ranked.length ? ranked.reduce((s, i) => s + i.score, 0) / ranked.length : 0;

  if (!hasResults && !isRunning) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Overview</h1>
          <p className="text-xs text-text-secondary">
            S3 interviews & market trends; community uses curated fixture posts until S3 community exists.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Metric label="Interviews (S3)" value={String(interviews)} subtitle="bronze/interviews" />
          <Metric
            label="Community"
            value={String(community)}
            subtitle={communityHardcoded ? "curated fixtures" : "S3"}
          />
          <Metric label="Market signals" value={String(trends)} subtitle="gold or bronze trends" />
        </div>
        <EmptyState
          title="No ranked missions yet"
          description="Run Ranking to process live S3 data through the LangGraph pipeline. The dashboard only shows engine output, not placeholder ideas."
        />
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Overview</h1>
        <p className="text-xs text-text-secondary">
          {isRunning
            ? pipeline.message
            : `${pipeline.missions_count} ranked missions · ${totalSignals} input signals`}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Input signals" value={String(totalSignals)} subtitle="interviews + community + trends" />
        <Metric label="Ranked missions" value={String(ideas.length)} subtitle="from last successful run" />
        <Metric label="Interviews" value={String(interviews)} />
        <Metric label="Avg score" value={avg.toFixed(1)} subtitle="final_score × 100" />
      </div>

      {hasResults && (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <Label>Top ranked</Label>
              <span className="text-[10px] text-text-tertiary">Engine score</span>
            </div>
            <ul className="mt-3 divide-y divide-border">
              {top3.map((i, idx) => {
                const meta = statusMeta[i.status];
                return (
                  <li key={i.id} className="flex items-center gap-3 py-2.5">
                    <span className="w-5 font-mono text-sm text-text-tertiary">{idx + 1}</span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm text-foreground">{i.title}</div>
                      <div className="mt-0.5 flex items-center gap-1.5">
                        <Dot className={meta.dot} />
                        <span className="text-[11px] text-text-secondary">{meta.label}</span>
                      </div>
                    </div>
                    <span className="font-mono text-sm font-semibold tabular-nums text-foreground">
                      {i.score.toFixed(1)}
                    </span>
                  </li>
                );
              })}
            </ul>
          </Card>

          <Card className="p-4">
            <Label>S3 inputs (last run)</Label>
            <ul className="mt-3 space-y-2.5">
              <li className="flex items-center gap-3">
                <Square className="bg-brand-blue" />
                <span className="flex-1 text-sm text-foreground">Interviews</span>
                <span className="font-mono text-sm tabular-nums text-text-secondary">{interviews}</span>
              </li>
              <li className="flex items-center gap-3">
                <Square className="bg-brand-amber" />
                <span className="flex-1 text-sm text-foreground">
                  Community{communityHardcoded ? " (curated)" : ""}
                </span>
                <span className="font-mono text-sm tabular-nums text-text-secondary">{community}</span>
              </li>
              <li className="flex items-center gap-3">
                <Square className="bg-brand-green" />
                <span className="flex-1 text-sm text-foreground">Market trends</span>
                <span className="font-mono text-sm tabular-nums text-text-secondary">{trends}</span>
              </li>
            </ul>
          </Card>
        </div>
      )}
    </div>
  );
}
