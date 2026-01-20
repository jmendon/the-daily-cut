"""
Email service for sending daily digest emails via Resend.
"""
import os
from datetime import datetime, timezone

import resend

# Hardcoded recipient email
RECIPIENT_EMAIL = "pri.mendon@gmail.com"

# Initialize Resend with API key
resend.api_key = os.environ.get("RESEND_API_KEY")


def generate_digest_html(items: list[dict]) -> str:
    """Generate HTML content for the daily digest email."""
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    # Group items by type
    podcasts = [i for i in items if i.get("type") == "podcast"]
    interviews = [i for i in items if i.get("type") == "interview"]
    awards = [i for i in items if i.get("type") == "award"]

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>The Daily Cut - {today}</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #0a0a0a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0a0a0a;">
            <tr>
                <td align="center" style="padding: 20px;">
                    <table role="presentation" width="100%" style="max-width: 600px; background-color: #141414; border-radius: 12px; overflow: hidden;">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #e50914 0%, #b20710 100%); padding: 30px 20px; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">The Daily Cut</h1>
                                <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.85); font-size: 14px;">{today}</p>
                            </td>
                        </tr>

                        <!-- Content -->
                        <tr>
                            <td style="padding: 20px;">
    """

    # Podcasts section
    if podcasts:
        html += _generate_section("New Podcast Episodes", podcasts, "podcast")

    # Interviews section
    if interviews:
        html += _generate_section("Latest Interviews", interviews, "interview")

    # Awards section
    if awards:
        html += _generate_section("Award News", awards, "award")

    # No content fallback
    if not items:
        html += """
                                <div style="text-align: center; padding: 40px 20px; color: #888888;">
                                    <p style="margin: 0; font-size: 16px;">No new content today. Check back tomorrow!</p>
                                </div>
        """

    # Footer
    html += """
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding: 20px; border-top: 1px solid #2a2a2a; text-align: center;">
                                <p style="margin: 0; color: #666666; font-size: 12px;">
                                    Your daily entertainment digest from The Daily Cut
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    return html


def _generate_section(title: str, items: list[dict], item_type: str) -> str:
    """Generate HTML for a content section."""
    # Type icons/labels
    type_colors = {
        "podcast": "#1DB954",  # Spotify green
        "interview": "#FF0000",  # YouTube red
        "award": "#FFD700"  # Gold
    }
    color = type_colors.get(item_type, "#e50914")

    html = f"""
                                <div style="margin-bottom: 30px;">
                                    <h2 style="margin: 0 0 15px 0; color: #ffffff; font-size: 18px; font-weight: 600; padding-bottom: 10px; border-bottom: 2px solid {color};">
                                        {title}
                                    </h2>
    """

    for item in items[:5]:  # Limit to 5 items per section
        title_text = item.get("title", "Untitled")
        source = item.get("source", "")
        description = item.get("summary") or item.get("description", "")
        if len(description) > 150:
            description = description[:147] + "..."

        link = item.get("spotify_url") or item.get("youtube_url") or item.get("url") or "#"
        thumbnail = item.get("thumbnail", "")

        html += f"""
                                    <div style="margin-bottom: 15px; padding: 15px; background-color: #1a1a1a; border-radius: 8px;">
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                            <tr>
        """

        if thumbnail:
            html += f"""
                                                <td width="80" valign="top" style="padding-right: 12px;">
                                                    <img src="{thumbnail}" alt="" width="80" height="80" style="border-radius: 6px; object-fit: cover; display: block;">
                                                </td>
            """

        html += f"""
                                                <td valign="top">
                                                    <a href="{link}" style="color: #ffffff; text-decoration: none; font-size: 15px; font-weight: 600; line-height: 1.3; display: block; margin-bottom: 4px;">
                                                        {title_text}
                                                    </a>
                                                    <p style="margin: 0 0 6px 0; color: {color}; font-size: 12px; font-weight: 500;">
                                                        {source}
                                                    </p>
                                                    <p style="margin: 0; color: #999999; font-size: 13px; line-height: 1.4;">
                                                        {description}
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </div>
        """

    html += """
                                </div>
    """

    return html


def send_daily_digest(items: list[dict]) -> dict:
    """
    Send the daily digest email.

    Args:
        items: List of feed items to include in the digest

    Returns:
        dict with status and message/error
    """
    if not resend.api_key:
        return {"success": False, "error": "RESEND_API_KEY not configured"}

    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    html_content = generate_digest_html(items)

    try:
        params = {
            "from": "The Daily Cut <thedailycut@atlasavengers.com>",
            "to": [RECIPIENT_EMAIL],
            "subject": f"The Daily Cut - {today}",
            "html": html_content,
        }

        response = resend.Emails.send(params)

        return {
            "success": True,
            "message": f"Email sent to {RECIPIENT_EMAIL}",
            "id": response.get("id") if isinstance(response, dict) else getattr(response, "id", None)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
