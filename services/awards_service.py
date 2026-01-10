"""
Awards service for fetching entertainment award news from multiple sources.
"""
import os
import re
import requests
from datetime import datetime, timezone
from typing import Optional

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


# Major award shows to track (ordered by current relevance - January)
AWARD_SHOWS = [
    "Golden Globes",  # January
    "SAG Awards",     # February
    "BAFTA",          # February
    "Oscars",         # March
    "Academy Awards",
    "Grammys",        # February
    "Grammy Awards",
    "Emmys",          # September
    "Emmy Awards",
    "Tony Awards",    # June
    "Critics Choice",
    "Sundance",
]


def get_news_api_key() -> Optional[str]:
    """Get NewsAPI key from environment."""
    return os.environ.get("NEWS_API_KEY")


def fetch_awards_news_api() -> list[dict]:
    """
    Fetch award-related news using NewsAPI.
    """
    api_key = get_news_api_key()
    if not api_key:
        return []

    try:
        query = " OR ".join(AWARD_SHOWS[:5])

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 10,
            "apiKey": api_key,
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        articles = []
        for article in data.get("articles", []):
            articles.append({
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "url": article.get("url", ""),
                "thumbnail": article.get("urlToImage"),
                "source": article.get("source", {}).get("name", "News"),
                "published": article.get("publishedAt", datetime.now(timezone.utc).isoformat()),
                "type": "awards",
            })

        return articles

    except Exception as e:
        print(f"NewsAPI error: {e}")
        return []


