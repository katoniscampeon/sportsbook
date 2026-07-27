import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

# Simple timezone setup
athens_tz = ZoneInfo("Europe/Athens")
now_athens = datetime.now(athens_tz)
effective_today = (now_athens - timedelta(hours=7)).date()

# Page config
st.set_page_config(page_title="Sportsbook Dashboard", page_icon="⚽", layout="wide")

st.title("⚽ Sportsbook Dashboard")
st.write("✅ App is working!")
st.write(f"Today: {effective_today}")
