"""
generate_pdf.py — Generate a printable PDF of any YAML log entry.

Uses WeasyPrint for high-quality PDF output suitable for physical family records.
Falls back to a plain-text file if WeasyPrint is unavailable.

Usage:
    python scripts/generate_pdf.py --entry-number 2
    python scripts/generate_pdf.py --entry-number 2 --output records/succession.pdf
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

MASTER_YAML_DEFAULT = Path(__file__).parent.parent / "yaml" / "raajadharma-log.yaml"
OUTPUT_DIR = Path(__file__).parent.parent / "examples"
COMMUNITY_URL = "https://x.com/i/communities/1981771124343283876"

HTML_PDF_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>RaajaDharma Family Log — Entry #{n}</title>
  <style>
    @page {{
      size: A4;
      margin: 2cm;
    }}
    body {{
      font-family: Georgia, serif;
      color: #111;
      font-size: 11pt;
      line-height: 1.6;
    }}
    h1 {{
      color: #1a1a6e;
      border-bottom: 2px solid #1a1a6e;
      padding-bottom: 8px;
    }}
    h2 {{ color: #333; font-size: 13pt; }}
    .meta-table {{
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0;
    }}
    .meta-table td {{
      padding: 6px 10px;
      border: 1px solid #ccc;
      vertical-align: top;
    }}
    .meta-table td:first-child {{
      font-weight: bold;
      width: 35%;
      background: #f5f5f5;
    }}
    pre {{
      background: #f8f8f8;
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 12px;
      font-family: 'Courier New', monospace;
      font-size: 9pt;
      white-space: pre-wrap;
      word-break: break-all;
    }}
    .footer {{
      margin-top: 30px;
      font-size: 9pt;
      color: #666;
      border-top: 1px solid #ccc;
      padding-top: 8px;
    }}
    .warning {{
      background: #fff3cd;
      border: 1px solid #ffc107;
      border-radius: 4px;
      padding: 10px 14px;
      margin: 16px 0;
      font-size: 10pt;
    }}
  </style>
</head>
<body>
  <h1>🏹 RaajaDharma Archery Club DAO<br>Family Governance Record</h1>

  <div class="warning">
    ⚠️ <strong>IMMUTABLE RECORD</strong> — This entry is permanently recorded in the
    RaajaDharma X community thread and git history. Do not alter.
  </div>

  <h2>Entry #{n} — {action_type}</h2>

  <table class="meta-table">
    <tr><td>Entry Number</td><td>#{n}</td></tr>
    <tr><td>Date</td><td>{date}</td></tr>
    <tr><td>Action Type</td><td>{action_type}</td></tr>
    <tr><td>Actor Wallet</td><td>{actor_wallet}</td></tr>
    <tr><td>Community Thread</td><td>{community_url}</td></tr>
    <tr><td>X Tweet ID</td><td>{x_tweet_id}</td></tr>
    {succession_rows}
  </table>

  <h2>Description</h2>
  <p>{description}</p>

  <h2>Full YAML Record</h2>
  <pre>{yaml_text}</pre>

  <div class="footer">
    Generated: {generated_at} &nbsp;|&nbsp;
    RaajaDharma Archery Club DAO &nbsp;|&nbsp;
    Community: {community_url}
  </div>
</body>
</html>"""

SUCCESSION_ROWS_TEMPLATE = """
    <tr><td>Successor Wallet</td><td>{successor_wallet}</td></tr>
    <tr><td>Succession Video Hash</td><td>{family_consent_video_hash}</td></tr>
    <tr><td>Affidavit Hash</td><td>{affidavit_hash}</td></tr>
"""


def _load_entry(yaml_path: Path, entry_number: int) -> dict:
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    for entry in data.get("updates", []):
        if entry.get("entry_number") == entry_number:
            return entry
    raise KeyError(f"No entry with entry_number={entry_number}")


def _build_html(entry: dict) -> str:
    yaml_text = yaml.dump(entry, allow_unicode=True, default_flow_style=False, sort_keys=False)

    succession_rows = ""
    if entry.get("action_type") == "blood_succession":
        succession_rows = SUCCESSION_ROWS_TEMPLATE.format(
            successor_wallet=entry.get("successor_wallet", ""),
            family_consent_video_hash=entry.get("family_consent_video_hash", ""),
            affidavit_hash=entry.get("affidavit_hash", ""),
        )

    return HTML_PDF_TEMPLATE.format(
        n=entry["entry_number"],
        date=entry.get("date", ""),
        action_type=entry.get("action_type", ""),
        actor_wallet=entry.get("actor_wallet", ""),
        community_url=COMMUNITY_URL,
        x_tweet_id=entry.get("x_tweet_id", "(not yet posted)"),
        description=entry.get("description", ""),
        succession_rows=succession_rows,
        yaml_text=yaml_text,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )


def generate_pdf(
    entry_number: int,
    output_path: Optional[Path] = None,
    yaml_path: Path = MASTER_YAML_DEFAULT,
) -> Path:
    """
    Generate a PDF for a given entry.

    Returns the path to the generated PDF.
    """
    entry = _load_entry(yaml_path, entry_number)
    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / f"entry_{entry_number:04d}.pdf"

    print(f"📄  Generating PDF for Entry #{entry_number} → {output_path}")

    html_content = _build_html(entry)

    try:
        import weasyprint  # noqa: PLC0415

        weasyprint.HTML(string=html_content).write_pdf(str(output_path))
        print(f"✅  PDF saved (WeasyPrint): {output_path}")
    except ImportError:
        # Fallback: write the HTML to a file instead
        html_path = output_path.with_suffix(".html")
        html_path.write_text(html_content, encoding="utf-8")
        print(
            f"⚠️  WeasyPrint not installed. HTML saved instead: {html_path}\n"
            "    Install with: pip install weasyprint",
            file=sys.stderr,
        )
        return html_path

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate PDF record for a log entry")
    parser.add_argument("--entry-number", type=int, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--yaml", type=Path, default=MASTER_YAML_DEFAULT)
    args = parser.parse_args()

    path = generate_pdf(args.entry_number, args.output, args.yaml)
    print(f"Output: {path}")
