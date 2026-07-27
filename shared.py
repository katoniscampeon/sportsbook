"""
Shared module for Sportsbook Dashboard and Calendar View.
Contains all data-fetching functions, constants, and helpers.
"""
import streamlit as st
import requests
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------------
session = requests.Session()
athens_tz = ZoneInfo("Europe/Athens")
now_athens = datetime.now(athens_tz)
effective_today = (now_athens - timedelta(hours=7)).date()
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# -------------------------------------------------------------
# CATEGORY & LEAGUE MAPPINGS
# -------------------------------------------------------------
categories_info = [
    {"id": "⭐ Top Leagues", "label": "Top Leagues", "flag": None},
    {"id": "🌐 All", "label": "All", "flag": None},
    {"id": "Germany", "label": "Germany", "flag": "de"},
    {"id": "Norway", "label": "Norway", "flag": "no"},
    {"id": "Finland", "label": "Finland", "flag": "fi"},
    {"id": "Netherlands", "label": "Netherlands", "flag": "nl"},
    {"id": "Sweden", "label": "Sweden", "flag": "se"},
    {"id": "Filler Leagues", "label": "Filler Leagues", "flag": "un"}
]

category_mapping = {
    "⭐ Top Leagues": [
        ("espn", "soccer", "eng.1", "Premier League", "gb-eng"),
        ("espn", "soccer", "esp.1", "La Liga", "es"),
        ("espn", "soccer", "ger.1", "Bundesliga", "de"),
        ("espn", "soccer", "ita.1", "Serie A", "it"),
        ("espn", "soccer", "uefa.champions", "UEFA Champions League", "eu"),
        ("espn", "soccer", "uefa.europa", "UEFA Europa League", "eu"),
        ("espn", "soccer", "uefa.europa.conf", "UEFA Conference League", "eu"),
        ("espn", "basketball", "usa.nba", "NBA", "us")
    ],
    "Germany": [
        ("espn", "soccer", "ger.1", "Germany - Bundesliga", "de"),
        ("espn", "soccer", "ger.2", "Germany - 2. Bundesliga", "de"),
        ("espn", "soccer", "aut.1", "Austria - Bundesliga", "at"),
        ("espn", "soccer", "tur.1", "Turkey - Süper Lig", "tr")
    ],
    "Norway": [
        ("espn", "soccer", "nor.1", "Norway - Eliteserien", "no")
    ],
    "Finland": [
        ("oddsapi", "soccer_finland_veikkausliiga", "Finland - Veikkausliiga", "fi"),
        ("oddsapi", "icehockey_liiga", "Finland - Liiga", "fi"),
        ("espn", "hockey", "usa.nhl", "NHL", "us")
    ],
    "Netherlands": [
        ("espn", "soccer", "ned.1", "Netherlands - Eredivisie", "nl")
    ],
    "Sweden": [
        ("espn", "soccer", "swe.1", "Sweden - Allsvenskan", "se")
    ],
    "Filler Leagues": [
        ("espn", "soccer", "bra.1", "Brazil - Série A", "br"),
        ("espn", "soccer", "arg.1", "Argentina - Liga Profesional", "ar"),
        ("espn", "soccer", "jpn.1", "Japan - J1 League", "jp")
    ]
}

odds_api_categories = ["Finland"]

def get_all_leagues_unique():
    """Return all unique leagues across all categories."""
    all_leagues = []
    seen = set()
    for leagues in category_mapping.values():
        for league in leagues:
            if league[0] == "espn":
                identifier = ("espn", league[2])
            else:
                identifier = ("oddsapi", league[1])
            if identifier not in seen:
                all_leagues.append(league)
                seen.add(identifier)
    return all_leagues

# -------------------------------------------------------------
# ODDS PARSER (ESPN)
# -------------------------------------------------------------
def parse_odd_value(raw):
    if raw is None or raw == "":
        return None
    try:
        if isinstance(raw, str) and (raw.startswith("+") or raw.startswith("-")):
            val = float(raw)
            if val > 0:
                return f"{(val / 100.0) + 1.0:.2f}"
            elif val < 0:
                return f"{(100.0 / abs(val)) + 1.0:.2f}"
        val = float(raw)
        if val == 0:
            return None
        if 1.0 < val < 50.0:
            return f"{val:.2f}"
        elif val > 0:
            return f"{(val / 100.0) + 1.0:.2f}"
        elif val < 0:
            return f"{(100.0 / abs(val)) + 1.0:.2f}"
    except (ValueError, TypeError):
        pass
    return None

