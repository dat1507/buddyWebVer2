"""Render the three VGU Buddy transactional emails into one local preview gallery."""

from __future__ import annotations

import argparse
import base64
from datetime import UTC, datetime, timedelta
from html import escape
from pathlib import Path

from pydantic import SecretBytes

from app.core.config import EmailVerificationDeliverySettings
from app.services.email_verification_requests import (
    EmailVerificationTemplate,
    seal_email_verification_token,
)
from app.services.invitation_email import (
    MatchingInvitationAcceptedTemplate,
    MatchingInvitationCreatedTemplate,
)

PREVIEW_NOW = datetime(2099, 1, 1, tzinfo=UTC)
PREVIEW_ORIGIN = "https://preview.vgubuddyprogram.invalid"
INVITATION_ID = "11111111-1111-4111-8111-111111111111"
CONVERSATION_ID = "44444444-4444-4444-8444-444444444444"


def _gallery_card(title: str, html_body: str) -> str:
    return f"""
      <section>
        <h2>{escape(title)}</h2>
        <iframe title="{escape(title, quote=True)}" srcdoc="{escape(html_body, quote=True)}"></iframe>
      </section>"""


def render_preview(output_path: Path) -> None:
    settings = EmailVerificationDeliverySettings(
        public_app_base_url=PREVIEW_ORIGIN,
        sealing_key=SecretBytes(bytes(range(32))),
    )
    token = base64.urlsafe_b64encode(bytes(reversed(range(32)))).rstrip(b"=").decode("ascii")
    verification_payload = seal_email_verification_token(
        token,
        PREVIEW_NOW + timedelta(minutes=15),
        settings,
        random_bytes=lambda size: b"p" * size,
    )
    emails = (
        (
            "Received Invitation",
            MatchingInvitationCreatedTemplate(settings).render(
                {
                    "version": 1,
                    "invitation_id": INVITATION_ID,
                    "sender_display_name": "Linh Nguyen",
                }
            ),
        ),
        (
            "Email Verified",
            EmailVerificationTemplate(settings, clock=lambda: PREVIEW_NOW).render(
                verification_payload
            ),
        ),
        (
            "Accepted Invitation",
            MatchingInvitationAcceptedTemplate(settings).render(
                {
                    "version": 1,
                    "conversation_id": CONVERSATION_ID,
                    "acceptor_display_name": "Alex Müller",
                }
            ),
        ),
    )

    repository_root = Path(__file__).resolve().parents[3]
    logo_bytes = (repository_root / "apps/web/public/vguBuddy_logo.png").read_bytes()
    logo_data_url = f"data:image/png;base64,{base64.b64encode(logo_bytes).decode('ascii')}"
    cards = []
    for title, email in emails:
        if email.html_body is None:
            raise RuntimeError(f"{title} did not render an HTML body.")
        html_body = email.html_body.replace(
            f"{PREVIEW_ORIGIN}/vguBuddy_logo.png",
            logo_data_url,
        )
        cards.append(_gallery_card(title, html_body))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>VGU Buddy transactional email previews</title>
    <style>
      body { margin: 0; padding: 24px; background: #e4e4e7; color: #171717; font-family: Arial, sans-serif; }
      h1 { margin: 0 0 24px; }
      main { display: grid; grid-template-columns: repeat(3, minmax(320px, 1fr)); gap: 20px; }
      section { min-width: 0; }
      h2 { margin: 0 0 10px; font-size: 18px; }
      iframe { width: 100%; height: 760px; border: 1px solid #a1a1aa; border-radius: 12px; background: white; }
      @media (max-width: 1100px) { main { grid-template-columns: 1fr; } }
    </style>
  </head>
  <body>
    <h1>Transactional email comparison</h1>
    <main>"""
        + "".join(cards)
        + """
    </main>
  </body>
</html>""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    render_preview(arguments.output.resolve())


if __name__ == "__main__":
    main()
