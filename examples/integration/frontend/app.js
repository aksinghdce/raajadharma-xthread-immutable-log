/**
 * app.js — RaajaDharma Student Portal frontend logic.
 *
 * Communicates with the FastAPI backend at /api (or API_BASE).
 * No build tools required — runs as plain ES2020 in modern browsers.
 */

"use strict";

// ── Configuration ─────────────────────────────────────────────────────────────

// Change this to point at your raajadharma.org backend.
// When opening index.html via file:// during development, set to the
// full URL, e.g. "http://localhost:8000".
const API_BASE = window.location.hostname === "localhost"
  ? "http://localhost:8000"
  : "/api";   // proxied by the raajadharma.org web server in production

// ── State ─────────────────────────────────────────────────────────────────────

let _groups = [];   // cached list of provisioned groups

// ── Utilities ─────────────────────────────────────────────────────────────────

function showToast(message, type = "info", durationMs = 3500) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast ${type}`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.className = "toast hidden";
  }, durationMs);
}

async function apiRequest(path, method = "GET", body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}${path}`, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return data;
}

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function formatDate(isoStr) {
  if (!isoStr) return "—";
  try { return new Date(isoStr).toLocaleString(); } catch { return isoStr; }
}

// ── SHA-256 hashing (Web Crypto API) ──────────────────────────────────────────

async function sha256File(file) {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
  const hex = Array.from(new Uint8Array(hashBuffer))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");
  return `sha256:${hex}`;
}

// ── Populate group selects ─────────────────────────────────────────────────────

function _populateGroupSelects(groups) {
  ["log-group-select", "record-group-select"].forEach(id => {
    const sel = document.getElementById(id);
    const current = sel.value;
    sel.innerHTML = `<option value="">— choose a group —</option>`;
    groups.forEach(g => {
      const opt = document.createElement("option");
      opt.value = g.group_id;
      opt.textContent = `${g.group_name} (${g.group_id})`;
      sel.appendChild(opt);
    });
    if (current) sel.value = current;
  });
}

// ── Group card rendering ───────────────────────────────────────────────────────

function renderGroupCard(g) {
  const memberNames = (g.members || []).map(m => escapeHtml(m.name)).join(", ");
  return `
    <div class="group-card">
      <div class="group-card-info">
        <h3>${escapeHtml(g.group_name)}</h3>
        <div class="group-card-meta">
          <strong>ID:</strong> ${escapeHtml(g.group_id)} &nbsp;|&nbsp;
          <strong>Members:</strong> ${(g.members || []).length} &nbsp;|&nbsp;
          <strong>Created:</strong> ${formatDate(g.created_at)}
        </div>
        <div class="group-card-meta" style="margin-top:4px">
          ${escapeHtml(memberNames)}
        </div>
      </div>
      <span class="discipline-badge">${escapeHtml(g.discipline || "archery")}</span>
    </div>`;
}

// ── Log entry rendering ────────────────────────────────────────────────────────

function renderLogEntry(entry) {
  const extraKeys = [
    "score", "distance_m", "arrow_count", "form_notes",
    "text_reference", "recitation_hash", "duration_seconds", "accuracy_pct",
  ];
  const extras = extraKeys
    .filter(k => entry[k] !== undefined && entry[k] !== null && entry[k] !== "")
    .map(k => `<span><strong>${k}:</strong> ${escapeHtml(entry[k])}</span>`)
    .join("  |  ");

  const tweetLink = entry.x_tweet_id
    ? `<a href="https://x.com/i/web/status/${escapeHtml(entry.x_tweet_id)}"
          target="_blank" rel="noopener">🐦 View tweet</a>`
    : "";

  return `
    <div class="log-entry">
      <span class="immutable-stamp">🔒 Immutable</span>
      <div class="log-entry-header">
        <span class="entry-number">#${entry.entry_number}</span>
        <span class="action-type-badge">${escapeHtml(entry.action_type)}</span>
        <span class="log-entry-date">${formatDate(entry.date)}</span>
      </div>
      <div class="log-entry-desc">${escapeHtml(entry.description)}</div>
      ${extras ? `<div class="log-entry-meta">${extras}</div>` : ""}
      <div class="log-entry-meta" style="margin-top:6px">
        <span class="log-entry-wallet">Wallet: ${escapeHtml(entry.actor_wallet)}</span>
        ${tweetLink ? `&nbsp;|&nbsp; ${tweetLink}` : ""}
      </div>
    </div>`;
}

