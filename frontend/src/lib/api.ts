import type { Idea, IdeaStatus } from "@/lib/rec-data";
import type { PipelineGraphMeta, PipelineStep } from "@/lib/pipeline-graph";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export type PipelineStatus = "idle" | "running" | "completed" | "failed";

export interface PipelineState {
  status: PipelineStatus;
  message: string;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  interviews_loaded: number;
  community_loaded: number;
  trends_loaded: number;
  missions_count: number;
  from_cache?: boolean;
  input_fingerprint?: string | null;
  current_step_id?: string | null;
  progress_percent?: number;
  steps?: PipelineStep[];
  graph?: PipelineGraphMeta;
}

export interface ApiMission {
  id: string;
  rank: number;
  title: string;
  impact: number;
  effort: number;
  value: number;
  score: number;
  status: IdeaStatus;
  contributors: number;
  sources: string[];
  writeup?: string | null;
  cluster_id?: string;
}

export interface RankedMissionsResponse {
  missions: ApiMission[];
  count: number;
  pipeline: PipelineState;
  data_source?: {
    interviews: string;
    community: string;
    market_trends: string;
    community_hardcoded: boolean;
  };
}

export interface DataSummary {
  bucket: string;
  s3: {
    interviews_json_count?: number;
    community_json_count?: number;
    gold_trend_signals_json_count?: number;
    market_bronze_file_count?: number;
  };
  pipeline: PipelineState;
  config: {
    community_source: string;
    community_note?: string;
    enrich_bronze_trends: boolean;
    lookback_days: number;
  };
}

export interface PipelineRunResponse extends PipelineState {
  accepted: boolean;
  message: string;
  from_cache?: boolean;
}

export interface NewsletterOAuthStatus {
  oauth_client_ready: boolean;
  connected: boolean;
  sender_email: string | null;
  runtime_connected: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export function fetchPipelineStatus(): Promise<PipelineState> {
  return request<PipelineState>("/api/pipeline/status");
}

export function triggerPipelineRun(): Promise<PipelineRunResponse> {
  return request<PipelineRunResponse>("/api/pipeline/run", { method: "POST" });
}

export function fetchRankedMissions(): Promise<RankedMissionsResponse> {
  return request<RankedMissionsResponse>("/api/missions/ranked");
}

export function fetchDataSummary(): Promise<DataSummary> {
  return request<DataSummary>("/api/data/summary");
}

export function updateKanbanStatuses(
  statuses: Record<string, IdeaStatus>,
): Promise<{ updated: string[]; count: number }> {
  return request("/api/kanban/statuses", {
    method: "PUT",
    body: JSON.stringify({ statuses }),
  });
}

export function updateMissionKanbanStatus(
  missionId: string,
  status: IdeaStatus,
): Promise<{ mission_id: string; status: string }> {
  return request(`/api/kanban/missions/${encodeURIComponent(missionId)}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function fetchNewsletterOAuthStatus(): Promise<NewsletterOAuthStatus> {
  return request<NewsletterOAuthStatus>("/api/newsletter/oauth/status");
}

export function startNewsletterOAuth(redirect_uri: string): Promise<{ auth_url: string; state: string }> {
  return request("/api/newsletter/oauth/start", {
    method: "POST",
    body: JSON.stringify({ redirect_uri }),
  });
}

export function exchangeNewsletterOAuthCode(
  code: string,
  state: string,
  redirect_uri: string,
): Promise<{ ok: boolean; sender_email: string; refresh_token: string; note: string }> {
  return request("/api/newsletter/oauth/exchange", {
    method: "POST",
    body: JSON.stringify({ code, state, redirect_uri }),
  });
}

export function sendNewsletter(
  recipient?: string,
  top_n = 10,
): Promise<{ ok: boolean; recipient: string; subject: string; missions_count: number }> {
  return request("/api/newsletter/send", {
    method: "POST",
    body: JSON.stringify({ recipient, top_n }),
  });
}

export function missionToIdea(m: ApiMission): Idea & { score: number; writeup?: string | null } {
  return {
    id: m.id,
    title: m.title,
    impact: m.impact,
    effort: m.effort,
    value: m.value,
    status: m.status,
    contributors: m.contributors,
    sources: m.sources,
    score: m.score,
    writeup: m.writeup,
  };
}
