import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { toast } from "sonner";
import {
  fetchDataSummary,
  fetchPipelineStatus,
  fetchRankedMissions,
  missionToIdea,
  updateMissionKanbanStatus,
  triggerPipelineRun,
  type DataSummary,
  type PipelineState,
} from "@/lib/api";
import type { Idea } from "@/lib/rec-data";

type RankedIdea = Idea & { score?: number; writeup?: string | null };

interface RecEngineContextValue {
  ideas: RankedIdea[];
  hasResults: boolean;
  pipeline: PipelineState;
  dataSummary: DataSummary | null;
  apiConnected: boolean;
  isRunning: boolean;
  refreshMissions: () => Promise<void>;
  refreshSummary: () => Promise<void>;
  runRanking: () => Promise<void>;
  updateMissionKanban: (missionId: string, status: Idea["status"]) => Promise<void>;
}

const RecEngineContext = createContext<RecEngineContextValue | null>(null);

const defaultPipeline: PipelineState = {
  status: "idle",
  message: "Ready",
  started_at: null,
  finished_at: null,
  error: null,
  interviews_loaded: 0,
  community_loaded: 0,
  trends_loaded: 0,
  missions_count: 0,
  current_step_id: null,
  progress_percent: 0,
  steps: [],
};

export function RecEngineProvider({ children }: { children: ReactNode }) {
  const [ideas, setIdeas] = useState<RankedIdea[]>([]);
  const [pipeline, setPipeline] = useState<PipelineState>(defaultPipeline);
  const [dataSummary, setDataSummary] = useState<DataSummary | null>(null);
  const [apiConnected, setApiConnected] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const hasResults = ideas.length > 0;

  const refreshSummary = useCallback(async () => {
    try {
      const summary = await fetchDataSummary();
      setDataSummary(summary);
      setPipeline(summary.pipeline);
      setApiConnected(true);
    } catch {
      setApiConnected(false);
    }
  }, []);

  const refreshMissions = useCallback(async () => {
    try {
      const data = await fetchRankedMissions();
      setPipeline(data.pipeline);
      setApiConnected(true);
      if (data.count > 0) {
        setIdeas(data.missions.map(missionToIdea));
      } else {
        setIdeas([]);
      }
    } catch {
      setApiConnected(false);
    }
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const status = await fetchPipelineStatus();
        setPipeline(status);
        if (status.status === "completed") {
          stopPolling();
          await refreshMissions();
          await refreshSummary();
          if (status.missions_count > 0) {
            const fromCache = (status as { from_cache?: boolean }).from_cache;
            toast.success(fromCache ? "Loaded cached analysis" : "Ranking complete", {
              description: status.message,
            });
          } else {
            toast.warning("Pipeline finished with no ranked missions", {
              description: "Check API logs and S3 data / Gemini quota.",
            });
          }
        } else if (status.status === "failed") {
          stopPolling();
          toast.error("Ranking failed", {
            description: status.error ?? status.message,
          });
        }
      } catch {
        stopPolling();
      }
    }, 1500);
  }, [refreshMissions, refreshSummary, stopPolling]);

  useEffect(() => {
    void (async () => {
      try {
        const status = await fetchPipelineStatus();
        setPipeline(status);
        setApiConnected(true);
        if (status.status === "running") {
          startPolling();
        }
      } catch {
        setApiConnected(false);
      }
      await Promise.all([refreshSummary(), refreshMissions()]);
    })();
    return stopPolling;
  }, [refreshMissions, refreshSummary, startPolling, stopPolling]);

  const updateMissionKanban = useCallback(
    async (missionId: string, status: Idea["status"]) => {
      setIdeas((prev) =>
        prev.map((i) => (i.id === missionId ? { ...i, status } : i)),
      );
      try {
        await updateMissionKanbanStatus(missionId, status);
        setApiConnected(true);
      } catch (err) {
        await refreshMissions();
        toast.error("Could not save board position", {
          description: err instanceof Error ? err.message : "API error",
        });
      }
    },
    [refreshMissions],
  );

  const runRanking = useCallback(async () => {
    try {
      const res = await triggerPipelineRun();
      setPipeline(res);
      setApiConnected(true);
      if (!res.accepted) {
        toast.info(res.message);
        return;
      }
      if (res.from_cache) {
        await refreshMissions();
        await refreshSummary();
        toast.success("Loaded cached analysis", { description: res.message });
        return;
      }
      setIdeas([]);
      toast.info("Ranking started", {
        description: "Loading S3 interviews & market trends, plus curated community posts…",
      });
      startPolling();
    } catch (err) {
      toast.error("Could not start ranking", {
        description: err instanceof Error ? err.message : "Is the API server running?",
      });
    }
  }, [startPolling]);

  const value = useMemo(
    () => ({
      ideas,
      hasResults,
      pipeline,
      dataSummary,
      apiConnected,
      isRunning: pipeline.status === "running",
      refreshMissions,
      refreshSummary,
      runRanking,
      updateMissionKanban,
    }),
    [
      ideas,
      hasResults,
      pipeline,
      dataSummary,
      apiConnected,
      refreshMissions,
      refreshSummary,
      runRanking,
      updateMissionKanban,
    ],
  );

  return <RecEngineContext.Provider value={value}>{children}</RecEngineContext.Provider>;
}

export function useRecEngine(): RecEngineContextValue {
  const ctx = useContext(RecEngineContext);
  if (!ctx) {
    throw new Error("useRecEngine must be used within RecEngineProvider");
  }
  return ctx;
}
