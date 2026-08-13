import streamlit as st
import streamlit.components.v1 as components
from datetime import date, timedelta, datetime
from shared import (
    athens_tz, now_athens, effective_today,
    get_all_leagues_unique, get_custom_league_order, priority_dialog,
    fetch_all_matches_for_range, fetch_all_matches_parallel,
    category_mapping, _league_sort_key,
)
from promo_store import load_promos, add_promo, delete_promo, dates_in_range

_nav = st.query_params.get('cal_nav', '')
if _nav:
    st.session_state.selected_date = date.fromisoformat(_nav)
    st.query_params.clear()
    st.switch_page('sportsbook_dashboard.py')

st.set_page_config(page_title="Calendar View", page_icon="📅", layout="wide")

st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 0rem;}
        [data-testid="stSidebarNav"] { display: none !important; }
        [data-testid="stSidebarContent"] { padding-top: 1rem !important; }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# ODDS API KEY
# -------------------------------------------------------------
def get_odds_api_key():
    try:
        key = st.secrets.get("odds_api_key", "")
        if key: return key
    except Exception:
        pass
    return st.session_state.get("odds_api_key", "")

BOOST_TYPES = ["Golden Boost", "Betslip Boost", "Other"]

# -------------------------------------------------------------
# PROMO DIALOGS
# -------------------------------------------------------------
@st.dialog("➕ Δημιουργία Promo")
def add_promo_dialog_cal():
    boost_type_choice = st.radio("Τύπος Boost", BOOST_TYPES, horizontal=True)
    if boost_type_choice == "Other":
        custom_type = st.text_input("Προσαρμοσμένος τύπος", placeholder="π.χ. Super Odds")
        boost_label = custom_type.strip() if custom_type.strip() else "Other"
    else:
        boost_label = boost_type_choice
    st.divider()
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
            st.warning("Η 'Έως' πρέπει να είναι μετά την 'Από'.")
            promo_dates = [range_start.strftime("%d/%m/%Y")]
        else:
            promo_dates = dates_in_range(range_start, range_end)
        ref_date = range_start
    st.divider()
    selection_type = st.radio(
        "Επιλογή", ["🏟️ Συγκεκριμένος Αγώνας", "🏆 Πρωτάθλημα", "📝 Άλλο"], horizontal=True
    )
    selected_match = selected_championship = other_label = None
    if selection_type == "🏟️ Συγκεκριμένος Αγώνας":
        all_leagues_l = get_all_leagues_unique()
        odds_api_key_l = get_odds_api_key()
        all_day_matches, _ = fetch_all_matches_parallel(all_leagues_l, ref_date, odds_api_key_l)
        match_options = [
            f"{m['Γηπεδούχος']} vs {m['Φιλοξενούμενος']} ({m['Ώρα']}) — {m['Διοργάνωση']}"
            for m in all_day_matches
        ]
        if match_options:
            selected_match = st.selectbox(f"Αγώνας ({ref_date.strftime('%d/%m/%Y')})", match_options)
        else:
            st.warning(f"Δεν βρέθηκαν αγώνες για {ref_date.strftime('%d/%m/%Y')}.")
    elif selection_type == "🏆 Πρωτάθλημα":
        all_leagues_l = get_all_leagues_unique()
        odds_api_key_l = get_odds_api_key()
        all_day_matches, _ = fetch_all_matches_parallel(all_leagues_l, ref_date, odds_api_key_l)
        champ_opts = sorted(set(m["Διοργάνωση"] for m in all_day_matches))
        if champ_opts:
            selected_championship = st.selectbox(f"Πρωτάθλημα ({ref_date.strftime('%d/%m/%Y')})", champ_opts)
        else:
            st.warning(f"Δεν βρέθηκαν πρωταθλήματα για {ref_date.strftime('%d/%m/%Y')}.")
    else:
        other_label = st.text_input("Περιγραφή", placeholder="π.χ. Super Sunday Special")
    specification = st.text_area("Σημειώσεις", placeholder="Γράψε τις λεπτομέρειες του promo...")
    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("💾 Αποθήκευση", use_container_width=True, type="primary"):
            promo = {
                "type": boost_label, "match": selected_match,
                "championship": selected_championship, "other": other_label,
                "notes": specification, "promo_dates": promo_dates,
                "promo_date": promo_dates[0] if promo_dates else "",
                "created": datetime.now(athens_tz).strftime("%d/%m/%Y %H:%M")
            }
            st.session_state.promos = add_promo(promo)
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
            st.markdown(f"**{promo['type']}** · _{promo.get('created','')}_ · 📅 {', '.join(promo.get('promo_dates',[promo.get('promo_date','')]))}")
            if promo.get("match"):        st.markdown(f"🏟️ {promo['match']}")
            if promo.get("championship"): st.markdown(f"🏆 {promo['championship']}")
            if promo.get("other"):        st.markdown(f"📝 {promo['other']}")
            if promo.get("notes"):        st.markdown(f"📝 {promo['notes']}")
            if st.button("🗑️ Διαγραφή", key=f"del_cal_{idx}", use_container_width=True):
                st.session_state.promos = delete_promo(idx)
                st.rerun()
            st.divider()

