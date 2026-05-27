import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Bar, Card, Dot } from "./primitives";
import { EmptyState } from "./EmptyState";
import { MarkdownContent } from "./MarkdownContent";
import { useRecEngine } from "@/context/RecEngineContext";
import { statusMeta } from "@/lib/rec-data";

type SortKey = "score" | "impact" | "value" | "effort";

const sortOptions: { key: SortKey; label: string }[] = [
  { key: "score", label: "Score" },
  { key: "impact", label: "Impact" },
  { key: "value", label: "Value" },
  { key: "effort", label: "Effort" },
];

export function RankedIdeas() {
  const { ideas, hasResults, isRunning, pipeline } = useRecEngine();
  const [sort, setSort] = useState<SortKey>("score");
  const [expanded, setExpanded] = useState<string | null>(null);

  if (!hasResults) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Ranked Ideas</h1>
          <p className="text-xs text-text-secondary">
            Missions ranked from S3 interviews & market trends, plus curated community posts.
          </p>
        </div>
        <EmptyState
          title={isRunning ? "Ranking in progress" : "No ranked missions yet"}
          description={
            isRunning
              ? pipeline.message
              : "Run the pipeline to generate ranked missions from your live S3 data. Mock demo ideas are not shown."
          }
          showRunButton={!isRunning}
        />
      </div>
    );
  }

  const rows = [...ideas]
    .map((i) => ({ ...i, score: i.score ?? 0 }))
    .sort((a, b) => {
      if (sort === "effort") return a.effort - b.effort;
      return (b as Record<SortKey, number>)[sort] - (a as Record<SortKey, number>)[sort];
    });

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Ranked Ideas</h1>
          <p className="text-xs text-text-secondary">
            {ideas.length} missions from the recommendation engine (S3 + Gemini).
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="mr-1 text-[10px] uppercase tracking-wider text-text-tertiary">Sort</span>
          {sortOptions.map((o) => {
            const active = sort === o.key;
            return (
              <button
                key={o.key}
                onClick={() => setSort(o.key)}
                className={[
                  "rounded-md border px-2.5 py-1 text-xs transition-colors",
                  active
                    ? "border-foreground bg-foreground text-primary-foreground"
                    : "border-border bg-card text-text-secondary hover:text-foreground",
                ].join(" ")}
              >
                {o.label}
              </button>
            );
          })}
        </div>
      </div>

      <Card className="overflow-hidden">
        <div className="grid grid-cols-[40px_1fr_120px_120px_120px_80px_120px_24px] items-center gap-3 border-b border-border bg-background/60 px-4 py-2 text-[10px] font-medium uppercase tracking-wider text-text-tertiary">
          <div>#</div>
          <div>Idea</div>
          <div>Impact</div>
          <div>Effort</div>
          <div>Value</div>
          <div>Score</div>
          <div>Status</div>
          <div />
        </div>
        <ul>
          {rows.map((i, idx) => {
            const meta = statusMeta[i.status];
            const isOpen = expanded === i.id;
            return (
              <li key={i.id} className="border-b border-border last:border-0">
                <button
                  onClick={() => setExpanded(isOpen ? null : i.id)}
                  className="grid w-full grid-cols-[40px_1fr_120px_120px_120px_80px_120px_24px] items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-background/60"
                >
                  <span className="font-mono text-sm text-text-tertiary">{idx + 1}</span>
                  <span className="truncate text-sm text-foreground">{i.title}</span>
                  <span className="flex items-center gap-2">
                    <Bar value={i.impact} color="bg-brand-blue" />
                    <span className="font-mono text-xs tabular-nums text-text-secondary">{i.impact}</span>
                  </span>
                  <span className="flex items-center gap-2">
                    <Bar value={i.effort} color="bg-brand-amber" />
                    <span className="font-mono text-xs tabular-nums text-text-secondary">{i.effort}</span>
                  </span>
                  <span className="flex items-center gap-2">
                    <Bar value={i.value} color="bg-brand-green" />
                    <span className="font-mono text-xs tabular-nums text-text-secondary">{i.value}</span>
                  </span>
                  <span className="font-mono text-sm font-semibold tabular-nums text-foreground">
                    {i.score.toFixed(1)}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Dot className={meta.dot} />
                    <span className="text-xs text-text-secondary">{meta.label}</span>
                  </span>
                  <span className="text-text-tertiary">
                    {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                  </span>
                </button>

                {isOpen && (
                  <div className="border-t border-border bg-background/40 px-4 py-4 animate-fade-in">
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Sources</div>
                        <ul className="mt-2 space-y-1 text-xs text-text-secondary">
                          {i.sources.map((s) => (
                            <li key={s}>· {s}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Contributors</div>
                        <div className="mt-2 font-mono text-2xl font-semibold text-foreground">{i.contributors}</div>
                      </div>
                    </div>
                    {i.writeup ? (
                      <div className="mt-4">
                        <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Mission writeup</div>
                        <div className="mt-2 max-h-[28rem] overflow-auto rounded border border-border bg-background/60 p-4">
                          <MarkdownContent content={i.writeup} />
                        </div>
                      </div>
                    ) : null}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </Card>
    </div>
  );
}
