# Archer Guide — RaajaDharma Archery Club DAO

> **Role:** Active competing member. Records personal achievements, consents to governance decisions, and participates in family votes.

---

## Your Responsibilities

| Duty | How often |
|---|---|
| Record personal archery achievements | After competitions |
| Respond to family votes | When called |
| Attend family consent meetings (required for succession) | When scheduled |
| Keep your wallet address updated with the Governor | If it changes |

---

## One-Time Setup

```bash
# 1. Clone the repository
git clone https://github.com/aksinghdce/raajadharma-xthread-immutable-log.git
cd raajadharma-xthread-immutable-log

# 2. Install Python dependencies
pip install PyYAML typer python-dotenv
```

---

## Recording a Personal Achievement

```bash
raajadharma-log append \
    --action personal_achievement \
    --wallet 0xYOUR_WALLET_ADDRESS \
    --desc "Won 3rd place at State Archery Championship 2024-04-20. Score: 285/300."
```

---

## Casting a Governance Vote

```bash
raajadharma-log append \
    --action governance_vote \
    --wallet 0xYOUR_WALLET_ADDRESS \
    --desc "Vote: YES — I support changing practice venue to the new sports complex."
```

---

## Viewing the Full Log

```bash
# See the most recent entry
raajadharma-log view-latest

# See a specific entry
raajadharma-log view-entry 3
```

---

## Participating in Family Consent for Succession

When the Governor calls a family meeting for a blood-succession transfer:

1. **Attend** the family meeting (video or in-person).
2. The video will be recorded and its SHA-256 hash added to the log entry.
3. You do **not** need to run any CLI command — your presence in the video is your consent.
4. After the Governor records the succession, you can verify it:

```bash
raajadharma-log view-entry <SUCCESSION_ENTRY_NUMBER>
```

---

## Community Thread

Follow all updates at:  
**https://x.com/i/communities/1981771124343283876**

---

## Safety Notes for Family Consent Videos

- Videos should clearly show all consenting family members.
- State your name and that you consent to the succession.
- The Governor will securely hash and store the video — it is NOT uploaded publicly by default.
- Only the SHA-256 hash of the video appears in the public log.
