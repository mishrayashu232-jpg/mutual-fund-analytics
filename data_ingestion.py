"""
data_ingestion.py
=================
Day 1 — Mutual Fund Analytics Project
Tasks: Load all 10 CSV datasets, inspect structure, validate AMFI codes,
       explore fund master metadata, and summarise data quality.

Run:  python data_ingestion.py
"""

import os
import sys
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
RAW_DIR  = os.path.join("data", "raw")
PROC_DIR = os.path.join("data", "processed")
os.makedirs(PROC_DIR, exist_ok=True)

DATASETS = {
    "fund_master":        "fund_master.csv",
    "nav_history":        "nav_history.csv",
    "portfolio_holdings": "portfolio_holdings.csv",
    "sip_transactions":   "sip_transactions.csv",
    "investor_profile":   "investor_profile.csv",
    "benchmark_index":    "benchmark_index.csv",
    "expense_ratio":      "expense_ratio.csv",
    "returns_summary":    "returns_summary.csv",
    "dividend_history":   "dividend_history.csv",
    "amc_info":           "amc_info.csv",
}

SEPARATOR = "=" * 70


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def section(title: str):
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def load_datasets(datasets: dict, raw_dir: str) -> dict[str, pd.DataFrame]:
    """Load every CSV in DATASETS; return a dict of DataFrames."""
    frames = {}
    anomaly_log = []

    for name, filename in datasets.items():
        path = os.path.join(raw_dir, filename)
        section(f"[{name.upper()}]  ← {filename}")

        if not os.path.exists(path):
            print(f"  ⚠  FILE NOT FOUND: {path}")
            continue

        df = pd.read_csv(path)
        frames[name] = df

        # ── shape ──
        print(f"\n  Shape   : {df.shape[0]:,} rows × {df.shape[1]} columns")

        # ── dtypes ──
        print("\n  dtypes:")
        for col, dtype in df.dtypes.items():
            nulls = df[col].isna().sum()
            null_info = f"  ({nulls:,} nulls)" if nulls else ""
            print(f"    {col:<35} {str(dtype):<12}{null_info}")

        # ── head ──
        print("\n  head(3):")
        print(df.head(3).to_string(index=False))

        # ── anomalies ──
        issues = _detect_anomalies(df, name)
        if issues:
            print(f"\n  ⚠  Anomalies detected:")
            for iss in issues:
                print(f"     • {iss}")
                anomaly_log.append({"dataset": name, "issue": iss})
        else:
            print("\n  ✅ No obvious anomalies detected.")

    return frames, anomaly_log


def _detect_anomalies(df: pd.DataFrame, name: str) -> list[str]:
    """Return a list of anomaly strings for the given DataFrame."""
    issues = []

    # Generic: null counts
    null_cols = df.columns[df.isnull().any()].tolist()
    if null_cols:
        for col in null_cols:
            pct = df[col].isna().mean() * 100
            issues.append(f"Column '{col}' has {df[col].isna().sum():,} nulls ({pct:.1f}%)")

    # Generic: duplicate rows
    dupes = df.duplicated().sum()
    if dupes:
        issues.append(f"{dupes:,} fully duplicate rows")

    # Dataset-specific checks
    if name == "portfolio_holdings":
        bad_w = df[df["weight_pct"] > 100]
        if not bad_w.empty:
            issues.append(f"weight_pct > 100 in {len(bad_w)} row(s) — impossible allocation")

    if name == "investor_profile":
        bad_age = df[df["age"] == 0]
        if not bad_age.empty:
            issues.append(f"age == 0 for {len(bad_age)} investor(s) — likely bad data")

    if name == "returns_summary":
        neg_5y = df[df["returns_5y"] < -50] if "returns_5y" in df.columns else pd.DataFrame()
        if not neg_5y.empty:
            issues.append(f"returns_5y < -50% for {len(neg_5y)} fund(s) — verify")

    if name == "nav_history":
        if "nav" in df.columns:
            neg_nav = df[df["nav"] <= 0]
            if not neg_nav.empty:
                issues.append(f"NAV ≤ 0 for {len(neg_nav)} record(s)")

    return issues


