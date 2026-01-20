"""
The Daily Cut - A mobile-first entertainment feed app.
"""
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, render_template, request, jsonify

from services.podcast_service import fetch_recent_episodes
from services.youtube_service import search_interviews
from services.awards_service import fetch_award_headlines
from services.llm_service import batch_summarize_episodes
from services.email_service import send_daily_digest


# Upcoming award shows (update these dates annually)
AWARD_SHOWS_2025 = [
    {"name": "Golden Globes", "date": "2025-01-05", "network": "CBS"},
    {"name": "Critics Choice Awards", "date": "2025-01-12", "network": "E!"},
    {"name": "SAG Awards", "date": "2025-02-23", "network": "Netflix"},
    {"name": "Grammy Awards", "date": "2025-02-02", "network": "CBS"},
    {"name": "BAFTA Film Awards", "date": "2025-02-16", "network": "BBC"},
    {"name": "Oscars", "date": "2025-03-02", "network": "ABC"},
    {"name": "Tony Awards", "date": "2025-06-08", "network": "CBS"},
    {"name": "Emmy Awards", "date": "2025-09-21", "network": "ABC"},
]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Settings file path
SETTINGS_FILE = Path(__file__).parent / "user_settings.json"


def load_settings() -> dict:
    """Load user settings from JSON file."""
    default_settings = {
        "interests": [],
        "blocked": [],
        "awardMode": False
    }

    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return {**default_settings, **json.load(f)}
        except Exception:
            return default_settings

    return default_settings


def save_settings(settings: dict) -> None:
    """Save user settings to JSON file."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def filter_blocked_content(items: list[dict], blocked_topics: list[str]) -> list[dict]:
    """Filter out items containing blocked keywords."""
    if not blocked_topics:
        return items

    filtered = []
    for item in items:
        title = item.get("title", "").lower()
        description = item.get("description", "").lower()
        source = item.get("source", "").lower()

        is_blocked = any(
            blocked.lower() in title or
            blocked.lower() in description or
            blocked.lower() in source
            for blocked in blocked_topics
        )

        if not is_blocked:
            filtered.append(item)

    return filtered


# ==================== Routes ====================

@app.route("/")
def index():
    """Main feed page."""
    return render_template("index.html")


@app.route("/settings")
def settings():
    """Settings page."""
    return render_template("settings.html")


# ==================== API Routes ====================

@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Get current user settings."""
    return jsonify(load_settings())


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Update user settings."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    settings = {
        "interests": data.get("interests", []),
        "blocked": data.get("blocked", []),
        "awardMode": data.get("awardMode", False)
    }

    save_settings(settings)
    return jsonify({"status": "success"})


@app.route("/api/feed", methods=["GET"])
def get_feed():
    """
    Get the main feed combining all content sources.

    Returns a list of items sorted by recency with:
    - Podcast episodes from the last 24 hours
    - YouTube interviews from the last 48 hours
    - Award headlines (if award mode is on)
    """
    settings = load_settings()
    blocked_topics = settings.get("blocked", [])
    interests = settings.get("interests", [])
    award_mode = settings.get("awardMode", False)

    all_items = []

    # 1. Fetch recent podcast episodes (always on)
    try:
        episodes = fetch_recent_episodes(hours=48)
        episodes = filter_blocked_content(episodes, blocked_topics)

        # Add LLM summaries
        episodes = batch_summarize_episodes(episodes)
        all_items.extend(episodes)
    except Exception as e:
        print(f"Error fetching podcasts: {e}")

    # 2. Fetch YouTube interviews (if user has interests)
    if interests:
        try:
            interviews = search_interviews(
                interests=interests,
                hours=48,
                blocked_topics=blocked_topics
            )
            all_items.extend(interviews)
        except Exception as e:
            print(f"Error fetching interviews: {e}")

    # 3. Fetch award headlines (if award mode is on)
    if award_mode:
        try:
            headlines = fetch_award_headlines()
            headlines = filter_blocked_content(headlines, blocked_topics)
            all_items.extend(headlines)
        except Exception as e:
            print(f"Error fetching awards: {e}")

    # Sort all items by published date (newest first)
    def get_sort_key(item):
        published = item.get("published", "")
        # Handle different date formats
        if published:
            return published
        return "0"  # Items without dates go to the end

    all_items.sort(key=get_sort_key, reverse=True)

    return jsonify({"items": all_items})


