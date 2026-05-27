import { useState } from "react";
import { TopNav, type ViewKey } from "@/components/rec/TopNav";
import { Overview } from "@/components/rec/Overview";
import { RankedIdeas } from "@/components/rec/RankedIdeas";
import { Signals } from "@/components/rec/Signals";
import { Pipeline } from "@/components/rec/Pipeline";
import { RankingRun } from "@/components/rec/RankingRun";
import { Insights } from "@/components/rec/Insights";

const Index = () => {
  const [view, setView] = useState<ViewKey>("overview");

  return (
    <div className="min-h-screen bg-background text-foreground">
      <TopNav view={view} onChange={setView} />
      <main className="px-4 py-6 md:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          {view === "overview" && <Overview />}
          {view === "ranked" && <RankedIdeas />}
          {view === "signals" && <Signals />}
          {view === "ranking" && <RankingRun />}
          {view === "pipeline" && <Pipeline />}
          {view === "insights" && <Insights />}
        </div>
      </main>
    </div>
  );
};

export default Index;
