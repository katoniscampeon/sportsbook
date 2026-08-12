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
# LEAGUE LOGOS (all sourced directly from ESPN scoreboard API)
# -------------------------------------------------------------
LEAGUE_LOGOS = {
    # ESPN soccer — top leagues
    ("espn", "eng.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/23.png",
    ("espn", "esp.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/15.png",
    ("espn", "ger.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/10.png",
    ("espn", "ita.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/12.png",
    ("espn", "fra.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/9.png",
    # ESPN soccer — UEFA
    ("espn", "uefa.champions"):      "https://a.espncdn.com/i/leaguelogos/soccer/500/2.png",
    ("espn", "uefa.europa"):         "https://a.espncdn.com/i/leaguelogos/soccer/500/2310.png",
    ("espn", "uefa.europa.conf"):    "https://a.espncdn.com/i/leaguelogos/soccer/500/20296.png",
    ("espn", "uefa.super_cup"):      "https://a.espncdn.com/i/leaguelogos/soccer/500/1272.png",
    # ESPN soccer — domestic cups
    ("espn", "eng.league_cup"):      "https://a.espncdn.com/i/leaguelogos/soccer/500/41.png",   # EFL/Carabao Cup
    ("espn", "fra.coupe_de_france"): "https://a.espncdn.com/i/leaguelogos/soccer/500/182.png",
    ("espn", "ger.dfb_pokal"):       "https://a.espncdn.com/i/leaguelogos/soccer/500/2061.png",  # fixed
    ("espn", "ita.coppa_italia"):    "https://a.espncdn.com/i/leaguelogos/soccer/500/2192.png",  # fixed
    ("espn", "esp.copa_del_rey"):    "https://a.espncdn.com/i/leaguelogos/soccer/500/73.png",
    ("espn", "ned.cup"):             "https://a.espncdn.com/i/leaguelogos/soccer/500/197.png",
    # ESPN soccer — other leagues
    ("espn", "ger.2"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/97.png",
    ("espn", "aut.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/5.png",
    ("espn", "tur.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/18.png",
    ("espn", "nor.1"):               "https://base44.app/api/apps/6a6377d69bbbbbc36ad8c7da/files/mp/public/6a6377d69bbbbbc36ad8c7da/180ab1032_eliteserien_logo.png",
    ("espn", "ned.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/11.png",
    ("espn", "swe.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/16.png",
    ("espn", "bra.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/85.png",
    ("espn", "arg.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/1.png",
    ("espn", "jpn.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/2199.png",
    ("espn", "bel.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/6.png",
    ("espn", "por.1"):               "https://a.espncdn.com/i/leaguelogos/soccer/500/14.png",
    # ESPN soccer — UEFA qualifiers (same logos as the main competitions)
    ("espn", "uefa.champions_qual"):   "https://a.espncdn.com/i/leaguelogos/soccer/500/2.png",
    ("espn", "uefa.europa_qual"):      "https://a.espncdn.com/i/leaguelogos/soccer/500/2310.png",
    ("espn", "uefa.europa.conf_qual"): "https://a.espncdn.com/i/leaguelogos/soccer/500/20296.png",
    # ESPN basketball
    ("espn", "usa.nba"):             "https://a.espncdn.com/i/teamlogos/leagues/500/nba.png",
    # ESPN hockey
    ("espn", "usa.nhl"):             "https://a.espncdn.com/i/teamlogos/leagues/500/nhl.png",
    # ESPN tennis — generic ATP logo; individual tournament logos set at fetch time
    ("espn", "atp"):                 "https://a.espncdn.com/combiner/i?img=/redesign/assets/img/icons/ESPN-icon-tennis.png",
    # Odds API
    ("oddsapi", "soccer_finland_veikkausliiga"): "https://base44.app/api/apps/6a6377d69bbbbbc36ad8c7da/files/mp/public/6a6377d69bbbbbc36ad8c7da/e11214525_veikkausliiga_logo.png",
    ("oddsapi", "icehockey_liiga"):              "https://base44.app/api/apps/6a6377d69bbbbbc36ad8c7da/files/mp/public/6a6377d69bbbbbc36ad8c7da/b5c79c5c1_liiga_logo.png",
}

def get_league_logo(source, code):
    return LEAGUE_LOGOS.get((source, code), "")

# -------------------------------------------------------------
# CATEGORY & LEAGUE MAPPINGS
# Tuple format:
#   ESPN:    ("espn", sport, league_code, display_name, flag_code)
#   OddsAPI: ("oddsapi", sport_key, display_name, flag_code)
# -------------------------------------------------------------
categories_info = [
    {"id": "⭐ Top Leagues", "label": "Top Leagues", "flag": None},
    {"id": "🌐 All",         "label": "All",         "flag": None},
    {"id": "France",         "label": "France",       "flag": "fr"},
    {"id": "Germany",        "label": "Germany",      "flag": "de"},
    {"id": "Norway",         "label": "Norway",       "flag": "no"},
    {"id": "Finland",        "label": "Finland",      "flag": "fi"},
    {"id": "Netherlands",    "label": "Netherlands",  "flag": "nl"},
    {"id": "Sweden",         "label": "Sweden",       "flag": "se"},
    {"id": "🎾 Tennis",      "label": "Tennis",       "flag": None},
    {"id": "Filler Leagues", "label": "Filler",       "flag": "un"},
]

category_mapping = {
    "⭐ Top Leagues": [
        ("espn", "soccer",     "eng.1",            "Premier League",             "gb-eng"),
        ("espn", "soccer",     "esp.1",            "La Liga",                    "es"),
        ("espn", "soccer",     "ger.1",            "Bundesliga",                 "de"),
        ("espn", "soccer",     "ita.1",            "Serie A",                    "it"),
        ("espn", "soccer",     "fra.1",            "Ligue 1",                    "fr"),
        ("espn", "soccer",     "uefa.champions",   "UEFA Champions League",      "eu"),
        ("espn", "soccer",     "uefa.europa",      "UEFA Europa League",         "eu"),
        ("espn", "soccer",     "uefa.europa.conf", "UEFA Conference League",     "eu"),
        ("espn", "soccer",     "uefa.super_cup",   "UEFA Super Cup",             "eu"),
        ("espn", "soccer",     "eng.league_cup",   "EFL Cup",                    "gb-eng"),
        ("espn", "basketball", "usa.nba",          "NBA",                        "us"),
        ("espn", "basketball", "usa.nba",          "NBA Preseason",              "us", "seasontype=1"),
        ("espn", "soccer",     "uefa.champions_qual",   "UCL Qualifying",        "eu"),
        ("espn", "soccer",     "uefa.europa_qual",      "UEL Qualifying",        "eu"),
        ("espn", "soccer",     "uefa.europa.conf_qual", "UECL Qualifying",       "eu"),
    ],
    "France": [
        ("espn", "soccer", "fra.1",            "France - Ligue 1",          "fr"),
        ("espn", "soccer", "fra.coupe_de_france","France - Coupe de France", "fr"),
    ],
    "Germany": [
        ("espn", "soccer", "ger.1",        "Germany - Bundesliga",    "de"),
        ("espn", "soccer", "ger.2",        "Germany - 2. Bundesliga", "de"),
        ("espn", "soccer", "ger.dfb_pokal","Germany - DFB Pokal",     "de"),
        ("espn", "soccer", "aut.1",        "Austria - Bundesliga",    "at"),
        ("espn", "soccer", "tur.1",        "Turkey - Süper Lig",      "tr"),
    ],
    "Norway": [
        ("espn", "soccer", "nor.1", "Norway - Eliteserien", "no"),
    ],
    "Finland": [
        ("oddsapi", "soccer_finland_veikkausliiga", "Finland - Veikkausliiga", "fi"),
        ("oddsapi", "icehockey_liiga",              "Finland - Liiga",         "fi"),
        ("espn",    "hockey", "usa.nhl",            "NHL",                     "us"),
    ],
    "Netherlands": [
        ("espn", "soccer", "ned.1",  "Netherlands - Eredivisie",  "nl"),
        ("espn", "soccer", "ned.cup","Netherlands - KNVB Beker",  "nl"),
    ],
    "Sweden": [
        ("espn", "soccer", "swe.1", "Sweden - Allsvenskan", "se"),
    ],
    "🎾 Tennis": [
        ("espn", "tennis", "atp", "ATP Tour", "un"),
    ],
    "Filler Leagues": [
        ("espn", "soccer", "bra.1",  "Brazil - Série A",                "br"),
        ("espn", "soccer", "arg.1",  "Argentina - Liga Profesional",    "ar"),
        ("espn", "soccer", "jpn.1",  "Japan - J1 League",               "jp"),
        ("espn", "soccer", "bel.1",  "Belgium - Pro League",            "be"),
        ("espn", "soccer", "por.1",  "Portugal - Primeira Liga",        "pt"),
    ],
}

# Leagues added to "🌐 All" on top of the per-category ones
ALL_EXTRA_LEAGUES = [
    ("espn", "soccer", "ita.coppa_italia",    "Coppa Italia",    "it"),
    ("espn", "soccer", "ger.dfb_pokal",       "DFB Pokal",       "de"),
    ("espn", "soccer", "eng.league_cup",      "EFL Cup",         "gb-eng"),
    ("espn", "soccer", "uefa.super_cup",      "UEFA Super Cup",  "eu"),
    ("espn", "soccer", "fra.coupe_de_france", "Coupe de France", "fr"),
]

odds_api_categories  = ["Finland"]
excluded_from_all    = ["Filler Leagues", "Tennis"]

# Display order — dashboard & calendar sort leagues by this list
LEAGUE_DISPLAY_ORDER = [
    ("espn", "uefa.champions"),
    ("espn", "uefa.europa"),
    ("espn", "uefa.europa.conf"),
    ("espn", "uefa.super_cup"),
    ("espn", "eng.1"),
    ("espn", "esp.1"),
    ("espn", "ger.1"),
    ("espn", "ita.1"),
    ("espn", "fra.1"),
    ("espn", "eng.league_cup"),
    ("espn", "eng.fa"),
    ("espn", "esp.copa_del_rey"),
    ("espn", "ger.dfb_pokal"),
    ("espn", "ita.coppa_italia"),
    ("espn", "fra.coupe_de_france"),
    ("espn", "ned.1"),
    ("espn", "ned.cup"),
    ("espn", "swe.1"),
    ("espn", "nor.1"),
    ("espn", "ger.2"),
    ("espn", "aut.1"),
    ("espn", "tur.1"),
    ("oddsapi", "soccer_finland_veikkausliiga"),
    ("oddsapi", "icehockey_liiga"),
    ("espn", "usa.nba"),
    ("espn", "usa.nhl"),
    ("espn", "atp"),
    ("espn", "bra.1"),
    ("espn", "arg.1"),
    ("espn", "jpn.1"),
    ("espn", "bel.1"),
    ("espn", "por.1"),
]

def get_custom_league_order():
    """Returns the custom league order from session_state, or the default LEAGUE_DISPLAY_ORDER."""
    if hasattr(st, "session_state") and "custom_league_order" in st.session_state:
        return st.session_state.custom_league_order
    return LEAGUE_DISPLAY_ORDER


def _league_sort_key(league, custom_order=None):
    order = custom_order if custom_order is not None else get_custom_league_order()
    key = ("espn", league[2]) if league[0] == "espn" else ("oddsapi", league[1])
    try:
        return order.index(key)
    except ValueError:
        return len(order)


@st.dialog("🏆 Priority Ordering", width="large")
def priority_dialog():
    """Dialog to reorder leagues with up/down buttons."""
    if "custom_league_order" not in st.session_state:
        st.session_state.custom_league_order = list(LEAGUE_DISPLAY_ORDER)

    order = list(st.session_state.custom_league_order)

    def lg_key(l):
        return ("espn", l[2]) if l[0] == "espn" else ("oddsapi", l[1])

    def lg_name(l):
        return l[3] if l[0] == "espn" else l[2]

    def lg_logo(l):
        src  = l[0]
        code = l[2] if src == "espn" else l[1]
        return LEAGUE_LOGOS.get((src, code), "")

    all_lg = get_all_leagues_unique(custom_order=order)

    # Ensure any league not yet in order is appended
    for lg in all_lg:
        k = lg_key(lg)
        if k not in order:
            order.append(k)

    st.markdown("Χρησιμοποίησε τα βελάκια για να αλλάξεις σειρά:")
    st.markdown("")

    for i, lg in enumerate(all_lg):
        key  = lg_key(lg)
        name = lg_name(lg)
        logo = lg_logo(lg)
        c_logo, c_name, c_up, c_dn = st.columns([0.5, 6, 1, 1])
        with c_logo:
            if logo:
                st.image(logo, width=20)
        with c_name:
            st.markdown(f"**{name}**")
        with c_up:
            if i > 0 and st.button("▲", key=f"prio_up_{i}"):
                prev_key = lg_key(all_lg[i - 1])
                ki = order.index(key)       if key      in order else -1
                pi = order.index(prev_key) if prev_key in order else -1
                if ki >= 0 and pi >= 0:
                    order[ki], order[pi] = order[pi], order[ki]
                    st.session_state.custom_league_order = order
                st.rerun()
        with c_dn:
            if i < len(all_lg) - 1 and st.button("▼", key=f"prio_dn_{i}"):
                next_key = lg_key(all_lg[i + 1])
                ki = order.index(key)       if key      in order else -1
                ni = order.index(next_key) if next_key in order else -1
                if ki >= 0 and ni >= 0:
                    order[ki], order[ni] = order[ni], order[ki]
                    st.session_state.custom_league_order = order
                st.rerun()

    st.divider()
    c_save, c_reset = st.columns(2)
    with c_save:
        if st.button("💾 Αποθήκευση", type="primary", use_container_width=True):
            st.session_state.custom_league_order = order
            st.rerun()
    with c_reset:
        if st.button("🔄 Reset Default", use_container_width=True):
            st.session_state.custom_league_order = list(LEAGUE_DISPLAY_ORDER)
            st.rerun()


def get_all_leagues_unique(custom_order=None):
    if custom_order is None:
        custom_order = get_custom_league_order()
    all_leagues = []
    seen = set()

    def _add(league):
        key = ("espn", league[2]) if league[0] == "espn" else ("oddsapi", league[1])
        if key not in seen:
            all_leagues.append(league)
            seen.add(key)

    for cat_name, leagues in category_mapping.items():
        if cat_name in excluded_from_all:
            continue
        for league in leagues:
            _add(league)

    for league in ALL_EXTRA_LEAGUES:
        _add(league)

    all_leagues.sort(key=lambda l: _league_sort_key(l, custom_order))
    return all_leagues
# -------------------------------------------------------------
# ODDS PARSER (ESPN American → Decimal)
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
    home_odd = draw_odd = away_odd = "N/A"
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
# THE ODDS API — h2h extractor
# -------------------------------------------------------------
def extract_odds_api_h2h(event, is_hockey=False):
    odd_1 = odd_X = odd_2 = "N/A"
    home_team = event.get("home_team", "")
    away_team = event.get("away_team", "")
    for bookmaker in event.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market.get("key") != "h2h":
                continue
            for outcome in market.get("outcomes", []):
                name  = outcome.get("name", "")
                price = outcome.get("price")
                price_str = f"{float(price):.2f}" if price and float(price) > 1.0 else "N/A"
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

# No-draw sports
NO_DRAW_SPORTS  = {"basketball", "hockey", "tennis"}
NO_DRAW_LEAGUES = {"usa.nba", "usa.nhl", "atp", "wta"}


@st.cache_data(ttl=120)
def fetch_single_league(sport, league_code, league_name, flag_code, target_date, extra_params=""):
    """Fetch matches for an ESPN league on a specific day. Handles tennis tournaments too."""
    date_str_curr = target_date.strftime("%Y%m%d")
    date_str_next = (target_date + timedelta(days=1)).strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league_code}/scoreboard?dates={date_str_curr}-{date_str_next}"
    if extra_params:
        url += f"&{extra_params}"

    is_tennis   = (sport == "tennis")
    no_draw     = (sport in NO_DRAW_SPORTS or league_code in NO_DRAW_LEAGUES)
    league_logo = get_league_logo("espn", league_code)

    try:
        response = session.get(url, timeout=6)
        if response.status_code != 200:
            return []
        data   = response.json()
        events = data.get("events", [])
        matches = []

        for event in events:
            # ---- Tennis: each event is a tournament, competitions are individual matches ----
            if is_tennis:
                tournament_name = event.get("name", league_name)
                tournament_logo = league_logo  # fallback; ATP has no per-tournament CDN logo
                for grouping in event.get("groupings", []):
                    group_label = grouping.get("grouping", {}).get("displayName", "")
                    if "Singles" not in group_label and "singles" not in group_label:
                        continue  # Only Men's/Women's Singles
                    for comp in grouping.get("competitions", []):
                        utc_dt    = datetime.fromisoformat(comp["date"].replace("Z", "+00:00"))
                        athens_dt = utc_dt.astimezone(ZoneInfo("Europe/Athens"))
                        match_date = (athens_dt - timedelta(hours=7)).date()
                        if match_date != target_date:
                            continue
                        status = comp.get("status", {}).get("type", {}).get("state", "")
                        # Build player names from competitors
                        competitors = comp.get("competitors", [])
                        names = []
                        for c in competitors:
                            athlete = c.get("athlete", {})
                            names.append(athlete.get("displayName", "?"))
                        home_name = names[0] if len(names) > 0 else "?"
                        away_name = names[1] if len(names) > 1 else "?"
                        matches.append({
                            "Διοργάνωση":      tournament_name,
                            "Flag":            flag_code,
                            "League Logo":     tournament_logo,
                            "Ώρα":             athens_dt.strftime("%H:%M"),
                            "Sport":           sport,
                            "Logo Γηπ.":       "",
                            "Γηπεδούχος":      home_name,
                            "1":               "—",
                            "X":               "-",
                            "2":               "—",
                            "Logo Φιλ.":       "",
                            "Φιλοξενούμενος":  away_name,
                        })
                continue  # done with this tennis tournament event

            # ---- Regular sports (soccer, basketball, hockey) ----
            utc_dt    = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
            athens_dt = utc_dt.astimezone(ZoneInfo("Europe/Athens"))
            match_date = (athens_dt - timedelta(hours=7)).date()
            if match_date != target_date:
                continue
            competitions = event.get("competitions", [])
            if not competitions:
                continue
            competition = competitions[0]
            competitors = competition.get("competitors", [])
            home_list = [c for c in competitors if c.get("homeAway") == "home"]
            away_list = [c for c in competitors if c.get("homeAway") == "away"]
            if not home_list or not away_list:
                continue
            home_comp = home_list[0]
            away_comp = away_list[0]
            home_team = home_comp.get("team", {}).get("displayName", "Home")
            home_logo = home_comp.get("team", {}).get("logo", "")
            away_team = away_comp.get("team", {}).get("displayName", "Away")
            away_logo = away_comp.get("team", {}).get("logo", "")
            odds_data = competition.get("odds", [])
            odd_1, odd_X, odd_2 = extract_all_match_odds(odds_data)
            if no_draw:
                odd_X = "-"
            matches.append({
                "Διοργάνωση":     league_name,
                "Flag":           flag_code,
                "League Logo":    league_logo,
                "Ώρα":            athens_dt.strftime("%H:%M"),
                "Sport":          sport,
                "Logo Γηπ.":      home_logo,
                "Γηπεδούχος":     home_team,
                "1":              odd_1,
                "X":              odd_X,
                "2":              odd_2,
                "Logo Φιλ.":      away_logo,
                "Φιλοξενούμενος": away_team,
            })
        return matches
    except Exception:
        return []

# -------------------------------------------------------------
# ODDS API — single day fetcher (fixtures first, odds if available)
# -------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_odds_api_league(sport_key, league_name, flag_code, target_date, api_key):
    if not api_key:
        return []
    is_hockey  = "icehockey" in sport_key
    league_logo = get_league_logo("oddsapi", sport_key)

    # 1) Try /events/ first (cheaper, fixtures only)
    events_url = f"{ODDS_API_BASE}/sports/{sport_key}/events/"
    odds_by_id = {}
    try:
        r = session.get(events_url, params={"apiKey": api_key, "dateFormat": "iso"}, timeout=10)
        if r.status_code == 200:
            raw_events = r.json()
        elif r.status_code == 401:
            return [{"error": "invalid_key"}]
        elif r.status_code == 422:
            raw_events = []
        else:
            raw_events = []
    except Exception:
        raw_events = []

    # 2) If no events from /events/, fall back to /odds/
    if not raw_events:
        try:
            r2 = session.get(
                f"{ODDS_API_BASE}/sports/{sport_key}/odds/",
                params={"apiKey": api_key, "regions": "eu", "oddsFormat": "decimal", "dateFormat": "iso"},
                timeout=10,
            )
            if r2.status_code == 200:
                raw_events = r2.json()
                # Mark events as having odds embedded
                for ev in raw_events:
                    odds_by_id[ev.get("id", "")] = ev
            elif r2.status_code == 401:
                return [{"error": "invalid_key"}]
            elif r2.status_code == 429:
                return [{"error": "rate_limit"}]
        except Exception:
            pass

    matches = []
    for event in raw_events:
        utc_str = event.get("commence_time", "")
        if not utc_str:
            continue
        utc_dt    = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        athens_dt = utc_dt.astimezone(ZoneInfo("Europe/Athens"))
        match_date = (athens_dt - timedelta(hours=7)).date()
        if match_date != target_date:
            continue
        home_team = event.get("home_team", "Home")
        away_team = event.get("away_team", "Away")
        # Try odds from the event itself (if /odds/ was used), else N/A
        ev_with_odds = odds_by_id.get(event.get("id", ""), event)
        odd_1, odd_X, odd_2 = extract_odds_api_h2h(ev_with_odds, is_hockey=is_hockey)
        matches.append({
            "Διοργάνωση":     league_name,
            "Flag":           flag_code,
            "League Logo":    league_logo,
            "Sport":          "hockey" if is_hockey else "soccer",
            "Ώρα":            athens_dt.strftime("%H:%M"),
            "Logo Γηπ.":      "",
            "Γηπεδούχος":     home_team,
            "1":              odd_1,
            "X":              odd_X,
            "2":              odd_2,
            "Logo Φιλ.":      "",
            "Φιλοξενούμενος": away_team,
        })
    return matches

# -------------------------------------------------------------
# PARALLEL FETCHER — single day
# -------------------------------------------------------------
def fetch_all_matches_parallel(leagues, target_date, odds_api_key=""):
    all_matches = []
    has_odds_api_error = None
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for league in leagues:
            if league[0] == "espn":
                _, sport, code, name, flag = league[:5]
                extra = league[5] if len(league) > 5 else ""
                futures[executor.submit(fetch_single_league, sport, code, name, flag, target_date, extra)] = "espn"
            elif league[0] == "oddsapi":
                _, sport_key, name, flag = league
                futures[executor.submit(fetch_odds_api_league, sport_key, name, flag, target_date, odds_api_key)] = "oddsapi"
        for future in as_completed(futures):
            res    = future.result()
            source = futures[future]
            if source == "oddsapi" and res and isinstance(res[0], dict) and "error" in res[0]:
                has_odds_api_error = res[0]["error"]
            elif res:
                all_matches.extend(res)
    return all_matches, has_odds_api_error

# -------------------------------------------------------------
# ESPN — date-range fetcher (for Calendar View)
# -------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_single_league_range(sport, league_code, league_name, flag_code, start_date, end_date, extra_params=""):
    date_str_start = start_date.strftime("%Y%m%d")
    date_str_end   = (end_date + timedelta(days=1)).strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league_code}/scoreboard?dates={date_str_start}-{date_str_end}"
    if extra_params:
        url += f"&{extra_params}"
    is_tennis   = (sport == "tennis")
    no_draw     = (sport in NO_DRAW_SPORTS or league_code in NO_DRAW_LEAGUES)
    league_logo = get_league_logo("espn", league_code)

    try:
        response = session.get(url, timeout=10)
        if response.status_code != 200:
            return {}
        data   = response.json()
        events = data.get("events", [])
        matches_by_date = {}

        for event in events:
            if is_tennis:
                tournament_name = event.get("name", league_name)
                tournament_logo = league_logo
                for grouping in event.get("groupings", []):
                    group_label = grouping.get("grouping", {}).get("displayName", "")
                    if "Singles" not in group_label and "singles" not in group_label:
                        continue
                    for comp in grouping.get("competitions", []):
                        utc_dt    = datetime.fromisoformat(comp["date"].replace("Z", "+00:00"))
                        athens_dt = utc_dt.astimezone(ZoneInfo("Europe/Athens"))
                        match_date = (athens_dt - timedelta(hours=7)).date()
                        if match_date < start_date or match_date > end_date:
                            continue
                        competitors = comp.get("competitors", [])
                        names = [c.get("athlete", {}).get("displayName", "?") for c in competitors]
                        home_name = names[0] if names else "?"
                        away_name = names[1] if len(names) > 1 else "?"
                        match = {
                            "Διοργάνωση":     tournament_name,
                            "Flag":           flag_code,
                            "League Logo":    tournament_logo,
                            "Ώρα":            athens_dt.strftime("%H:%M"),
                            "Sport":          sport,
                            "Γηπεδούχος":     home_name,
                            "Φιλοξενούμενος": away_name,
                            "1": "—", "X": "-", "2": "—",
                        }
                        matches_by_date.setdefault(match_date, []).append(match)
                continue

            # Regular sport
            utc_dt    = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
            athens_dt = utc_dt.astimezone(ZoneInfo("Europe/Athens"))
            match_date = (athens_dt - timedelta(hours=7)).date()
            if match_date < start_date or match_date > end_date:
                continue
            competitions = event.get("competitions", [])
            if not competitions:
                continue
            competition = competitions[0]
            competitors = competition.get("competitors", [])
            home_list = [c for c in competitors if c.get("homeAway") == "home"]
            away_list = [c for c in competitors if c.get("homeAway") == "away"]
            if not home_list or not away_list:
                continue
            home_team = home_list[0].get("team", {}).get("displayName", "Home")
            away_team = away_list[0].get("team", {}).get("displayName", "Away")
            odds_data = competition.get("odds", [])
            odd_1, odd_X, odd_2 = extract_all_match_odds(odds_data)
            if no_draw:
                odd_X = "-"
            match = {
                "Διοργάνωση":     league_name,
                "Flag":           flag_code,
                "League Logo":    league_logo,
                "Ώρα":            athens_dt.strftime("%H:%M"),
                "Sport":          sport,
                "Γηπεδούχος":     home_team,
                "Φιλοξενούμενος": away_team,
                "1": odd_1, "X": odd_X, "2": odd_2,
            }
            matches_by_date.setdefault(match_date, []).append(match)
        return matches_by_date
    except Exception:
        return {}

@st.cache_data(ttl=300)
def fetch_odds_api_league_range(sport_key, league_name, flag_code, start_date, end_date, api_key):
    if not api_key:
        return {}
    is_hockey   = "icehockey" in sport_key
    league_logo = get_league_logo("oddsapi", sport_key)
    matches_by_date = {}

    # Use /events/ first (fixtures only, cheaper)
    try:
        r = session.get(
            f"{ODDS_API_BASE}/sports/{sport_key}/events/",
            params={"apiKey": api_key, "dateFormat": "iso"},
            timeout=10,
        )
        raw_events = r.json() if r.status_code == 200 else []
    except Exception:
        raw_events = []

    # Fall back to /odds/ if empty
    if not raw_events:
        try:
            r2 = session.get(
                f"{ODDS_API_BASE}/sports/{sport_key}/odds/",
                params={"apiKey": api_key, "regions": "eu", "oddsFormat": "decimal", "dateFormat": "iso"},
                timeout=10,
            )
            raw_events = r2.json() if r2.status_code == 200 else []
        except Exception:
            pass

    for event in raw_events:
        utc_str = event.get("commence_time", "")
        if not utc_str:
            continue
        utc_dt     = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        athens_dt  = utc_dt.astimezone(ZoneInfo("Europe/Athens"))
        match_date = (athens_dt - timedelta(hours=7)).date()
        if match_date < start_date or match_date > end_date:
            continue
        home_team = event.get("home_team", "Home")
        away_team = event.get("away_team", "Away")
        odd_1, odd_X, odd_2 = extract_odds_api_h2h(event, is_hockey=is_hockey)
        match = {
            "Διοργάνωση":     league_name,
            "Flag":           flag_code,
            "League Logo":    league_logo,
            "Sport":          "hockey" if is_hockey else "soccer",
            "Ώρα":            athens_dt.strftime("%H:%M"),
            "Γηπεδούχος":     home_team,
            "Φιλοξενούμενος": away_team,
            "1": odd_1, "X": odd_X, "2": odd_2,
        }
        matches_by_date.setdefault(match_date, []).append(match)
    return matches_by_date

def fetch_all_matches_for_range(all_leagues, start_date, end_date, odds_api_key=""):
    matches_by_date = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for league in all_leagues:
            if league[0] == "espn":
                _, sport, code, name, flag = league[:5]
                extra = league[5] if len(league) > 5 else ""
                futures[executor.submit(fetch_single_league_range, sport, code, name, flag, start_date, end_date, extra)] = "espn"
            elif league[0] == "oddsapi":
                _, sport_key, name, flag = league
                futures[executor.submit(fetch_odds_api_league_range, sport_key, name, flag, start_date, end_date, odds_api_key)] = "oddsapi"
        for future in as_completed(futures):
            res = future.result()
            if isinstance(res, dict):
                for d, matches in res.items():
                    matches_by_date.setdefault(d, []).extend(matches)
    return matches_by_date
