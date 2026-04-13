"""
generate_diff_screenshot.py — Generate a PNG screenshot of the YAML diff for a given entry.

Requires playwright (pip install playwright && playwright install chromium).
Falls back to a plain-text image via Pillow if playwright is unavailable.

Usage:
    python scripts/generate_diff_screenshot.py --entry-number 3
    python scripts/generate_diff_screenshot.py --entry-number 3 --output out.png
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import yaml

MASTER_YAML_DEFAULT = Path(__file__).parent.parent / "yaml" / "raajadharma-log.yaml"
OUTPUT_DIR = Path(__file__).parent.parent / "examples"

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>RaajaDharma Log — Entry #{n}</title>
  <style>
    body {{
      background: #0d1117;
      color: #e6edf3;
      font-family: 'Courier New', monospace;
      padding: 32px;
      margin: 0;
    }}
    h1 {{ color: #58a6ff; margin-bottom: 4px; }}
    .subtitle {{ color: #8b949e; font-size: 0.85em; margin-bottom: 24px; }}
    pre {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 20px;
      overflow-x: auto;
      font-size: 0.9em;
      line-height: 1.6;
      white-space: pre-wrap;
    }}
    .key {{ color: #79c0ff; }}
    .footer {{
      margin-top: 20px;
      font-size: 0.75em;
      color: #8b949e;
    }}
    .footer a {{ color: #58a6ff; text-decoration: none; }}
  </style>
</head>
<body>
  <h1>🏹 RaajaDharma Family Log — Update #{n}</h1>
  <div class="subtitle">
    {date} &nbsp;|&nbsp; Action: <strong>{action_type}</strong>
  </div>
  <pre>{yaml_text}</pre>
  <div class="footer">
    Immutable ledger &nbsp;•&nbsp;
    <a href="https://x.com/i/communities/1981771124343283876">
      x.com/i/communities/1981771124343283876
    </a>
  </div>
</body>
</html>"""


def _load_entry(yaml_path: Path, entry_number: int) -> dict:
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    for entry in data.get("updates", []):
        if entry.get("entry_number") == entry_number:
            return entry
    raise KeyError(f"No entry with entry_number={entry_number}")


def generate_screenshot_playwright(
    entry: dict, output_path: Path
) -> bool:
    """Try to generate a screenshot using playwright. Returns True on success."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    yaml_text = yaml.dump(entry, allow_unicode=True, default_flow_style=False, sort_keys=False)
    html_content = HTML_TEMPLATE.format(
        n=entry["entry_number"],
        date=entry.get("date", ""),
        action_type=entry.get("action_type", ""),
        yaml_text=yaml_text,
    )

    tmp_html = output_path.parent / f"_tmp_entry_{entry['entry_number']}.html"
    try:
        tmp_html.write_text(html_content, encoding="utf-8")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 900, "height": 600})
            page.goto(f"file://{tmp_html.resolve()}")
            page.screenshot(path=str(output_path), full_page=True)
            browser.close()
        return True
    finally:
        if tmp_html.exists():
            tmp_html.unlink()


def generate_screenshot_pillow(entry: dict, output_path: Path) -> bool:
    """Fallback: render text as a PNG image using Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False

    yaml_text = yaml.dump(entry, allow_unicode=True, default_flow_style=False, sort_keys=False)
    lines = yaml_text.splitlines()
    padding = 20
    line_height = 18
    font_size = 14
    img_width = 900
    img_height = padding * 2 + (len(lines) + 4) * line_height

    img = Image.new("RGB", (img_width, img_height), color=(13, 17, 23))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", font_size)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
        title_font = font

    y = padding
    title = f"🏹 RaajaDharma Family Log — Update #{entry['entry_number']}"
    draw.text((padding, y), title, fill=(88, 166, 255), font=title_font)
    y += line_height * 2

    for line in lines:
        draw.text((padding, y), line, fill=(230, 237, 243), font=font)
        y += line_height

    y += line_height
    footer = "Immutable ledger • https://x.com/i/communities/1981771124343283876"
    draw.text((padding, y), footer, fill=(139, 148, 158), font=font)

    img.save(str(output_path))
    return True


def generate_diff_screenshot(
    entry_number: int,
    output_path: Optional[Path] = None,
    yaml_path: Path = MASTER_YAML_DEFAULT,
) -> Path:
    """
    Generate a screenshot PNG for a given entry number.

    Returns the path to the generated image.
    """
    entry = _load_entry(yaml_path, entry_number)
    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / f"entry_{entry_number:04d}.png"

    print(f"📸  Generating screenshot for Entry #{entry_number} → {output_path}")

    if generate_screenshot_playwright(entry, output_path):
        print(f"✅  Screenshot saved (playwright): {output_path}")
    elif generate_screenshot_pillow(entry, output_path):
        print(f"✅  Screenshot saved (pillow fallback): {output_path}")
    else:
        print(
            "⚠️  Neither playwright nor Pillow is available. "
            "Install with: pip install playwright Pillow && playwright install chromium",
            file=sys.stderr,
        )
        raise RuntimeError("No screenshot backend available.")

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate diff screenshot for a log entry")
    parser.add_argument("--entry-number", type=int, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--yaml", type=Path, default=MASTER_YAML_DEFAULT)
    args = parser.parse_args()

    path = generate_diff_screenshot(args.entry_number, args.output, args.yaml)
    print(f"Output: {path}")
