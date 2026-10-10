"""Multi-channel alerting: get the alert off the screen and into a pocket.

The gap analysis puts this well: "a forest officer does not stare at a dashboard
waiting for alerts", and an invasive-species detection whose value is early
warning loses that value entirely if it sits unread on a map.

Four channels, every one off unless configured:

  log       always on. Structured, so it is greppable.
  email     SMTP. stdlib, works with any provider.
  webhook   HTTP POST of the alert JSON. This is the Slack/Teams path, and also
            the SMS path -- every Indian SMS gateway takes an HTTP POST, so one
            generic channel covers all of them rather than hard-coding a vendor.
  browser   pushed to open dashboards over the SSE stream; the page raises a
            Notification. No service worker, so it reaches a tab that is open in
            the background but not a closed one.

On Twilio specifically: the analysis names it, and it is one POST away through
the webhook channel. It is not a built-in because it needs a paid account and an
Indian sender registration (TRAI DLT), so hard-coding it would produce a feature
that cannot be demonstrated. The webhook works today with any provider.

Nothing sends unless the corresponding environment variable is set. A dashboard
that silently emails people because a default was left on is worse than one that
does not email at all.

    BIORADAR_SMTP_HOST=smtp.gmail.com
    BIORADAR_SMTP_PORT=587
    BIORADAR_SMTP_USER=...
    BIORADAR_SMTP_PASSWORD=...           # app password, not the account password
    BIORADAR_ALERT_EMAIL=officer@example.gov.in,lab@example.org
    BIORADAR_ALERT_WEBHOOK=https://hooks.example.com/...
    BIORADAR_ALERT_MIN_SEVERITY=medium   # high | medium | info
"""

from __future__ import annotations

import json
import os
import smtplib
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Callable, Dict, List, Optional

from bioradar import obs

log = obs.logger("notify")

SEVERITY_ORDER = {"info": 0, "medium": 1, "high": 2}

# Subscribers for the browser channel: the SSE handler registers a callback per
# connected dashboard.
_subscribers: List[Callable[[Dict[str, Any]], None]] = []
_sub_lock = threading.Lock()


