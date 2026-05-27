"""Build and send ranked-mission newsletters via Gmail API."""

from __future__ import annotations

import base64
from email.message import EmailMessage
from typing import Any
from urllib.parse import urlencode

import httpx
import markdown as md

from recommendation_engine.config.settings import Settings

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
USERINFO_EMAIL_SCOPE = "https://www.googleapis.com/auth/userinfo.email"
# gmail.send alone cannot call Gmail users/me/profile (403). userinfo.email resolves sender.
OAUTH_SCOPES = " ".join((GMAIL_SEND_SCOPE, USERINFO_EMAIL_SCOPE))


class NewsletterConfigError(RuntimeError):
    """Raised when Gmail config is missing."""


def _require_gmail_client_config(settings: Settings) -> None:
    missing: list[str] = []
    if not settings.gmail_client_id:
        missing.append("GMAIL_CLIENT_ID")
    if not settings.gmail_client_secret:
        missing.append("GMAIL_CLIENT_SECRET")
    if missing:
        raise NewsletterConfigError("Missing Gmail OAuth client config: " + ", ".join(missing))


def _require_gmail_send_config(
    settings: Settings,
    *,
    refresh_token_override: str | None = None,
    sender_override: str | None = None,
) -> None:
    _require_gmail_client_config(settings)
    missing: list[str] = []
    if not (refresh_token_override or settings.gmail_refresh_token):
        missing.append("GMAIL_REFRESH_TOKEN")
    if not (sender_override or settings.gmail_sender_email):
        missing.append("GMAIL_SENDER_EMAIL")
    if missing:
        raise NewsletterConfigError("Missing Gmail send config: " + ", ".join(missing))


def oauth_config_ready(settings: Settings) -> bool:
    return bool(settings.gmail_client_id and settings.gmail_client_secret)