# -------------------------------------------------------------
# SYNC PROMOS
# -------------------------------------------------------------
st.session_state.promos = load_promos()

# -------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------
with st.sidebar:
    _vc1, _vc2 = st.columns(2)
    with _vc1:
        if st.button("⚽ Dashboard", key="nav_dash", use_container_width=True, type="secondary"):
            st.switch_page("sportsbook_dashboard.py")
    with _vc2:
        if st.button("📅 Calendar", key="nav_cal", use_container_width=True, type="primary"):
            pass

    if st.button("🏆 Priority", use_container_width=True):
        priority_dialog()

    st.divider()
    st.markdown("**Πλοήγηση**")

if "cal_start_date" not in st.session_state:
    st.session_state.cal_start_date = effective_today

with st.sidebar:
    _nc1, _nc2, _nc3 = st.columns([1, 1, 1])
    with _nc1:
        if st.button("◀ 7", key="cal_prev", use_container_width=True):
            st.session_state.cal_start_date -= timedelta(days=7)
            st.rerun()
    with _nc2:
        if st.button("📅 Σήμερα", key="cal_today", use_container_width=True):
            st.session_state.cal_start_date = effective_today
            st.rerun()
    with _nc3:
        if st.button("7 ▶", key="cal_next", use_container_width=True):
            st.session_state.cal_start_date += timedelta(days=7)
            st.rerun()

    st.divider()
    promo_count = len(st.session_state.promos)
    if st.button("➕ Add Promo", use_container_width=True):
        add_promo_dialog_cal()
    if st.button(f"👁 Promos ({promo_count})" if promo_count else "👁 Promos", use_container_width=True):
        view_promos_dialog_cal()

# -------------------------------------------------------------
# MAIN
# -------------------------------------------------------------
st.title("📅 Calendar View")

start_date = st.session_state.cal_start_date
num_days   = 90
end_date   = start_date + timedelta(days=num_days - 1)
st.markdown(f"**{start_date.strftime('%d/%m/%Y')} — {end_date.strftime('%d/%m/%Y')}**")

# -------------------------------------------------------------
# FETCH
# -------------------------------------------------------------
odds_api_key    = get_odds_api_key()
custom_order    = get_custom_league_order()
all_leagues     = get_all_leagues_unique(custom_order)
tennis_leagues  = category_mapping.get("🎾 Tennis", [])
all_cal_leagues = all_leagues + [l for l in tennis_leagues if l not in all_leagues]

with st.spinner("Φόρτωση αγώνων..."):
    matches_by_date = fetch_all_matches_for_range(all_cal_leagues, start_date, end_date, odds_api_key)

