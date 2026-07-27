import streamlit as st
import pandas as pd
import sys
import traceback
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

# Setup logging
def log_error(msg):
    print(f"[ERROR] {msg}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)

try:
    # Import shared module
    from shared import (
        athens_tz, effective_today, 
        categories_info, category_mapping, odds_api_categories,
        get_all_leagues_unique,
        fetch_all_matches_parallel
    )
except Exception as e:
    log_error(f"Failed to import shared: {str(e)}")
    st.error(f"❌ Failed to import shared module: {str(e)}")
    st.stop()

try:
    # Import promo store
    from promo_store import load_promos, add_promo, delete_promo, dates_in_range
except Exception as e:
    log_error(f"Failed to import promo_store: {str(e)}")
    st.error(f"❌ Failed to import promo_store module: {str(e)}")
    st.stop()

# Page config
st.set_page_config(page_title="Sportsbook Dashboard", page_icon="⚽", layout="wide")

st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 0rem;}
        h3 {margin-top: 0.5rem;}
        [data-testid="stSidebarNav"] { display: none !important; }
        [data-testid="stSidebarContent"] { padding-top: 1rem !important; }
        section[data-testid="stSidebar"] .stButton > button { margin-bottom: 2px; }
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

# Get odds API key
def get_odds_api_key():
    try:
        key = st.secrets.get("odds_api_key", "")
        if key:
            return key
    except Exception:
        pass
    return st.session_state.get("odds_api_key", "")

# Initialize session state
if "selected_date" not in st.session_state:
    st.session_state.selected_date = effective_today

if "selected_category" not in st.session_state:
    st.session_state.selected_category = "🌐 All"

st.session_state.promos = load_promos()

# Navigation callbacks
def prev_day():
    st.session_state.selected_date -= timedelta(days=1)

def next_day():
    st.session_state.selected_date += timedelta(days=1)

def go_today():
    st.session_state.selected_date = effective_today

# Promo form
BOOST_TYPES = ["Golden Boost", "Betslip Boost", "Other"]

