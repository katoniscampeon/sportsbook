#!/usr/bin/env python3
import sys
import subprocess

print("=" * 60)
print("DIAGNOSTIC SCRIPT")
print("=" * 60)

# Check Python version
print(f"\n✓ Python version: {sys.version}")

# Check if streamlit is installed
try:
    import streamlit
    print(f"✓ Streamlit installed: {streamlit.__version__}")
except ImportError as e:
    print(f"✗ Streamlit NOT installed: {e}")
    sys.exit(1)

# Check if pandas is installed
try:
    import pandas
    print(f"✓ Pandas installed: {pandas.__version__}")
except ImportError as e:
    print(f"✗ Pandas NOT installed: {e}")
    sys.exit(1)

# Check if requests is installed
try:
    import requests
    print(f"✓ Requests installed: {requests.__version__}")
except ImportError as e:
    print(f"✗ Requests NOT installed: {e}")
    sys.exit(1)

# Check if cachetools is installed
try:
    import cachetools
    print(f"✓ Cachetools installed: {cachetools.__version__}")
except ImportError as e:
    print(f"✗ Cachetools NOT installed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("All dependencies OK!")
print("=" * 60)
print("\nNow run:")
print("  streamlit run sportsbook_dashboard.py --server.port 5000 --server.address 0.0.0.0")
