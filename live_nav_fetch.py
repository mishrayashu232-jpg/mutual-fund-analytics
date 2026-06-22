"""
live_nav_fetch.py
=================
Day 1 — Mutual Fund Analytics Project
Tasks 4 & 5: Fetch live NAV data from mfapi.in for 6 large-cap schemes,
             parse JSON response, and save as CSV.

API endpoint : GET https://api.mfapi.in/mf/{scheme_code}
Schemes      : HDFC Top 100, SBI Bluechip, ICICI Bluechip,
               Nippon Large Cap, Axis Bluechip, Kotak Bluechip

Run          : python live_nav_fetch.py
"""

import os
import json
import time
import requests
import pandas as pd
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BASE_URL  = "https://api.mfapi.in/mf"
RAW_DIR   = os.path.join("data", "raw")
PROC_DIR  = os.path.join("data", "processed")
os.makedirs(RAW_DIR,  exist_ok=True)
os.makedirs(PROC_DIR, exist_ok=True)

SCHEMES = {
    125497: "HDFC Top 100 Direct",
    119551: "SBI Bluechip Direct",
    120503: "ICICI Bluechip Direct",
    118632: "Nippon Large Cap Direct",
    119092: "Axis Bluechip Direct",
    120841: "Kotak Bluechip Direct",
}

SEPARATOR = "=" * 70


# ─────────────────────────────────────────────
# FETCH + PARSE
# ─────────────────────────────────────────────
def fetch_nav(scheme_code: int, retries: int = 3, backoff: float = 2.0) -> dict | None:
    """
    Fetch NAV JSON from mfapi.in with retry/backoff.
    Returns parsed dict on success, None on failure.
    """
    url = f"{BASE_URL}/{scheme_code}"
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "SUCCESS":
                return data
            else:
                print(f"  [WARN] API returned non-SUCCESS for {scheme_code}: {data.get('status')}")
                return None
        except requests.exceptions.ConnectionError:
            print(f"  [WARN] Connection error for {scheme_code} (attempt {attempt}/{retries})")
        except requests.exceptions.Timeout:
            print(f"  [WARN] Timeout for {scheme_code} (attempt {attempt}/{retries})")
        except requests.exceptions.HTTPError as e:
            print(f"  [WARN] HTTP {e.response.status_code} for {scheme_code}: {e}")
        except json.JSONDecodeError:
            print(f"  [WARN] Invalid JSON for {scheme_code}")

        if attempt < retries:
            print(f"  Retrying in {backoff:.0f}s …")
            time.sleep(backoff)
            backoff *= 2

    return None