def search_team_odd_in_dict(d):
    if d is None:
        return None
    if not isinstance(d, dict):
        return parse_odd_value(d)
    for key in ["value", "moneyLine", "moneyline", "odds", "american", "decimal", "summary"]:
        if key in d and d[key] is not None:
            res = parse_odd_value(d[key])
            if res:
                return res
    return None

def extract_all_match_odds(odds_data):
    home_odd = "N/A"
    draw_odd = "N/A"
    away_odd = "N/A"
    if not odds_data or not isinstance(odds_data, list):
        return home_odd, draw_odd, away_odd
    for provider in odds_data:
        if not isinstance(provider, dict):
            continue
        if home_odd == "N/A":
            ml = provider.get("moneyline") or provider.get("moneyLine")
            if isinstance(ml, dict):
                home_info = ml.get("home", {})
                if isinstance(home_info, dict):
                    for period in ["close", "open"]:
                        odd_entry = home_info.get(period, {})
                        if isinstance(odd_entry, dict) and "odds" in odd_entry:
                            res = parse_odd_value(odd_entry["odds"])
                            if res:
                                home_odd = res
                                break
        if away_odd == "N/A":
            ml = provider.get("moneyline") or provider.get("moneyLine")
            if isinstance(ml, dict):
                away_info = ml.get("away", {})
                if isinstance(away_info, dict):
                    for period in ["close", "open"]:
                        odd_entry = away_info.get(period, {})
                        if isinstance(odd_entry, dict) and "odds" in odd_entry:
                            res = parse_odd_value(odd_entry["odds"])
                            if res:
                                away_odd = res
                                break
        if draw_odd == "N/A":
            draw_info = provider.get("drawOdds")
            if isinstance(draw_info, dict):
                res = parse_odd_value(draw_info.get("moneyLine"))
                if res:
                    draw_odd = res
        if home_odd == "N/A":
            for key in ["homeTeamOdds", "home", "homeOdds"]:
                res = search_team_odd_in_dict(provider.get(key))
                if res:
                    home_odd = res
                    break
        if away_odd == "N/A":
            for key in ["awayTeamOdds", "away", "awayOdds"]:
                res = search_team_odd_in_dict(provider.get(key))
                if res:
                    away_odd = res
                    break
        if draw_odd == "N/A":
            for key in ["draw", "drawOdds"]:
                res = search_team_odd_in_dict(provider.get(key))
                if res:
                    draw_odd = res
                    break
        if home_odd != "N/A" and away_odd != "N/A" and draw_odd != "N/A":
            break
    return home_odd, draw_odd, away_odd

# -------------------------------------------------------------
# THE ODDS API HELPERS
# -------------------------------------------------------------
def extract_odds_api_h2h(event, is_hockey=False):
    odd_1 = "N/A"
    odd_X = "N/A"
    odd_2 = "N/A"
    home_team = event.get("home_team", "")
    away_team = event.get("away_team", "")
    for bookmaker in event.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market.get("key") != "h2h":
                continue
            for outcome in market.get("outcomes", []):
                name = outcome.get("name", "")
                price = outcome.get("price")
                if price is not None and float(price) > 1.0:
                    price_str = f"{float(price):.2f}"
                else:
                    price_str = "N/A"
                if name == home_team and odd_1 == "N/A":
                    odd_1 = price_str
                elif name == away_team and odd_2 == "N/A":
                    odd_2 = price_str
                elif name in ("Draw", "draw") and odd_X == "N/A":
                    odd_X = price_str
            if odd_1 != "N/A" and odd_2 != "N/A":
                break
        if odd_1 != "N/A" and odd_2 != "N/A":
            break
    if is_hockey:
        odd_X = "-"
    return odd_1, odd_X, odd_2

