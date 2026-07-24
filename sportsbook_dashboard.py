import streamlit as st
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
categories_info = [
    {"id": "⭐ Top Leagues", "label": "Top Leagues", "flag": None},
    {"id": "🌐 All", "label": "All", "flag": None},
    {"id": "Germany", "label": "Germany", "flag": "de"},
    {"id": "Norway", "label": "Norway", "flag": "no"},
    {"id": "Finland", "label": "Finland", "flag": "fi"},
    {"id": "Sweden", "label": "Sweden", "flag": "se"},
    {"id": "Filler Leagues", "label": "Filler Leagues", "flag": "un"}
]

category_mapping = {
    "⭐ Top Leagues": [
        ("soccer", "eng.1", "Premier League", "gb-eng"),
        ("soccer", "esp.1", "La Liga", "es"),
        ("soccer", "ger.1", "Bundesliga", "de"),
        ("soccer", "ita.1", "Serie A", "it"),
        ("soccer", "uefa.champions", "UEFA Champions League", "eu"),
        ("soccer", "uefa.europa", "UEFA Europa League", "eu"),
        ("soccer", "uefa.europa.conf", "UEFA Conference League", "eu"),
        ("basketball", "usa.nba", "NBA", "us")
    ],
    "Germany": [
        ("soccer", "ger.1", "Germany - Bundesliga", "de"),
        ("soccer", "ger.2", "Germany - 2. Bundesliga", "de"),
        ("soccer", "aut.1", "Austria - Bundesliga", "at"),
        ("soccer", "tur.1", "Turkey - Süper Lig", "tr")
    ],
    "Norway": [
        ("soccer", "nor.1", "Norway - Eliteserien", "no")
    ],
    "Finland": [
        ("soccer", "fin.1", "Finland - Veikkausliiga", "fi"),
        ("hockey", "usa.nhl", "NHL", "us"),
        ("hockey", "liiga", "Finland - Liiga", "fi")
    ],
    "Sweden": [
        ("soccer", "swe.1", "Sweden - Allsvenskan", "se")
    ],
    "Filler Leagues": [
        ("soccer", "bra.1", "Brazil - Série A", "br"),
        ("soccer", "arg.1", "Argentina - Liga Profesional", "ar"),
        ("soccer", "jpn.1", "Japan - J1 League", "jp")
    ]
}

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
                no_draw_leagues = ["usa.nba", "usa.nhl", "liiga"]
                
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

def fetch_all_matches_parallel(leagues, target_date):
    all_matches = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(fetch_single_league, sport, code, name, flag, target_date)
            for sport, code, name, flag in leagues
        ]
        for future in as_completed(futures):
            res = future.result()
            if res:
                all_matches.extend(res)
    return all_matches

# -------------------------------------------------------------
# 6. PROMO DIALOGS (ADD / VIEW)
# -------------------------------------------------------------
@st.dialog("➕ Δημιουργία Promo")
def add_promo_dialog():
    boost_type = st.radio("Τύπος Boost", ["Golden Boost", "Betslip Boost"])

    # Fetch matches for the currently selected day (Top Leagues)
    promo_date = st.session_state.selected_date
    top_matches = fetch_all_matches_parallel(category_mapping["⭐ Top Leagues"], promo_date)
    match_options = [
        f"{m['Γηπεδούχος']} vs {m['Φιλοξενούμενος']} ({m['Ώρα']}) — {m['Διοργάνωση']}"
        for m in top_matches
    ]

    if match_options:
        selected_match = st.selectbox(f"Επιλογή Αγώνα (Top Leagues — {promo_date.strftime('%d/%m/%Y')})", match_options)
    else:
        selected_match = None
        st.warning(f"Δεν βρέθηκαν αγώνες Top Leagues για {promo_date.strftime('%d/%m/%Y')}.")

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

# Promo buttons moved to bottom
st.sidebar.markdown("---")

if st.sidebar.button("➕ Add Promo", use_container_width=True):
    add_promo_dialog()

if st.sidebar.button("👁 View Promo", use_container_width=True):
    view_promos_dialog()

# -------------------------------------------------------------
# 8. LEAGUE FILTERING LOGIC
# -------------------------------------------------------------
selected_cat = st.session_state.selected_category

if selected_cat == "🌐 All":
    leagues_to_fetch = []
    seen_codes = set()
    excluded_categories = ["Filler Leagues"]
    
    for cat_name, leagues in category_mapping.items():
        if cat_name not in excluded_categories:
            for sport, code, name, flag in leagues:
                if (sport, code) not in seen_codes:
                    leagues_to_fetch.append((sport, code, name, flag))
                    seen_codes.add((sport, code))
else:
    leagues_to_fetch = category_mapping[selected_cat]

# -------------------------------------------------------------
# 9. MAIN DISPLAY
# -------------------------------------------------------------
selected_date = st.session_state.selected_date

st.title("⚽ Sportsbook Dashboard")
st.subheader(f"📅 Αγώνες για {selected_date.strftime('%d/%m/%Y')} — Κατηγορία: {selected_cat}")

with st.spinner("Φόρτωση αγώνων..."):
    all_matches = fetch_all_matches_parallel(leagues_to_fetch, selected_date)

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
else:
    st.info(f"Δεν υπάρχουν προγραμματισμένοι αγώνες για την κατηγορία '{selected_cat}' στις {selected_date.strftime('%d/%m/%Y')}.")
