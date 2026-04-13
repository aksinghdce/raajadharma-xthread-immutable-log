# Contributor Guide — RaajaDharma Archery Club DAO

> **Role:** Supporting family member. Contributes to club activities, records participation, and witnesses important decisions.

---

## Your Responsibilities

| Duty | How often |
|---|---|
| Record contributions (events, donations, volunteering) | As they happen |
| Witness family decisions when requested | As needed |
| Attend succession consent meetings | When scheduled |
| Stay informed via the community thread | Regularly |

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

## Recording a Contribution

```bash
raajadharma-log append \
    --action contribution \
    --wallet 0xYOUR_WALLET_ADDRESS \
    --desc "Organized the 2024 annual archery fundraising dinner. Raised $500 for new equipment."
```

---

## Recording an Event Attendance

```bash
raajadharma-log append \
    --action event_attendance \
    --wallet 0xYOUR_WALLET_ADDRESS \
    --desc "Attended State Archery Championship 2024-04-20 as family support crew."
```

---

## Viewing the Log

```bash
# Most recent entry
raajadharma-log view-latest

# Specific entry
raajadharma-log view-entry 5
```

---

## Following the Community Thread

All governance actions are publicly posted here — you don't need to run any code to follow along:  
**https://x.com/i/communities/1981771124343283876**

---

## Getting Help

If you're not comfortable running CLI commands, ask the Coach or Governor to record your contribution on your behalf. Provide them with:
- Your wallet address
- A clear description of what you did and when
- Any relevant dates

---

## Tips

- Your wallet address is your permanent identity in the DAO. Keep it safe.
- If you don't have a crypto wallet, you can use any Ethereum address generator (e.g., MetaMask).
- You don't need gas/ETH — this is a zero-gas ledger using git + X as immutability layers.
- Every entry you create is permanent — once committed and tweeted, it cannot be edited.
