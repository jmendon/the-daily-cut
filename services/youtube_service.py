"""
YouTube search service for finding recent interviews.
Uses the YouTube Data API v3 with a web scraping fallback.
"""
import os
import re
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote_plus

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


# Priority channels for entertainment interviews
PRIORITY_CHANNELS = [
    "The Tonight Show Starring Jimmy Fallon",
    "The Late Show with Stephen Colbert",
    "Late Night with Seth Meyers",
    "Jimmy Kimmel Live",
    "The Late Late Show with James Corden",
    "The Drew Barrymore Show",
    "The Kelly Clarkson Show",
    "The Jennifer Hudson Show",
    "Good Morning America",
    "TODAY",
    "CBS Mornings",
    "Variety",
    "Vanity Fair",
    "The Hollywood Reporter",
    "Entertainment Tonight",
    "Access Hollywood",
    "E! News",
    "Hot Ones",
    "Wired",
    "GQ",
    "W Magazine",
    "Elle",
    "Vogue",
    "60 Minutes",
    "The View",
]

# Terms that indicate low-quality or irrelevant content
EXCLUDED_TERMS = [
    "kids", "children", "cartoon", "animation", "animated",
    "nursery", "rhyme", "toddler", "baby", "peppa",
    "cocomelon", "paw patrol", "sesame street",
    "toy", "unboxing", "gameplay", "playthrough",
    "reaction video", "fan made", "parody",
    "meme", "tiktok compilation", "shorts compilation",
    "asmr", "mukbang", "10 hours",
]

# TV show disambiguation - add context to avoid wrong matches
TV_SHOW_CONTEXT = {
    "the bear": "The Bear FX Hulu TV show",
    "succession": "Succession HBO TV show",
    "the office": "The Office TV show cast",
    "friends": "Friends TV show reunion",
    "wednesday": "Wednesday Netflix Jenna Ortega",
    "euphoria": "Euphoria HBO Zendaya",
    "house of the dragon": "House of the Dragon HBO",
    "the last of us": "The Last of Us HBO Pedro Pascal",
    "yellowjackets": "Yellowjackets Showtime",
    "abbott elementary": "Abbott Elementary ABC Quinta Brunson",
}


def get_youtube_api_key() -> Optional[str]:
    """Get YouTube Data API key from environment."""
    return os.environ.get("YOUTUBE_API_KEY")


def is_relevant_content(title: str, description: str, interest: str) -> bool:
    """
    Check if content is actually relevant to the interest.
    Returns True if the interest appears in the title or if it's from a priority channel.
    """
    title_lower = title.lower()
    desc_lower = description.lower()
    interest_lower = interest.lower()

    # Check for excluded terms
    combined = f"{title_lower} {desc_lower}"
    for excluded in EXCLUDED_TERMS:
        if excluded in combined:
            return False

    # For multi-word interests, check if most words appear
    interest_words = interest_lower.split()
    if len(interest_words) > 1:
        # For names like "Timothee Chalamet", check last name at minimum
        last_word = interest_words[-1]
        if last_word in title_lower:
            return True
        # Check if at least 2 words match for longer phrases
        matches = sum(1 for word in interest_words if word in title_lower)
        if matches >= min(2, len(interest_words)):
            return True
    else:
        # Single word - must appear in title
        if interest_lower in title_lower:
            return True

    return False


def get_search_query(interest: str) -> str:
    """
    Build an optimized search query for the interest.
    Adds context for ambiguous TV shows and interview keywords.
    """
    interest_lower = interest.lower().strip()

    # Check if this is a known TV show that needs disambiguation
    if interest_lower in TV_SHOW_CONTEXT:
        base_query = TV_SHOW_CONTEXT[interest_lower]
    else:
        base_query = interest

    return f"{base_query} interview"


