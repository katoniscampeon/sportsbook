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
        .block-container {padding-top: 1rem; padding-bottom: 0rem;}
        h3 {margin-top: 0.5rem;}

        /* Hide ONLY the default Streamlit page navigation links */
        [data-testid="stSidebarNav"] { display: none !important; }

        /* Slightly reduce sidebar spacing */
        [data-testid="stSidebarContent"] {
            padding-top: 1rem !important;
        }
        section[data-testid="stSidebar"] .stButton > button {
            margin-bottom: 2px;
        }

        /* Custom match table */
        .match-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }
        .match-table th {
            text-align: left;
            padding: 4px 8px;
            color: rgba(128,128,128,0.6);
            font-weight: 600;
            font-size: 0.75rem;
            border-bottom: 1px solid rgba(128,128,128,0.2);
        }
        .match-table td {
            padding: 5px 8px;
            border-bottom: 1px solid rgba(128,128,128,0.08);
            vertical-align: middle;
        }
        .match-table tr:hover td {
            background-color: rgba(128,128,128,0.05);
        }
        .match-table img.team-logo {
            width: 36px;
            height: 36px;
            object-fit: contain;
            vertical-align: middle;
        }
        .match-table img.no-logo {
            width: 36px;
            height: 36px;
            display: inline-block;
            opacity: 0;
        }
        .match-table .odds-cell {
            text-align: center;
            font-weight: 600;
            min-width: 42px;
        }
        .match-table .time-cell {
            font-weight: 600;
            white-space: nowrap;
            color: rgba(128,128,128,0.8);
        }
        .match-table .team-cell {
            font-weight: 500;
        }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. ODDS API KEY
# -------------------------------------------------------------
def get_odds_api_key():
    try:
        key = st.secrets.get("odds_api_key", "")
        if key:
            return key
    except Exception:
        pass
    return st.session_state.get("odds_api_key", "")

# -------------------------------------------------------------
# 3. STATE MANAGEMENT
# -------------------------------------------------------------
if "selected_date" not in st.session_state:
    st.session_state.selected_date = effective_today

if "selected_category" not in st.session_state:
    st.session_state.selected_category = "🌐 All"

if "promos" not in st.session_state:
    st.session_state.promos = []

def prev_day():
    st.session_state.selected_date -= timedelta(days=1)

def next_day():
    st.session_state.selected_date += timedelta(days=1)

def go_today():
    st.session_state.selected_date = effective_today

# -------------------------------------------------------------
# 4. PROMO DIALOGS
# -------------------------------------------------------------
@st.dialog("➕ Δημιουργία Promo")
def add_promo_dialog():
    boost_type = st.radio("Τύπος Boost", ["Golden Boost", "Betslip Boost"])
    selection_type = st.radio("Επιλογή", ["🏟️ Συγκεκριμένος Αγώνας", "🏆 Πρωτάθλημα της Ημέρας"])

    promo_date = st.session_state.selected_date
    all_leagues = get_all_leagues_unique()
    odds_api_key = get_odds_api_key()
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
        championship_options = sorted(set(m["Διοργάνωση"] for m in all_day_matches))
        if championship_options:
            selected_championship = st.selectbox(f"Πρωτάθλημα ({promo_date.strftime('%d/%m/%Y')})", championship_options)
        else:
            selected_championship = None
            st.warning(f"Δεν βρέθηκαν πρωταθλήματα για {promo_date.strftime('%d/%m/%Y')}.")
        selected_match = None

    specification = st.text_area("Specification", placeholder="Γράψε τις λεπτομέρειες / σημειώσεις του promo...")

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
# 5. SIDEBAR
# -------------------------------------------------------------
view_col1, view_col2 = st.sidebar.columns(2)
with view_col1:
    if st.button("⚽ Dashboard", key="nav_dash", use_container_width=True, type="primary"):
        pass
with view_col2:
    if st.button("📅 Calendar", key="nav_cal", use_container_width=True, type="secondary"):
        st.switch_page("pages/Calendar_View.py")

st.sidebar.divider()