def load_nav_from_local_json(scheme_code: int) -> dict | None:
    """
    Fallback: load previously saved raw JSON (used when API is offline or
    network egress to mfapi.in is restricted — e.g. in CI / sandboxed envs).
    """
    path = os.path.join(RAW_DIR, f"nav_{scheme_code}_raw.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def parse_nav_response(data: dict, scheme_code: int) -> pd.DataFrame:
    """
    Parse mfapi.in JSON response into a flat DataFrame.

    JSON shape:
        {
          "status": "SUCCESS",
          "meta": {
              "scheme_name": "...",
              "fund_house":  "...",
              "scheme_code": 125497,
              "scheme_type": "...",
              "scheme_category": "..."
          },
          "data": [
              {"date": "01-01-2024", "nav": "912.4500"},
              ...
          ]
        }
    """
    meta   = data.get("meta", {})
    points = data.get("data", [])

    rows = []
    for pt in points:
        rows.append({
            "scheme_code":     scheme_code,
            "scheme_name":     meta.get("scheme_name", ""),
            "fund_house":      meta.get("fund_house",  ""),
            "scheme_category": meta.get("scheme_category", ""),
            "date":            pt.get("date", ""),
            "nav":             float(pt.get("nav", 0.0)),
        })

    df = pd.DataFrame(rows)

    # Parse date — mfapi returns "DD-MM-YYYY"
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ─────────────────────────────────────────────
# COMBINE ALL SCHEMES
# ─────────────────────────────────────────────
def fetch_all_schemes(schemes: dict) -> pd.DataFrame:
    """
    Fetch (or load cached) NAV data for all schemes.
    Returns a combined DataFrame and saves individual CSVs.
    """
    all_frames = []

    for code, label in schemes.items():
        print(f"\n  [{code}] {label}")
        print(f"  URL: {BASE_URL}/{code}")

        # Try live API first
        data = fetch_nav(code)

        # Fallback to local JSON if live fetch failed
        if data is None:
            print("  ↳ Live fetch failed — loading from cached local JSON …")
            data = load_nav_from_local_json(code)

        if data is None:
            print(f"  ✗  No data available for scheme {code}. Skipping.")
            continue

        source = "live" if data.get("_source") != "cache" else "cache"

        # Save raw JSON
        json_path = os.path.join(RAW_DIR, f"nav_{code}_raw.json")
        if not os.path.exists(json_path):
            with open(json_path, "w") as f:
                json.dump(data, f, indent=2)

        # Parse → DataFrame
        df = parse_nav_response(data, code)

        # Save per-scheme CSV
        csv_path = os.path.join(RAW_DIR, f"nav_{code}_live.csv")
        df.to_csv(csv_path, index=False)

        latest_nav  = df["nav"].iloc[-1]  if not df.empty else "N/A"
        oldest_date = df["date"].iloc[0].strftime("%Y-%m-%d") if not df.empty else "N/A"
        newest_date = df["date"].iloc[-1].strftime("%Y-%m-%d") if not df.empty else "N/A"

        print(f"  ✅ {len(df):>5} records  |  {oldest_date} → {newest_date}  |  Latest NAV: ₹{latest_nav:.4f}")
        print(f"     Saved → {csv_path}")

        all_frames.append(df)

    if not all_frames:
        print("\n  ✗  No data fetched for any scheme.")
        return pd.DataFrame()

    combined = pd.concat(all_frames, ignore_index=True)
    return combined


# ─────────────────────────────────────────────
# ANALYSIS
# ─────────────────────────────────────────────
def analyse_nav_data(df: pd.DataFrame):
    """Print a quick analysis of the combined NAV DataFrame."""
    print(f"\n{'─'*70}")
    print("  Combined NAV Analysis")
    print(f"{'─'*70}")
    print(f"\n  Total records  : {len(df):,}")
    print(f"  Schemes loaded : {df['scheme_code'].nunique()}")
    print(f"  Date range     : {df['date'].min().strftime('%Y-%m-%d')} → {df['date'].max().strftime('%Y-%m-%d')}")

    print("\n  Latest NAV per scheme:")
    latest = (df.sort_values("date")
                .groupby(["scheme_code", "scheme_name"])
                .last()
                .reset_index()[["scheme_code", "scheme_name", "date", "nav"]])
    for _, row in latest.iterrows():
        print(f"    [{row['scheme_code']}] {row['scheme_name'][:45]:<46} ₹{row['nav']:>10.4f}")

    print("\n  1-Year NAV Change (approx):")
    one_year_ago = df["date"].max() - pd.DateOffset(years=1)
    for code in df["scheme_code"].unique():
        sub   = df[df["scheme_code"] == code].sort_values("date")
        end_n = sub["nav"].iloc[-1]
        near  = sub[sub["date"] >= one_year_ago]
        if near.empty:
            continue
        start_n  = near["nav"].iloc[0]
        chg_pct  = (end_n - start_n) / start_n * 100
        arrow    = "▲" if chg_pct >= 0 else "▼"
        name     = sub["scheme_name"].iloc[0][:40]
        print(f"    [{code}] {name:<41}  {arrow} {abs(chg_pct):>6.2f}%")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print(SEPARATOR)
    print("  MUTUAL FUND ANALYTICS — DAY 1: LIVE NAV FETCH")
    print("  live_nav_fetch.py")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEPARATOR)

    print("\n  Target Schemes:")
    for code, label in SCHEMES.items():
        print(f"    {code}  →  {label}")

    # TASK 4 & 5 — Fetch / load all 6 schemes
    print("\n\nFetching NAV data …")
    combined_df = fetch_all_schemes(SCHEMES)

    if combined_df.empty:
        print("No data to process. Exiting.")
        return

    # Save combined CSV
    out_path = os.path.join(PROC_DIR, "all_schemes_nav.csv")
    combined_df.to_csv(out_path, index=False)
    print(f"\n  ✅ Combined NAV saved → {out_path}")
    print(f"     Shape: {combined_df.shape}")

    # Quick analysis
    analyse_nav_data(combined_df)

    print(f"\n{SEPARATOR}")
    print("  Live NAV fetch complete. ✅")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
