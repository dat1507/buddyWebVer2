"""Shared VGU Buddy transactional-email presentation primitives."""

from __future__ import annotations

from html import escape


def render_branded_email_html(
    *,
    document_title: str,
    preheader: str,
    logo_url: str,
    heading: str,
    message_html: str,
    cta_label: str,
    cta_url: str,
    notice_html: str,
    fallback_url: str | None = None,
) -> str:
    """Render the table-based design established by Received Invitation.

    ``message_html`` and ``notice_html`` are server-owned fragments. Callers must escape every
    dynamic value before including it in either fragment.
    """

    escaped_document_title = escape(document_title, quote=False)
    escaped_preheader = escape(preheader, quote=False)
    escaped_logo_url = escape(logo_url, quote=True)
    escaped_heading = escape(heading, quote=False)
    escaped_cta_label = escape(cta_label, quote=False)
    escaped_cta_url = escape(cta_url, quote=True)
    fallback_html = ""
    if fallback_url is not None:
        escaped_fallback_url = escape(fallback_url, quote=True)
        fallback_html = f"""
                <p style="margin:28px 0 8px;color:#52525b;font-size:13px;line-height:1.5;">If the button does not work, copy and paste this link into your browser:</p>
                <p style="margin:0 0 28px;font-size:13px;line-height:1.5;word-break:break-all;"><a href="{escaped_fallback_url}" style="color:#c2410c;text-decoration:underline;">{escaped_fallback_url}</a></p>"""

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escaped_document_title}</title>
    <style>
      @media only screen and (max-width: 620px) {{
        .email-shell {{ width: 100% !important; }}
        .email-content {{ padding: 32px 24px !important; }}
        .email-footer {{ padding: 24px !important; }}
        .email-button {{ display: block !important; text-align: center !important; }}
      }}
    </style>
  </head>
  <body style="margin:0;padding:0;background:#f4f4f5;color:#171717;font-family:Arial,Helvetica,sans-serif;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
      {escaped_preheader}
    </div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;background:#f4f4f5;">
      <tr>
        <td align="center" style="padding:32px 12px;">
          <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" class="email-shell" style="width:600px;max-width:600px;background:#ffffff;border:1px solid #e4e4e7;border-radius:16px;overflow:hidden;">
            <tr>
              <td align="center" style="background:#000000;padding:18px 24px;">
                <img src="{escaped_logo_url}" width="160" alt="VGU Buddy Program" style="display:block;width:160px;max-width:100%;height:auto;border:0;">
              </td>
            </tr>
            <tr>
              <td class="email-content" style="padding:40px 48px;">
                <p style="margin:0 0 12px;color:#ff670d;font-size:13px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;">VGU Buddy Program</p>
                <h1 style="margin:0 0 20px;color:#000000;font-size:28px;line-height:1.25;font-weight:700;">{escaped_heading}</h1>
                <p style="margin:0 0 28px;color:#3f3f46;font-size:16px;line-height:1.65;">{message_html}</p>
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 0 28px;">
                  <tr>
                    <td bgcolor="#ff670d" style="border-radius:10px;">
                      <a href="{escaped_cta_url}" class="email-button" style="display:inline-block;padding:14px 24px;color:#000000;font-size:16px;font-weight:700;line-height:1;text-decoration:none;border-radius:10px;">{escaped_cta_label}</a>
                    </td>
                  </tr>
                </table>{fallback_html}
                <p style="margin:0;padding:16px 18px;background:#fff7ed;border-left:4px solid #ff670d;border-radius:8px;color:#52525b;font-size:14px;line-height:1.5;">{notice_html}</p>
              </td>
            </tr>
            <tr>
              <td class="email-footer" style="padding:24px 48px;background:#000000;color:#ffffff;">
                <p style="margin:0;font-size:14px;font-weight:700;line-height:1.5;">VGU Buddy Program</p>
                <p style="margin:2px 0 0;color:#d4d4d8;font-size:13px;line-height:1.5;">Vietnamese-German University</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


__all__ = ["render_branded_email_html"]