# -------------------------------------------------------------
# SINGLE-DAY FETCHERS
# -------------------------------------------------------------
@st.cache_data(ttl=120)
def fetch_single_league(sport, league_code, league_name, flag_code, target_date):
    date_str_curr = target_date.strftime("%Y%m%d")
    date_str_next = (target_date + timedelta(days=1)).strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league_code}/scoreboard?dates={date_str_curr}-{date_str_next}"
    try:
        response = session.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            events = data.get("events", [])
            matches = []
            for event in events:
                utc_dt = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
                athens_dt = utc_dt.astimezone(ZoneInfo("Europe/Athens"))
                match_effective_date = (athens_dt - timedelta(hours=7)).date()
                if match_effective_date != target_date:
                    continue
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                competition = competitions[0]
                competitors = competition.get("competitors", [])
                home_comp_list = [c for c in competitors if c.get("homeAway") == "home"]
                away_comp_list = [c for c in competitors if c.get("homeAway") == "away"]
                if not home_comp_list or not away_comp_list:
                    continue
                home_comp = home_comp_list[0]
                away_comp = away_comp_list[0]
                home_team = home_comp.get("team", {}).get("displayName", "Home")
                home_logo = home_comp.get("team", {}).get("logo", "")
                away_team = away_comp.get("team", {}).get("displayName", "Away")
                away_logo = away_comp.get("team", {}).get("logo", "")
                odds_data = competition.get("odds", [])
                odd_1, odd_X, odd_2 = extract_all_match_odds(odds_data)
                no_draw_sports = ["basketball", "hockey"]
                no_draw_leagues = ["usa.nba", "usa.nhl"]
                if sport in no_draw_sports or league_code in no_draw_leagues:
                    odd_X = "-"
                matches.append({
                    "Διοργάνωση": league_name,
                    "Flag": flag_code,
                    "Ώρα": athens_dt.strftime("%H:%M"),
                    "Logo Γηπ.": home_logo,
                    "Γηπεδούχος": home_team,
                    "1": odd_1,
                    "X": odd_X,
                    "2": odd_2,
                    "Logo Φιλ.": away_logo,
                    "Φιλοξενούμενος": away_team
                })
            return matches
    except Exception:
        pass
    return []

@st.cache_data(ttl=300)
def fetch_odds_api_league(sport_key, league_name, flag_code, target_date, api_key):
    if not api_key:
        return []
    url = f"{ODDS_API_BASE}/sports/{sport_key}/odds/"
    params = {"apiKey": api_key, "regions": "eu", "oddsFormat": "decimal", "dateFormat": "iso"}
    try:
        response = session.get(url, params=params, timeout=10)
        if response.status_code == 422:
            return []
        if response.status_code == 401:
            return [{"error": "invalid_key"}]
        if response.status_code == 429:
            return [{"error": "rate_limit"}]
        if response.status_code != 200:
            return []
        events = response.json()
        is_hockey = "icehockey" in sport_key
        matches = []
        for event in events:
            utc_str = event.get("commence_time", "")
            if not utc_str:
                continue
            utc_dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
            athens_dt = utc_dt.astimezone(ZoneInfo("Europe/Athens"))
            match_effective_date = (athens_dt - timedelta(hours=7)).date()
            if match_effective_date != target_date:
                continue
            home_team = event.get("home_team", "Home")
            away_team = event.get("away_team", "Away")
            odd_1, odd_X, odd_2 = extract_odds_api_h2h(event, is_hockey=is_hockey)
            matches.append({
                "Διοργάνωση": league_name,
                "Flag": flag_code,
                "Ώρα": athens_dt.strftime("%H:%M"),
                "Logo Γηπ.": "",
                "Γηπεδούχος": home_team,
                "1": odd_1,
                "X": odd_X,
                "2": odd_2,
                "Logo Φιλ.": "",
                "Φιλοξενούμενος": away_team
            })
        return matches
    except Exception:
        pass
    return []

def fetch_all_matches_parallel(leagues, target_date, odds_api_key=""):
    all_matches = []
    has_odds_api_error = None
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for league in leagues:
            if league[0] == "espn":
                _, sport, code, name, flag = league
                futures[executor.submit(fetch_single_league, sport, code, name, flag, target_date)] = "espn"
            elif league[0] == "oddsapi":
                _, sport_key, name, flag = league
                futures[executor.submit(fetch_odds_api_league, sport_key, name, flag, target_date, odds_api_key)] = "oddsapi"
        for future in as_completed(futures):
            res = future.result()
            source = futures[future]
            if source == "oddsapi" and res and isinstance(res, list) and res and isinstance(res[0], dict) and "error" in res[0]:
                has_odds_api_error = res[0]["error"]
            elif res:
                all_matches.extend(res)
    return all_matches, has_odds_api_error

