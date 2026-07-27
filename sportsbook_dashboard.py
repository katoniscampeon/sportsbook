import streamlit as st
import sys
import traceback

# Add error logging to stderr so you can see it in terminal
def log_error(msg):
    print(f"[STREAMLIT ERROR] {msg}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)

try:
    st.set_page_config(page_title="Sportsbook Dashboard", page_icon="⚽", layout="wide")
    st.title("⚽ Sportsbook Dashboard")
    st.write("✅ Basic app works!")
    
except Exception as e:
    log_error(f"Error in page config: {str(e)}")
    st.error(f"Error: {str(e)}")
    traceback.print_exc()