def search_youtube_api(query: str, max_results: int = 10, published_after: datetime = None) -> list[dict]:
    """
    Search YouTube using the Data API v3.

    Returns list of video dictionaries.
    """
    api_key = get_youtube_api_key()
    if not api_key:
        return []

    base_url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "order": "date",
        "key": api_key,
        "relevanceLanguage": "en",
        "safeSearch": "moderate",  # Filter out inappropriate content
    }

    if published_after:
        params["publishedAfter"] = published_after.strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        videos = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId")

            if not video_id:
                continue

            # Check if from priority channel
            channel_title = snippet.get("channelTitle", "")
            is_priority = any(p.lower() in channel_title.lower() for p in PRIORITY_CHANNELS)

            videos.append({
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": get_best_thumbnail(snippet.get("thumbnails", {})),
                "source": channel_title,
                "published": snippet.get("publishedAt", ""),
                "type": "interview",
                "priority": is_priority,
            })

        return videos

    except Exception as e:
        print(f"YouTube API error: {e}")
        return []


def get_best_thumbnail(thumbnails: dict) -> Optional[str]:
    """Get the highest quality thumbnail available."""
    for quality in ["maxres", "high", "medium", "default"]:
        if quality in thumbnails:
            return thumbnails[quality].get("url")
    return None


def scrape_youtube_search(query: str, max_results: int = 10) -> list[dict]:
    """
    Fallback: Scrape YouTube search results.
    Note: This is less reliable and may break if YouTube changes their HTML.
    """
    if not HAS_BS4:
        return []

    try:
        search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()

        videos = []

        # Extract video data from YouTube's initial data JSON
        # Look for channelTitle as well for better filtering
        video_pattern = r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"([^"]+)"'
        channel_pattern = r'"ownerText":\{"runs":\[\{"text":"([^"]+)"'

        matches = re.findall(video_pattern, response.text)
        channels = re.findall(channel_pattern, response.text)

        seen_ids = set()
        for idx, (video_id, title) in enumerate(matches[:max_results * 2]):
            if video_id in seen_ids:
                continue
            seen_ids.add(video_id)

            if len(videos) >= max_results:
                break

            channel = channels[idx] if idx < len(channels) else "YouTube"
            is_priority = any(p.lower() in channel.lower() for p in PRIORITY_CHANNELS)

            videos.append({
                "title": title,
                "description": "",
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                "source": channel,
                "published": datetime.now(timezone.utc).isoformat(),
                "type": "interview",
                "priority": is_priority,
            })

        return videos

    except Exception as e:
        print(f"YouTube scraping error: {e}")
        return []


def search_interviews(interests: list[str], hours: int = 48, blocked_topics: list[str] = None) -> list[dict]:
    """
    Search for recent interviews related to user interests.

    Args:
        interests: List of topics/people to search for
        hours: How far back to search (default 48 hours)
        blocked_topics: Keywords to filter out

    Returns:
        List of video dictionaries sorted by priority and date
    """
    if not interests:
        return []

    blocked_topics = blocked_topics or []
    published_after = datetime.now(timezone.utc) - timedelta(hours=hours)

    all_videos = []
    seen_urls = set()

    for interest in interests:
        # Build optimized search query
        query = get_search_query(interest)

        # Use API only - scraping assigns fake timestamps which causes old videos to appear
        videos = search_youtube_api(query, max_results=8, published_after=published_after)

        for video in videos:
            url = video.get("url", "")
            if url in seen_urls:
                continue

            title = video.get("title", "")
            description = video.get("description", "")

            # Check relevance - must actually be about the interest
            if not is_relevant_content(title, description, interest):
                # Exception: always include priority channels
                if not video.get("priority", False):
                    continue

            # Check for user-blocked topics
            title_lower = title.lower()
            desc_lower = description.lower()

            is_blocked = any(
                blocked.lower() in title_lower or blocked.lower() in desc_lower
                for blocked in blocked_topics
            )

            if is_blocked:
                continue

            seen_urls.add(url)
            all_videos.append(video)

    # Sort: priority channels first, then by recency
    all_videos.sort(key=lambda x: x.get("published", ""), reverse=True)
    all_videos.sort(key=lambda x: x.get("priority", False), reverse=True)

    # Limit to top results
    return all_videos[:10]