def _render_promo_form(default_date: date):
    """Render the promo form fields."""
    try:
        boost_type_choice = st.radio("Τύπος Boost", BOOST_TYPES, horizontal=True)
        if boost_type_choice == "Other":
            custom_type = st.text_input("Προσαρμοσμένος τύπος", placeholder="π.χ. Super Odds")
            boost_label = custom_type.strip() if custom_type.strip() else "Other"
        else:
            boost_label = boost_type_choice

        st.divider()

        date_mode = st.radio("Επιλογή ημερομηνίας", ["Μία ημέρα", "Εύρος ημερομηνιών"], horizontal=True)
        if date_mode == "Μία ημέρα":
            chosen_date = st.date_input("Ημερομηνία", value=default_date)
            promo_dates = [chosen_date.strftime("%d/%m/%Y")]
        else:
            col_s, col_e = st.columns(2)
            with col_s:
                range_start = st.date_input("Από", value=default_date)
            with col_e:
                range_end = st.date_input("Έως", value=default_date + timedelta(days=6))
            if range_end < range_start:
                st.warning("Η ημερομηνία 'Έως' πρέπει να είναι μετά την 'Από'.")
                promo_dates = [range_start.strftime("%d/%m/%Y")]
            else:
                promo_dates = dates_in_range(range_start, range_end)

        st.divider()

        selection_type = st.radio(
            "Επιλογή",
            ["🏟️ Συγκεκριμένος Αγώνας", "🏆 Πρωτάθλημα", "📝 Άλλο"],
            horizontal=True
        )

        selected_match = None
        selected_championship = None
        other_label = None

        if selection_type == "🏟️ Συγκεκριμένος Αγώνας":
            try:
                ref_date = date.fromisoformat(promo_dates[0].split("/")[-1] + "-" +
                                               promo_dates[0].split("/")[1] + "-" +
                                               promo_dates[0].split("/")[0])
                all_leagues = get_all_leagues_unique()
                odds_api_key = get_odds_api_key()
                all_day_matches, _ = fetch_all_matches_parallel(all_leagues, ref_date, odds_api_key)
                match_options = [
                    f"{m['Γηπεδούχος']} vs {m['Φιλοξενούμενος']} ({m['Ώρα']}) — {m['Διοργάνωση']}"
                    for m in all_day_matches
                ]
                if match_options:
                    selected_match = st.selectbox(f"Αγώνας ({ref_date.strftime('%d/%m/%Y')})", match_options)
                else:
                    st.warning(f"Δεν βρέθηκαν αγώνες για {ref_date.strftime('%d/%m/%Y')}.")
            except Exception as e:
                st.warning(f"Σφάλμα: {str(e)}")

        elif selection_type == "🏆 Πρωτάθλημα":
            try:
                ref_date = date.fromisoformat(promo_dates[0].split("/")[-1] + "-" +
                                               promo_dates[0].split("/")[1] + "-" +
                                               promo_dates[0].split("/")[0])
                all_leagues = get_all_leagues_unique()
                odds_api_key = get_odds_api_key()
                all_day_matches, _ = fetch_all_matches_parallel(all_leagues, ref_date, odds_api_key)
                championship_options = sorted(set(m["Διοργάνωση"] for m in all_day_matches))
                if championship_options:
                    selected_championship = st.selectbox(f"Πρωτάθλημα ({ref_date.strftime('%d/%m/%Y')})", championship_options)
                else:
                    st.warning(f"Δεν βρέθηκαν πρωταθλήματα για {ref_date.strftime('%d/%m/%Y')}.")
            except Exception as e:
                st.warning(f"Σφάλμα: {str(e)}")

        else:
            other_label = st.text_input("Περιγραφή", placeholder="π.χ. Super Sunday Special")

        specification = st.text_area("Σημειώσεις", placeholder="Γράψε τις λεπτομέρειες του promo...")

        return {
            "type": boost_label,
            "match": selected_match,
            "championship": selected_championship,
            "other": other_label,
            "notes": specification,
            "promo_dates": promo_dates,
            "promo_date": promo_dates[0] if promo_dates else "",
            "created": datetime.now(athens_tz).strftime("%d/%m/%Y %H:%M")
        }
    except Exception as e:
        st.error(f"Σφάλμα στη φόρμα: {str(e)}")
        return None

# Promo dialogs
@st.dialog("➕ Δημιουργία Promo")
def add_promo_dialog():
    try:
        promo = _render_promo_form(default_date=st.session_state.selected_date)
        if promo:
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("💾 Αποθήκευση", use_container_width=True, type="primary"):
                    try:
                        updated = add_promo(promo)
                        st.session_state.promos = updated
                        st.rerun()
                    except Exception as e:
                        st.error(f"Σφάλμα αποθήκευσης: {str(e)}")
            with col_cancel:
                if st.button("❌ Ακύρωση", use_container_width=True):
                    st.rerun()
    except Exception as e:
        st.error(f"Σφάλμα διαλόγου: {str(e)}")

@st.dialog("👁 Promos")
def view_promos_dialog():
    try:
        promos = load_promos()
        if not promos:
            st.info("Δεν υπάρχουν αποθηκευμένα promos.")
        else:
            for idx, promo in enumerate(promos):
                st.markdown(f"**{promo['type']}** — _{promo.get('created', '')}_")
                if promo.get("match"):
                    st.markdown(f"🏟️ {promo['match']}")
                if promo.get("championship"):
                    st.markdown(f"🏆 {promo['championship']}")
                if promo.get("other"):
                    st.markdown(f"📝 {promo['other']}")
                if promo.get("notes"):
                    st.markdown(f"📝 {promo['notes']}")
                if st.button("🗑️ Διαγραφή", key=f"del_promo_{idx}", use_container_width=True):
                    updated = delete_promo(idx)
                    st.session_state.promos = updated
                    st.rerun()
                st.divider()
    except Exception as e:
        st.error(f"Σφάλμα προβολής: {str(e)}")

