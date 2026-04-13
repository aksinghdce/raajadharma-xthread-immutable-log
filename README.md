# 🏹 RaajaDharma X-Thread Immutable Log

> **Zero-gas, media-rich, append-only governance ledger for the 9-person blood-relationship RaajaDharma Archery Club DAO.**

[![Validate YAML](https://github.com/aksinghdce/raajadharma-xthread-immutable-log/actions/workflows/validate-yaml.yml/badge.svg)](https://github.com/aksinghdce/raajadharma-xthread-immutable-log/actions/workflows/validate-yaml.yml)

**Community Thread:** https://x.com/i/communities/1981771124343283876  
**Cost:** $0  
**Gas required:** None

---

## Strategy: How Immutability Is Achieved

This system uses **two independent immutability layers**:

| Layer | Mechanism | Immutable After |
|---|---|---|
| **X (Twitter) thread** | X's 1-hour edit window expires | 60 minutes after posting |
| **Git commit history** | SHA-256 content-addressing | Immediately on push to GitHub |
| **GitHub Actions CI** | PR validation rejects any mutation | On every pull request |

### The Core Idea

1. Every governance action is appended as a new block at the bottom of `yaml/raajadharma-log.yaml`.
2. The new block is immediately tweeted as a reply in the **pinned community thread** at https://x.com/i/communities/1981771124343283876.
3. After 60 minutes, X locks the post permanently. Combined with git history, the record is fully immutable.
4. Blood-succession transfers additionally require a **family consent video** + **signed affidavit**, both SHA-256 hashed into the log entry.

---

## Folder Structure

```
raajadharma-xthread-immutable-log/
├── yaml/
│   └── raajadharma-log.yaml          # Master append-only ledger
├── scripts/
│   ├── append_only_yaml.py           # Core immutability engine
│   ├── cli.py                        # Typer CLI (raajadharma-log command)
│   ├── validate_yaml.py              # Standalone validation + CI check
│   ├── post_to_community.py          # X integration + manual fallback
│   ├── generate_diff_screenshot.py   # PNG screenshot of YAML diff
│   └── generate_pdf.py               # Printable PDF for physical records
├── tests/
│   ├── test_append_only_yaml.py      # Unit tests for immutability engine
│   └── test_validate_yaml.py         # Unit tests for validation
├── docs/
│   ├── COMMUNITY_THREAD_SETUP.md     # One-time thread initialization guide
│   └── guides/
│       ├── governor.md               # Governor role guide
│       ├── coach.md                  # Coach role guide
│       ├── archer.md                 # Archer role guide
│       └── contributor.md            # Contributor role guide
├── templates/
│   ├── pinned_post_template.txt      # First pinned post text
│   └── tweet_template.txt            # Per-update tweet format
├── examples/
│   └── example_usage.py              # Working end-to-end demo
├── .github/
│   └── workflows/
│       └── validate-yaml.yml         # GitHub Actions CI
├── .env.example                      # X API keys template
├── requirements.txt
└── README.md
```

---

## One-Time Setup

```bash
# 1. Clone
git clone https://github.com/aksinghdce/raajadharma-xthread-immutable-log.git
cd raajadharma-xthread-immutable-log

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) X API keys for automated posting
cp .env.example .env
# Edit .env — all X_* fields are optional; manual mode always works

# 4. Install the CLI
pip install -e .   # or: alias raajadharma-log="python scripts/cli.py"
```

**Initialize the community thread (first time only):**

```bash
raajadharma-log init-thread
# → Copy the output and paste as the first pinned post in the community
```

See [docs/COMMUNITY_THREAD_SETUP.md](docs/COMMUNITY_THREAD_SETUP.md) for full details.

---

## CLI Quick Reference

```bash
# Append a governance decision
raajadharma-log append \
    --action governance_vote \
    --wallet 0xYOUR_WALLET \
    --desc "Approved new practice schedule"

# Record a blood-succession transfer
raajadharma-log blood-succession \
    --wallet 0xGOVERNOR_WALLET \
    --successor-wallet 0xNEW_GOVERNOR \
    --video-hash sha256:abc123... \
    --affidavit-hash sha256:def456... \
    --desc "Governor role transferred to M002"

# View the latest entry
raajadharma-log view-latest

# Generate a screenshot for tweeting
raajadharma-log generate-screenshot --entry 3

# Generate a printable PDF
raajadharma-log generate-pdf --entry 3

# Post to the X community thread
raajadharma-log post-to-community --entry 3 --reply-to <PREV_TWEET_ID>

# Link a manually-posted tweet ID
raajadharma-log update-tweet-id --entry 3 --tweet-id 1234567890

# Validate the log for immutability violations
raajadharma-log validate
```

---

## Governance Roles

| Role | Responsibilities |
|---|---|
| **Governor** | Head of family. Signs major decisions. Initiates blood-succession. |
| **Coach** | Trains archers. Records training decisions and milestones. |
| **Archer** | Active competitor. Records achievements. Votes on family decisions. |
| **Contributor** | Supporting member. Records contributions and event attendance. |

Role-specific guides:
- 📖 [Governor Guide](docs/guides/governor.md)
- 📖 [Coach Guide](docs/guides/coach.md)
- 📖 [Archer Guide](docs/guides/archer.md)
- 📖 [Contributor Guide](docs/guides/contributor.md)

---

## Blood-Succession Workflow

A blood-succession transfer permanently changes who holds the Governor role.

**Requirements:**
1. Record a family meeting video (all 9 members present or notified).
2. Outgoing Governor signs a paper affidavit and scans it.
3. Compute SHA-256 hashes of both files:
   ```bash
   sha256sum family_meeting.mp4
   sha256sum affidavit_signed.pdf
   ```
4. Run the succession command:
   ```bash
   raajadharma-log blood-succession \
       --wallet 0xOLD_GOVERNOR \
       --successor-wallet 0xNEW_GOVERNOR \
       --video-hash sha256:... \
       --affidavit-hash sha256:... \
       --desc "Governor role transferred"
   ```
5. Tweet the update to the community thread within the hour.

⚠️ **Safety Note:** The video and affidavit files themselves are **not** uploaded to GitHub or X. Only their SHA-256 hashes are stored in the public log. Keep the original files in a secure family archive.

---

## Immutability Enforcement

The `append_only_yaml.py` engine enforces the following at runtime:

- **No past entry may be modified.** Every append call verifies the fingerprints of all existing entries before writing.
- **No past entry may be deleted.** Deletions are detected as missing entry numbers.
- **Blood succession requires video + affidavit.** The CLI rejects any succession entry that is missing these hashes.
- **Sequential entry numbering.** Gaps in entry numbers are flagged by the validator.
- **GitHub Actions CI** runs `validate_yaml.py` on every pull request that touches `yaml/`.

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Running the Demo

```bash
python examples/example_usage.py
```

---

## Live Community Thread

All governance actions are publicly visible at:  
**https://x.com/i/communities/1981771124343283876**

After X's 1-hour edit window, each post is permanently locked — making this a zero-gas, media-rich, fully immutable governance ledger for the family DAO.

---

## License

MIT — see [LICENSE](LICENSE).
