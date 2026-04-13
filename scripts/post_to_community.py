"""
post_to_community.py — X (Twitter) Community Thread Integration.

Posts a new reply in the pinned RaajaDharma thread inside the community:
  https://x.com/i/communities/1981771124343283876

Supports:
  - Automated posting via tweepy (requires X API keys in .env)
  - Manual fallback: prints the formatted tweet text to the terminal

Usage:
    python scripts/post_to_community.py --entry-number 3 --media screenshot.png
"""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path
from typing import Optional

import yaml

try:
    import tweepy

    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

COMMUNITY_URL = "https://x.com/i/communities/1981771124343283876"
MASTER_YAML_DEFAULT = Path(__file__).parent.parent / "yaml" / "raajadharma-log.yaml"
TWEET_TEMPLATE = (
    "Update #{n} • {date} • RaajaDharma Family Log\n"
    "Community: {community_url}\n"
    "[YAML appended below]\n\n"
    "{yaml_snippet}"
)
MAX_TWEET_CHARS = 280


def _load_entry(yaml_path: Path, entry_number: int) -> dict:
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    for entry in data.get("updates", []):
        if entry.get("entry_number") == entry_number:
            return entry
    raise KeyError(f"No entry with entry_number={entry_number} in {yaml_path}")


def _build_tweet_text(entry: dict) -> str:
    yaml_snippet = yaml.dump(
        {k: v for k, v in entry.items() if k not in ("community_url", "verified_by")},
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    full_text = TWEET_TEMPLATE.format(
        n=entry["entry_number"],
        date=entry["date"],
        community_url=COMMUNITY_URL,
        yaml_snippet=yaml_snippet,
    )
    # Trim to X character limit if needed
    if len(full_text) > MAX_TWEET_CHARS:
        header = TWEET_TEMPLATE.format(
            n=entry["entry_number"],
            date=entry["date"],
            community_url=COMMUNITY_URL,
            yaml_snippet="",
        )
        available = MAX_TWEET_CHARS - len(header) - 4  # 4 for " ..."
        trimmed = yaml_snippet[:available] + " ..."
        full_text = header + trimmed
    return full_text


def _get_tweepy_client() -> "tweepy.Client | None":
    api_key = os.getenv("X_API_KEY", "").strip()
    api_secret = os.getenv("X_API_SECRET", "").strip()
    access_token = os.getenv("X_ACCESS_TOKEN", "").strip()
    access_secret = os.getenv("X_ACCESS_TOKEN_SECRET", "").strip()

    if not all([api_key, api_secret, access_token, access_secret]):
        return None

    if not TWEEPY_AVAILABLE:
        return None

    return tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )


def post_reply(
    entry_number: int,
    reply_to_tweet_id: str,
    media_paths: list[Path] | None = None,
    yaml_path: Path = MASTER_YAML_DEFAULT,
    dry_run: bool = False,
) -> str | None:
    """
    Post (or print) a tweet reply in the community thread.

    Parameters
    ----------
    entry_number      : The update entry number to tweet.
    reply_to_tweet_id : The tweet ID of the previous post in the thread (or the pinned post).
    media_paths       : Optional list of media files to attach (screenshot, video, affidavit).
    yaml_path         : Path to the master YAML.
    dry_run           : If True, print the tweet text but do not post.

    Returns
    -------
    The new tweet ID (str) if posted automatically, or None in manual/dry-run mode.
    """
    entry = _load_entry(yaml_path, entry_number)
    tweet_text = _build_tweet_text(entry)

    print("\n" + "=" * 60)
    print(f"📢  Tweet Preview — Entry #{entry_number}")
    print("=" * 60)
    print(tweet_text)
    print(f"\nCharacter count: {len(tweet_text)} / {MAX_TWEET_CHARS}")
    print("=" * 60 + "\n")

    if dry_run:
        print("ℹ️  Dry-run mode — not posting to X.")
        return None

    client = _get_tweepy_client()
    if client is None:
        _print_manual_instructions(tweet_text, reply_to_tweet_id)
        return None

    try:
        # Upload media if provided
        media_ids: list[str] = []
        if media_paths:
            # Media upload requires v1.1 API
            auth = tweepy.OAuth1UserHandler(
                os.getenv("X_API_KEY"),
                os.getenv("X_API_SECRET"),
                os.getenv("X_ACCESS_TOKEN"),
                os.getenv("X_ACCESS_TOKEN_SECRET"),
            )
            api_v1 = tweepy.API(auth)
            for mp in media_paths:
                print(f"⬆️  Uploading media: {mp}")
                media = api_v1.media_upload(str(mp))
                media_ids.append(str(media.media_id))

        kwargs: dict = {
            "text": tweet_text,
            "in_reply_to_tweet_id": reply_to_tweet_id,
        }
        if media_ids:
            kwargs["media_ids"] = media_ids

        response = client.create_tweet(**kwargs)
        new_tweet_id = str(response.data["id"])
        print(f"✅  Posted successfully! Tweet ID: {new_tweet_id}")
        print(f"    https://x.com/i/web/status/{new_tweet_id}")
        return new_tweet_id

    except Exception as exc:  # noqa: BLE001
        print(f"❌  Failed to post automatically: {exc}", file=sys.stderr)
        _print_manual_instructions(tweet_text, reply_to_tweet_id)
        return None


def _print_manual_instructions(tweet_text: str, reply_to_tweet_id: str) -> None:
    print(
        textwrap.dedent(
            f"""
            ╔══════════════════════════════════════════════════════════╗
            ║          MANUAL POSTING INSTRUCTIONS                    ║
            ╚══════════════════════════════════════════════════════════╝

            1. Open X (Twitter) in your browser.
            2. Navigate to the community thread:
               {COMMUNITY_URL}
            3. Find the post with ID: {reply_to_tweet_id}
               (or reply to the last post in the thread)
            4. Copy-paste the following text as a REPLY:

            ── BEGIN TWEET TEXT ─────────────────────────────────────
            {tweet_text}
            ── END TWEET TEXT ───────────────────────────────────────

            5. Attach any media files (screenshot, video, affidavit).
            6. After posting, note the new tweet ID and run:
               raajadharma-log update-tweet-id --entry <N> --tweet-id <ID>

            ⏱️  Remember: after 1 hour, X locks the post → immutability achieved!
            """
        )
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Post an entry to the X community thread")
    parser.add_argument("--entry-number", type=int, required=True)
    parser.add_argument("--reply-to", type=str, default="", help="Tweet ID to reply to")
    parser.add_argument("--media", type=Path, nargs="*", default=None)
    parser.add_argument("--yaml", type=Path, default=MASTER_YAML_DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = post_reply(
        entry_number=args.entry_number,
        reply_to_tweet_id=args.reply_to,
        media_paths=args.media,
        yaml_path=args.yaml,
        dry_run=args.dry_run,
    )
    if result:
        print(f"New tweet ID: {result}")
