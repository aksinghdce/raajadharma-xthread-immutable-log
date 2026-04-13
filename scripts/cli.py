"""
cli.py — RaajaDharma Immutable Log CLI

A beginner-friendly command-line tool for the 9-member RaajaDharma Archery
Club DAO family.  Designed for family members aged 14+ with no coding
background.

Commands
--------
  append                Append a new entry to the immutable log
  blood-succession      Record a blood-succession transfer (Governor role)
  view-latest           Show the most recent log entry
  view-entry            Show a specific log entry by number
  generate-screenshot   Take a screenshot of an entry (for tweeting)
  generate-pdf          Create a printable PDF record of an entry
  post-to-community     Post an entry to the X community thread
  update-tweet-id       Link a posted tweet ID to a log entry
  validate              Validate the log for immutability violations
  init-thread           Print the first pinned post template for the community

Usage Examples
--------------
  raajadharma-log append \\
      --action governance_vote \\
      --wallet 0x1234... \\
      --desc "Vote to change archery practice day to Saturday"

  raajadharma-log blood-succession \\
      --wallet 0x1234... \\
      --successor-wallet 0x5678... \\
      --video-hash sha256:abc... \\
      --affidavit-hash sha256:def... \\
      --desc "Governor role transferred to eldest child"

  raajadharma-log view-latest
  raajadharma-log generate-screenshot --entry 3
  raajadharma-log post-to-community --entry 3 --reply-to 1234567890
  raajadharma-log validate
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
import yaml

# Allow running as `python scripts/cli.py` and as installed `raajadharma-log`
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from scripts.append_only_yaml import AppendOnlyYAML  # noqa: E402
from scripts.validate_yaml import main as run_validate  # noqa: E402

app = typer.Typer(
    name="raajadharma-log",
    help=(
        "🏹  RaajaDharma Archery Club DAO — Immutable Family Log CLI\n\n"
        "Community: https://x.com/i/communities/1981771124343283876"
    ),
    add_completion=False,
)

MASTER_YAML = _REPO_ROOT / "yaml" / "raajadharma-log.yaml"
COMMUNITY_URL = "https://x.com/i/communities/1981771124343283876"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_log(yaml_path: Path = MASTER_YAML) -> AppendOnlyYAML:
    return AppendOnlyYAML(yaml_path)


def _print_entry(entry: dict) -> None:
    typer.echo(
        typer.style(
            f"\n── Entry #{entry['entry_number']} ──────────────────────────────",
            fg=typer.colors.CYAN,
        )
    )
    typer.echo(yaml.dump(entry, allow_unicode=True, default_flow_style=False, sort_keys=False))


# ── Commands ──────────────────────────────────────────────────────────────────

@app.command("append")
def cmd_append(
    action: str = typer.Option(..., "--action", "-a", help="Action type, e.g. governance_vote"),
    wallet: str = typer.Option(..., "--wallet", "-w", help="Your wallet address (0x...)"),
    desc: str = typer.Option(..., "--desc", "-d", help="Description of the action"),
    media: Optional[list[str]] = typer.Option(None, "--media", "-m", help="SHA-256 hashes of attached media files"),
    ipfs: Optional[list[str]] = typer.Option(None, "--ipfs", help="IPFS CIDs for media"),
    yaml_path: Path = typer.Option(MASTER_YAML, "--yaml", help="Path to master YAML"),
) -> None:
    """
    Append a new entry to the immutable log.

    Example:
      raajadharma-log append --action governance_vote --wallet 0x1234 --desc "Changed practice day"
    """
    log = _get_log(yaml_path)
    entry = log.append(
        action_type=action,
        actor_wallet=wallet,
        description=desc,
        media_hashes=media or [],
        ipfs_hashes=ipfs or [],
    )
    typer.echo(typer.style("✅  Entry appended successfully!", fg=typer.colors.GREEN))
    _print_entry(entry)
    typer.echo(
        "\n💡  Next steps:\n"
        f"   1. Run: raajadharma-log generate-screenshot --entry {entry['entry_number']}\n"
        f"   2. Run: raajadharma-log post-to-community --entry {entry['entry_number']}\n"
    )


@app.command("blood-succession")
def cmd_blood_succession(
    wallet: str = typer.Option(..., "--wallet", "-w", help="Current Governor wallet (0x...)"),
    successor_wallet: str = typer.Option(..., "--successor-wallet", help="Successor's wallet (0x...)"),
    video_hash: str = typer.Option(..., "--video-hash", help="SHA-256 of family consent video"),
    affidavit_hash: str = typer.Option(..., "--affidavit-hash", help="SHA-256 of signed affidavit"),
    desc: str = typer.Option(
        "Governor blood-succession transfer",
        "--desc", "-d",
        help="Description of the succession",
    ),
    successor_id: Optional[str] = typer.Option(None, "--successor-id", help="Member ID of successor (e.g. M002)"),
    witnesses: Optional[list[str]] = typer.Option(None, "--witness", help="Witness wallet addresses"),
    yaml_path: Path = typer.Option(MASTER_YAML, "--yaml"),
) -> None:
    """
    Record a blood-succession Governor transfer.

    ⚠️  SAFETY NOTE: This action requires:
        • A recorded family consent video (all 9 members present or notified)
        • A signed affidavit from the outgoing Governor
        • Both files hashed with SHA-256 before running this command

    Example:
      raajadharma-log blood-succession \\
          --wallet 0x0001 \\
          --successor-wallet 0x0002 \\
          --video-hash sha256:abc123 \\
          --affidavit-hash sha256:def456
    """
    typer.echo(
        typer.style(
            "\n⚠️  Blood Succession — please confirm all requirements are met:",
            fg=typer.colors.YELLOW,
        )
    )
    typer.echo("   ✓ Family consent video is recorded and hashed")
    typer.echo("   ✓ Signed affidavit is scanned and hashed")
    typer.echo("   ✓ All 9 family members are notified\n")

    if not typer.confirm("Do you confirm all of the above? (y/N)"):
        typer.echo("Aborted.")
        raise typer.Exit(0)

    extra: dict = {
        "successor_wallet": successor_wallet,
        "family_consent_video_hash": video_hash,
        "affidavit_hash": affidavit_hash,
    }
    if successor_id:
        extra["successor_member_id"] = successor_id
    if witnesses:
        extra["witnesses"] = [{"wallet": w} for w in witnesses]

    log = _get_log(yaml_path)
    entry = log.append(
        action_type="blood_succession",
        actor_wallet=wallet,
        description=desc,
        **extra,
    )
    typer.echo(typer.style("✅  Blood succession recorded!", fg=typer.colors.GREEN))
    _print_entry(entry)


@app.command("view-latest")
def cmd_view_latest(
    yaml_path: Path = typer.Option(MASTER_YAML, "--yaml"),
) -> None:
    """Show the most recent log entry."""
    log = _get_log(yaml_path)
    entry = log.latest_entry()
    if entry is None:
        typer.echo("No entries found.")
        raise typer.Exit(0)
    _print_entry(entry)


@app.command("view-entry")
def cmd_view_entry(
    entry_number: int = typer.Argument(..., help="Entry number to display"),
    yaml_path: Path = typer.Option(MASTER_YAML, "--yaml"),
) -> None:
    """Show a specific log entry by number."""
    log = _get_log(yaml_path)
    matches = [e for e in log.all_entries() if e["entry_number"] == entry_number]
    if not matches:
        typer.echo(f"Entry #{entry_number} not found.", err=True)
        raise typer.Exit(1)
    _print_entry(matches[0])


@app.command("generate-screenshot")
def cmd_generate_screenshot(
    entry: int = typer.Option(..., "--entry", "-e", help="Entry number"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PNG path"),
    yaml_path: Path = typer.Option(MASTER_YAML, "--yaml"),
) -> None:
    """
    Generate a screenshot PNG of a log entry (for attaching to tweets).

    Requires playwright (pip install playwright && playwright install chromium)
    or Pillow as a fallback.
    """
    from scripts.generate_diff_screenshot import generate_diff_screenshot  # noqa: PLC0415

    path = generate_diff_screenshot(entry, output, yaml_path)
    typer.echo(f"Screenshot saved: {path}")


@app.command("generate-pdf")
def cmd_generate_pdf(
    entry: int = typer.Option(..., "--entry", "-e", help="Entry number"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PDF path"),
    yaml_path: Path = typer.Option(MASTER_YAML, "--yaml"),
) -> None:
    """
    Generate a printable PDF record of a log entry (for physical family archives).

    Requires WeasyPrint (pip install weasyprint).
    """
    from scripts.generate_pdf import generate_pdf  # noqa: PLC0415

    path = generate_pdf(entry, output, yaml_path)
    typer.echo(f"PDF saved: {path}")


@app.command("post-to-community")
def cmd_post_to_community(
    entry: int = typer.Option(..., "--entry", "-e", help="Entry number to post"),
    reply_to: str = typer.Option("", "--reply-to", help="Tweet ID of the post to reply to"),
    media: Optional[list[Path]] = typer.Option(None, "--media", "-m", help="Media files to attach"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print tweet text without posting"),
    yaml_path: Path = typer.Option(MASTER_YAML, "--yaml"),
) -> None:
    """
    Post a log entry as a reply in the X community thread.

    Requires X API keys in .env (see .env.example).
    Without API keys, prints manual copy-paste instructions.

    Example:
      raajadharma-log post-to-community --entry 3 --reply-to 1234567890
    """
    from scripts.post_to_community import post_reply  # noqa: PLC0415

    tweet_id = post_reply(
        entry_number=entry,
        reply_to_tweet_id=reply_to,
        media_paths=media,
        yaml_path=yaml_path,
        dry_run=dry_run,
    )
    if tweet_id:
        if typer.confirm(f"Update entry #{entry} with tweet ID {tweet_id}?", default=True):
            log = _get_log(yaml_path)
            log.update_tweet_id(entry, tweet_id)
            typer.echo(typer.style("✅  Tweet ID saved to log.", fg=typer.colors.GREEN))


@app.command("update-tweet-id")
def cmd_update_tweet_id(
    entry: int = typer.Option(..., "--entry", "-e", help="Entry number"),
    tweet_id: str = typer.Option(..., "--tweet-id", help="The X tweet ID to link"),
    yaml_path: Path = typer.Option(MASTER_YAML, "--yaml"),
) -> None:
    """
    Manually link a tweet ID to a log entry (after manual posting).

    Example:
      raajadharma-log update-tweet-id --entry 3 --tweet-id 1234567890123456789
    """
    log = _get_log(yaml_path)
    log.update_tweet_id(entry, tweet_id)
    typer.echo(
        typer.style(
            f"✅  Entry #{entry} linked to tweet {tweet_id}",
            fg=typer.colors.GREEN,
        )
    )


@app.command("validate")
def cmd_validate(
    yaml_path: Path = typer.Option(MASTER_YAML, "--yaml"),
) -> None:
    """
    Validate the master YAML for immutability violations and structural errors.
    Exits with code 1 if any issues are found.
    """
    code = run_validate(yaml_path)
    raise typer.Exit(code)


@app.command("init-thread")
def cmd_init_thread(
    yaml_path: Path = typer.Option(MASTER_YAML, "--yaml"),
) -> None:
    """
    Print the first pinned post template for the X community thread.

    Copy-paste this text as the very first post in:
      https://x.com/i/communities/1981771124343283876
    """
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    member_count = len(data.get("members", []))
    entry_count = len(data.get("updates", []))

    template = f"""
╔══════════════════════════════════════════════════════════╗
║  COPY THIS TEXT AS THE FIRST PINNED POST IN:            ║
║  {COMMUNITY_URL}  ║
╚══════════════════════════════════════════════════════════╝

📌 PINNED — RaajaDharma Archery Club DAO
🏹 Family Governance Thread — Immutable Ledger

This thread is the single source of truth for the
RaajaDharma Archery Club DAO — a 9-person blood-relationship
family governance structure.

Every reply below this post is a permanent, immutable record
of a family governance action. After X's 1-hour edit window,
each post is forever locked.

📊 Current Status
  • Members: {member_count}
  • Log entries: {entry_count}
  • Ledger: github.com/aksinghdce/raajadharma-xthread-immutable-log

📜 Governance Roles
  • Governor — Head of family; holds succession key
  • Coach    — Trains and mentors archers
  • Archer   — Active competing members
  • Contributor — Supporting family members

🔐 Blood Succession
  Any Governor transfer requires:
  ✓ Family consent video (all 9 members)
  ✓ Signed & scanned affidavit
  ✓ New wallet address

#RaajaDharma #FamilyDAO #ArcheryClub #ImmutableLedger
"""
    typer.echo(template)


if __name__ == "__main__":
    app()
