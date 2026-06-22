# Mutual Fund Analytics Project

End-to-end mutual fund data pipeline: ingestion → SQL → analysis → dashboard.

## Structure
```
mutual_fund_analysis/
├── data/
│   ├── raw/           # Source CSVs + live NAV JSON files
│   └── processed/     # Cleaned, validated outputs
├── notebooks/         # Exploratory analysis notebooks
├── sql/               # Schema definitions and queries
├── dashboard/         # Plotly / Dash dashboard code
├── reports/           # Generated PDF / HTML reports
├── data_ingestion.py  # Day 1: Load all 10 datasets, validate, explore
├── live_nav_fetch.py  # Day 1: Fetch live NAV from mfapi.in
└── requirements.txt
```

## Quick Start
```bash
pip install -r requirements.txt
python data_ingestion.py    # Task 3, 6, 7
python live_nav_fetch.py    # Task 4, 5
```

## Data Sources
- **mfapi.in** — Free AMFI NAV API (`GET https://api.mfapi.in/mf/{scheme_code}`)
- **10 CSV datasets** — fund_master, nav_history, portfolio_holdings, sip_transactions,
  investor_profile, benchmark_index, expense_ratio, returns_summary, dividend_history, amc_info

## Key Schemes Tracked
| Code   | Scheme                              |
|--------|-------------------------------------|
| 125497 | HDFC Top 100 Direct                 |
| 119551 | SBI Bluechip Direct                 |
| 120503 | ICICI Prudential Bluechip Direct    |
| 118632 | Nippon India Large Cap Direct       |
| 119092 | Axis Bluechip Direct                |
| 120841 | Kotak Bluechip Direct               |