# -------------------------------------------------------------
# PROMO LOOKUP
# -------------------------------------------------------------
promos_by_date: dict = {}
for promo in st.session_state.promos:
    dates = promo.get("promo_dates", [promo.get("promo_date", "")])
    for pdate in dates:
        if pdate:
            promos_by_date.setdefault(pdate, []).append(promo)

# -------------------------------------------------------------
# SPORT CLASSIFICATION
# -------------------------------------------------------------
def get_match_sport(match):
    sport = match.get("Sport", "")
    if sport:
        return sport
    logo   = match.get("League Logo", "").lower()
    league = match.get("Διοργάνωση", "").lower()
    if "nba" in logo or "basketball" in logo:
        return "basketball"
    if "nhl" in logo or "icehockey" in logo:
        return "hockey"
    if "liiga" in league and "veikkaus" not in league:
        return "hockey"
    if "tennis" in logo or "atp" in logo:
        return "tennis"
    return "soccer"

def sport_logos_html(day_matches, sport_filter, custom_order=None):
    # Build league→priority lookup from custom_order
    from shared import LEAGUE_DISPLAY_ORDER, get_custom_league_order
    order = custom_order if custom_order is not None else get_custom_league_order()

    def match_priority(m):
        src      = m.get("_src", "espn")
        code     = m.get("_code", "")
        key      = (src, code)
        try:
            return order.index(key)
        except ValueError:
            return len(order)

    filtered = [m for m in day_matches if get_match_sport(m) == sport_filter]
    filtered.sort(key=match_priority)

    seen  = set()
    parts = []
    for m in filtered:
        league = m["Διοργάνωση"]
        logo   = m.get("League Logo", "")
        if league in seen:
            continue
        seen.add(league)
        if logo:
            parts.append(f'<img src="{logo}" title="{league}" onerror="this.remove()">')
        else:
            parts.append(f'<span title="{league}">🏆</span>')
    if parts:
        return f'<div class="logos">{"".join(parts)}</div>'
    return '<span class="empty">—</span>'

# -------------------------------------------------------------
# BUILD CALENDAR — native Streamlit rows (date = st.button)
# -------------------------------------------------------------
month_names_gr     = ["Ιανουάριος","Φεβρουάριος","Μάρτιος","Απρίλιος","Μάιος","Ιούνιος",
                      "Ιούλιος","Αύγουστος","Σεπτέμβριος","Οκτώβριος","Νοέμβριος","Δεκέμβριος"]
day_names_gr_short = ["Δευ","Τρι","Τετ","Πεμ","Παρ","Σαβ","Κυρ"]

# Column proportions: date | soccer | basketball | tennis | hockey | promos
COL_W = [1.1, 3.2, 1.3, 1.0, 1.0, 2.6]

# Shared CSS injected once
st.markdown("""
<style>
/* Calendar table styling */
.cal-header { font-size:0.68rem; color:rgba(128,128,128,0.6); font-weight:700;
              padding:1px 0 2px; border-bottom:1px solid rgba(128,128,128,0.18); }
.cal-logos  { display:flex; flex-wrap:wrap; gap:2px; align-items:center;
              padding:0; min-height:20px; }
.cal-logos img { width:18px; height:18px; object-fit:contain; border-radius:2px; }
.cal-empty  { color:rgba(128,128,128,0.35); font-size:0.75rem; }
.cal-promo  { font-size:0.72rem; line-height:1.3; }
.cal-month  { font-size:0.95rem; font-weight:700; margin-top:8px; margin-bottom:0px;
              padding-bottom:2px; border-bottom:2px solid rgba(128,128,128,0.25); }
/* Shrink all streamlit element containers to remove vertical gaps */
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlock"] { gap: 0rem !important; }
div[data-testid="column"] { padding: 0 2px !important; }
div[data-testid="stMarkdown"] { margin-bottom: 0 !important; line-height: 1; }
hr { margin: 0 !important; }
/* Date buttons — look like plain links, tight height */
div[data-testid="stButton"] > button {
    background: none !important;
    border: none !important;
    padding: 1px 0 !important;
    color: inherit !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    text-align: left !important;
    box-shadow: none !important;
    width: 100% !important;
    min-height: unset !important;
    height: auto !important;
    line-height: 1.3 !important;
}
div[data-testid="stButton"] > button:hover {
    color: #e8a800 !important;
    text-decoration: underline !important;
    background: none !important;
}
</style>
""", unsafe_allow_html=True)

