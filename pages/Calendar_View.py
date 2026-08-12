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
view_col1, view_col2 = st.sidebar.columns(2)
with view_col1:
    if st.button("⚽ Dashboard", key="nav_dash", use_container_width=True, type="secondary"):
        st.switch_page("sportsbook_dashboard.py")
with view_col2:
    if st.button("📅 Calendar", key="nav_cal", use_container_width=True, type="primary"):
        pass

if st.sidebar.button("🏆 Priority", use_container_width=True):
    priority_dialog()

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
promo_count = len(st.session_state.promos)
if st.sidebar.button("➕ Add Promo", use_container_width=True):
    add_promo_dialog_cal()
if st.sidebar.button(f"👁 Promos ({promo_count})" if promo_count else "👁 Promos", use_container_width=True):
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

def sport_logos_html(day_matches, sport_filter):
    seen  = set()
    parts = []
    for m in day_matches:
        if get_match_sport(m) != sport_filter:
            continue
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
# BUILD FULL HTML TABLE (dates are clickable inside the table)
# -------------------------------------------------------------
month_names_gr     = ["Ιανουάριος","Φεβρουάριος","Μάρτιος","Απρίλιος","Μάιος","Ιούνιος",
                      "Ιούλιος","Αύγουστος","Σεπτέμβριος","Οκτώβριος","Νοέμβριος","Δεκέμβριος"]
day_names_gr_short = ["Δευ","Τρι","Τετ","Πεμ","Παρ","Σαβ","Κυρ"]

html_rows     = []
current_month = None

for i in range(num_days):
    d         = start_date + timedelta(days=i)
    date_str  = d.strftime("%d/%m/%Y")
    day_name  = day_names_gr_short[d.weekday()]
    month_key = (d.month, d.year)

    if month_key != current_month:
        current_month = month_key
        if html_rows:
            html_rows.append("</tbody></table>")
        html_rows.append(
            f'<div class="month-hdr">{month_names_gr[d.month-1]} {d.year}</div>'
            f'<table><thead><tr>'
            f'<th class="h-date">Ημερομηνία</th>'
            f'<th class="h-soccer">⚽ Ποδόσφαιρο</th>'
            f'<th class="h-basket">🏀 Μπάσκετ</th>'
            f'<th class="h-tennis">🎾 Τένις</th>'
            f'<th class="h-hockey">🏒 Χόκεϊ</th>'
            f'<th class="h-promo">📋 Promos</th>'
            f'</tr></thead><tbody>'
        )

    day_matches = matches_by_date.get(d, [])
    day_promos  = promos_by_date.get(date_str, [])
    is_today    = (d == effective_today)
    nav_iso     = d.strftime("%Y-%m-%d")

    today_badge  = '<span class="badge">ΣΗΜΕΡΑ</span>' if is_today else ""
    onclick_js   = f"window.parent.location.href = window.parent.location.href.replace(/\\/Calendar_View[^?#]*/, '') + '?cal_nav={nav_iso}';"
    date_cell    = f'<a href="#" class="dlink" onclick="{onclick_js} return false;">{d.day}/{d.month} {day_name}{today_badge}</a>'

    s_html = sport_logos_html(day_matches, "soccer")
    b_html = sport_logos_html(day_matches, "basketball")
    t_html = sport_logos_html(day_matches, "tennis")
    h_html = sport_logos_html(day_matches, "hockey")

    if day_promos:
        p_parts = []
        for p in day_promos:
            label = p.get("match") or p.get("championship") or p.get("other") or "—"
            icon  = "🏟️" if p.get("match") else ("🏆" if p.get("championship") else "📝")
            short = label[:45] + ("…" if len(label) > 45 else "")
            p_parts.append(f"<b>{p['type']}</b> {icon} <span class='pl'>{short}</span>")
        promo_html = "<br>".join(p_parts)
    else:
        promo_html = '<span class="empty">—</span>'

    row_cls = "today" if is_today else ""
    html_rows.append(
        f'<tr class="{row_cls}">'
        f'<td class="c-date">{date_cell}</td>'
        f'<td class="c-soccer">{s_html}</td>'
        f'<td class="c-basket">{b_html}</td>'
        f'<td class="c-tennis">{t_html}</td>'
        f'<td class="c-hockey">{h_html}</td>'
        f'<td class="c-promo">{promo_html}</td>'
        f'</tr>'
    )

html_rows.append("</tbody></table>")

full_html = """<!DOCTYPE html>
<html>
<head>
<style>
  body { margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:0.82rem; color:inherit; }
  .month-hdr {
    font-size:1.0rem; font-weight:700;
    margin-top:12px; margin-bottom:2px; padding-bottom:2px;
    border-bottom:2px solid rgba(128,128,128,0.25);
  }
  table { width:100%; border-collapse:collapse; table-layout:fixed; margin-bottom:2px; }
  th {
    font-size:0.7rem; color:rgba(128,128,128,0.6); font-weight:700;
    text-align:left; padding:3px 6px 2px;
    border-bottom:1px solid rgba(128,128,128,0.18);
    background:rgba(128,128,128,0.03);
  }
  td { padding:3px 6px; border-bottom:1px solid rgba(128,128,128,0.08); vertical-align:middle; overflow:hidden; }
  tr:hover td { background-color:rgba(128,128,128,0.06); }
  tr.today td { background-color:rgba(255,200,0,0.07); border-left:3px solid #e8a800; }

  .h-date, .c-date { width:95px; white-space:nowrap; }
  .h-soccer,.c-soccer { width:29%; }
  .h-basket,.c-basket { width:12%; }
  .h-tennis,.c-tennis { width:10%; }
  .h-hockey,.c-hockey { width:10%; }
  .h-promo, .c-promo  { width:26%; }

  .dlink {
    color: inherit; text-decoration: none;
    font-weight: 600; font-size: 0.82rem;
  }
  .dlink:hover { color: #e8a800; text-decoration: underline; cursor: pointer; }

  .badge {
    font-size:0.6rem; background:#e8a800; color:#000;
    border-radius:3px; padding:0 3px; margin-left:3px;
    font-weight:700; vertical-align:middle;
  }
  .empty { color:rgba(128,128,128,0.35); }
  .logos { display:flex; flex-wrap:wrap; gap:3px; align-items:center; }
  .logos img { width:22px; height:22px; object-fit:contain; border-radius:2px; }
  .pl { font-size:0.75rem; }
</style>
</head>
<body>
""" + "".join(html_rows) + """
</body>
</html>"""

estimated_height = num_days * 29 + 4 * 55 + 80
components.html(full_html, height=estimated_height, scrolling=True)
