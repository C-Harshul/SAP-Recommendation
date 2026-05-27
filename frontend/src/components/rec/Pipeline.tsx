import { useState } from "react";
import { Bar, Card, Dot } from "./primitives";
import { EmptyState } from "./EmptyState";
import { useRecEngine } from "@/context/RecEngineContext";
import { statusColumnOrder, statusMeta, type IdeaStatus } from "@/lib/rec-data";
import { cn } from "@/lib/utils";

const cols = statusColumnOrder;

export function Pipeline() {
  const { ideas, hasResults, isRunning, pipeline, updateMissionKanban } = useRecEngine();
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverCol, setDragOverCol] = useState<IdeaStatus | null>(null);

  if (!hasResults) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Mission Board</h1>
          <p className="text-xs text-text-secondary">Kanban view of ranked missions from the engine.</p>
        </div>
        <EmptyState
          title={isRunning ? "Building pipeline…" : "Pipeline empty"}
          description={
            isRunning
              ? pipeline.message
              : "Complete a ranking run to populate the board with real missions."
          }
          showRunButton={!isRunning}
        />
      </div>
    );
  }

  const handleDrop = (status: IdeaStatus) => {
    if (!draggingId) return;
    const item = ideas.find((i) => i.id === draggingId);
    if (item && item.status !== status) {
      void updateMissionKanban(draggingId, status);
    }
    setDraggingId(null);
    setDragOverCol(null);
  };

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Mission Board</h1>
          <p className="text-xs text-text-secondary">
            {ideas.length} ranked missions — drag to move between stages (saved to cache).
          </p>
        </div>
      </div>

      <div className="-mx-4 overflow-x-auto px-4 md:mx-0 md:px-0">
        <div className="grid min-w-[900px] grid-cols-4 gap-3">
          {cols.map((status) => {
            const meta = statusMeta[status];
            const colItems = ideas
              .filter((i) => i.status === status)
              .map((i) => ({ ...i, score: i.score ?? 0 }));
            return (
              <div
                key={status}
                onDragOver={(e) => {
                  e.preventDefault();
                  if (dragOverCol !== status) setDragOverCol(status);
                }}
                onDragLeave={(e) => {
                  if (e.currentTarget.contains(e.relatedTarget as Node)) return;
                  setDragOverCol((c) => (c === status ? null : c));
                }}
                onDrop={() => handleDrop(status)}
                className={cn(
                  "flex flex-col rounded-lg border bg-muted/40 transition-colors",
                  dragOverCol === status ? "border-foreground/40 bg-muted" : "border-border",
                )}
              >
                <div className="flex items-center justify-between border-b border-border px-3 py-2">
                  <div className="flex items-center gap-2">
                    <Dot className={meta.dot} />
                    <span className="text-xs font-semibold uppercase tracking-wider text-foreground">
                      {meta.label}
                    </span>
                  </div>
                  <span className="rounded bg-background px-1.5 py-0.5 font-mono text-[11px] text-text-secondary">
                    {colItems.length}
                  </span>
                </div>
                <div className="flex flex-1 flex-col gap-2 p-2">
                  {colItems.length === 0 ? (
                    <div className="rounded border border-dashed border-border p-6 text-center text-xs text-text-tertiary">
                      No ideas
                    </div>
                  ) : (
                    colItems.map((i) => (
                      <Card
                        key={i.id}
                        draggable
                        onDragStart={(e) => {
                          setDraggingId(i.id);
                          e.dataTransfer.effectAllowed = "move";
                          e.dataTransfer.setData("text/plain", i.id);
                        }}
                        onDragEnd={() => {
                          setDraggingId(null);
                          setDragOverCol(null);
                        }}
                        className={cn(
                          "cursor-grab p-3 shadow-sm transition-all hover:-translate-y-0.5 hover:border-foreground/40 hover:shadow-md active:cursor-grabbing",
                          draggingId === i.id && "opacity-50",
                        )}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="text-sm leading-snug text-foreground">{i.title}</div>
                          <span className="shrink-0 font-mono text-xs font-semibold text-foreground">
                            {i.score.toFixed(1)}
                          </span>
                        </div>
                        <div className="mt-2">
                          <Bar value={i.score} color={meta.dot} full />
                        </div>
                      </Card>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