@app.route("/api/podcasts", methods=["GET"])
def get_podcasts():
    """Get recent podcast episodes only."""
    settings = load_settings()
    blocked_topics = settings.get("blocked", [])

    episodes = fetch_recent_episodes(hours=48)
    episodes = filter_blocked_content(episodes, blocked_topics)
    episodes = batch_summarize_episodes(episodes)

    return jsonify({"items": episodes})


@app.route("/api/interviews", methods=["GET"])
def get_interviews():
    """Get recent interviews based on user interests."""
    settings = load_settings()
    interests = settings.get("interests", [])
    blocked_topics = settings.get("blocked", [])

    if not interests:
        return jsonify({"items": [], "message": "No interests configured"})

    interviews = search_interviews(
        interests=interests,
        hours=48,
        blocked_topics=blocked_topics
    )

    return jsonify({"items": interviews})


@app.route("/api/awards", methods=["GET"])
def get_awards():
    """Get award headlines."""
    settings = load_settings()
    blocked_topics = settings.get("blocked", [])

    headlines = fetch_award_headlines()
    headlines = filter_blocked_content(headlines, blocked_topics)

    return jsonify({"items": headlines})


@app.route("/api/awards/countdown", methods=["GET"])
def get_award_countdown():
    """Get countdown to the next award show."""
    now = datetime.now(timezone.utc).date()

    upcoming = []
    for show in AWARD_SHOWS_2025:
        show_date = datetime.strptime(show["date"], "%Y-%m-%d").date()
        days_until = (show_date - now).days

        if days_until >= 0:
            upcoming.append({
                "name": show["name"],
                "date": show["date"],
                "network": show["network"],
                "days_until": days_until,
                "is_today": days_until == 0,
                "is_tomorrow": days_until == 1,
            })

    # Sort by date
    upcoming.sort(key=lambda x: x["days_until"])

    return jsonify({
        "next": upcoming[0] if upcoming else None,
        "upcoming": upcoming[:5]
    })


@app.route("/api/send-digest", methods=["GET", "POST"])
def send_digest_email():
    """Send the daily digest email now. Requires CRON_SECRET for authentication."""
    # Verify cron secret for automated requests
    cron_secret = os.environ.get("CRON_SECRET")
    provided_secret = request.headers.get("X-Cron-Secret") or request.args.get("secret")

    if not cron_secret:
        return jsonify({"error": "CRON_SECRET not configured"}), 500

    if provided_secret != cron_secret:
        return jsonify({"error": "Unauthorized"}), 401

    settings = load_settings()
    blocked_topics = settings.get("blocked", [])
    interests = settings.get("interests", [])
    award_mode = settings.get("awardMode", False)

    all_items = []

    # Fetch all content (same logic as /api/feed)
    try:
        episodes = fetch_recent_episodes(hours=48)
        episodes = filter_blocked_content(episodes, blocked_topics)
        episodes = batch_summarize_episodes(episodes)
        all_items.extend(episodes)
    except Exception as e:
        print(f"Error fetching podcasts for email: {e}")

    if interests:
        try:
            interviews = search_interviews(
                interests=interests,
                hours=48,
                blocked_topics=blocked_topics
            )
            all_items.extend(interviews)
        except Exception as e:
            print(f"Error fetching interviews for email: {e}")

    if award_mode:
        try:
            headlines = fetch_award_headlines()
            headlines = filter_blocked_content(headlines, blocked_topics)
            all_items.extend(headlines)
        except Exception as e:
            print(f"Error fetching awards for email: {e}")

    # Sort by date
    all_items.sort(key=lambda x: x.get("published", ""), reverse=True)

    # Send the email
    result = send_daily_digest(all_items)

    if result["success"]:
        return jsonify(result)
    else:
        return jsonify(result), 500


# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return render_template("base.html"), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


# ==================== Main ====================

if __name__ == "__main__":
    # Create settings file if it doesn't exist
    if not SETTINGS_FILE.exists():
        save_settings({
            "interests": [],
            "blocked": [],
            "awardMode": False
        })

    # Run in debug mode for development
    app.run(debug=True, host="0.0.0.0", port=5001)