if st.sidebar.button("🔄 Ανανέωση Δεδομένων", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

if st.sidebar.button("📅 Σήμερα", on_click=go_today, use_container_width=True):
    pass

date_col1, date_col2, date_col3 = st.sidebar.columns([1, 3, 1])
with date_col1:
    st.button("◀", on_click=prev_day, use_container_width=True)
with date_col2:
    st.date_input("Ημερομηνία", key="selected_date", label_visibility="collapsed")
with date_col3:
    st.button("▶", on_click=next_day, use_container_width=True)

st.sidebar.divider()
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

st.sidebar.divider()
if st.sidebar.button("➕ Add Promo", use_container_width=True):
    add_promo_dialog()

# -------------------------------------------------------------
# 6. ODDS API KEY setup
# -------------------------------------------------------------
needs_odds_api = st.session_state.selected_category in (odds_api_categories + ["🌐 All"])
odds_api_key = get_odds_api_key()

if needs_odds_api and not odds_api_key:
    st.sidebar.markdown("")
    st.sidebar.markdown("**🔑 The Odds API**")
    st.sidebar.info(
        "ℹ️ Για αγώνες Φινλανδίας, βάλε το δωρεάν key σου στο:\n"
        "`.streamlit/secrets.toml`\n\n"
        "```\nodds_api_key = \"το_key σου\"\n```\n\n"
        "👉 [the-odds-api.com](https://the-odds-api.com)"
    )

# -------------------------------------------------------------
# 7. LEAGUE FILTERING
# -------------------------------------------------------------
selected_cat = st.session_state.selected_category
if selected_cat == "🌐 All":
    leagues_to_fetch = get_all_leagues_unique()
else:
    leagues_to_fetch = category_mapping[selected_cat]

# -------------------------------------------------------------
# 8. MAIN DISPLAY
# -------------------------------------------------------------
selected_date = st.session_state.selected_date

col_title, col_promos = st.columns([8, 2])
with col_title:
    st.title("⚽ Sportsbook Dashboard")
    st.subheader(f"📅 Αγώνες για {selected_date.strftime('%d/%m/%Y')} — Κατηγορία: {selected_cat}")

with col_promos:
    has_promos = len(st.session_state.promos) > 0
    promo_count = len(st.session_state.promos)
    btn_label = f"👁 Promos ({promo_count})" if has_promos else "👁 Promos"
    btn_color = "#28a745" if has_promos else "#dc3545"

    st.write("")
    st.write("")

    if st.button(btn_label, key="top_view_promos", use_container_width=True, type="primary"):
        view_promos_dialog()

components.html(f"""
<script>
    setTimeout(function() {{
        const buttons = parent.document.querySelectorAll('button');
        for (const btn of buttons) {{
            if (btn.textContent.includes('Promos') && !btn.textContent.includes('Add')) {{
                btn.style.backgroundColor = '{btn_color}';
                btn.style.borderColor = '{btn_color}';
                btn.style.color = 'white';
                btn.addEventListener('click', function() {{
                    this.style.backgroundColor = '{btn_color}';
                    this.style.borderColor = '{btn_color}';
                }});
            }}
        }}
    }}, 100);
</script>
""", height=0)

# -------------------------------------------------------------
# 9. DATA FETCH & DISPLAY (custom HTML table)
# -------------------------------------------------------------
def build_match_table_html(matches):
    """Build an HTML table for matches with proper logo rendering."""
    rows = []
    for m in matches:
        home_logo = m.get("Logo Γηπ.", "")
        away_logo = m.get("Logo Φιλ.", "")
        home_team = m.get("Γηπεδούχος", "")
        away_team = m.get("Φιλοξενούμενος", "")
        match_time = m.get("Ώρα", "")
        odd_1 = m.get("1", "N/A")
        odd_X = m.get("X", "N/A")
        odd_2 = m.get("2", "N/A")

        home_logo_html = f'<img class="team-logo" src="{home_logo}" onerror="this.style.visibility=\'hidden\'">' if home_logo else '<span class="no-logo"></span>'
        away_logo_html = f'<img class="team-logo" src="{away_logo}" onerror="this.style.visibility=\'hidden\'">' if away_logo else '<span class="no-logo"></span>'

        row = f"""
        <tr>
            <td class="time-cell">{match_time}</td>
            <td>{home_logo_html}</td>
            <td class="team-cell">{home_team}</td>
            <td class="odds-cell">{odd_1}</td>
            <td class="odds-cell">{odd_X}</td>
            <td class="odds-cell">{odd_2}</td>
            <td class="team-cell">{away_team}</td>
            <td>{away_logo_html}</td>
        </tr>
        """
        rows.append(row)

    table = f"""
    <table class="match-table">
        <thead>
            <tr>
                <th>Ώρα</th>
                <th></th>
                <th>Γηπεδούχος</th>
                <th>1</th>
                <th>X</th>
                <th>2</th>
                <th>Φιλοξενούμενος</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
    """
    return table


with st.spinner("Φόρτωση αγώνων..."):
    all_matches, odds_api_error = fetch_all_matches_parallel(leagues_to_fetch, selected_date, odds_api_key)

if odds_api_error == "invalid_key":
    st.error("❌ Το Odds API key δεν είναι έγκυρο. Έλεγξε το `.streamlit/secrets.toml`.")
elif odds_api_error == "rate_limit":
    st.warning("⚠️ Όριο κλήσεων Odds API συμπληρώθηκε.")

if all_matches:
    df_all = pd.DataFrame(all_matches)

    for league_name, group in df_all.groupby("Διοργάνωση", sort=False):
        league_logo = group["League Logo"].iloc[0] if "League Logo" in group.columns else ""
        flag_code = group["Flag"].iloc[0] if "Flag" in group.columns else ""

        if league_logo:
            st.markdown(
                f"#### <img src='{league_logo}' style='vertical-align: middle; margin-right: 8px;' width='48' height='48' onerror=\"this.style.display='none'\"> {league_name}",
                unsafe_allow_html=True
            )
        elif flag_code:
            flag_url = f"https://flagcdn.com/24x18/{flag_code}.png"
            st.markdown(
                f"#### <img src='{flag_url}' style='vertical-align: middle; margin-right: 8px;' width='24'> {league_name}",
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"#### {league_name}")

        # Custom HTML table instead of st.dataframe
        table_html = build_match_table_html(group.to_dict('records'))
        st.markdown(table_html, unsafe_allow_html=True)
        st.divider()
else:
    st.info(f"Δεν υπάρχουν προγραμματισμένοι αγώνες για την κατηγορία '{selected_cat}' στις {selected_date.strftime('%d/%m/%Y')}.")
