import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------------------------------------------------------------
# 1. PAGE CONFIGURATION & STYLING
# -------------------------------------------------------------
st.set_page_config(page_title="Sportsbook Dashboard", page_icon="⚽", layout="wide")

st.markdown("""
    <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 0rem;}
        h3 {margin-top: 0.5rem;}
        
        section[data-testid="stSidebar"] div.stButton {
            margin-bottom: -10px;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div {
            gap: 0.3rem !important;
        }
        div[data-testid="stHorizontalBlock"] {
            align-items: center;
        }
    </style>
""", unsafe_allow_html=True)

# Reusable HTTP session
session = requests.Session()

# -------------------------------------------------------------
# 2. HELPER FUNCTIONS: ODDS PARSER
# -------------------------------------------------------------
def parse_odd_value(raw):
    """Converts American or raw float odds to standard Decimal format string."""
    if raw is None or raw == "":
        return None
    try:
        # If it's a string starting with + or -, it's definitively American odds
        if isinstance(raw, str) and (raw.startswith("+") or raw.startswith("-")):
            val = float(raw)
            if val > 0:
                return f"{(val / 100.0) + 1.0:.2f}"
            elif val < 0:
                return f"{(100.0 / abs(val)) + 1.0:.2f}"

        val = float(raw)
        if val == 0:
            return None
        # Decimal Odds (e.g. 1.85, 3.40)
        if 1.0 < val < 50.0:
            return f"{val:.2f}"
        # American Positive Odds (e.g. 150 -> 2.50)
        elif val > 0:
            return f"{(val / 100.0) + 1.0:.2f}"
        # American Negative Odds (e.g. -150 -> 1.67)
        elif val < 0:
            return f"{(100.0 / abs(val)) + 1.0:.2f}"
    except (ValueError, TypeError):
        pass
    return None

def search_team_odd_in_dict(d):
    """Recursively checks common ESPN odds keys within a dictionary structure."""
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
    """Iterates through provider odds data to extract Home (1), Draw (X), and Away (2) odds.
    
    ESPN API structure:
      - Home: odds[i]["moneyline"]["home"]["close"]["odds"]  (string, American format)
      - Away: odds[i]["moneyline"]["away"]["close"]["odds"]  (string, American format)
      - Draw: odds[i]["drawOdds"]["moneyLine"]                (number, American format)
    """
    home_odd = "N/A"
    draw_odd = "N/A"
    away_odd = "N/A"

    if not odds_data or not isinstance(odds_data, list):
        return home_odd, draw_odd, away_odd

    for provider in odds_data:
        if not isinstance(provider, dict):
            continue

        # --- Home odds: provider["moneyline"]["home"]["close"]["odds"] ---
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

        # --- Away odds: provider["moneyline"]["away"]["close"]["odds"] ---
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

        # --- Draw odds: provider["drawOdds"]["moneyLine"] ---
        if draw_odd == "N/A":
            draw_info = provider.get("drawOdds")
            if isinstance(draw_info, dict):
                res = parse_odd_value(draw_info.get("moneyLine"))
                if res:
                    draw_odd = res

        # --- Fallback: try legacy key structures for backwards compatibility ---
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
# 2b. THE ODDS API FETCHER (for leagues ESPN doesn't cover)
# -------------------------------------------------------------
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

def extract_odds_api_h2h(event, is_hockey=False):
    """Extract H2H (1X2) odds from The Odds API event response."""
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

@st.cache_data(ttl=300)
def fetch_odds_api_league(sport_key, league_name, flag_code, target_date, api_key):
    """Fetch matches from The Odds API for a given sport key."""
    if not api_key:
        return []

    url = f"{ODDS_API_BASE}/sports/{sport_key}/odds/"
    params = {
        "apiKey": api_key,
        "regions": "eu",
        "oddsFormat": "decimal",
        "dateFormat": "iso"
    }

    try:
        response = session.get(url, params=params, timeout=10)
        if response.status_code == 422:
            return []  # Sport not in season
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

# -------------------------------------------------------------
# 3. STATE MANAGEMENT (Athens Time)
# -------------------------------------------------------------
athens_tz = ZoneInfo("Europe/Athens")
now_athens = datetime.now(athens_tz)

