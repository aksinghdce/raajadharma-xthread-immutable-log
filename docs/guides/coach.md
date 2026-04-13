# Coach Guide — RaajaDharma Archery Club DAO

> **Role:** Trains and mentors archers. Records training milestones, session decisions, and member progress.

---

## Your Responsibilities

| Duty | How often |
|---|---|
| Record training schedule changes | As decided |
| Log archery milestone achievements | After each session |
| Witness governance decisions (when requested) | As needed |
| Notify the Governor of succession readiness | When applicable |

---

## One-Time Setup

```bash
# 1. Clone the repository
git clone https://github.com/aksinghdce/raajadharma-xthread-immutable-log.git
cd raajadharma-xthread-immutable-log

# 2. Install Python dependencies
pip install -r requirements.txt
```

---

## Recording a Training Decision

```bash
raajadharma-log append \
    --action training_decision \
    --wallet 0xYOUR_WALLET_ADDRESS \
    --desc "Changed weekly practice from Wednesday to Saturday. All members agreed."
```

---

## Recording an Archery Milestone

```bash
raajadharma-log append \
    --action archery_milestone \
    --wallet 0xYOUR_WALLET_ADDRESS \
    --desc "M003 achieved Level 2 certification at the regional competition on 2024-03-15"
```

---

## Witnessing a Succession

When the Governor initiates a blood-succession transfer, your wallet may be listed as a witness. The Governor's CLI command will include `--witness 0xYOUR_WALLET`. You don't need to run any command yourself — just confirm your presence at the family meeting.

---

## Viewing the Latest Entry

```bash
raajadharma-log view-latest
```

---

## Community Thread

All updates are posted here:  
**https://x.com/i/communities/1981771124343283876**

---

## Tips for 14+ Family Members

- Always use a **wallet address** you control when recording entries. If you don't have one, ask the Governor to set one up.
- The `--desc` text becomes part of the permanent record — be clear and factual.
- If you're unsure about an entry, ask the Governor to review it before running the command.
- After running `append`, check the output to confirm the entry was saved correctly.
