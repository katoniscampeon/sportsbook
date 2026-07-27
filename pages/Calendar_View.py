import streamlit as st
from datetime import timedelta
from shared import (
    athens_tz, now_athens, effective_today,
    get_all_leagues_unique, fetch_all_matches_for_range
)

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
        .cal-logos {
            flex: 1; display: flex; flex-wrap: wrap; gap: 2px;
            align-items: center;
        }
        .cal-logos img {
            width: 20px; height: 20px;
            border-radius: 2px;
            object-fit: contain;
        }
        .cal-promo {
            width: 45%; flex-shrink: 0;
            padding-left: 10px;
            font-size: 0.78rem;
        }
        .cal-empty { color: rgba(128,128,128,0.4); }
        .cal-today-badge {
            font-size: 0.7rem; background: #e8a800; color: #000;
            border-radius: 3px; padding: 0 3px; margin-left: 4px;
            font-weight: 700;
        }
        /* Hide default Streamlit page navigation */
        [data-testid="stSidebarNav"] { display: none !important; }
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
# SIDEBAR — View toggle at top
# -------------------------------------------------------------
st.sidebar.markdown("**Navigation**")
view_col1, view_col2 = st.sidebar.columns(2)
with view_col1:
    if st.button("⚽ Dashboard", key="nav_dash", use_container_width=True, type="secondary"):
        st.switch_page("sportsbook_dashboard.py")
with view_col2:
    if st.button("📅 Calendar", key="nav_cal", use_container_width=True, type="primary"):
        pass  # already on calendar

st.sidebar.markdown("---")

# Navigation buttons (prev/next week)
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

st.sidebar.markdown("---")

# -------------------------------------------------------------
# INIT STATE
# -------------------------------------------------------------
if "promos" not in st.session_state:
    st.session_state.promos = []

st.title("📅 Calendar View")

start_date = st.session_state.cal_start_date
# Load ALL events ahead — 90 days covers the rest of the season
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
# -------------------------------------------------------------
promos_by_date = {}
for promo in st.session_state.promos:
    pdate = promo.get("promo_date", "")
    if pdate:
        promos_by_date.setdefault(pdate, []).append(promo)

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
    unique_champs = {}
    for m in day_matches:
        league = m["Διοργάνωση"]
        logo = m.get("League Logo", "")
        if league not in unique_champs:
            unique_champs[league] = logo

    day_promos = promos_by_date.get(date_str, [])
    is_today = (d == effective_today)

    today_badge = '<span class="cal-today-badge">ΣΗΜΕΡΑ</span>' if is_today else ""
    date_cell = f"{d.day}/{d.month} {day_name}{today_badge}"

    if unique_champs:
        logos_html = "".join(
            f'<img src="{logo}" title="{league}" onerror="this.remove()">'
            if logo else f'<span style="font-size:14px">🏆</span>'
            for league, logo in unique_champs.items()
        )
    else:
        logos_html = '<span class="cal-empty">—</span>'

    if day_promos:
        promo_parts = []
        for p in day_promos:
            label = p.get("match") or p.get("championship") or "—"
            icon = "🏟️" if p.get("match") else "🏆"
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
        f'<div class="cal-logos">{logos_html}</div>'
        f'<div class="cal-promo">{promo_html}</div>'
        f'</div>'
    )

st.markdown("".join(html_parts), unsafe_allow_html=True)