def logos_html(day_matches, sport_filter, custom_order=None):
    """Returns inline HTML string of league logos for a sport column."""
    from shared import get_custom_league_order
    order = custom_order if custom_order is not None else get_custom_league_order()

    def match_priority(m):
        key = (m.get("_src", "espn"), m.get("_code", ""))
        try:    return order.index(key)
        except: return len(order)

    filtered = sorted(
        [m for m in day_matches if get_match_sport(m) == sport_filter],
        key=match_priority
    )
    seen, parts = set(), []
    for m in filtered:
        league = m["Διοργάνωση"]
        logo   = m.get("League Logo", "")
        if league in seen: continue
        seen.add(league)
        if logo:
            parts.append(f'<img src="{logo}" title="{league}" onerror="this.remove()">')
        else:
            parts.append(f'<span title="{league}" style="font-size:0.8rem">🏆</span>')
    if parts:
        return f'<div class="cal-logos">{"".join(parts)}</div>'
    return '<div class="cal-logos"><span class="cal-empty">—</span></div>'

def promo_html(day_promos):
    if not day_promos:
        return '<span class="cal-empty">—</span>'
    parts = []
    for p in day_promos:
        label = p.get("match") or p.get("championship") or p.get("other") or "—"
        icon  = "🏟️" if p.get("match") else ("🏆" if p.get("championship") else "📝")
        short = label[:40] + ("…" if len(label) > 40 else "")
        parts.append(f'<span class="cal-promo"><b>{p["type"]}</b> {icon} {short}</span>')
    return "<br>".join(parts)

# ── render ──
current_month = None

# Track if user clicked a date button this render pass
_nav_target = None

for i in range(num_days):
    d        = start_date + timedelta(days=i)
    date_str = d.strftime("%d/%m/%Y")
    day_name = day_names_gr_short[d.weekday()]
    is_today = (d == effective_today)
    month_key = (d.month, d.year)

    # Month header
    if month_key != current_month:
        current_month = month_key
        st.markdown(f'<div class="cal-month">{month_names_gr[d.month-1]} {d.year}</div>', unsafe_allow_html=True)
        # Column headers
        h_cols = st.columns(COL_W)
        headers = ["Ημερομηνία", "⚽ Ποδόσφαιρο", "🏀 Μπάσκετ", "🎾 Τένις", "🏒 Χόκεϊ", "📋 Promos"]
        for hc, ht in zip(h_cols, headers):
            hc.markdown(f'<div class="cal-header">{ht}</div>', unsafe_allow_html=True)

    day_matches = matches_by_date.get(d, [])
    day_promos  = promos_by_date.get(date_str, [])

    row_cols = st.columns(COL_W)

    # Date column — st.button so it navigates properly
    with row_cols[0]:
        badge = " 🟡" if is_today else ""
        label = f"{d.day}/{d.month} {day_name}{badge}"
        if st.button(label, key=f"cal_btn_{i}", use_container_width=True):
            st.session_state.selected_date = d
            st.switch_page("sportsbook_dashboard.py")

    # Sports columns
    for col, sport in zip(row_cols[1:5], ["soccer", "basketball", "tennis", "hockey"]):
        col.markdown(logos_html(day_matches, sport, custom_order), unsafe_allow_html=True)

    # Promos column
    row_cols[5].markdown(promo_html(day_promos), unsafe_allow_html=True)

    # Thin separator between days via CSS only (no extra markdown element)

