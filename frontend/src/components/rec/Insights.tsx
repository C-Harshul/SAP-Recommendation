import { useEffect, useState } from "react";
import { Card } from "./primitives";
import { EmptyState } from "./EmptyState";
import { MarkdownContent } from "./MarkdownContent";
import { useRecEngine } from "@/context/RecEngineContext";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  fetchNewsletterOAuthStatus,
  sendNewsletter,
  startNewsletterOAuth,
  type NewsletterOAuthStatus,
} from "@/lib/api";
import { toast } from "sonner";

export function Insights() {
  const { hasResults, ideas, isRunning } = useRecEngine();
  const topIdeas = ideas.slice(0, 10);
  const [recipient, setRecipient] = useState("harshulc2001@gmail.com");
  const [sending, setSending] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [oauth, setOauth] = useState<NewsletterOAuthStatus | null>(null);
  const [selectedIdeaId, setSelectedIdeaId] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const status = await fetchNewsletterOAuthStatus();
        setOauth(status);
      } catch {
        setOauth(null);
      }
    })();
  }, []);

  const connectGmail = async () => {
    try {
      setConnecting(true);
      const redirectUri = `${window.location.origin}/oauth/gmail/callback`;
      const { auth_url } = await startNewsletterOAuth(redirectUri);
      window.location.href = auth_url;
    } catch (err) {
      toast.error("Could not start Gmail OAuth", {
        description: err instanceof Error ? err.message : "API error",
      });
    } finally {
      setConnecting(false);
    }
  };

  const sendNow = async () => {
    try {
      setSending(true);
      const res = await sendNewsletter(recipient || undefined, 10);
      toast.success("Newsletter sent", {
        description: `Sent ${res.missions_count} ranked ideas to ${res.recipient}`,
      });
    } catch (err) {
      toast.error("Could not send newsletter", {
        description: err instanceof Error ? err.message : "API error",
      });
    } finally {
      setSending(false);
    }
  };

  const selectedIdea = topIdeas.find((i) => i.id === selectedIdeaId) ?? null;

  if (!hasResults) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div>
          <h1 className="text-lg font-semibold text-foreground">AI Insights</h1>
          <p className="text-xs text-text-secondary">
            Generated from ranked mission writeups and cluster rationale — not static placeholders.
          </p>
        </div>
        <EmptyState
          title={isRunning ? "Generating insights…" : "No insights yet"}
          description="After a successful ranking run, open ranked missions for mission writeups and market context from the engine."
          showRunButton={!isRunning}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <div>
        <h1 className="text-lg font-semibold text-foreground">AI Insights</h1>
        <p className="text-xs text-text-secondary">
          Newsletter-style preview from the latest ranking run ({ideas.length} missions).
        </p>
      </div>

      <Card className="space-y-3 p-4">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Newsletter</h2>
          <p className="text-xs text-text-secondary">
            Connect Gmail via OAuth, then send the latest ranked ideas as an email newsletter.
          </p>
        </div>
        <div className="grid gap-2 md:grid-cols-[1fr_auto_auto]">
          <Input
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            placeholder="Recipient email"
          />
          <Button
            variant="secondary"
            onClick={() => void connectGmail()}
            disabled={connecting || !oauth?.oauth_client_ready}
          >
            {connecting ? "Connecting..." : "Connect Gmail"}
          </Button>
          <Button onClick={() => void sendNow()} disabled={sending || !oauth?.connected}>
            {sending ? "Sending..." : "Send Newsletter"}
          </Button>
        </div>
        <p className="text-xs text-text-secondary">
          {oauth?.oauth_client_ready
            ? oauth.connected
              ? `Connected as ${oauth.sender_email ?? "unknown sender"}.`
              : "OAuth client ready. Connect Gmail to enable sending."
            : "Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in .env, then restart API."}
        </p>
      </Card>

      <Card className="overflow-hidden p-0">
        <div className="border-b border-border bg-muted/40 px-4 py-3">
          <div className="text-xs text-text-secondary">From: {oauth?.sender_email ?? "you@company.com"}</div>
          <div className="text-xs text-text-secondary">To: {recipient || "recipient@company.com"}</div>
          <div className="mt-1 text-sm font-semibold text-foreground">Subject: SAP Experience garage ideas</div>
        </div>
        <div className="max-h-[70vh] space-y-3 overflow-y-auto px-4 py-4">
          <p className="text-sm text-foreground">
            Click a row to open the full markdown writeup.
          </p>
          {topIdeas.map((m, idx) => (
            <button
              key={m.id}
              type="button"
              onClick={() => setSelectedIdeaId(m.id)}
              className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-start gap-3 rounded-md border border-border p-3 text-left transition-colors hover:bg-muted/40"
            >
              <div>
                <div className="text-sm font-semibold text-foreground">
                  {idx + 1}. {m.title}
                </div>
                <div className="mt-1 text-xs text-text-secondary">
                  Stage: {m.status} · Sources: {m.sources.join(", ")}
                </div>
              </div>
              <span className="font-mono text-xs font-semibold text-foreground">
                {m.score?.toFixed(1)}
              </span>
            </button>
          ))}
        </div>
      </Card>

      <Dialog open={!!selectedIdea} onOpenChange={(open) => !open && setSelectedIdeaId(null)}>
        <DialogContent className="max-h-[85vh] max-w-3xl overflow-hidden p-0">
          <DialogHeader className="border-b border-border px-6 py-4">
            <DialogTitle>{selectedIdea?.title ?? "Mission"}</DialogTitle>
            <DialogDescription>
              Score {selectedIdea?.score?.toFixed(1) ?? "0.0"} · Stage {selectedIdea?.status ?? "ideation"}
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[65vh] overflow-y-auto px-6 py-4">
            {selectedIdea?.writeup ? (
              <MarkdownContent content={selectedIdea.writeup} />
            ) : (
              <p className="text-sm text-text-tertiary">No writeup returned for this mission.</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
