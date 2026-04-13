# Governor Guide — RaajaDharma Archery Club DAO

> **Role:** Head of the family DAO. Holds the succession key. Signs off on all major governance decisions.

---

## Your Responsibilities

| Duty | How often |
|---|---|
| Append governance decisions to the log | As needed |
| Initiate blood-succession transfers | Lifetime event |
| Confirm all 9 members are notified before major actions | Before any succession |
| Tweet each update to the community thread | Same day as log entry |

---

## One-Time Setup

```bash
# 1. Clone the repository
git clone https://github.com/aksinghdce/raajadharma-xthread-immutable-log.git
cd raajadharma-xthread-immutable-log

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. (Optional) Set up X API keys for automated tweeting
cp .env.example .env
# Edit .env and fill in your X API credentials
```

---

## Recording a Governance Decision

```bash
raajadharma-log append \
    --action governance_vote \
    --wallet 0xYOUR_WALLET_ADDRESS \
    --desc "Approved new archery training schedule for summer 2024"
```

After running this command, you will see the new entry number. Use it in the next steps.

---

## Recording a Blood-Succession Transfer

A blood-succession transfer permanently changes who holds the Governor role.

### Requirements before you begin
- [ ] Record a family meeting video (all 9 members present or notified)
- [ ] Get the video file and compute its SHA-256: `sha256sum family_meeting.mp4`
- [ ] Have the outgoing Governor sign a paper affidavit, scan it, compute SHA-256
- [ ] Have the new Governor's wallet address ready

### Command

```bash
raajadharma-log blood-succession \
    --wallet 0xOUTGOING_GOVERNOR_WALLET \
    --successor-wallet 0xNEW_GOVERNOR_WALLET \
    --video-hash sha256:abc123def456... \
    --affidavit-hash sha256:xyz789... \
    --desc "Governor role transferred to M002 (Eldest Child) — Family consent recorded"
```

The CLI will ask you to confirm all safety requirements before proceeding.

---

## Tweeting the Update to the Community

```bash
# Step 1 — Generate a screenshot for the tweet attachment
raajadharma-log generate-screenshot --entry <ENTRY_NUMBER>

# Step 2 — Post to the X community thread (automated if API keys set)
raajadharma-log post-to-community \
    --entry <ENTRY_NUMBER> \
    --reply-to <PREVIOUS_TWEET_ID> \
    --media examples/entry_XXXX.png

# Step 3 — If posting manually, run this after copying the tweet ID
raajadharma-log update-tweet-id --entry <ENTRY_NUMBER> --tweet-id <NEW_TWEET_ID>
```

**Community thread:** https://x.com/i/communities/1981771124343283876

---

## Creating a Printable Record

```bash
raajadharma-log generate-pdf --entry <ENTRY_NUMBER>
```

Print the resulting PDF and keep it in the family physical records binder.

---

## Initializing the Community Thread (First Time Only)

Run this **once** when setting up the thread:

```bash
raajadharma-log init-thread
```

Copy the output and paste it as the very first post in the community. Pin it.

---

## Frequently Asked Questions

**Q: Can I edit an old entry if I made a mistake?**  
A: No. The ledger is append-only. If you made an error, append a new entry with action type `correction` describing what was wrong and what the correct information is.

**Q: What if I don't have X API keys?**  
A: The CLI will print manual copy-paste instructions. You can post the tweet manually and then run `update-tweet-id` to link it.

**Q: Is this free?**  
A: Yes. $0 cost. Uses GitHub (free) + X's free tier + git history for immutability.
