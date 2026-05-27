import { useState } from "react";
import { Bell, Loader2, Menu, Play, X } from "lucide-react";
import { useRecEngine } from "@/context/RecEngineContext";
import { Button } from "@/components/ui/button";

export type ViewKey =
  | "overview"
  | "ranked"
  | "signals"
  | "ranking"
  | "pipeline"
  | "insights";

const items: { key: ViewKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "ranked", label: "Ranked Ideas" },
  { key: "signals", label: "Signals" },
  { key: "ranking", label: "Ranking Run" },
  { key: "pipeline", label: "Board" },
  { key: "insights", label: "AI Insights" },
];

interface Props {
  view: ViewKey;
  onChange: (v: ViewKey) => void;
}

function SapLogo() {
  return (
    <div
      aria-label="SAP"
      className="relative grid h-8 w-[58px] place-items-center rounded-[2px] bg-white text-sap-navy"
      style={{
        clipPath: "polygon(0 0, 100% 0, 88% 100%, 0 100%)",
      }}
    >
      <span className="font-bold tracking-tight text-[18px] leading-none">SAP</span>
    </div>
  );
}

export function TopNav({ view, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const { runRanking, isRunning, pipeline, hasResults, apiConnected } = useRecEngine();

  return (
    <header className="sticky top-0 z-40 w-full">
      {/* Shell bar */}
      <div className="flex h-12 items-center gap-3 bg-sap-navy px-3 text-sap-navy-foreground sm:px-5">
        <SapLogo />
        <div className="h-5 w-px bg-white/30" />
        <div className="flex items-center gap-2 truncate">
          <span className="truncate text-[15px] font-normal">rec.engine</span>
          <span className="hidden truncate text-[12px] text-white/70 sm:inline">
            · SAP Experience Garage
          </span>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <Button
            size="sm"
            variant="secondary"
            className="hidden h-8 gap-1.5 border-0 bg-sap-amber text-sap-navy hover:bg-sap-amber/90 sm:inline-flex"
            onClick={() => void runRanking()}
            disabled={isRunning}
          >
            {isRunning ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            {isRunning ? "Ranking…" : "Run Ranking"}
          </Button>
          <span className="hidden font-mono text-[11px] text-white/70 lg:inline">
            {!apiConnected
              ? "API offline"
              : hasResults
                ? `${pipeline.missions_count} missions`
                : "S3 · no results yet"}
            {pipeline.status === "running" ? ` · ${pipeline.message}` : ""}
          </span>
          <button
            className="grid h-8 w-8 place-items-center rounded-full text-white/80 hover:bg-white/10"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
          </button>
          <div className="hidden text-[13px] sm:block">Hello Admin</div>
          <div className="grid h-8 w-8 place-items-center rounded-full bg-white/15 text-[12px] font-semibold">
            A
          </div>
          <button
            className="grid h-8 w-8 place-items-center rounded text-white/80 hover:bg-white/10 md:hidden"
            aria-label="Menu"
            onClick={() => setOpen((o) => !o)}
          >
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Page nav */}
      <nav className="hidden border-b border-border bg-card md:block">
        <ul className="mx-auto flex max-w-7xl items-center justify-center gap-2 px-6">
          {items.map((it) => {
            const active = view === it.key;
            return (
              <li key={it.key}>
                <button
                  onClick={() => onChange(it.key)}
                  className={[
                    "relative px-5 py-3 text-[14px] transition-colors",
                    active
                      ? "text-sap-amber font-semibold"
                      : "text-text-secondary hover:text-foreground",
                  ].join(" ")}
                >
                  {it.label}
                  {active && (
                    <span className="absolute inset-x-3 -bottom-px h-[3px] rounded-t bg-sap-amber" />
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Mobile drawer */}
      {open && (
        <div className="md:hidden">
          <div className="border-b border-border bg-card animate-fade-in">
            <Button
              size="sm"
              className="mx-5 mt-3 gap-1.5 bg-sap-amber text-sap-navy hover:bg-sap-amber/90"
              onClick={() => {
                void runRanking();
                setOpen(false);
              }}
              disabled={isRunning}
            >
              {isRunning ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Play className="h-3.5 w-3.5" />
              )}
              {isRunning ? "Ranking…" : "Run Ranking"}
            </Button>
            <ul className="flex flex-col">
              {items.map((it) => {
                const active = view === it.key;
                return (
                  <li key={it.key} className="border-b border-border last:border-0">
                    <button
                      onClick={() => {
                        onChange(it.key);
                        setOpen(false);
                      }}
                      className={[
                        "flex w-full items-center justify-between px-5 py-3 text-left text-sm",
                        active
                          ? "border-l-[3px] border-sap-amber text-sap-amber font-semibold"
                          : "text-text-secondary",
                      ].join(" ")}
                    >
                      {it.label}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}
    </header>
  );
}