# SIDEBAR
try:
    view_col1, view_col2 = st.sidebar.columns(2)
    with view_col1:
        if st.button("⚽ Dashboard", key="nav_dash", use_container_width=True, type="primary"):
            pass
    with view_col2:
        if st.button("📅 Calendar", key="nav_cal", use_container_width=True, type="secondary"):
            try:
                st.switch_page("pages/Calendar_View.py")
            except Exception as e:
                st.warning("Calendar View not available yet")

    st.sidebar.divider()

    if st.sidebar.button("🔄 Ανανέωση Δεδομένων", use_container_width=True):
        try:
            from shared import (
                _single_cache, _oddsapi_cache, _range_cache, _oddsapi_range_cache,
                _single_cache_lock, _oddsapi_cache_lock, _range_cache_lock, _oddsapi_range_cache_lock
            )
            for cache, lock in [
                (_single_cache, _single_cache_lock),
                (_oddsapi_cache, _oddsapi_cache_lock),
                (_range_cache, _range_cache_lock),
                (_oddsapi_range_cache, _oddsapi_range_cache_lock),
            ]:
                with lock:
                    cache.clear()
            st.rerun()
        except Exception as e:
            st.warning(f"Refresh error: {str(e)}")

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

except Exception as e:
    log_error(f"Sidebar error: {str(e)}")
    st.sidebar.error(f"Sidebar error: {str(e)}")

# MAIN CONTENT
try:
    selected_cat = st.session_state.selected_category
    if selected_cat == "🌐 All":
        leagues_to_fetch = get_all_leagues_unique()
    else:
        leagues_to_fetch = category_mapping.get(selected_cat, [])

    selected_date = st.session_state.selected_date

    col_title, col_promos = st.columns([8, 2])
    with col_title:
        st.title("⚽ Sportsbook Dashboard")
        st.subheader(f"📅 Αγώνες για {selected_date.strftime('%d/%m/%Y')} — Κατηγορία: {selected_cat}")

    with col_promos:
        has_promos = len(st.session_state.promos) > 0
        promo_count = len(st.session_state.promos)
        btn_label = f"👁 Promos ({promo_count})" if has_promos else "👁 Promos"
        st.write("")
        st.write("")
        if st.button(btn_label, key="top_view_promos", use_container_width=True, type="primary"):
            view_promos_dialog()

    # Fetch data
    with st.spinner("Φόρτωση αγώνων..."):
        odds_api_key = get_odds_api_key()
        all_matches, odds_api_error = fetch_all_matches_parallel(leagues_to_fetch, selected_date, odds_api_key)

    if odds_api_error == "invalid_key":
        st.error("❌ Το Odds API key δεν είναι έγκυρο.")
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

            # Build table
            rows = []
            for m in group.to_dict('records'):
                home_logo = m.get("Logo Γηπ.", "")
                away_logo = m.get("Logo Φιλ.", "")
                home_team = m.get("Γηπεδούχος", "")
                away_team = m.get("Φιλοξενούμενος", "")
                match_time = m.get("Ώρα", "")
                odd_1 = m.get("1", "N/A")
                odd_X = m.get("X", "N/A")
                odd_2 = m.get("2", "N/A")

                home_logo_html = f"""<img class="team-logo" src="{home_logo}" onerror="this.style.visibility='hidden'">""" if home_logo else ''
                away_logo_html = f"""<img class="team-logo" src="{away_logo}" onerror="this.style.visibility='hidden'">""" if away_logo else ''

                rows.append(f"""
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
                """)

            table_html = f"""
            <table class="match-table">
                <thead>
                    <tr>
                        <th>Ώρα</th><th></th><th>Γηπεδούχος</th>
                        <th>1</th><th>X</th><th>2</th>
                        <th>Φιλοξενούμενος</th><th></th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
            """
            st.html(table_html)
            st.divider()
    else:
        st.info(f"Δεν υπάρχουν αγώνες για {selected_date.strftime('%d/%m/%Y')}.")

except Exception as e:
    log_error(f"Main content error: {str(e)}")
    st.error(f"Error: {str(e)}")
