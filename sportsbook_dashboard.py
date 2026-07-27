import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, date, timedelta
from shared import (
    session, athens_tz, now_athens, effective_today, ODDS_API_BASE,
    categories_info, category_mapping, odds_api_categories,
    get_all_leagues_unique,
    parse_odd_value, search_team_odd_in_dict, extract_all_match_odds,
    extract_odds_api_h2h,
    fetch_single_league, fetch_odds_api_league, fetch_all_matches_parallel
)

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

# -------------------------------------------------------------
# 2. STATE MANAGEMENT
# -------------------------------------------------------------
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
# 3. PROMO DIALOGS (ADD / VIEW)
# -------------------------------------------------------------
@st.dialog("➕ Δημιουργία Promo")
def add_promo_dialog():
    boost_type = st.radio("Τύπος Boost", ["Golden Boost", "Betslip Boost"])

    # Selection type: specific event or championship of the day
    selection_type = st.radio("Επιλογή", ["🏟️ Συγκεκριμένος Αγώνας", "🏆 Πρωτάθλημα της Ημέρας"])

    # Fetch matches for the currently selected day from ALL leagues in the app
    promo_date = st.session_state.selected_date
    all_leagues = get_all_leagues_unique()

    odds_api_key = st.session_state.get("odds_api_key", "")
    all_day_matches, _ = fetch_all_matches_parallel(all_leagues, promo_date, odds_api_key)

    if selection_type == "🏟️ Συγκεκριμένος Αγώνας":
        match_options = [
            f"{m['Γηπεδούχος']} vs {m['Φιλοξενούμενος']} ({m['Ώρα']}) — {m['Διοργάνωση']}"
            for m in all_day_matches
        ]
        if match_options:
            selected_match = st.selectbox(f"Αγώνας ({promo_date.strftime('%d/%m/%Y')})", match_options)
        else:
            selected_match = None
            st.warning(f"Δεν βρέθηκαν αγώνες για {promo_date.strftime('%d/%m/%Y')}.")
        selected_championship = None
    else:
        # Championship of the day: list unique leagues from the fetched matches
        championship_options = sorted(set(m["Διοργάνωση"] for m in all_day_matches))
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
                "promo_date": promo_date.strftime("%d/%m/%Y"),
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
# 4. SIDEBAR CONTROLS
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
# 5. THE ODDS API KEY INPUT
# -------------------------------------------------------------
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
# 6. LEAGUE FILTERING LOGIC
# -------------------------------------------------------------
selected_cat = st.session_state.selected_category

if selected_cat == "🌐 All":
    leagues_to_fetch = []
    seen_codes = set()
    excluded_categories = ["Filler Leagues"]

    for cat_name, leagues in category_mapping.items():
        if cat_name not in excluded_categories:
            for league in leagues:
                if league[0] == "espn":
                    identifier = ("espn", league[2])
                else:
                    identifier = ("oddsapi", league[1])
                if identifier not in seen_codes:
                    leagues_to_fetch.append(league)
                    seen_codes.add(identifier)
else:
    leagues_to_fetch = category_mapping[selected_cat]

# -------------------------------------------------------------
# 7. MAIN DISPLAY
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
