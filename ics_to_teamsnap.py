#!/usr/bin/env python3
"""Convert a FIFA World Cup 2026 ICS file to a TeamSnap-importable CSV.

Usage:
    python ics_to_teamsnap.py <input> output.csv [arrival_minutes]

Arguments:
    input             Local .ics file path  OR  a myworldcupcalendar.com URL
                      (shared calendar page or direct /api/calendar.ics URL)
    output.csv        Path where the TeamSnap CSV will be written
    arrival_minutes   Minutes before kickoff to set as arrival time (default: 30)
"""

import csv
import re
import sys
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.parse import urljoin


# ---------------------------------------------------------------------------
# ICS source loading (file or URL)
# ---------------------------------------------------------------------------

_USER_AGENT = "Mozilla/5.0 (compatible; ics_to_teamsnap/1.0)"
_MYWC_HOST = "myworldcupcalendar.com"


def _http_get(url):
    req = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def _resolve_ics_url(url):
    """Return a direct ICS URL given any myworldcupcalendar.com URL."""
    # Already a direct ICS endpoint
    if "/api/calendar.ics" in url:
        return url
    # Shared calendar page — scrape the embedded ICS download href
    html = _http_get(url)
    m = re.search(r'href="(/api/calendar\.ics[^"]*)"', html)
    if not m:
        raise ValueError(
            "Could not find an ICS download link on the page. "
            "Make sure the URL is a myworldcupcalendar.com shared calendar page."
        )
    base = "https://" + _MYWC_HOST
    return urljoin(base, m.group(1))


def load_ics_content(source):
    """Return raw ICS text from a file path or URL."""
    if source.startswith("http://") or source.startswith("https://"):
        if _MYWC_HOST in source:
            ics_url = _resolve_ics_url(source)
            print(f"Fetching: {ics_url}")
        else:
            ics_url = source
        return _http_get(ics_url)
    with open(source, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# ICS parsing (no external dependencies)
# ---------------------------------------------------------------------------

def _unfold(text):
    """Remove ICS line-folding (continuation lines start with space or tab)."""
    return re.sub(r"\r?\n[ \t]", "", text)


def _unescape(value):
    """Unescape ICS text values."""
    return (
        value
        .replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def parse_ics_events(source):
    """Return a list of dicts, one per VEVENT block."""
    raw = load_ics_content(source)

    raw = _unfold(raw)
    events = []
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", raw, re.DOTALL):
        event = {}
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            key, _, value = line.partition(":")
            # Strip property parameters (e.g. DTSTART;TZID=America/New_York)
            key = key.split(";")[0].strip()
            event[key] = _unescape(value.strip())
        if event:
            events.append(event)
    return events


# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------

def local_kickoff(description):
    """Parse 'Local kickoff: 2026-06-11 13:00 UTC-6' from the DESCRIPTION."""
    m = re.search(
        r"Local kickoff:\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+UTC([+-]\d+)",
        description,
    )
    if m:
        dt = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M")
        return dt
    return None


def parse_utc_dt(value):
    """Parse an ICS UTC datetime string like '20260611T190000Z'."""
    return datetime.strptime(value.rstrip("Z"), "%Y%m%dT%H%M%S")


def duration_str(dtstart, dtend):
    """Return 'H:MM' duration string."""
    delta = dtend - dtstart
    total_min = int(delta.total_seconds() // 60)
    return f"{total_min // 60}:{total_min % 60:02d}"


def match_names(summary):
    """Split 'Team A vs Team B - FIFA World Cup 2026' → ('Team A', 'Team B')."""
    s = re.sub(r"\s*-\s*FIFA World Cup 2026$", "", summary, flags=re.IGNORECASE)
    parts = s.split(" vs ", 1)
    return (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else (s, "")


def event_notes(description):
    """Build a compact notes string from the group/round/match lines."""
    lines = []
    for line in description.split("\n"):
        line = line.strip()
        if not line or line.startswith("Local kickoff:") or line.startswith("Venue:"):
            continue
        lines.append(line)
    return " | ".join(lines)


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------

def ics_to_teamsnap_csv(ics_path, csv_path, arrival_minutes=30):
    events = parse_ics_events(ics_path)

    columns = [
        "Date",
        "Time",
        "Duration (HH:MM)",
        "Arrival Time (Minutes)",
        "Name",
        "Opponent Name",
        "Opponent Contact Name",
        "Opponent Contact Phone Number",
        "Opponent Contact E-mail Address",
        "Location Name",
        "Location Address",
        "Location Details",
        "Location URL",
        "Home or Away",
        "Uniform",
        "Extra Label",
        "Notes",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)

        for ev in events:
            summary = ev.get("SUMMARY", "")
            description = ev.get("DESCRIPTION", "")
            location = ev.get("LOCATION", "")
            dtstart_str = ev.get("DTSTART", "")
            dtend_str = ev.get("DTEND", "")

            # Prefer local kickoff time from DESCRIPTION; fall back to UTC DTSTART
            local_dt = local_kickoff(description)
            if local_dt is None and dtstart_str:
                local_dt = parse_utc_dt(dtstart_str)

            # Duration is timezone-independent (difference between UTC times)
            dur = "2:00"
            if dtstart_str and dtend_str:
                dur = duration_str(parse_utc_dt(dtstart_str), parse_utc_dt(dtend_str))

            date_s = local_dt.strftime("%m/%d/%Y")
            # 12-hour time without leading zero on the hour
            time_s = local_dt.strftime("%I:%M %p").lstrip("0")

            team1, team2 = match_names(summary)
            name = f"{team1} vs {team2}"
            notes = event_notes(description)

            writer.writerow([
                date_s,          # Date
                time_s,          # Time
                dur,             # Duration (HH:MM)
                arrival_minutes, # Arrival Time (Minutes)
                name,            # Name  (event style — no opponent fields needed)
                "",              # Opponent Name
                "",              # Opponent Contact Name
                "",              # Opponent Contact Phone Number
                "",              # Opponent Contact E-mail Address
                location,        # Location Name
                "",              # Location Address
                "",              # Location Details
                "",              # Location URL
                "",              # Home or Away
                "",              # Uniform
                "World Cup 2026",# Extra Label
                notes,           # Notes
            ])

    print(f"Wrote {len(events)} events → {csv_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    ics_file = sys.argv[1]
    csv_file = sys.argv[2]
    arrival = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    ics_to_teamsnap_csv(ics_file, csv_file, arrival_minutes=arrival)
