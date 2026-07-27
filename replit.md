# Sportsbook Dashboard

A Streamlit-based sportsbook dashboard with live odds and a calendar view.

## Stack
- **Python 3.12** — Streamlit app
- **Streamlit** — UI framework
- **ESPN Scoreboard API** — free, no key required; fetches soccer, basketball, hockey, and tennis fixtures
- **The Odds API** — optional; provides odds for Finnish leagues (Veikkausliiga, Liiga)
- **promo_store.py** — local JSON-backed persistent promo storage (`promos.json`)

## Running the app
```
streamlit run sportsbook_dashboard.py --server.port 5000 --server.address 0.0.0.0
```
Or use the **Start application** workflow in Replit.

## Pages
- `sportsbook_dashboard.py` — main day-by-day odds view
- `pages/Calendar_View.py` — 90-day calendar with sport separation and promo display

## Key files
| File | Purpose |
|---|---|
| `shared.py` | All fetch functions, league/category config, sport helpers |
| `promo_store.py` | Read/write `promos.json`; auto-expires past promos on load |
| `promos.json` | Persisted promos (auto-created on first save) |
| `.streamlit/config.toml` | Server config, disables usage stats prompt |

## Optional secrets
Add to `.streamlit/secrets.toml` for Finnish league odds:
```toml
odds_api_key = "your_key_here"
```
Get a free key at https://the-odds-api.com

## User preferences
- UI language: Greek (Ελληνικά) for labels; code comments in English
- Timezone: Europe/Athens; effective day shifts at 07:00
- Keep existing file/module structure — do not restructure or migrate
