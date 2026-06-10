# worldcup-teamsnap

Convert a FIFA World Cup 2026 calendar into a TeamSnap-importable CSV schedule, so team members can see every match for their favorite nations directly in the TeamSnap app.

## How it works

1. Visit [myworldcupcalendar.com](https://myworldcupcalendar.com), pick the teams you want to follow, and copy your personalized calendar URL (e.g. `https://myworldcupcalendar.com/calendar/WrQgqpGv`).
2. Run `ics_to_teamsnap.py` with that URL (or a downloaded `.ics` file) to generate the CSV.
3. Import the CSV into TeamSnap.

The script requires no third-party libraries — only the Python standard library.

## Usage

```bash
python3 ics_to_teamsnap.py <input> <output.csv> [arrival_minutes]
```

| Argument | Description |
|---|---|
| `input` | Shared calendar page URL, direct `.ics` API URL, or a local `.ics` file path |
| `output.csv` | Path where the TeamSnap-importable CSV will be written |
| `arrival_minutes` | Minutes before kickoff to set as arrival time (default: `30`) |

### Examples

```bash
# From a shared myworldcupcalendar.com URL (recommended)
python3 ics_to_teamsnap.py https://myworldcupcalendar.com/calendar/WrQgqpGv worldcup2026.csv

# With a custom arrival time of 45 minutes
python3 ics_to_teamsnap.py https://myworldcupcalendar.com/calendar/WrQgqpGv worldcup2026.csv 45

# From a locally downloaded .ics file
python3 ics_to_teamsnap.py schedule.ics worldcup2026.csv
```

When given a shared calendar page URL, the script automatically discovers and fetches the underlying `.ics` download link — no manual downloading required.

## CSV output format

Each row in the output represents one match as a TeamSnap **event** with:

| TeamSnap field | Value |
|---|---|
| Date | Local match date (`MM/DD/YYYY`) |
| Time | Local kickoff time (`HH:MM AM/PM`) |
| Duration | Match duration (typically `2:00`) |
| Arrival Time | Minutes before kickoff (configurable) |
| Name | `Team A vs Team B` |
| Location Name | Host city and country |
| Extra Label | `World Cup 2026` |
| Notes | Group, matchday, and match number |

Times are shown in the **host city's local timezone** as published by myworldcupcalendar.com, not converted to UTC.

## Importing into TeamSnap

1. In TeamSnap, open your team and go to **Schedule**.
2. Click **Import Events** and select the generated CSV file.
3. Confirm the column mapping when prompted and complete the import.

## Files

| File | Description |
|---|---|
| `ics_to_teamsnap.py` | Conversion script |
| `teamsnap_schedule_template.csv` | Official TeamSnap import template (for reference) |
| `world-cup-2026-*.ics` | Example downloaded ICS file for 10 nations, 3 host nations and 7 most favorite to win it |
