import streamlit as st
from datetime import timedelta
from shared import (
    athens_tz, now_athens, effective_today,
    get_all_leagues_unique, fetch_all_matches_for_range
)

st.set_page_config(page_title="Calendar View", page_icon="📅", layout="wide")

st.markdown("""
    <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 0rem;}
        .cal-row {padding: 0.6rem 0; border-bottom: 1px solid rgba(128,128,128,0.2);}
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# INIT STATE
# -------------------------------------------------------------
if "promos" not in st.session_state:
    st.session_state.promos = []

# Date range controls
st.title("📅 Calendar View")
st.subheader("Επισκόπηση αγώνων & promos ανά ημέρα")

col_range, col_days = st.columns([3, 1])
with col_range:
    num_days = st.slider("Ημέρες προς τα εμπρός", min_value=3, max_value=14, value=7, step=1)
with col_days:
    st.write("")
    if st.button("📅 Σήμερα", use_container_width=True):
        st.session_state.cal_start_date = effective_today
        st.rerun()

# Start date for the calendar
if "cal_start_date" not in st.session_state:
    st.session_state.cal_start_date = effective_today

start_date = st.session_state.cal_start_date
end_date = start_date + timedelta(days=num_days - 1)

# Date navigation
col_prev, col_date, col_next = st.columns([1, 3, 1])
with col_prev:
    if st.button("◀", use_container_width=True):
        st.session_state.cal_start_date -= timedelta(days=num_days)
        st.rerun()
with col_date:
    st.markdown(f"**{start_date.strftime('%d/%m/%Y')} — {end_date.strftime('%d/%m/%Y')}**")
with col_next:
    if st.button("▶", use_container_width=True):
        st.session_state.cal_start_date += timedelta(days=num_days)
        st.rerun()

st.markdown("---")

# -------------------------------------------------------------
# FETCH ALL MATCHES FOR THE DATE RANGE
# -------------------------------------------------------------
odds_api_key = st.session_state.get("odds_api_key", "")
all_leagues = get_all_leagues_unique()

with st.spinner("Φόρτωση αγώνων..."):
    matches_by_date = fetch_all_matches_for_range(all_leagues, start_date, end_date, odds_api_key)

# -------------------------------------------------------------
# BUILD PROMO LOOKUP BY DATE
# -------------------------------------------------------------
promos_by_date = {}
for promo in st.session_state.promos:
    promo_date_str = promo.get("promo_date", "")
    if promo_date_str:
        if promo_date_str not in promos_by_date:
            promos_by_date[promo_date_str] = []
        promos_by_date[promo_date_str].append(promo)

# -------------------------------------------------------------
# CALENDAR LIST DISPLAY
# -------------------------------------------------------------
# Header row
hdr_col1, hdr_col2, hdr_col3 = st.columns([2, 5, 5])
with hdr_col1:
    st.markdown("**📅 Ημερομηνία**")
with hdr_col2:
    st.markdown("**🏆 Πρωταθλήματα**")
with hdr_col3:
    st.markdown("**🎁 Promos**")

st.markdown("---")

day_names_gr = ["Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο", "Κυριακή"]

for i in range(num_days):
    d = start_date + timedelta(days=i)
    date_str = d.strftime("%d/%m/%Y")
    day_name = day_names_gr[d.weekday()]

    # Get matches for this date
    day_matches = matches_by_date.get(d, [])

    # Get unique championships and their flags
    unique_champs = {}
    for m in day_matches:
        league = m["Διοργάνωση"]
        flag = m["Flag"]
        if league not in unique_champs:
            unique_champs[league] = flag

    # Get promos for this date
    day_promos = promos_by_date.get(date_str, [])

    is_today = (d == effective_today)

    col1, col2, col3 = st.columns([2, 5, 5])

    with col1:
        if is_today:
            st.markdown(f"### 📌 {date_str}")
        else:
            st.markdown(f"### {date_str}")
        st.caption(day_name)
        st.caption(f"{len(day_matches)} αγώνες")

    with col2:
        if unique_champs:
            # Build flags HTML
            flags_html = ""
            for league, flag in unique_champs.items():
                if flag:
                    flags_html += f"<img src='https://flagcdn.com/24x18/{flag}.png' style='vertical-align: middle; margin-right: 4px;' width='22' title='{league}'>"
                else:
                    flags_html += f"🏳️ "
            st.markdown(flags_html, unsafe_allow_html=True)
            # League names
            league_names = list(unique_champs.keys())
            st.caption(" · ".join(league_names))
        else:
            st.caption("—")

    with col3:
        if day_promos:
            for p in day_promos:
                promo_label = p.get("match") or p.get("championship") or "—"
                icon = "🏟️" if p.get("match") else "🏆"
                st.markdown(f"**{p['type']}** — {icon} {promo_label}")
                if p.get("notes"):
                    st.caption(f"📝 {p['notes']}")
        else:
            st.caption("—")

    st.markdown("---")

# Summary footer
total_matches = sum(len(v) for v in matches_by_date.values())
total_promos = sum(len(v) for v in promos_by_date.values())
st.caption(f"Σύνολο: {total_matches} αγώνες · {total_promos} promos σε {num_days} ημέρες")
