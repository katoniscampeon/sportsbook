import urllib.request
import json
import re

def main():
    # 1. Fetch scoreboard
    try:
        req = urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            sb = json.loads(resp.read().decode())
            print("=== SCOREBOARD LOGOS ===")
            find_logos(sb)
    except Exception as e:
        print("Scoreboard fetch failed:", e)

    # 2. Fetch events
    try:
        req = urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/tennis/atp/events", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            evs = json.loads(resp.read().decode())
            print("\n=== EVENTS LOGOS ===")
            find_logos(evs)
    except Exception as e:
        print("Events fetch failed:", e)

def find_logos(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            current_path = f"{path}.{k}" if path else k
            if k in ["logo", "href", "logos"] and isinstance(v, str) and (".png" in v or ".jpg" in v or ".jpeg" in v):
                print(f"{current_path}: {v}")
            elif isinstance(v, (dict, list)):
                find_logos(v, current_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_logos(item, f"{path}[{i}]")

if __name__ == "__main__":
    main()
