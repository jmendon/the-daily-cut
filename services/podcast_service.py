"""
Podcast RSS feed service for tracking new episodes.
"""
import feedparser
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
from typing import Optional


# Hardcoded podcast RSS feeds with Spotify show IDs
PODCAST_FEEDS = {
    "SmartLess": {
        "rss": "https://feeds.simplecast.com/4T39_jAj",
        "spotify_show": "1bJRgaFZHuzifad4IAApFR",
        "link_type": "spotify",
    },
    "Conan O'Brien Needs a Friend": {
        "rss": "https://feeds.simplecast.com/dHoohVNH",
        "spotify_show": "4fIONMwaYRqfSClxLzzFNH",
        "link_type": "spotify",
    },
    "Armchair Expert": {
        "rss": "https://feeds.megaphone.fm/armchair-expert",
        "spotify_show": "6kAsbP8pxwaU2kPibKTuHE",
        "link_type": "spotify",
    },
    "Good Hang with Amy Poehler": {
        "rss": "https://feeds.simplecast.com/LdQjTvPL",
        "youtube_channel": "UCp0hYYBW6IMayGgR-WeoCvQ",
        "link_type": "youtube",
    },
}


def get_spotify_search_url(podcast_name: str, episode_title: str) -> str:
    """Generate a Spotify search URL for an episode."""
    from urllib.parse import quote_plus
    query = f"{podcast_name} {episode_title}"
    return f"https://open.spotify.com/search/{quote_plus(query)}"


def get_spotify_show_url(spotify_show_id: str) -> str:
    """Generate a direct Spotify show URL."""
    return f"https://open.spotify.com/show/{spotify_show_id}"


def get_youtube_search_url(podcast_name: str, episode_title: str) -> str:
    """Generate a YouTube search URL for an episode."""
    from urllib.parse import quote_plus
    query = f"{podcast_name} {episode_title}"
    return f"https://www.youtube.com/results?search_query={quote_plus(query)}"


def get_youtube_channel_url(channel_id: str) -> str:
    """Generate a YouTube channel URL."""
    return f"https://www.youtube.com/channel/{channel_id}"


def get_episode_thumbnail(entry: dict) -> Optional[str]:
    """Extract thumbnail from podcast episode entry."""
    # Try various common locations for episode artwork
    if hasattr(entry, 'image') and entry.image:
        if isinstance(entry.image, dict):
            return entry.image.get('href') or entry.image.get('url')
        return str(entry.image)

    # Check media content
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if media.get('medium') == 'image' or 'image' in media.get('type', ''):
                return media.get('url')

    # Check media thumbnail
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        return entry.media_thumbnail[0].get('url')

    # Check itunes image
    if hasattr(entry, 'itunes_image') and entry.itunes_image:
        return entry.itunes_image.get('href')

    return None


def get_feed_thumbnail(feed: dict) -> Optional[str]:
    """Get the podcast's main artwork from the feed."""
    if hasattr(feed, 'image') and feed.image:
        if isinstance(feed.image, dict):
            return feed.image.get('href') or feed.image.get('url')

    if hasattr(feed, 'itunes_image') and feed.itunes_image:
        return feed.itunes_image.get('href')

    return None


def parse_published_date(entry: dict) -> Optional[datetime]:
    """Parse the published date from various possible fields."""
    date_str = None

    if hasattr(entry, 'published') and entry.published:
        date_str = entry.published
    elif hasattr(entry, 'updated') and entry.updated:
        date_str = entry.updated
    elif hasattr(entry, 'pubDate'):
        date_str = entry.pubDate

    if date_str:
        try:
            parsed = date_parser.parse(date_str)
            # Ensure timezone aware
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except Exception:
            return None

    return None


def fetch_recent_episodes(hours: int = 48) -> list[dict]:
    """
    Fetch episodes published within the last N hours from all tracked podcasts.

    Returns a list of episode dictionaries with:
    - title: Episode title
    - description: Episode description
    - url: Spotify link for the episode
    - thumbnail: Episode or podcast artwork URL
    - source: Podcast name
    - published: ISO format datetime string
    - type: 'podcast'
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    episodes = []

    for podcast_name, podcast_info in PODCAST_FEEDS.items():
        feed_url = podcast_info["rss"]
        link_type = podcast_info.get("link_type", "spotify")

        try:
            feed = feedparser.parse(feed_url)

            if not feed.entries:
                continue

            # Get feed-level thumbnail as fallback
            feed_thumbnail = get_feed_thumbnail(feed.feed)

            for entry in feed.entries[:5]:  # Check last 5 episodes
                published = parse_published_date(entry)

                if published and published > cutoff:
                    thumbnail = get_episode_thumbnail(entry) or feed_thumbnail
                    episode_title = entry.get('title', 'Untitled Episode')

                    # Generate URL based on link type
                    if link_type == "youtube":
                        episode_url = get_youtube_search_url(podcast_name, episode_title)
                        show_url = get_youtube_channel_url(podcast_info.get("youtube_channel", ""))
                    else:
                        episode_url = get_spotify_search_url(podcast_name, episode_title)
                        show_url = get_spotify_show_url(podcast_info.get("spotify_show", ""))

                    episodes.append({
                        "title": episode_title,
                        "description": entry.get('summary', entry.get('description', '')),
                        "url": episode_url,
                        "thumbnail": thumbnail,
                        "source": podcast_name,
                        "published": published.isoformat(),
                        "type": "podcast",
                        "link_type": link_type,
                        "show_url": show_url,
                    })
        except Exception as e:
            print(f"Error fetching {podcast_name}: {e}")
            continue

    # Sort by published date, newest first
    episodes.sort(key=lambda x: x['published'], reverse=True)

    return episodes


def get_all_podcasts() -> list[dict]:
    """Get list of all tracked podcasts with their latest episode info."""
    podcasts = []

    for podcast_name, podcast_info in PODCAST_FEEDS.items():
        feed_url = podcast_info["rss"]

        try:
            feed = feedparser.parse(feed_url)

            if feed.entries:
                latest = feed.entries[0]
                podcasts.append({
                    "name": podcast_name,
                    "feed_url": feed_url,
                    "spotify_url": get_spotify_show_url(podcast_info["spotify_show"]),
                    "latest_episode": latest.get('title', 'Unknown'),
                    "thumbnail": get_episode_thumbnail(latest) or get_feed_thumbnail(feed.feed)
                })
        except Exception:
            podcasts.append({
                "name": podcast_name,
                "feed_url": feed_url,
                "spotify_url": get_spotify_show_url(podcast_info["spotify_show"]),
                "latest_episode": "Error fetching",
                "thumbnail": None
            })

    return podcasts