# -------------------------------------------------------------
# DATE-RANGE FETCHERS (for Calendar View)
# -------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_single_league_range(sport, league_code, league_name, flag_code, start_date, end_date):
    """Fetch matches for a date range, returning dict of date -> list of matches."""
    date_str_start = start_date.strftime("%Y%m%d")
    date_str_end = (end_date + timedelta(days=1)).strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league_code}/scoreboard?dates={date_str_start}-{date_str_end}"
    try:
        response = session.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            events = data.get("events", [])
            matches_by_date = {}
            for event in events:
                utc_dt = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
                athens_dt = utc_dt.astimezone(ZoneInfo("Europe/Athens"))
                match_date = (athens_dt - timedelta(hours=7)).date()
                if match_date < start_date or match_date > end_date:
                    continue
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                competition = competitions[0]
                competitors = competition.get("competitors", [])
                home_comp_list = [c for c in competitors if c.get("homeAway") == "home"]
                away_comp_list = [c for c in competitors if c.get("homeAway") == "away"]
                if not home_comp_list or not away_comp_list:
                    continue
                home_comp = home_comp_list[0]
                away_comp = away_comp_list[0]
                home_team = home_comp.get("team", {}).get("displayName", "Home")
                away_team = away_comp.get("team", {}).get("displayName", "Away")
                odds_data = competition.get("odds", [])
                odd_1, odd_X, odd_2 = extract_all_match_odds(odds_data)
                no_draw_sports = ["basketball", "hockey"]
                no_draw_leagues = ["usa.nba", "usa.nhl"]
                if sport in no_draw_sports or league_code in no_draw_leagues:
                    odd_X = "-"
                match = {
                    "Διοργάνωση": league_name,
                    "Flag": flag_code,
                    "Ώρα": athens_dt.strftime("%H:%M"),
                    "Γηπεδούχος": home_team,
                    "Φιλοξενούμενος": away_team,
                    "1": odd_1,
                    "X": odd_X,
                    "2": odd_2
                }
                if match_date not in matches_by_date:
                    matches_by_date[match_date] = []
                matches_by_date[match_date].append(match)
            return matches_by_date
    except Exception:
        pass
    return {}

@st.cache_data(ttl=300)
def fetch_odds_api_league_range(sport_key, league_name, flag_code, start_date, end_date, api_key):
    """Fetch matches for a date range from The Odds API."""
    if not api_key:
        return {}
    url = f"{ODDS_API_BASE}/sports/{sport_key}/odds/"
    params = {"apiKey": api_key, "regions": "eu", "oddsFormat": "decimal", "dateFormat": "iso"}
    try:
        response = session.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return {}
        events = response.json()
        is_hockey = "icehockey" in sport_key
        matches_by_date = {}
        for event in events:
            utc_str = event.get("commence_time", "")
            if not utc_str:
                continue
            utc_dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
            athens_dt = utc_dt.astimezone(ZoneInfo("Europe/Athens"))
            match_date = (athens_dt - timedelta(hours=7)).date()
            if match_date < start_date or match_date > end_date:
                continue
            home_team = event.get("home_team", "Home")
            away_team = event.get("away_team", "Away")
            odd_1, odd_X, odd_2 = extract_odds_api_h2h(event, is_hockey=is_hockey)
            match = {
                "Διοργάνωση": league_name,
                "Flag": flag_code,
                "Ώρα": athens_dt.strftime("%H:%M"),
                "Γηπεδούχος": home_team,
                "Φιλοξενούμενος": away_team,
                "1": odd_1,
                "X": odd_X,
                "2": odd_2
            }
            if match_date not in matches_by_date:
                matches_by_date[match_date] = []
            matches_by_date[match_date].append(match)
        return matches_by_date
    except Exception:
        pass
    return {}

def fetch_all_matches_for_range(all_leagues, start_date, end_date, odds_api_key=""):
    """Fetch all matches for a date range, returning dict of date -> list of matches."""
    matches_by_date = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for league in all_leagues:
            if league[0] == "espn":
                _, sport, code, name, flag = league
                futures[executor.submit(fetch_single_league_range, sport, code, name, flag, start_date, end_date)] = "espn"
            elif league[0] == "oddsapi":
                _, sport_key, name, flag = league
                futures[executor.submit(fetch_odds_api_league_range, sport_key, name, flag, start_date, end_date, odds_api_key)] = "oddsapi"
        for future in as_completed(futures):
            res = future.result()
            if isinstance(res, dict):
                for d, matches in res.items():
                    if d not in matches_by_date:
                        matches_by_date[d] = []
                    matches_by_date[d].extend(matches)
    return matches_by_date