# Effective date calculation with 07:00 AM cutoff
effective_today = (now_athens - timedelta(hours=7)).date()

if "selected_date" not in st.session_state:
    st.session_state.selected_date = effective_today

if "selected_category" not in st.session_state:
    st.session_state.selected_category = "⭐ Top Leagues"

if "promos" not in st.session_state:
    st.session_state.promos = []

def prev_day():
    st.session_state.selected_date -= timedelta(days=1)

def next_day():
    st.session_state.selected_date += timedelta(days=1)

def go_today():
    st.session_state.selected_date = effective_today

# -------------------------------------------------------------
# 4. CATEGORY & LEAGUE MAPPINGS
# -------------------------------------------------------------
# League tuple format: (source, code, name, flag)
#   source="espn"     -> code is ESPN league slug (e.g. "eng.1")
#   source="oddsapi"  -> code is The Odds API sport key (e.g. "soccer_finland_veikkausliiga")

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

# Leagues that use The Odds API (need API key)
odds_api_categories = ["Finland"]

# -------------------------------------------------------------
# 5. DATA FETCHING (PARALLELIZED)
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

def fetch_all_matches_parallel(leagues, target_date, odds_api_key=""):
    """Fetch matches from multiple leagues in parallel.
    
    League tuples can be ESPN format (5 elements starting with "espn")
    or Odds API format (4 elements starting with "oddsapi").
    """
    all_matches = []
    has_odds_api_error = None

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}

        for league in leagues:
            if league[0] == "espn":
                # ESPN format: ("espn", sport, code, name, flag)
                _, sport, code, name, flag = league
                futures[executor.submit(fetch_single_league, sport, code, name, flag, target_date)] = "espn"
            elif league[0] == "oddsapi":
                # Odds API format: ("oddsapi", sport_key, name, flag)
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
# 6. PROMO DIALOGS (ADD / VIEW)
# -------------------------------------------------------------
@st.dialog("➕ Δημιουργία Promo")
def add_promo_dialog():
    boost_type = st.radio("Τύπος Boost", ["Golden Boost", "Betslip Boost"])

    # Selection type: specific event or championship of the day
    selection_type = st.radio("Επιλογή", ["🏟️ Συγκεκριμένος Αγώνας", "🏆 Πρωτάθλημα της Ημέρας"])

    # Fetch matches for the currently selected day (Top Leagues)
    promo_date = st.session_state.selected_date
    espn_top_leagues = [
        ("espn", sport, code, name, flag)
        for (espn, sport, code, name, flag) in category_mapping["⭐ Top Leagues"]
    ]
    top_matches, _ = fetch_all_matches_parallel(espn_top_leagues, promo_date)

    if selection_type == "🏟️ Συγκεκριμένος Αγώνας":
        match_options = [
            f"{m['Γηπεδούχος']} vs {m['Φιλοξενούμενος']} ({m['Ώρα']}) — {m['Διοργάνωση']}"
            for m in top_matches
        ]
        if match_options:
            selected_match = st.selectbox(f"Αγώνας (Top Leagues — {promo_date.strftime('%d/%m/%Y')})", match_options)
        else:
            selected_match = None
            st.warning(f"Δεν βρέθηκαν αγώνες Top Leagues για {promo_date.strftime('%d/%m/%Y')}.")
        selected_championship = None
    else:
        # Championship of the day: list unique leagues from the fetched matches
        championship_options = sorted(set(m["Διοργάνωση"] for m in top_matches))
        if championship_options:
            selected_championship = st.selectbox(f"Πρωτάθλημα ({promo_date.strftime('%d/%m/%Y')})", championship_options)
        else:
            selected_championship = None
            st.warning(f"Δεν βρέθηκαν πρωταθλήματα για {promo_date.strftime('%d/%m/%Y')}.")
        selected_match = None

    specification = st.text_area(
        "Specification",
        placeholder="Γράψε τις λεπτομέρειες / σημειώσεις του promo..."
    )

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("💾 Αποθήκευση", use_container_width=True, type="primary"):
            st.session_state.promos.append({
                "type": boost_type,
                "match": selected_match,
                "championship": selected_championship,
                "notes": specification,
                "created": datetime.now(athens_tz).strftime("%d/%m/%Y %H:%M")
            })
            st.rerun()
    with col_cancel:
        if st.button("❌ Ακύρωση", use_container_width=True):
            st.rerun()