# ─────────────────────────────────────────────
# TASK 6 — EXPLORE FUND MASTER
# ─────────────────────────────────────────────
def explore_fund_master(df: pd.DataFrame):
    section("TASK 6 — Fund Master Exploration")

    print("\n  Unique Fund Houses:")
    for fh in sorted(df["fund_house"].unique()):
        n = df[df["fund_house"] == fh].shape[0]
        print(f"    {fh:<35} {n:>3} schemes")

    print("\n  Unique Categories:")
    for cat in sorted(df["category"].unique()):
        n = df[df["category"] == cat].shape[0]
        print(f"    {cat:<25} {n:>3} schemes")

    print("\n  Sub-categories:")
    for sub in sorted(df["sub_category"].unique()):
        print(f"    • {sub}")

    print("\n  Risk Grades:")
    for risk, cnt in df["risk_grade"].value_counts().items():
        bar = "█" * (cnt // 2)
        print(f"    {risk:<25} {cnt:>3}  {bar}")

    print("\n  AMFI Scheme Code Structure:")
    codes = df["amfi_code"].sort_values()
    print(f"    Range  : {codes.min()} → {codes.max()}")
    print(f"    Count  : {codes.nunique()} unique codes")
    print(f"    Format : 6-digit numeric (e.g. {codes.iloc[0]}, {codes.iloc[1]}, ...)")
    print("    Note   : Codes are assigned sequentially by AMFI on registration.")
    print("             Direct plans typically have higher codes than Regular plans.")


# ─────────────────────────────────────────────
# TASK 7 — VALIDATE AMFI CODES
# ─────────────────────────────────────────────
def validate_amfi_codes(fund_master: pd.DataFrame, nav_history: pd.DataFrame) -> pd.DataFrame:
    section("TASK 7 — AMFI Code Validation (fund_master ↔ nav_history)")

    master_codes = set(fund_master["amfi_code"].unique())
    nav_codes    = set(nav_history["amfi_code"].unique())

    in_both         = master_codes & nav_codes
    only_in_master  = master_codes - nav_codes
    only_in_nav     = nav_codes    - master_codes

    print(f"\n  fund_master  unique codes : {len(master_codes):>5}")
    print(f"  nav_history  unique codes : {len(nav_codes):>5}")
    print(f"  Codes in BOTH             : {len(in_both):>5}  ✅")
    print(f"  In master, NOT in nav     : {len(only_in_master):>5}  {'⚠' if only_in_master else '✅'}")
    print(f"  In nav, NOT in master     : {len(only_in_nav):>5}  {'⚠' if only_in_nav else '✅'}")

    coverage = len(in_both) / len(master_codes) * 100 if master_codes else 0
    print(f"\n  Coverage rate             : {coverage:.1f}%")

    # Build quality summary
    summary = pd.DataFrame([
        {"check": "fund_master unique codes",              "value": len(master_codes), "status": "INFO"},
        {"check": "nav_history unique codes",              "value": len(nav_codes),    "status": "INFO"},
        {"check": "AMFI code coverage (master in nav)",    "value": f"{coverage:.1f}%","status": "PASS" if coverage == 100 else "WARN"},
        {"check": "Codes missing from nav_history",        "value": len(only_in_master),"status": "PASS" if not only_in_master else "WARN"},
        {"check": "Orphan codes in nav_history",           "value": len(only_in_nav),  "status": "PASS" if not only_in_nav else "WARN"},
    ])

    print("\n  Data Quality Summary:")
    print(summary.to_string(index=False))

    out_path = os.path.join("data", "processed", "data_quality_summary.csv")
    summary.to_csv(out_path, index=False)
    print(f"\n  ✅ Quality summary saved → {out_path}")

    return summary


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print(SEPARATOR)
    print("  MUTUAL FUND ANALYTICS — DAY 1: DATA INGESTION")
    print("  data_ingestion.py")
    print(SEPARATOR)

    # TASKS 3 — Load all datasets
    section("TASKS 3 — Loading 10 CSV Datasets")
    frames, anomaly_log = load_datasets(DATASETS, RAW_DIR)

    if len(frames) < len(DATASETS):
        print(f"\n  ⚠  Only {len(frames)}/{len(DATASETS)} datasets loaded. Check data/raw/.")
    else:
        print(f"\n  ✅ All {len(frames)} datasets loaded successfully.")

    # TASK 6 — Fund Master exploration
    if "fund_master" in frames:
        explore_fund_master(frames["fund_master"])

    # TASK 7 — AMFI code validation
    if "fund_master" in frames and "nav_history" in frames:
        validate_amfi_codes(frames["fund_master"], frames["nav_history"])

    # Overall anomaly recap
    section("ANOMALY RECAP")
    if anomaly_log:
        recap = pd.DataFrame(anomaly_log)
        print(recap.to_string(index=False))
        recap.to_csv(os.path.join("data", "processed", "anomaly_log.csv"), index=False)
        print(f"\n  Anomaly log saved → data/processed/anomaly_log.csv")
    else:
        print("  ✅ No anomalies detected across all datasets.")

    print(f"\n{SEPARATOR}")
    print("  Day 1 data ingestion complete. ✅")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