def subscribe(callback: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
    """Register a live dashboard. Returns the unsubscribe function."""
    with _sub_lock:
        _subscribers.append(callback)

    def unsubscribe() -> None:
        with _sub_lock:
            if callback in _subscribers:
                _subscribers.remove(callback)

    return unsubscribe


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _recipients() -> List[str]:
    raw = _env("BIORADAR_ALERT_EMAIL")
    return [address.strip() for address in raw.split(",") if address.strip()]


def configured_channels() -> Dict[str, Any]:
    """What is actually wired up. Surfaced in the UI so nobody assumes.

    A settings screen that shows toggles for channels which will never fire is a
    lie told through omission; showing the real state costs one endpoint.
    """
    smtp_ready = bool(_env("BIORADAR_SMTP_HOST") and _recipients())
    return {
        "log": {"enabled": True, "detail": "structured log, always on"},
        "email": {
            "enabled": smtp_ready,
            "detail": (
                "{n} recipient(s) via {host}".format(
                    n=len(_recipients()), host=_env("BIORADAR_SMTP_HOST")
                )
                if smtp_ready
                else "set BIORADAR_SMTP_HOST and BIORADAR_ALERT_EMAIL"
            ),
        },
        "webhook": {
            "enabled": bool(_env("BIORADAR_ALERT_WEBHOOK")),
            "detail": (
                "POST to a configured endpoint"
                if _env("BIORADAR_ALERT_WEBHOOK")
                else "set BIORADAR_ALERT_WEBHOOK (Slack, Teams, or an SMS gateway)"
            ),
        },
        "browser": {
            "enabled": True,
            "detail": "{n} dashboard(s) connected".format(n=len(_subscribers)),
        },
        "min_severity": _env("BIORADAR_ALERT_MIN_SEVERITY", "medium"),
    }


def _meets_threshold(severity: str) -> bool:
    threshold = _env("BIORADAR_ALERT_MIN_SEVERITY", "medium")
    return SEVERITY_ORDER.get(severity, 0) >= SEVERITY_ORDER.get(threshold, 1)


def dispatch(
    *,
    title: str,
    body: str,
    severity: str = "info",
    kind: str = "alert",
    data: Optional[Dict[str, Any]] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Send one notification to every configured channel.

    Never raises. A notification failure must not take down the run that
    triggered it -- the analysis result is the thing that matters, and losing it
    because an SMTP server was unreachable would be an absurd trade.
    """
    event = {
        "kind": kind,
        "severity": severity,
        "title": title,
        "body": body,
        "data": data or {},
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    if not force and not _meets_threshold(severity):
        log.debug("notify.below_threshold", title=title, severity=severity)
        return {"sent": [], "skipped": ["below severity threshold"]}

    sent: List[str] = []
    failed: List[Dict[str, str]] = []

    log.info("notify.alert", title=title, severity=severity, kind=kind)
    sent.append("log")

    with _sub_lock:
        listeners = list(_subscribers)
    for callback in listeners:
        try:
            callback(event)
        except Exception:  # noqa: BLE001
            pass
    if listeners:
        sent.append("browser")

    if _env("BIORADAR_SMTP_HOST") and _recipients():
        try:
            _send_email(title, body, event)
            sent.append("email")
        except Exception as exc:  # noqa: BLE001
            log.exception("notify.email_failed", exc, title=title)
            failed.append({"channel": "email", "error": str(exc)})

    if _env("BIORADAR_ALERT_WEBHOOK"):
        try:
            _send_webhook(event)
            sent.append("webhook")
        except Exception as exc:  # noqa: BLE001
            log.exception("notify.webhook_failed", exc, title=title)
            failed.append({"channel": "webhook", "error": str(exc)})

    return {"sent": sent, "failed": failed, "event": event}


def _send_email(title: str, body: str, event: Dict[str, Any]) -> None:
    host = _env("BIORADAR_SMTP_HOST")
    port = int(_env("BIORADAR_SMTP_PORT", "587") or 587)
    user = _env("BIORADAR_SMTP_USER")
    password = _env("BIORADAR_SMTP_PASSWORD")
    sender = _env("BIORADAR_SMTP_FROM") or user or "bioradar@localhost"
    recipients = _recipients()

    message = EmailMessage()
    message["Subject"] = "[BioRadar {sev}] {t}".format(sev=event["severity"].upper(), t=title)
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(
        "{body}\n\n"
        "Severity : {sev}\n"
        "Type     : {kind}\n"
        "Time     : {at} UTC\n\n"
        "{detail}\n\n"
        "-- \n"
        "BioRadar. An eDNA detection is a probabilistic result: verify in the\n"
        "field before taking action.\n".format(
            body=body,
            sev=event["severity"],
            kind=event["kind"],
            at=event["at"],
            detail=json.dumps(event["data"], indent=2, ensure_ascii=False)[:4000],
        )
    )

    timeout = float(_env("BIORADAR_SMTP_TIMEOUT", "20") or 20)
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=timeout)
    else:
        server = smtplib.SMTP(host, port, timeout=timeout)
    try:
        if port != 465:
            try:
                server.starttls()
            except smtplib.SMTPException:
                # A server that does not offer STARTTLS on 587 is misconfigured,
                # but failing the send is more useful than silently downgrading
                # to plaintext with a password in hand.
                raise
        if user and password:
            server.login(user, password)
        server.send_message(message)
    finally:
        try:
            server.quit()
        except Exception:  # noqa: BLE001
            pass


def _send_webhook(event: Dict[str, Any]) -> None:
    url = _env("BIORADAR_ALERT_WEBHOOK")
    payload = dict(event)
    # Slack and Teams both render a top-level `text`; giving them one means the
    # generic webhook is useful in both without a per-vendor adapter.
    payload["text"] = "[BioRadar {sev}] {t}\n{b}".format(
        sev=event["severity"].upper(), t=event["title"], b=event["body"]
    )
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "BioRadar"},
        method="POST",
    )
    timeout = float(_env("BIORADAR_WEBHOOK_TIMEOUT", "10") or 10)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status >= 400:
            raise RuntimeError("webhook returned HTTP {s}".format(s=response.status))


# --------------------------------------------------------------------------
# Ready-made notifications
# --------------------------------------------------------------------------


def run_finished(run: Dict[str, Any], alerts: Optional[Dict[str, Any]] = None) -> None:
    """Announce a completed run, escalating if the watchlist matched."""
    summary = (alerts or {}).get("summary", {})
    high = summary.get("high", 0)
    name = run.get("dataset_name", run.get("run_id", "run"))

    if high:
        top = [a["scientific_name"] for a in (alerts or {}).get("alerts", []) if a["severity"] == "high"]
        dispatch(
            title="{n} species of concern in {d}".format(n=high, d=name),
            body=(
                "{n} high-severity detection(s): {names}. "
                "Confirm in the field before acting.".format(
                    n=high, names=", ".join(top[:5])
                )
            ),
            severity="high",
            kind="watchlist",
            data={"run_id": run.get("run_id"), "alerts": (alerts or {}).get("alerts", [])[:10]},
        )
        return

    report = run.get("report") or {}
    dispatch(
        title="Analysis complete: {d}".format(d=name),
        body="{s} named species across {n} sample(s). No watchlist matches.".format(
            s=report.get("named_species", 0), n=report.get("samples", 0)
        ),
        severity="info",
        kind="run",
        data={"run_id": run.get("run_id")},
    )


def run_failed(run: Dict[str, Any]) -> None:
    dispatch(
        title="Analysis failed: {d}".format(d=run.get("dataset_name", run.get("run_id", ""))),
        body=run.get("error", "The pipeline did not complete."),
        severity="medium",
        kind="run",
        data={"run_id": run.get("run_id"), "error_id": run.get("error_id")},
    )
