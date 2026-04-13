# Integration Example — RaajaDharma Student Portal

This directory contains a **complete, runnable integration** showing how the
raajadharma.org web portal backend and frontend can use this repository as an
immutable practice-record database for student groups.

---

## Who is this for?

Any group of **2–9 students** at raajadharma.org can use this portal to maintain
a permanent, tamper-proof trail of:

| Discipline | What is recorded |
|---|---|
| **Archery Practice** | Score, distance, arrow count, coach's form notes |
| **Spoken Sanskrit** | Recitation reference, audio hash, duration, assessed accuracy |

Each group gets its **own fork** of this repository, cloned on the
raajadharma.org backend server. All writes are append-only — no entry can ever
be edited or deleted.

---

## Architecture

```
raajadharma.org server
│
├── /var/raajadharma/groups/
│   ├── batch-2024-a/
│   │   └── raajadharma-xthread-immutable-log/   ← group's personal clone
│   │       └── yaml/raajadharma-log.yaml         ← append-only ledger
│   └── batch-2024-b/
│       └── raajadharma-xthread-immutable-log/
│
├── examples/integration/backend/
│   ├── app.py           ← FastAPI REST API
│   ├── group_manager.py ← per-group clone manager
│   └── requirements.txt
│
└── examples/integration/frontend/
    ├── index.html   ← student portal (served as static files)
    ├── app.js       ← fetch API calls, form logic
    └── style.css    ← portal styling
```

---

## Quick Start

### 1. Install backend dependencies

```bash
cd examples/integration/backend
pip install -r requirements.txt
```

### 2. Start the API server

```bash
# Development — uses /tmp/test-groups to avoid needing a real git remote
RAAJADHARMA_GROUPS_ROOT=/tmp/test-groups \
RAAJADHARMA_TEMPLATE_REPO=https://github.com/aksinghdce/raajadharma-xthread-immutable-log.git \
uvicorn app:app --reload --port 8000
```

### 3. Open the student portal

Serve the frontend as static files:

```bash
cd examples/integration/frontend
python -m http.server 3000
```

Then open **http://localhost:3000** in your browser.

The frontend will talk to the API at `http://localhost:8000` automatically
(detected via `window.location.hostname`).

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/groups` | Create a student group (clones the template repo) |
| `GET`  | `/groups` | List all groups |
| `GET`  | `/groups/{id}` | Get group details |
| `DELETE` | `/groups/{id}` | Remove a group (admin / reset) |
| `GET`  | `/groups/{id}/log` | List all log entries |
| `GET`  | `/groups/{id}/log/latest` | Get latest entry |
| `POST` | `/groups/{id}/log/archery` | Record an archery practice |
| `POST` | `/groups/{id}/log/sanskrit` | Record a Sanskrit recitation |
| `POST` | `/groups/{id}/log/custom` | Append a custom entry |
| `GET`  | `/groups/{id}/validate` | Validate log integrity |

Interactive API docs (Swagger UI): **http://localhost:8000/docs**

---

## Example: Creating a Group (cURL)

```bash
curl -s -X POST http://localhost:8000/groups \
  -H "Content-Type: application/json" \
  -d '{
    "group_id":   "batch-2024-a",
    "group_name": "Morning Archery Batch A",
    "discipline": "archery",
    "members": [
      {"name": "Arjun Sharma",   "wallet": "0xAAA"},
      {"name": "Priya Mehta",    "wallet": "0xBBB"},
      {"name": "Rohan Verma",    "wallet": "0xCCC"}
    ]
  }' | python -m json.tool
```

## Example: Recording an Archery Session

```bash
curl -s -X POST http://localhost:8000/groups/batch-2024-a/log/archery \
  -H "Content-Type: application/json" \
  -d '{
    "actor_wallet": "0xAAA",
    "description":  "Monday warm-up — 30 arrows at 18m",
    "score":        252,
    "distance_m":   18,
    "arrow_count":  30,
    "form_notes":   "Release tension improved; elbow flare persists"
  }' | python -m json.tool
```

## Example: Recording a Sanskrit Recitation

```bash
# First hash your audio file (client-side):
HASH="sha256:$(sha256sum recitation.mp3 | awk '{print $1}')"

curl -s -X POST http://localhost:8000/groups/batch-2024-a/log/sanskrit \
  -H "Content-Type: application/json" \
  -d "{
    \"actor_wallet\":      \"0xBBB\",
    \"description\":       \"Gayatri Mantra — 3 rounds\",
    \"text_reference\":    \"Rigveda 3.62.10\",
    \"recitation_hash\":   \"$HASH\",
    \"duration_seconds\":  87,
    \"accuracy_pct\":      92
  }" | python -m json.tool
```

---

## Group Size Constraints

| Constraint | Value |
|---|---|
| Minimum members | 2 |
| Maximum members | 9 |
| Disciplines | `archery`, `sanskrit`, `both` |

The API returns HTTP **422** if these constraints are violated.

---

## Immutability Guarantee

Every record written through this API is:

1. **Append-only** in the YAML file — the `AppendOnlyYAML` engine rejects any attempt to modify past entries.
2. **Committed to git** — each write creates a new git commit in the group's working copy.
3. **Pushed to GitHub** — the commit is pushed to the group's remote repository, creating a permanent public record.
4. **Optionally tweeted** — use the `raajadharma-log post-to-community` CLI to mirror the entry in the [X community thread](https://x.com/i/communities/1981771124343283876), where X's 1-hour edit lock provides an additional layer of immutability.

---

## Production Deployment on raajadharma.org

```nginx
# nginx.conf (partial)
location /api/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_set_header Host $host;
}

location / {
    root /var/www/raajadharma/student-portal;
    try_files $uri $uri/ /index.html;
}
```

```bash
# systemd service
[Unit]
Description=RaajaDharma Student Portal API
After=network.target

[Service]
User=raajadharma
WorkingDirectory=/var/www/raajadharma/raajadharma-xthread-immutable-log
Environment=RAAJADHARMA_GROUPS_ROOT=/var/raajadharma/groups
ExecStart=/usr/local/bin/uvicorn examples.integration.backend.app:app --host 127.0.0.1 --port 8000

[Install]
WantedBy=multi-user.target
```

---

## Running the Integration Tests

```bash
# From the repository root
pip install pytest httpx fastapi
python -m pytest tests/integration/ -v
```
