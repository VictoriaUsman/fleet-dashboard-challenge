
A technical task for candidates applying to SolidGPS.

---

## My Approach
<img width="1670" height="942" alt="image" src="https://github.com/user-attachments/assets/03e5611f-cd6e-4771-a837-95d42525fc6c" />

**How I used AI to complete this task**

I used Claude Google Gemini as a pair programmer throughout. I gave it the README requirements and the CSV, and it wrote the initial Python script and HTML template. I reviewed the output, checked edge cases in the data (invalid coordinates, out-of-range battery values, a future timestamp, an undocumented `maintenance` status), and had Gemini handle them gracefully rather than crash or silently skip them.

**Colour/status logic**

| Status | Colour | Reasoning |
|---|---|---|
| Active | Green `#22c55e` | Universal "all good" signal |
| Idle | Amber `#f59e0b` | Needs attention but not urgent |
| Low Battery | Red `#ef4444` | Action required soon |
| Offline | Grey `#6b7280` | Unknown/unreachable — muted to avoid alarm fatigue |
| Maintenance | Blue `#3b82f6` | Intentionally out of service — distinct from a fault |

Offline is grey rather than red because a device being offline isn't always an emergency (e.g. overnight parking), while low battery demands immediate attention before the device goes dark.

**One thing I would add for a real product**

A **live auto-refresh** — polling the backend every 60 seconds and updating marker positions and statuses without a full page reload. A fleet manager leaving the dashboard open all day needs it to stay current, not reflect a stale snapshot from when they first opened it.

---

## The Task

You have been given `fleet_status.csv` — a real-world snapshot of 30 GPS tracking devices currently in the field across Australia.

**Write a Python script that reads the CSV and produces a single `fleet_dashboard.html`** that a fleet manager could open in any browser with no setup.

---

## Input

`fleet_status.csv` contains the following columns:

| Column | Description |
|--------|-------------|
| `device_id` | Unique tracker ID (e.g. `TRK001`) |
| `name` | Vehicle name |
| `status` | One of: `active`, `idle`, `offline`, `low_battery` |
| `battery_pct` | Battery percentage (0–100) |
| `lat` | Latitude |
| `lon` | Longitude |
| `last_seen` | Timestamp of last GPS ping (`YYYY-MM-DD HH:MM:SS`) |
| `location` | Nearest suburb/city |

---

## Requirements

Your `fleet_dashboard.html` must include:

1. **A map** — each device plotted at its GPS location, colour-coded by status
2. **A device list** — showing status, battery level, and how long ago the device was last seen
3. **A summary** — total count per status (active / idle / offline / low battery)

**Rules:**
- Python standard library only — no `pandas`, `folium`, `requests`, or other third-party packages
- One script → one output file (`fleet_dashboard.html`)
- Must run in under 30 seconds
- The HTML must be self-contained (no external files)

---

## Submission

Create a **public GitHub repository** containing:

- Your script (`fleet_dashboard.py` or similar)
- Your output (`fleet_dashboard.html`)
- A `README.md` with a section titled **"My Approach"** that answers:
  - How you used AI to complete this task
  - What colour/status logic you chose and why
  - One thing you would add if this were a real product

Paste the GitHub link in your application.

---

## What We're Looking For

We're not testing whether you can code from scratch — we're testing whether you can use AI tools effectively to produce something genuinely useful.

A good submission is one a fleet manager could open on Monday morning and immediately understand.