// ── Load groups ────────────────────────────────────────────────────────────────

async function loadGroups() {
  const listEl = document.getElementById("groups-list");
  try {
    _groups = await apiRequest("/groups");
    if (_groups.length === 0) {
      listEl.innerHTML = `<p class="loading-text">No groups yet — create the first one above.</p>`;
    } else {
      listEl.innerHTML = _groups.map(renderGroupCard).join("");
    }
    _populateGroupSelects(_groups);
  } catch (err) {
    listEl.innerHTML = `<p class="loading-text" style="color:var(--red)">
      Could not load groups: ${escapeHtml(err.message)}</p>`;
  }
}

// ── Create group ───────────────────────────────────────────────────────────────

document.getElementById("create-group-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;

  const nameInputs   = form.querySelectorAll(".member-name");
  const walletInputs = form.querySelectorAll(".member-wallet");
  const members = Array.from(nameInputs).map((inp, i) => ({
    name:   inp.value.trim(),
    wallet: walletInputs[i]?.value.trim() || "",
  })).filter(m => m.name);

  if (members.length < 2) {
    showToast("Please add at least 2 members.", "error"); return;
  }
  if (members.length > 9) {
    showToast("Maximum 9 members per group.", "error"); return;
  }

  const payload = {
    group_id:   form.group_id.value.trim(),
    group_name: form.group_name.value.trim(),
    discipline: form.discipline.value,
    members,
  };

  try {
    const manifest = await apiRequest("/groups", "POST", payload);
    showToast(`✅ Group "${manifest.group_name}" created!`, "success");
    form.reset();
    // Reset member rows
    document.getElementById("members-list").innerHTML = `
      <h4>Members <span class="hint">(2–9 required)</span></h4>
      <div class="member-row">
        <input type="text" placeholder="Member 1 name" class="member-name" required>
        <input type="text" placeholder="Wallet (optional)" class="member-wallet">
      </div>
      <div class="member-row">
        <input type="text" placeholder="Member 2 name" class="member-name" required>
        <input type="text" placeholder="Wallet (optional)" class="member-wallet">
      </div>`;
    await loadGroups();
  } catch (err) {
    showToast(`❌ ${err.message}`, "error", 6000);
  }
});

document.getElementById("add-member-btn").addEventListener("click", () => {
  const list  = document.getElementById("members-list");
  const count = list.querySelectorAll(".member-row").length + 1;
  if (count > 9) { showToast("Maximum 9 members per group.", "error"); return; }
  const row = document.createElement("div");
  row.className = "member-row";
  row.innerHTML = `
    <input type="text" placeholder="Member ${count} name" class="member-name">
    <input type="text" placeholder="Wallet (optional)" class="member-wallet">`;
  list.appendChild(row);
});

// ── Load log ───────────────────────────────────────────────────────────────────

document.getElementById("load-log-btn").addEventListener("click", async () => {
  const groupId = document.getElementById("log-group-select").value;
  if (!groupId) { showToast("Please select a group first.", "info"); return; }

  const logEl = document.getElementById("log-entries");
  logEl.innerHTML = `<p class="loading-text">Loading entries…</p>`;

  try {
    const entries = await apiRequest(`/groups/${groupId}/log`);
    if (entries.length === 0) {
      logEl.innerHTML = `<p class="loading-text">No entries yet for this group.</p>`;
    } else {
      // Show newest first
      logEl.innerHTML = [...entries].reverse().map(renderLogEntry).join("");
    }
  } catch (err) {
    logEl.innerHTML = `<p class="loading-text" style="color:var(--red)">
      Error: ${escapeHtml(err.message)}</p>`;
  }
});

// ── Validate log ───────────────────────────────────────────────────────────────

