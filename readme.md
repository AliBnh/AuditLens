# 🔍 AuditLens — Procurement Risk Intelligence

> Detecting value-leakage signals in 1.55 million Colombian government contracts using anomaly detection, contract splitting analysis, vendor network graph analytics, and community detection.

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.54-red)](https://streamlit.io)
[![Data](https://img.shields.io/badge/Data-SECOP%20II%20Colombia-green)](https://www.datos.gov.co/resource/jbjy-vk9h.json)
[![Contracts](https://img.shields.io/badge/Contracts%20Analyzed-1.55M-orange)]()
[![Spend](https://img.shields.io/badge/Spend%20Analyzed-406T%20COP-purple)]()

---

## What This Is

AuditLens is a procurement risk scoring system built on Colombia's SECOP II dataset — the national electronic contracting platform with 1.55 million contracts and 406 trillion COP (~$100B USD) in spend from 2019-2022.

The system scores every contract across three independent risk dimensions and produces a ranked agency exposure leaderboard that tells auditors **where to look first**. This is exactly the class of tool that consulting firms charge EUR 500,000+ to deliver for government clients.

**It is not a fraud detector. It is an audit prioritization engine.**

---

## Headline Numbers

| Metric                     | Value                                             |
| -------------------------- | ------------------------------------------------- |
| Contracts analyzed         | 1,553,594                                         |
| Total spend analyzed       | 406 trillion COP (~$100B USD)                     |
| Direct award rate          | 89% — 9 in 10 contracts non-competitive           |
| High-risk contracts        | 621,437 (40% of portfolio)                        |
| Suspicious splitting pairs | 764 vendor-agency pairs, 7.2% of national spend   |
| Concentrated agencies      | 692 agencies with majority spend to single vendor |
| Vendor communities detected| 127 communities via Louvain algorithm             |
| Estimated value at risk    | 98.5 trillion COP                                 |
| Precision@K lift (top 5%)  | 1.54x above random selection                      |
| Precision@K lift (top 10%) | 1.93x above random selection                      |
| Permutation test Z-score   | 62.9 — lift is statistically real                 |

---

## The Three Risk Signals

### 1. Process Anomaly Score (60% weight)

Isolation Forest + HBOS ensemble trained on 25 behavioral features per contract. Detects contracts that are structurally unusual relative to their peer group — unusual duration, value, vendor behavior, or agency concentration patterns. Models trained on 2019-2021 data only; scored blind on 2022.

**Key Features:**
- Temporal features: contract duration, signature lag, Q4 rush patterns
- Value features: log contract value, extreme value flags
- Behavioral features: direct award, post-award modification, vendor/agency rates
- Concentration metrics: HHI, top vendor share, vendor diversity

### 2. Contract Splitting Score (25% weight)

Rule-based rolling window detector. Flags vendor-agency pairs that award multiple contracts just below Colombia's statutory audit thresholds (SMMLV-denominated) within 30, 60, and 90-day windows. Found 764 suspicious pairs covering 12,487 contracts and 7.2% of national spend — within the 5-15% range reported in the procurement audit literature.

**Detection Logic:**
- Monitors contracts within 10% below SMMLV thresholds
- Rolling windows: 30, 60, 90 days
- Accounts for year-over-year SMMLV adjustments
- Flags vendor-agency pairs, not individual contracts

### 3. Network Concentration Score (15% weight)

Bipartite vendor-agency graph (194,477 vendor nodes, 1,705 agency nodes) analyzed using PageRank, Herfindahl-Hirschman Index, and Louvain community detection. Found 692 agencies routing majority spend to a single vendor. In a healthy competitive market this rate should be below 20%.

**Graph Analytics:**
- **PageRank:** Identifies influential vendors in the network
- **HHI:** Measures market concentration per agency
- **Louvain Community Detection:** Discovers 127 tightly-connected vendor clusters
- **Preferential Attachment:** Flags contracts with disproportionate vendor-agency coupling

Community detection reveals hidden collusion patterns — vendors operating as coordinated groups across agencies that appear independent on the surface.

---

## Risk Tiers

Tiers are assigned based on empirical proxy label rates, not arbitrary percentile cutoffs:

| Tier   | Proxy Label Rate | Contracts | Share | Score Range |
| ------ | ---------------- | --------- | ----- | ----------- |
| High   | 35.6%            | 621,437   | 40%   | 0.75 – 0.90 |
| Medium | 13.0%            | 155,360   | 10%   | 0.45 – 0.60 |
| Low    | 0.1%             | 776,797   | 50%   | 0.15 – 0.30 |

Tier ordering is monotonically correct: High > Medium > Low by proxy rate and by calibrated score.

---

## Model Validation

| Test                        | Result                                                    | Interpretation                                                    |
| --------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------- |
| Out-of-time holdout (2022)  | Precision@K improves 13.3% → 15.5%                        | No temporal overfitting                                           |
| Permutation test (100 runs) | Z-score = 62.9                                            | Lift is statistically real                                        |
| Cross-year stability        | 1.72-1.97x lift in 2020, 2021, 2022                       | Consistent across time                                            |
| Predictive ratio            | 1.48x                                                     | High-risk agencies show higher modification rates in holdout year |
| Core signal drift (PSI)     | is_direct = 0.000, is_modified = 0.000, splitting = 0.000 | Fundamental signals are time-stable                               |

---

## Project Structure

```
AuditLens/
├── config/
│   └── settings.py              # All constants, thresholds, SMMLV values, risk weights
├── data/
│   ├── raw/secop_raw.parquet    # 1.55M contracts from API (gitignored)
│   └── processed/               # Feature matrix, scores, leaderboard (gitignored)
├── notebooks/
│   ├── 01_ingest_quality.ipynb  # Schema audit, null analysis, quality checks
│   ├── 02_eda.ipynb             # 8 charts, 6 key findings
│   ├── 03_feature_engineering.ipynb  # 45 features, zero nulls
│   ├── 04_anomaly_detection.ipynb    # IsoForest + HBOS ensemble
│   ├── 05_splitting_detection.ipynb  # 764 suspicious pairs
│   ├── 06_network_analysis.ipynb     # Graph analysis + Louvain communities
│   ├── 07_risk_index.ipynb           # Composite score, tier assignment
│   └── 08_temporal_validation.ipynb  # PSI drift, Precision@K holdout
├── src/
│   └── ingest/secop_client.py   # Paginated Socrata API client
├── dashboard/
│   └── app.py                   # Streamlit — 4 tabs
└── outputs/
    ├── charts/                  # 12 publication-quality PNG visualizations
    └── tables/                  # agency_exposure.csv, psi_drift_report.csv, community_stats.csv
```

---

## Quickstart

**Requirements:** Python 3.10+, ~4GB RAM

```bash
git clone https://github.com/your-username/AuditLens.git
cd AuditLens
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

**Run the dashboard** (requires processed data files):

```bash
streamlit run dashboard/app.py
```

**Re-run the full pipeline** (takes ~90 minutes, requires API access):

```bash
jupyter nbconvert --to notebook --execute notebooks/01_ingest_quality.ipynb
jupyter nbconvert --to notebook --execute notebooks/02_eda.ipynb
jupyter nbconvert --to notebook --execute notebooks/03_feature_engineering.ipynb
jupyter nbconvert --to notebook --execute notebooks/04_anomaly_detection.ipynb
jupyter nbconvert --to notebook --execute notebooks/05_splitting_detection.ipynb
jupyter nbconvert --to notebook --execute notebooks/06_network_analysis.ipynb
jupyter nbconvert --to notebook --execute notebooks/07_risk_index.ipynb
jupyter nbconvert --to notebook --execute notebooks/08_temporal_validation.ipynb
```

---

## Data Source

**Colombia SECOP II** — Sistema Electronico de Contratacion Publica II
Open data, no credentials required.
API: `https://www.datos.gov.co/resource/jbjy-vk9h.json`
Updated daily. Pull filtered to `valor_del_contrato > 0` and date range 2019-2022.

---

## Dashboard

Four tabs:

- **National Overview** — 4 KPI metrics, risk tier distribution, direct award rate trend, top 10 agencies by value at risk
- **Agency Drill-Down** — Per-agency risk profile: tier breakdown, top vendors, monthly risk score trend, high-risk contracts table
- **Contract Explorer** — Searchable and filterable table of all 1.55M scored contracts with CSV export
- **Methodology** — Plain-language explanation of all scoring components and ethical framing

---

## Key Methodological Decisions

**Why proxy labels instead of fraud labels?**
No contracts in SECOP II are officially labeled as fraudulent. The strong proxy — direct award AND post-award modification — is an auditor-endorsed compound risk signal with a 15.8% base rate consistent with the procurement audit literature.

**Why two anomaly detectors instead of one?**
Isolation Forest and HBOS have structurally different failure modes. Their 59.4% top-5% overlap means each independently flags ~30,000 contracts the other misses. The rank-average ensemble reduces false positives compared to either model alone.

**Why tier-aware ranking?**
Empirical analysis revealed a non-monotonic relationship between raw anomaly scores and proxy labels — extreme outliers (top 10%) score highest numerically but have lower proxy rates than the 50th-90th percentile zone. Tier-aware ranking correctly surfaces the proxy-aligned High tier first, achieving 1.54x precision lift versus 1.00x for raw score ranking.

**Why PSI instead of KS test for drift monitoring?**
PSI has established industry thresholds (stable < 0.10, monitor 0.10-0.20, retrain > 0.20) that are interpretable by non-statisticians. The KS test produces a binary p-value with no actionable business meaning.

**Why Louvain for community detection?**
Louvain maximizes modularity to discover naturally-occurring vendor clusters. Unlike k-means, it doesn't require specifying the number of communities upfront and handles the bipartite graph structure natively. The 127 communities detected reveal coordinated bidding patterns invisible to bilateral analysis.

---

## Honest Limitations

- **Cramer's V = 0.04** between anomaly scores and proxy labels. This is expected — behavioral outliers and structural risk flags measure complementary phenomena, not the same thing.
- **2019 cross-year lift = 0.50x** — below random. Pre-COVID procurement had a structurally different proxy rate (21.3% vs ~15% in later years), creating a distribution mismatch with tier thresholds calibrated on the full dataset.
- **Two features drift in 2022** — contract duration and signature lag (PSI > 0.40). Post-COVID normalization of timelines. In production these would use rolling 12-month baselines. Core signals (is_direct, is_modified, splitting) are stable at PSI = 0.000.
- **No ground truth labels exist.** All findings are audit prioritization signals, not determinations of wrongdoing.
- **Community detection is descriptive, not predictive.** Louvain identifies structural patterns but does not prove collusion — manual investigation required.

---

## Ethical Framing

AuditLens tells auditors **where to look first**. It does not accuse vendors, confirm fraud, or replace human judgment. The word "fraud" appears nowhere in the codebase, scores, or dashboard by design.

**Intended use:** audit prioritization, resource allocation, policy research.
**Prohibited use:** individual accusation, automated enforcement, public disclosure of vendor names as fraudulent.

---

## V2 Roadmap

- [ ] Price benchmarking regressor (XGBoost on log contract value)
- [ ] TF-IDF category normalization (spaCy Spanish + KMeans)
- [x] Graph community detection (Louvain algorithm) — **COMPLETED**
- [ ] SHAP per-contract explainability waterfall charts
- [ ] Incremental API ingestion with weekly PSI monitoring
- [ ] Time-series anomaly detection on agency spending patterns
- [ ] Geographic clustering analysis by departamento

---

## Tech Stack

`Python 3.13` · `pandas` · `scikit-learn` · `pyod` · `networkx` · `python-louvain` · `plotly` · `streamlit` · `pyarrow` · `scipy` · `numpy`

---

## Citation

If you use this methodology in academic or policy research, please cite:

```
AuditLens: Procurement Risk Intelligence for SECOP II Colombia (2024)
https://github.com/your-username/AuditLens
```

---

## License

MIT License — See LICENSE file for details.

**Disclaimer:** This is a research prototype. Production deployment requires legal review, stakeholder consultation, and formal validation by domain experts.
