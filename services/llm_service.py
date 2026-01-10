"""
LLM service for generating episode summaries using Claude API.
"""
import os
from typing import Optional

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


def get_client() -> Optional["Anthropic"]:
    """Get Anthropic client if API key is available."""
    if not HAS_ANTHROPIC:
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    return Anthropic(api_key=api_key)


def summarize_episode(title: str, description: str, podcast_name: str) -> str:
    """
    Generate a 2-sentence 'Is it worth it?' summary for a podcast episode.

    Falls back to a truncated description if no API key is available.
    """
    client = get_client()

    if not client:
        # Fallback: return first 200 chars of description
        if description:
            clean_desc = ' '.join(description.split())  # Normalize whitespace
            if len(clean_desc) > 200:
                return clean_desc[:197] + "..."
            return clean_desc
        return "New episode available. Check it out!"

    try:
        prompt = f"""You're a podcast recommendation assistant. Based on this episode info, write exactly 2 sentences in a casual, helpful tone answering "Is it worth listening to?"

Podcast: {podcast_name}
Episode Title: {title}
Description: {description[:1000] if description else 'No description available'}

Be specific about who the guest is (if mentioned) and what makes this episode interesting. Keep it concise and engaging."""

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=150,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text.strip()

    except Exception as e:
        print(f"LLM summarization error: {e}")
        # Fallback to truncated description
        if description:
            clean_desc = ' '.join(description.split())
            if len(clean_desc) > 200:
                return clean_desc[:197] + "..."
            return clean_desc
        return "New episode available. Check it out!"


def batch_summarize_episodes(episodes: list[dict]) -> list[dict]:
    """
    Add summaries to a list of episode dictionaries.
    Modifies episodes in place and returns the list.
    """
    for episode in episodes:
        if episode.get('type') == 'podcast':
            episode['summary'] = summarize_episode(
                title=episode.get('title', ''),
                description=episode.get('description', ''),
                podcast_name=episode.get('source', 'Podcast')
            )

    return episodes