document.getElementById("validate-btn").addEventListener("click", async () => {
  const groupId = document.getElementById("log-group-select").value;
  if (!groupId) { showToast("Please select a group first.", "info"); return; }
  try {
    const result = await apiRequest(`/groups/${groupId}/validate`);
    if (result.valid) {
      showToast("✅ Log integrity check passed — all entries intact.", "success", 5000);
    } else {
      showToast("❌ Integrity violation detected! Check server logs.", "error", 8000);
    }
  } catch (err) {
    showToast(`❌ Validation error: ${err.message}`, "error", 6000);
  }
});

// ── Record type toggle ────────────────────────────────────────────────────────

document.getElementById("record-type-select").addEventListener("change", (e) => {
  document.getElementById("archery-form").classList.toggle("hidden", e.target.value !== "archery");
  document.getElementById("sanskrit-form").classList.toggle("hidden", e.target.value !== "sanskrit");
});

// ── Audio hashing (Sanskrit form) ─────────────────────────────────────────────

document.getElementById("audio-file-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const display = document.getElementById("recitation-hash-display");
  const hidden  = document.getElementById("recitation-hash-input");
  display.textContent = "⏳ Hashing…";
  try {
    const hash = await sha256File(file);
    hidden.value = hash;
    display.textContent = hash;
  } catch {
    display.textContent = "❌ Could not hash file.";
  }
});

// ── Archery form submit ────────────────────────────────────────────────────────

document.getElementById("archery-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const groupId = document.getElementById("record-group-select").value;
  if (!groupId) { showToast("Please select a group.", "info"); return; }

  const form = e.target;
  const payload = {
    actor_wallet: form.actor_wallet.value.trim(),
    description:  form.description.value.trim(),
  };
  const score    = parseInt(form.score.value);
  const dist     = parseInt(form.distance_m.value);
  const arrows   = parseInt(form.arrow_count.value);
  const notes    = form.form_notes.value.trim();

  if (!isNaN(score))  payload.score = score;
  if (!isNaN(dist))   payload.distance_m = dist;
  if (!isNaN(arrows)) payload.arrow_count = arrows;
  if (notes)          payload.form_notes = notes;

  try {
    const entry = await apiRequest(`/groups/${groupId}/log/archery`, "POST", payload);
    showToast(`✅ Archery session recorded as Entry #${entry.entry_number}`, "success", 5000);
    form.reset();
    // Reload log if visible
    if (document.getElementById("log-group-select").value === groupId) {
      document.getElementById("load-log-btn").click();
    }
  } catch (err) {
    showToast(`❌ ${err.message}`, "error", 7000);
  }
});

// ── Sanskrit form submit ───────────────────────────────────────────────────────

document.getElementById("sanskrit-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const groupId = document.getElementById("record-group-select").value;
  if (!groupId) { showToast("Please select a group.", "info"); return; }

  const form = e.target;
  const payload = {
    actor_wallet: form.actor_wallet.value.trim(),
    description:  form.description.value.trim(),
  };
  const ref      = form.text_reference.value.trim();
  const hash     = form.recitation_hash.value.trim();
  const duration = parseInt(form.duration_seconds.value);
  const accuracy = parseInt(form.accuracy_pct.value);

  if (ref)             payload.text_reference   = ref;
  if (hash)            payload.recitation_hash  = hash;
  if (!isNaN(duration)) payload.duration_seconds = duration;
  if (!isNaN(accuracy)) payload.accuracy_pct    = accuracy;

  try {
    const entry = await apiRequest(`/groups/${groupId}/log/sanskrit`, "POST", payload);
    showToast(`✅ Sanskrit recitation recorded as Entry #${entry.entry_number}`, "success", 5000);
    form.reset();
    document.getElementById("recitation-hash-display").textContent = "";
    if (document.getElementById("log-group-select").value === groupId) {
      document.getElementById("load-log-btn").click();
    }
  } catch (err) {
    showToast(`❌ ${err.message}`, "error", 7000);
  }
});

// ── Bootstrap ─────────────────────────────────────────────────────────────────

(async () => {
  await loadGroups();
})();