def build_oauth_authorize_url(*, settings: Settings, redirect_uri: str, state: str) -> str:
    _require_gmail_client_config(settings)
    query = {
        "client_id": settings.gmail_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": OAUTH_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(query)}"


def _newsletter_subject() -> str:
    return "SAP Experience garage ideas"


def _render_text(missions: list[dict[str, Any]]) -> str:
    section_titles = [
        "🚀 Headlines & Launches",
        "🧠 Deep Dives & Analysis",
        "🧑‍💻 Engineering & Research",
        "🎁 Miscellaneous",
        "⚡ Quick Links",
    ]
    lines = [
        "SAP Experience garage ideas",
        "",
        "⚡ Top ranked opportunities from this run",
        "",
    ]
    for section in section_titles:
        lines.append(section)
        lines.append("")
        for idx, mission in enumerate(missions, start=1):
            if section_titles[(idx - 1) % len(section_titles)] != section:
                continue
            score = mission.get("score", 0)
            title = mission.get("title", "Untitled mission")
            status = mission.get("status", "ideation")
            sources = ", ".join(mission.get("sources", []))
            lines.extend(
                [
                    f"{title}",
                    f"Score {score} · Stage {status}",
                    f"Signals: {sources}",
                    "",
                ]
            )
    return "\n".join(lines).strip()


def _render_markdown_fragment(markdown_text: str | None) -> str:
    if not markdown_text:
        return "<p style='color:#6b7280'>No writeup returned for this mission.</p>"
    return md.markdown(markdown_text, extensions=["extra", "sane_lists"])


def _render_html(missions: list[dict[str, Any]]) -> str:
    section_titles = [
        "🚀 Headlines & Launches",
        "🧠 Deep Dives & Analysis",
        "🧑‍💻 Engineering & Research",
        "🎁 Miscellaneous",
        "⚡ Quick Links",
    ]

    grouped: dict[str, list[dict[str, Any]]] = {k: [] for k in section_titles}
    for idx, mission in enumerate(missions, start=1):
        section = section_titles[(idx - 1) % len(section_titles)]
        grouped[section].append(mission)

    sections_html: list[str] = []
    for section in section_titles:
        items = grouped[section]
        if not items:
            continue
        item_html: list[str] = []
        for mission in items:
            rendered_writeup = _render_markdown_fragment(mission.get("writeup"))
            item_html.append(
                "<article style='margin:0 0 18px 0'>"
                f"<h3 style='margin:0 0 5px 0;font-size:18px;line-height:1.35'>{mission.get('title', 'Untitled mission')}</h3>"
                f"<p style='margin:0 0 8px 0;font-size:12px;color:#4b5563'>"
                f"Score {mission.get('score', 0)} · Stage {mission.get('status', 'ideation')} · "
                f"Signals: {', '.join(mission.get('sources', []))}"
                "</p>"
                "<div style='font-size:15px;line-height:1.6;color:#111827'>"
                f"{rendered_writeup}"
                "</div>"
                "</article>"
            )
        sections_html.append(
            "<section style='margin:0 0 24px 0'>"
            f"<h2 style='margin:0 0 12px 0;font-size:22px'>{section}</h2>"
            f"{''.join(item_html)}"
            "</section>"
        )

    body = "".join(sections_html)
    return (
        "<html><body style='font-family:Arial,sans-serif;background:#f8fafc;margin:0;padding:20px'>"
        "<div style='max-width:880px;margin:0 auto;background:white;border:1px solid #e5e7eb;border-radius:12px;padding:20px'>"
        "<h1 style='margin:0 0 6px 0;font-size:28px'>SAP Experience garage ideas</h1>"
        "<p style='margin:0 0 14px 0;font-size:15px;color:#374151'>"
        "⚡ Top ranked opportunities and mission briefs from your latest pipeline run."
        "</p>"
        f"<p style='margin:0 0 24px 0;color:#6b7280'>Total ranked ideas: <strong>{len(missions)}</strong></p>"
        f"{body}"
        "<hr style='border:none;border-top:1px solid #e5e7eb;margin:24px 0'/>"
        "<p style='margin:0;color:#6b7280;font-size:12px'>Generated by DAPL Recommendation Engine</p>"
        "</div>"
        "</body></html>"
    )


def _build_message(
    *,
    sender: str,
    recipient: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> str:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return raw


def exchange_code_for_tokens(*, settings: Settings, code: str, redirect_uri: str) -> dict[str, Any]:
    _require_gmail_client_config(settings)
    payload = {
        "client_id": settings.gmail_client_id,
        "client_secret": settings.gmail_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    response = httpx.post("https://oauth2.googleapis.com/token", data=payload, timeout=20.0)
    response.raise_for_status()
    return response.json()


def exchange_refresh_token_for_access_token(
    *,
    settings: Settings,
    refresh_token: str | None = None,
) -> str:
    _require_gmail_client_config(settings)
    payload = {
        "client_id": settings.gmail_client_id,
        "client_secret": settings.gmail_client_secret,
        "refresh_token": refresh_token or settings.gmail_refresh_token,
        "grant_type": "refresh_token",
    }
    response = httpx.post("https://oauth2.googleapis.com/token", data=payload, timeout=20.0)
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("OAuth token exchange succeeded but no access_token returned")
    return token


def oauth_account_email(*, access_token: str) -> str:
    """Primary Google account email (works with userinfo.email scope)."""
    response = httpx.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20.0,
    )
    response.raise_for_status()
    email = response.json().get("email")
    if not email:
        raise RuntimeError("Google userinfo did not include email")
    return str(email)


def resolve_sender_email(
    *,
    access_token: str,
    settings: Settings,
) -> str:
    """Resolve sender from OAuth userinfo, else env GMAIL_SENDER_EMAIL."""
    try:
        return oauth_account_email(access_token=access_token)
    except httpx.HTTPStatusError as exc:
        if settings.gmail_sender_email:
            return str(settings.gmail_sender_email)
        raise RuntimeError(
            "Could not read account email from Google userinfo "
            f"({exc.response.status_code}). Set GMAIL_SENDER_EMAIL in .env or "
            "re-connect Gmail after adding userinfo.email scope on the OAuth consent screen."
        ) from exc


def send_ranked_missions_newsletter(
    *,
    settings: Settings,
    missions: list[dict[str, Any]],
    recipient: str | None = None,
    refresh_token_override: str | None = None,
    sender_override: str | None = None,
) -> dict[str, Any]:
    _require_gmail_send_config(
        settings,
        refresh_token_override=refresh_token_override,
        sender_override=sender_override,
    )
    to_email = recipient or settings.newsletter_default_recipient
    sender_email = sender_override or settings.gmail_sender_email
    subject = _newsletter_subject()
    text_body = _render_text(missions)
    html_body = _render_html(missions)
    raw_message = _build_message(
        sender=str(sender_email),
        recipient=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
    access_token = exchange_refresh_token_for_access_token(
        settings=settings, refresh_token=refresh_token_override
    )
    response = httpx.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        json={"raw": raw_message},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20.0,
    )
    response.raise_for_status()
    data = response.json()
    return {
        "recipient": to_email,
        "subject": subject,
        "missions_count": len(missions),
        "gmail_message_id": data.get("id"),
        "gmail_thread_id": data.get("threadId"),
    }
