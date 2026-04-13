# Community Thread Setup — One-Time Initialization

> This document guides the Governor through setting up the pinned X community thread
> that serves as the public immutable ledger for the RaajaDharma Archery Club DAO.

---

## Community URL

**https://x.com/i/communities/1981771124343283876**

---

## Step 1 — Generate the First Post Template

Run this command to get the text for the first pinned post:

```bash
raajadharma-log init-thread
```

Copy the output text.

---

## Step 2 — Post to the Community

1. Open **https://x.com/i/communities/1981771124343283876** in your browser.
2. Click **"Post to community"**.
3. Paste the text from Step 1.
4. Add an image of the DAO logo or the first YAML snapshot (optional but recommended).
5. Click **Post**.

---

## Step 3 — Pin the Post

1. Click the three dots (`•••`) on the post you just created.
2. Select **"Pin to Community"** (if you are a community admin) or ask the community admin.
3. Copy the URL of the pinned post — it will look like:
   `https://x.com/i/web/status/TWEET_ID_HERE`

---

## Step 4 — Record the Tweet ID

Note down the Tweet ID from the URL (the number at the end). Add it to your `.env` file:

```
PINNED_THREAD_TWEET_ID=1234567890123456789
```

All future replies will use this as the root of the thread.

---

## Step 5 — Link the First Log Entry

```bash
raajadharma-log update-tweet-id --entry 1 --tweet-id 1234567890123456789
```

---

## Thread Format

Every subsequent update is posted as a **reply** to the previous post in the thread. This creates a continuous, publicly visible chain:

```
📌 Pinned Post (initialization)
  └── Reply: Entry #1 — DAO Initialization
       └── Reply: Entry #2 — Blood Succession (Governor Transfer)
            └── Reply: Entry #3 — Training Decision
                 └── ...
```

---

## Immutability After 1 Hour

After X's 1-hour edit window expires, each post is **permanently locked**. No one — not even the poster — can edit or delete it. Combined with the git history of `yaml/raajadharma-log.yaml`, this creates a dual-layer immutable record:

| Layer | Mechanism | Immutable after |
|---|---|---|
| X thread | X's 1-hour edit lock | 60 minutes after posting |
| Git history | SHA-256 commit hashes | Immediately on push |
| GitHub PR validation | CI checks append-only rule | On every PR |

---

## Troubleshooting

**Q: I accidentally posted the wrong text. Can I delete it?**  
A: Yes — but **only within the first 60 minutes**. After that, you cannot. If you need to correct an error after the lock, append a new log entry with `action_type: correction` explaining the error.

**Q: I don't have X API keys. Can I still post?**  
A: Yes. Run `post-to-community --dry-run` to get the formatted text, then copy-paste it manually into the community thread.

**Q: How many media files can I attach?**  
A: X allows up to 4 images, or 1 video, per post on the free tier.
