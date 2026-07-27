"""
Persistent promo storage — reads/writes promos.json.
Automatically removes promos whose dates have all passed.
"""
import json
import os
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

PROMO_FILE = "promos.json"
_athens_tz = ZoneInfo("Europe/Athens")


def _today_athens() -> date:
    return datetime.now(_athens_tz).date()


def load_promos() -> list:
    """Load promos from file, dropping any where all dates have already passed."""
    if not os.path.exists(PROMO_FILE):
        return []
    try:
        with open(PROMO_FILE, "r", encoding="utf-8") as f:
            promos = json.load(f)
    except Exception:
        return []

    today = _today_athens()
    valid = []
    changed = False

    for p in promos:
        # Normalize legacy promos that stored a single promo_date string
        if "promo_dates" not in p:
            old = p.get("promo_date", "")
            p["promo_dates"] = [old] if old else []

        future = []
        for d in p["promo_dates"]:
            try:
                if datetime.strptime(d, "%d/%m/%Y").date() >= today:
                    future.append(d)
            except Exception:
                pass

        if future:
            p["promo_dates"] = future
            valid.append(p)
        else:
            changed = True

    if changed:
        save_promos(valid)
    return valid


def save_promos(promos: list) -> None:
    """Persist promos list to JSON file."""
    try:
        with open(PROMO_FILE, "w", encoding="utf-8") as f:
            json.dump(promos, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_promo(promo: dict) -> list:
    """Append a promo and persist. Returns updated list."""
    promos = load_promos()
    promos.append(promo)
    save_promos(promos)
    return promos


def delete_promo(idx: int) -> list:
    """Delete promo by index and persist. Returns updated list."""
    promos = load_promos()
    if 0 <= idx < len(promos):
        promos.pop(idx)
        save_promos(promos)
    return promos


def dates_in_range(start: date, end: date) -> list:
    """Return list of 'DD/MM/YYYY' strings for every day from start to end (inclusive)."""
    days = []
    current = start
    while current <= end:
        days.append(current.strftime("%d/%m/%Y"))
        current += timedelta(days=1)
    return days
