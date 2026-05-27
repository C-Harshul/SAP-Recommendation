import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { exchangeNewsletterOAuthCode } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/rec/primitives";

export default function GmailOauthCallback() {
  const navigate = useNavigate();
  const [message, setMessage] = useState("Finalizing Gmail OAuth...");
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const params = new URLSearchParams(window.location.search);
      const code = params.get("code");
      const state = params.get("state");
      const err = params.get("error");
      if (err) {
        setMessage(`OAuth canceled or failed: ${err}`);
        return;
      }
      if (!code || !state) {
        setMessage("Missing OAuth code/state. Please retry Connect Gmail.");
        return;
      }
      try {
        const redirectUri = `${window.location.origin}/oauth/gmail/callback`;
        const res = await exchangeNewsletterOAuthCode(code, state, redirectUri);
        setToken(res.refresh_token);
        setMessage(
          `Connected as ${res.sender_email}. Runtime auth is ready. Add the refresh token to .env for persistence.`,
        );
      } catch (e) {
        setMessage(e instanceof Error ? e.message : "OAuth exchange failed");
      }
    })();
  }, []);

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-2xl">
        <Card className="space-y-4 p-6">
          <h1 className="text-lg font-semibold text-foreground">Gmail OAuth</h1>
          <p className="text-sm text-text-secondary">{message}</p>
          {token ? (
            <div className="space-y-2">
              <p className="text-xs text-text-secondary">Copy this to `GMAIL_REFRESH_TOKEN` in `.env`:</p>
              <div className="rounded border border-border bg-muted p-2 font-mono text-xs break-all">
                {token}
              </div>
            </div>
          ) : null}
          <div className="flex gap-2">
            <Button onClick={() => navigate("/")}>Back to Dashboard</Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
