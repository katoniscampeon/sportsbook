import streamlit as st
from datetime import date, timedelta, datetime
from shared import (
    athens_tz, now_athens, effective_today,
    get_all_leagues_unique, fetch_all_matches_for_range,
    SPORT_ICON
)
from promo_store import load_promos, add_promo, delete_promo, dates_in_range

st.set_page_config(page_title="Calendar View", page_icon="📅", layout="wide")

st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 0rem;}
        .cal-month {
            font-size: 1.1rem; font-weight: 700;
            margin-top: 14px; margin-bottom: 2px;
            padding-bottom: 2px;
            border-bottom: 2px solid rgba(128,128,128,0.25);
        }
        .cal-row {
            display: flex; align-items: center;
            padding: 3px 6px;
            border-bottom: 1px solid rgba(128,128,128,0.08);
            font-size: 0.82rem;
        }
        .cal-row:hover { background-color: rgba(128,128,128,0.06); }
        .cal-today {
            background-color: rgba(255,200,0,0.07);
            border-left: 3px solid #e8a800;
            padding-left: 3px;
        }
        .cal-date {
            width: 95px; flex-shrink: 0;
            font-weight: 600;
        }
        .cal-sports {
            flex: 1; display: flex; flex-wrap: wrap; gap: 4px;
            align-items: center;
        }
        .cal-sport-group {
            display: flex; align-items: center; gap: 2px;
        }
        .cal-sport-icon {
            font-size: 13px; line-height: 1;
        }
        .cal-logos img {
            width: 20px; height: 20px;
            border-radius: 2px;
            object-fit: contain;
        }
        .cal-sport-sep {
            color: rgba(128,128,128,0.3);
            margin: 0 3px;
            font-size: 10px;
        }
        .cal-promo {
            width: 42%; flex-shrink: 0;
            padding-left: 10px;
            font-size: 0.78rem;
        }
        .cal-empty { color: rgba(128,128,128,0.4); }
        .cal-today-badge {
            font-size: 0.7rem; background: #e8a800; color: #000;
            border-radius: 3px; padding: 0 3px; margin-left: 4px;
            font-weight: 700;
        }
        /* Hide ONLY default Streamlit page navigation */
        [data-testid="stSidebarNav"] { display: none !important; }
        /* Slightly reduce sidebar spacing */
        [data-testid="stSidebarContent"] {
            padding-top: 1rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# ODDS API KEY
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
# BOOST TYPES (shared with dashboard)
# -------------------------------------------------------------
BOOST_TYPES = ["Golden Boost", "Betslip Boost", "Other"]

# -------------------------------------------------------------
# PROMO DIALOG (calendar-specific — no pre-selected match date)
# -------------------------------------------------------------
@st.dialog("➕ Δημιουργία Promo")
def add_promo_dialog_cal():
    from shared import get_all_leagues_unique, fetch_all_matches_parallel

    # --- Boost type ---
    boost_type_choice = st.radio("Τύπος Boost", BOOST_TYPES, horizontal=True)
    if boost_type_choice == "Other":
        custom_type = st.text_input("Προσαρμοσμένος τύπος", placeholder="π.χ. Super Odds")
        boost_label = custom_type.strip() if custom_type.strip() else "Other"
    else:
        boost_label = boost_type_choice

    st.divider()

    # --- Date selection ---
    date_mode = st.radio("Επιλογή ημερομηνίας", ["Μία ημέρα", "Εύρος ημερομηνιών"], horizontal=True)
    if date_mode == "Μία ημέρα":
        chosen_date = st.date_input("Ημερομηνία", value=effective_today)
        promo_dates = [chosen_date.strftime("%d/%m/%Y")]
        ref_date = chosen_date
    else:
        col_s, col_e = st.columns(2)
        with col_s:
            range_start = st.date_input("Από", value=effective_today)
        with col_e:
            range_end = st.date_input("Έως", value=effective_today + timedelta(days=6))
        if range_end < range_start:
            st.warning("Η ημερομηνία 'Έως' πρέπει να είναι μετά την 'Από'.")
            promo_dates = [range_start.strftime("%d/%m/%Y")]
        else:
            promo_dates = dates_in_range(range_start, range_end)
        ref_date = range_start

    st.divider()

    # --- Selection type ---
    selection_type = st.radio(
        "Επιλογή",
        ["🏟️ Συγκεκριμένος Αγώνας", "🏆 Πρωτάθλημα", "📝 Άλλο"],
        horizontal=True
    )

    selected_match = None
    selected_championship = None
    other_label = None

    if selection_type == "🏟️ Συγκεκριμένος Αγώνας":
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

    elif selection_type == "🏆 Πρωτάθλημα":
        all_leagues = get_all_leagues_unique()
        odds_api_key = get_odds_api_key()
        all_day_matches, _ = fetch_all_matches_parallel(all_leagues, ref_date, odds_api_key)
        championship_options = sorted(set(m["Διοργάνωση"] for m in all_day_matches))
        if championship_options:
            selected_championship = st.selectbox(f"Πρωτάθλημα ({ref_date.strftime('%d/%m/%Y')})", championship_options)
        else:
            st.warning(f"Δεν βρέθηκαν πρωταθλήματα για {ref_date.strftime('%d/%m/%Y')}.")

    else:
        other_label = st.text_input("Περιγραφή", placeholder="π.χ. Super Sunday Special")

    specification = st.text_area("Σημειώσεις / Specification", placeholder="Γράψε τις λεπτομέρειες του promo...")

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("💾 Αποθήκευση", use_container_width=True, type="primary"):
            promo = {
                "type": boost_label,
                "match": selected_match,
                "championship": selected_championship,
                "other": other_label,
                "notes": specification,
                "promo_dates": promo_dates,
                "promo_date": promo_dates[0] if promo_dates else "",
                "created": datetime.now(athens_tz).strftime("%d/%m/%Y %H:%M")
            }
            updated = add_promo(promo)
            st.session_state.promos = updated
            st.rerun()
    with col_cancel:
        if st.button("❌ Ακύρωση", use_container_width=True):
            st.rerun()


@st.dialog("👁 Promos")
def view_promos_dialog_cal():
    promos = load_promos()
    if not promos:
        st.info("Δεν υπάρχουν αποθηκευμένα promos.")
    else:
        for idx, promo in enumerate(promos):
            st.markdown(f"**{promo['type']}** &nbsp;·&nbsp; _{promo.get('created', '')}_ &nbsp;·&nbsp; 📅 {', '.join(promo.get('promo_dates', [promo.get('promo_date', '')]))}")
            if promo.get("match"):
                st.markdown(f"🏟️ {promo['match']}")
            if promo.get("championship"):
                st.markdown(f"🏆 {promo['championship']}")
            if promo.get("other"):
                st.markdown(f"📝 {promo['other']}")
            if promo.get("notes"):
                st.markdown(f"📝 {promo['notes']}")
            if st.button("🗑️ Διαγραφή", key=f"del_cal_promo_{idx}", use_container_width=True):
                updated = delete_promo(idx)
                st.session_state.promos = updated
                st.rerun()
            st.divider()


# -------------------------------------------------------------
# SYNC PERSISTENT PROMOS
# -------------------------------------------------------------
st.session_state.promos = load_promos()

# -------------------------------------------------------------
# SIDEBAR — Navigation at very top
# -------------------------------------------------------------
view_col1, view_col2 = st.sidebar.columns(2)
with view_col1:
    if st.button("⚽ Dashboard", key="nav_dash", use_container_width=True, type="secondary"):
        st.switch_page("sportsbook_dashboard.py")
with view_col2:
    if st.button("📅 Calendar", key="nav_cal", use_container_width=True, type="primary"):
        pass  # already on calendar

st.sidebar.divider()

st.sidebar.markdown("**Πλοήγηση**")
if "cal_start_date" not in st.session_state:
    st.session_state.cal_start_date = effective_today

nav_col1, nav_col2, nav_col3 = st.sidebar.columns([1, 1, 1])
with nav_col1:
    if st.button("◀ 7", key="cal_prev", use_container_width=True):
        st.session_state.cal_start_date -= timedelta(days=7)
        st.rerun()
with nav_col2:
    if st.button("📅 Σήμερα", key="cal_today", use_container_width=True):
        st.session_state.cal_start_date = effective_today
        st.rerun()
with nav_col3:
    if st.button("7 ▶", key="cal_next", use_container_width=True):
        st.session_state.cal_start_date += timedelta(days=7)
        st.rerun()

st.sidebar.divider()

# Promo buttons in sidebar
promo_count = len(st.session_state.promos)
if st.sidebar.button(f"➕ Add Promo", use_container_width=True):
    add_promo_dialog_cal()

promo_view_label = f"👁 Promos ({promo_count})" if promo_count > 0 else "👁 Promos"
if st.sidebar.button(promo_view_label, use_container_width=True):
    view_promos_dialog_cal()

st.sidebar.divider()

# -------------------------------------------------------------
# MAIN TITLE
# -------------------------------------------------------------
st.title("📅 Calendar View")

start_date = st.session_state.cal_start_date
num_days = 90
end_date = start_date + timedelta(days=num_days - 1)

st.markdown(f"**{start_date.strftime('%d/%m/%Y')} — {end_date.strftime('%d/%m/%Y')}** _(90 ημέρες ahead)_")

# -------------------------------------------------------------
# FETCH ALL MATCHES
# -------------------------------------------------------------
odds_api_key = get_odds_api_key()
all_leagues = get_all_leagues_unique()

with st.spinner("Φόρτωση όλων των αγώνων..."):
    matches_by_date = fetch_all_matches_for_range(all_leagues, start_date, end_date, odds_api_key)

# -------------------------------------------------------------
# BUILD PROMO LOOKUP BY DATE
# Promos can have a list of dates (promo_dates) or a single promo_date.
# -------------------------------------------------------------
promos_by_date: dict = {}
for promo in st.session_state.promos:
    dates = promo.get("promo_dates", [promo.get("promo_date", "")])
    for pdate in dates:
        if pdate:
            promos_by_date.setdefault(pdate, []).append(promo)

# -------------------------------------------------------------
# SPORT ORDER for calendar display
# -------------------------------------------------------------
SPORT_ORDER = ["soccer", "basketball", "tennis", "hockey", "other"]


def build_sport_logos_html(day_matches: list) -> str:
    """
    Group day's leagues by sport and return HTML with sport icons
    followed by league logos, separated by sport.
    E.g.:  ⚽ [PL] [UCL]  🏀 [NBA]  🎾 [ATP]  🏒 [NHL]
    """
    # sport -> list of (league_name, logo_url) unique
    sports_map: dict = {s: [] for s in SPORT_ORDER}
    seen_leagues: set = set()

    for m in day_matches:
        sport = m.get("Sport", "soccer")
        if sport not in sports_map:
            sport = "other"
        league = m["Διοργάνωση"]
        logo = m.get("League Logo", "")
        if league not in seen_leagues:
            seen_leagues.add(league)
            sports_map[sport].append((league, logo))

    parts = []
    for sport in SPORT_ORDER:
        leagues = sports_map[sport]
        if not leagues:
            continue
        icon = SPORT_ICON.get(sport, "🏆")
        group_html = f'<span class="cal-sport-icon">{icon}</span>'
        for league_name, logo in leagues:
            if logo:
                group_html += f'<img src="{logo}" title="{league_name}" onerror="this.remove()" style="width:20px;height:20px;border-radius:2px;object-fit:contain;vertical-align:middle;">'
            else:
                group_html += f'<span title="{league_name}" style="font-size:14px">🏆</span>'
        parts.append(f'<span class="cal-sport-group">{group_html}</span>')

    if parts:
        return '<span class="cal-sport-sep">·</span>'.join(parts)
    return '<span class="cal-empty">—</span>'


# -------------------------------------------------------------
# BUILD CALENDAR HTML (grouped by month)
# -------------------------------------------------------------
month_names_gr = [
    "Ιανουάριος", "Φεβρουάριος", "Μάρτιος", "Απρίλιος", "Μάιος", "Ιούνιος",
    "Ιούλιος", "Αύγουστος", "Σεπτέμβριος", "Οκτώβριος", "Νοέμβριος", "Δεκέμβριος"
]
day_names_gr_short = ["Δευ", "Τρι", "Τετ", "Πεμ", "Παρ", "Σαβ", "Κυρ"]

html_parts = []
current_month = None

for i in range(num_days):
    d = start_date + timedelta(days=i)
    date_str = d.strftime("%d/%m/%Y")
    day_name = day_names_gr_short[d.weekday()]
    month_key = (d.month, d.year)

    if month_key != current_month:
        current_month = month_key
        html_parts.append(f'<div class="cal-month">{month_names_gr[d.month - 1]} {d.year}</div>')

    day_matches = matches_by_date.get(d, [])
    day_promos = promos_by_date.get(date_str, [])
    is_today = (d == effective_today)

    today_badge = '<span class="cal-today-badge">ΣΗΜΕΡΑ</span>' if is_today else ""
    date_cell = f"{d.day}/{d.month} {day_name}{today_badge}"

    # Sport-separated logos
    logos_html = build_sport_logos_html(day_matches)

    # Promo column
    if day_promos:
        promo_parts = []
        for p in day_promos:
            label = p.get("match") or p.get("championship") or p.get("other") or "—"
            if p.get("match"):
                icon = "🏟️"
            elif p.get("championship"):
                icon = "🏆"
            else:
                icon = "📝"
            promo_parts.append(f"<b>{p['type']}</b> {icon} {label}")
            if p.get("notes"):
                promo_parts.append(f"<span class='cal-empty'>📝 {p['notes']}</span>")
        promo_html = "<br>".join(promo_parts)
    else:
        promo_html = '<span class="cal-empty">—</span>'

    row_class = "cal-row cal-today" if is_today else "cal-row"
    html_parts.append(
        f'<div class="{row_class}">'
        f'<div class="cal-date">{date_cell}</div>'
        f'<div class="cal-sports">{logos_html}</div>'
        f'<div class="cal-promo">{promo_html}</div>'
        f'</div>'
    )

st.markdown("".join(html_parts), unsafe_allow_html=True)