@st.dialog("👁 Promos")
def view_promos_dialog():
    if not st.session_state.promos:
        st.info("Δεν υπάρχουν αποθηκευμένα promos.")
    else:
        for idx, promo in enumerate(st.session_state.promos):
            st.markdown(f"**{promo['type']}** &nbsp;·&nbsp; _{promo['created']}_")
            if promo.get("match"):
                st.markdown(f"🏟️ {promo['match']}")
            if promo.get("championship"):
                st.markdown(f"🏆 {promo['championship']}")
            if promo.get("notes"):
                st.markdown(f"📝 {promo['notes']}")
            if st.button("🗑️ Διαγραφή", key=f"del_promo_{idx}", use_container_width=True):
                st.session_state.promos.pop(idx)
                st.rerun()
            st.divider()


# -------------------------------------------------------------
# 7. SIDEBAR CONTROLS
# -------------------------------------------------------------
if st.sidebar.button("🔄 Ανανέωση Δεδομένων", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

# Today button on top of day navigation
if st.sidebar.button("📅 Σήμερα", on_click=go_today, use_container_width=True):
    pass

date_col1, date_col2, date_col3 = st.sidebar.columns([1, 3, 1])

with date_col1:
    st.button("◀", on_click=prev_day, use_container_width=True)

with date_col2:
    st.date_input(
        "Ημερομηνία",
        key="selected_date",
        label_visibility="collapsed"
    )

with date_col3:
    st.button("▶", on_click=next_day, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**🏆 Κατηγορίες**")

for cat in categories_info:
    cat_id = cat["id"]
    is_selected = (st.session_state.selected_category == cat_id)
    btn_type = "primary" if is_selected else "secondary"

    if cat.get("flag"):
        c_flag, c_btn = st.sidebar.columns([1, 5])
        with c_flag:
            flag_url = f"https://flagcdn.com/24x18/{cat['flag']}.png"
            st.image(flag_url, width=22)
        with c_btn:
            if st.button(cat["label"], key=f"side_btn_{cat_id}", use_container_width=True, type=btn_type):
                st.session_state.selected_category = cat_id
                st.rerun()
    else:
        if st.sidebar.button(f"{cat_id}", key=f"side_btn_{cat_id}", use_container_width=True, type=btn_type):
            st.session_state.selected_category = cat_id
            st.rerun()

# Promo button in sidebar
st.sidebar.markdown("---")

if st.sidebar.button("➕ Add Promo", use_container_width=True):
    add_promo_dialog()

# -------------------------------------------------------------
# 8. THE ODDS API KEY INPUT
# -------------------------------------------------------------
# Show API key input if Finland category is selected or in All
needs_odds_api = st.session_state.selected_category in (odds_api_categories + ["🌐 All"])

if needs_odds_api:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🔑 The Odds API**")
    odds_api_key = st.sidebar.text_input(
        "API Key (για Finland)",
        value=st.session_state.get("odds_api_key", ""),
        type="password",
        key="odds_api_key",
        help="Δωρεάν κλειδί από https://the-odds-api.com"
    )
    if not odds_api_key:
        st.sidebar.info("ℹ️ Πάρε δωρεάν κλειδί από [the-odds-api.com](https://the-odds-api.com) για αγώνες Φινλανδίας.")

# -------------------------------------------------------------
# 9. LEAGUE FILTERING LOGIC
# -------------------------------------------------------------
selected_cat = st.session_state.selected_category

if selected_cat == "🌐 All":
    leagues_to_fetch = []
    seen_codes = set()
    excluded_categories = ["Filler Leagues"]

    for cat_name, leagues in category_mapping.items():
        if cat_name not in excluded_categories:
            for league in leagues:
                # Use the full tuple as identifier
                if league[0] == "espn":
                    identifier = ("espn", league[2])  # (source, espn_code)
                else:
                    identifier = ("oddsapi", league[1])  # (source, odds_api_key)
                if identifier not in seen_codes:
                    leagues_to_fetch.append(league)
                    seen_codes.add(identifier)
else:
    leagues_to_fetch = category_mapping[selected_cat]

# -------------------------------------------------------------
# 10. MAIN DISPLAY
# -------------------------------------------------------------
selected_date = st.session_state.selected_date

# Top row: title on the left, View Promos button on the right
col_title, col_promos = st.columns([8, 2])

with col_title:
    st.title("⚽ Sportsbook Dashboard")
    st.subheader(f"📅 Αγώνες για {selected_date.strftime('%d/%m/%Y')} — Κατηγορία: {selected_cat}")

with col_promos:
    has_promos = len(st.session_state.promos) > 0
    promo_count = len(st.session_state.promos)
    btn_label = f"👁 Promos ({promo_count})" if has_promos else "👁 Promos"
    btn_color = "#28a745" if has_promos else "#dc3545"

    # Spacer to align with title vertically
    st.write("")
    st.write("")

    if st.button(btn_label, key="top_view_promos", use_container_width=True, type="primary"):
        view_promos_dialog()

# Inject JS to color the View Promos button green/red based on state
components.html(f"""
<script>
    setTimeout(function() {{
        const buttons = parent.document.querySelectorAll('button');
        for (const btn of buttons) {{
            if (btn.textContent.includes('Promos') && !btn.textContent.includes('Add')) {{
                btn.style.backgroundColor = '{btn_color}';
                btn.style.borderColor = '{btn_color}';
                btn.style.color = 'white';
                btn.addEventListener('mouseenter', function() {{
                    btn.style.opacity = '0.85';
                }});
                btn.addEventListener('mouseleave', function() {{
                    btn.style.opacity = '1';
                }});
            }}
        }}
    }}, 200);
</script>
""", height=0)

# Get Odds API key from session state
odds_api_key = st.session_state.get("odds_api_key", "")

# Check if we need the API key but don't have it
if needs_odds_api and not odds_api_key:
    st.warning("⚠️ Η κατηγορία Finland χρειάζεται δωρεάν API key από [The Odds API](https://the-odds-api.com). Βάλε το στο sidebar (αριστερά).")
    # Still show ESPN leagues if in "All" category
    if selected_cat == "🌐 All":
        espn_only = [l for l in leagues_to_fetch if l[0] == "espn"]
        with st.spinner("Φόρτωση αγώνων (χωρίς Finland)..."):
            all_matches, _ = fetch_all_matches_parallel(espn_only, selected_date)
    else:
        all_matches = []
else:
    with st.spinner("Φόρτωση αγώνων..."):
        all_matches, odds_error = fetch_all_matches_parallel(leagues_to_fetch, selected_date, odds_api_key)

        if odds_error == "invalid_key":
            st.error("❌ Το API key δεν είναι έγκυρο. Έλεγξε το κλειδί από το the-odds-api.com.")
        elif odds_error == "rate_limit":
            st.warning("⚠️ Έχεις ξεπεράσει το όριο requests (500/μήνα). Δοκίμασε αύριο.")

if all_matches:
    df_all = pd.DataFrame(all_matches)

    for league_name, group in df_all.groupby("Διοργάνωση", sort=False):
        flag_code = group["Flag"].iloc[0]
        flag_url = f"https://flagcdn.com/24x18/{flag_code}.png"

        st.markdown(
            f"#### <img src='{flag_url}' style='vertical-align: middle; margin-right: 8px;' width='24'> {league_name}",
            unsafe_allow_html=True
        )

        display_group = group.drop(columns=["Διοργάνωση", "Flag"])

        st.dataframe(
            display_group,
            column_config={
                "Logo Γηπ.": st.column_config.ImageColumn("", width="small"),
                "Logo Φιλ.": st.column_config.ImageColumn("", width="small"),
                "1": st.column_config.TextColumn("1", width="small"),
                "X": st.column_config.TextColumn("X", width="small"),
                "2": st.column_config.TextColumn("2", width="small")
            },
            use_container_width=True,
            hide_index=True
        )
        st.divider()
elif not (needs_odds_api and not odds_api_key):
    st.info(f"Δεν υπάρχουν προγραμματισμένοι αγώνες για την κατηγορία '{selected_cat}' στις {selected_date.strftime('%d/%m/%Y')}.")