def scrape_variety_awards() -> list[dict]:
    """Scrape Variety's awards section."""
    if not HAS_BS4:
        return []

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }

        response = requests.get("https://variety.com/v/awards/", headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []

        for card in soup.select("article, .c-card, .o-card")[:10]:
            title_elem = card.select_one("h3, h2, .c-title, .o-card__title")
            link_elem = card.select_one("a[href]")
            img_elem = card.select_one("img")

            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            url = link_elem.get("href", "") if link_elem else ""
            thumbnail = None

            if img_elem:
                thumbnail = img_elem.get("src") or img_elem.get("data-src") or img_elem.get("data-lazy-src")

            if title and url:
                articles.append({
                    "title": title,
                    "description": "",
                    "url": url if url.startswith("http") else f"https://variety.com{url}",
                    "thumbnail": thumbnail,
                    "source": "Variety",
                    "published": datetime.now(timezone.utc).isoformat(),
                    "type": "awards",
                })

        return articles[:5]

    except Exception as e:
        print(f"Variety scraping error: {e}")
        return []


def scrape_hollywood_reporter() -> list[dict]:
    """Scrape The Hollywood Reporter's awards section."""
    if not HAS_BS4:
        return []

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        response = requests.get("https://www.hollywoodreporter.com/t/awards/", headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []

        for card in soup.select("article, .lrv-u-flex, .c-card")[:10]:
            title_elem = card.select_one("h3, h2, .c-title, a.c-title")
            link_elem = card.select_one("a[href*='/awards/'], a[href*='hollywoodreporter']")
            img_elem = card.select_one("img")

            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            url = ""
            if link_elem:
                url = link_elem.get("href", "")
            elif title_elem.name == "a":
                url = title_elem.get("href", "")

            thumbnail = None
            if img_elem:
                thumbnail = img_elem.get("src") or img_elem.get("data-src")

            if title and url and len(title) > 10:
                articles.append({
                    "title": title,
                    "description": "",
                    "url": url if url.startswith("http") else f"https://www.hollywoodreporter.com{url}",
                    "thumbnail": thumbnail,
                    "source": "The Hollywood Reporter",
                    "published": datetime.now(timezone.utc).isoformat(),
                    "type": "awards",
                })

        return articles[:5]

    except Exception as e:
        print(f"Hollywood Reporter scraping error: {e}")
        return []


def scrape_deadline() -> list[dict]:
    """Scrape Deadline's awards section."""
    if not HAS_BS4:
        return []

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        response = requests.get("https://deadline.com/category/awards/", headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []

        for card in soup.select("article, .c-card")[:10]:
            title_elem = card.select_one("h2, h3, .entry-title, .c-title")
            link_elem = card.select_one("a[href*='deadline.com']")
            img_elem = card.select_one("img")

            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            url = link_elem.get("href", "") if link_elem else ""
            thumbnail = None

            if img_elem:
                thumbnail = img_elem.get("src") or img_elem.get("data-src")

            if title and url and len(title) > 10:
                articles.append({
                    "title": title,
                    "description": "",
                    "url": url,
                    "thumbnail": thumbnail,
                    "source": "Deadline",
                    "published": datetime.now(timezone.utc).isoformat(),
                    "type": "awards",
                })

        return articles[:5]

    except Exception as e:
        print(f"Deadline scraping error: {e}")
        return []


def scrape_ew_awards() -> list[dict]:
    """Scrape Entertainment Weekly's awards coverage."""
    if not HAS_BS4:
        return []

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        response = requests.get("https://ew.com/awards/", headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []

        for card in soup.select("article, .card, .mntl-card")[:10]:
            title_elem = card.select_one("h3, h2, .card__title, span.card__title")
            link_elem = card.select_one("a[href]")
            img_elem = card.select_one("img")

            title = ""
            if title_elem:
                title = title_elem.get_text(strip=True)

            url = link_elem.get("href", "") if link_elem else ""
            thumbnail = None

            if img_elem:
                thumbnail = img_elem.get("src") or img_elem.get("data-src")

            if title and url and len(title) > 10:
                articles.append({
                    "title": title,
                    "description": "",
                    "url": url if url.startswith("http") else f"https://ew.com{url}",
                    "thumbnail": thumbnail,
                    "source": "Entertainment Weekly",
                    "published": datetime.now(timezone.utc).isoformat(),
                    "type": "awards",
                })

        return articles[:4]

    except Exception as e:
        print(f"EW scraping error: {e}")
        return []


def scrape_indiewire() -> list[dict]:
    """Scrape IndieWire's awards coverage."""
    if not HAS_BS4:
        return []

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        response = requests.get("https://www.indiewire.com/c/awards/", headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []

        for card in soup.select("article, .c-card")[:10]:
            title_elem = card.select_one("h2, h3, .c-title")
            link_elem = card.select_one("a[href]")
            img_elem = card.select_one("img")

            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            url = link_elem.get("href", "") if link_elem else ""
            thumbnail = None

            if img_elem:
                thumbnail = img_elem.get("src") or img_elem.get("data-src")

            if title and url and len(title) > 10:
                articles.append({
                    "title": title,
                    "description": "",
                    "url": url if url.startswith("http") else f"https://www.indiewire.com{url}",
                    "thumbnail": thumbnail,
                    "source": "IndieWire",
                    "published": datetime.now(timezone.utc).isoformat(),
                    "type": "awards",
                })

        return articles[:4]

    except Exception as e:
        print(f"IndieWire scraping error: {e}")
        return []


def fetch_award_headlines() -> list[dict]:
    """
    Fetch award-related headlines from multiple sources.
    Tries API first, then scrapes multiple entertainment sites.
    """
    all_articles = []

    # Try NewsAPI first
    api_articles = fetch_awards_news_api()
    all_articles.extend(api_articles)

    # Scrape multiple sources
    all_articles.extend(scrape_variety_awards())
    all_articles.extend(scrape_hollywood_reporter())
    all_articles.extend(scrape_deadline())
    all_articles.extend(scrape_ew_awards())
    all_articles.extend(scrape_indiewire())

    # Deduplicate by URL and similar titles
    seen_urls = set()
    seen_titles = set()
    unique_articles = []

    for article in all_articles:
        url = article.get("url", "")
        title = article.get("title", "").lower()[:50]  # First 50 chars for fuzzy matching

        if url and url not in seen_urls and title not in seen_titles:
            seen_urls.add(url)
            seen_titles.add(title)
            unique_articles.append(article)

    # Sort to interleave sources (variety of perspectives)
    # Group by source, then take one from each in round-robin
    by_source = {}
    for article in unique_articles:
        source = article.get("source", "Other")
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(article)

    interleaved = []
    max_per_source = 3
    for i in range(max_per_source):
        for source in by_source:
            if i < len(by_source[source]):
                interleaved.append(by_source[source][i])

    return interleaved[:12]
