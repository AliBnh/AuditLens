# dashboard/app.py
"""
AuditLens — Public Procurement Risk Intelligence Dashboard
Colombia SECOP II | 2019-2022
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config.settings import DATA_PROCESSED

st.set_page_config(
    page_title="AuditLens — Procurement Risk Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_data
def load_contracts():
    df = pd.read_parquet(DATA_PROCESSED / "risk_scores.parquet")
    df["fecha_de_inicio_del_contrato"] = pd.to_datetime(
        df["fecha_de_inicio_del_contrato"], errors="coerce"
    )
    return df

@st.cache_data
def load_leaderboard():
    return pd.read_parquet(DATA_PROCESSED / "agency_leaderboard.parquet")

with st.spinner("Loading data..."):
    df = load_contracts()
    leaderboard = load_leaderboard()

# ── Sidebar ──────────────────────────────────────────────────────
st.sidebar.title("AuditLens")
st.sidebar.caption("Procurement Risk Intelligence")
st.sidebar.divider()

year_min = int(df["year"].min())
year_max = int(df["year"].max())
selected_years = st.sidebar.slider("Year range", year_min, year_max, (year_min, year_max))

selected_sectors = st.sidebar.multiselect(
    "Sector", options=sorted(df["sector"].dropna().unique()), default=[]
)

selected_tiers = st.sidebar.multiselect(
    "Risk tier", options=["High", "Medium", "Low"], default=["High", "Medium", "Low"]
)

selected_dept = st.sidebar.multiselect(
    "Department", options=sorted(df["departamento"].dropna().unique()), default=[]
)

st.sidebar.divider()
st.sidebar.caption("Data: Colombia SECOP II | 2019-2022")
st.sidebar.caption("1.5M contracts analyzed")

# ── Filter ───────────────────────────────────────────────────────
def apply_filters(df, years, sectors, tiers, depts):
    out = df[df["year"].between(years[0], years[1])]
    if tiers:
        out = out[out["risk_tier"].isin(tiers)]
    if sectors:
        out = out[out["sector"].isin(sectors)]
    if depts:
        out = out[out["departamento"].isin(depts)]
    return out

filtered = apply_filters(df, selected_years, selected_sectors, selected_tiers, selected_dept)

# ── Tabs ─────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🌐 National Overview",
    "🏛️ Agency Drill-Down",
    "📄 Contract Explorer",
    "📖 Methodology"
])

# ════════════════════════════════════════════════════════════════
# TAB 1 — NATIONAL OVERVIEW
# ════════════════════════════════════════════════════════════════
with tab1:
    st.title("🔍 AuditLens — Procurement Risk Intelligence")
    st.caption("Detecting value-leakage signals in Colombian government contracting")
    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Contracts Analyzed", f"{len(filtered):,}")
    col2.metric("Total Spend", f"${filtered['valor_del_contrato'].sum()/1e12:.1f}T COP")
    col3.metric("High-Risk Contracts", f"{(filtered['risk_tier']=='High').sum():,}")
    col4.metric("Direct Award Rate", f"{filtered['is_direct'].mean()*100:.1f}%")

    st.divider()
    col_left, col_right = st.columns(2)

    with col_left:
        tier_counts = filtered["risk_tier"].value_counts().reset_index()
        tier_counts.columns = ["Risk Tier", "Count"]
        tier_counts["Risk Tier"] = pd.Categorical(
            tier_counts["Risk Tier"], categories=["High", "Medium", "Low"], ordered=True
        )
        tier_counts = tier_counts.sort_values("Risk Tier")
        fig = px.bar(
            tier_counts, x="Risk Tier", y="Count",
            color="Risk Tier",
            color_discrete_map={"High": "#e74c3c", "Medium": "#f39c12", "Low": "#3498db"},
            title="Contract Risk Tier Distribution"
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        yoy = filtered.groupby("year").agg(
            contracts=("id_contrato", "count"),
            direct_rate=("is_direct", "mean")
        ).reset_index()
        fig = px.line(
            yoy, x="year", y="direct_rate", markers=True,
            title="Direct Award Rate by Year",
            labels={"direct_rate": "Direct Award Rate", "year": "Year"}
        )
        fig.update_yaxes(tickformat=".0%")
        fig.update_traces(line_color="#e74c3c", line_width=2)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 Agencies by Value at Risk")
    lb_filtered = leaderboard.copy()
    if selected_sectors:
        lb_filtered = lb_filtered[lb_filtered["sector"].isin(selected_sectors)]
    if selected_dept:
        lb_filtered = lb_filtered[lb_filtered["departamento"].isin(selected_dept)]

    top10 = lb_filtered.nlargest(10, "value_at_risk").copy()
    top10["value_at_risk_B"] = top10["value_at_risk"] / 1e9
    top10["label"] = top10["codigo_entidad"].astype(str) + " | " + top10["sector"]
    fig = px.bar(
        top10.sort_values("value_at_risk_B"),
        x="value_at_risk_B", y="label", orientation="h",
        color="mean_calibrated_score", color_continuous_scale="Reds",
        title="Top 10 Agencies by Estimated Value at Risk (Billion COP)",
        labels={"value_at_risk_B": "Value at Risk (B COP)", "label": "Agency"}
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Risk Distribution by Sector")
    sector_risk = filtered.groupby(["sector", "risk_tier"]).size().reset_index(name="count")
    fig = px.bar(
        sector_risk, x="sector", y="count", color="risk_tier",
        color_discrete_map={"High": "#e74c3c", "Medium": "#f39c12", "Low": "#3498db"},
        title="Contract Count by Sector and Risk Tier",
        labels={"count": "Contracts", "sector": "Sector", "risk_tier": "Risk Tier"}
    )
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════
# TAB 2 — AGENCY DRILL-DOWN
# ════════════════════════════════════════════════════════════════
with tab2:
    st.title("🏛️ Agency Drill-Down")
    st.caption("Select an agency to explore its risk profile in detail")

    agency_options = sorted(filtered["codigo_entidad"].unique())
    if not agency_options:
        st.warning("No agencies match current filters.")
    else:
        selected_agency = st.selectbox(
            "Select Agency",
            options=agency_options,
            format_func=lambda x: f"{x} | {filtered[filtered['codigo_entidad']==x]['sector'].iloc[0] if len(filtered[filtered['codigo_entidad']==x]) > 0 else ''}",
            index=0
        )

        agency_df = filtered[filtered["codigo_entidad"] == selected_agency]

        if len(agency_df) == 0:
            st.warning("No contracts found for this agency.")
        else:
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Contracts", f"{len(agency_df):,}")
            col2.metric("Total Spend", f"{agency_df['valor_del_contrato'].sum()/1e9:.1f}B COP")
            col3.metric("Mean Risk Score", f"{agency_df['risk_score_calibrated'].mean():.3f}")
            col4.metric("High-Risk Contracts", f"{(agency_df['risk_tier']=='High').sum():,}")

            col_left, col_right = st.columns(2)

            with col_left:
                tier_counts = agency_df["risk_tier"].value_counts().reset_index()
                tier_counts.columns = ["Risk Tier", "Count"]
                fig = px.pie(
                    tier_counts, names="Risk Tier", values="Count",
                    color="Risk Tier",
                    color_discrete_map={"High": "#e74c3c", "Medium": "#f39c12", "Low": "#3498db"},
                    title="Risk Tier Breakdown"
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_right:
                vendor_spend = agency_df.groupby("codigo_proveedor")["valor_del_contrato"].sum()
                vendor_spend = vendor_spend.nlargest(8).reset_index()
                vendor_spend.columns = ["Vendor", "Spend"]
                vendor_spend["Spend_B"] = vendor_spend["Spend"] / 1e9
                fig = px.bar(
                    vendor_spend.sort_values("Spend_B"),
                    x="Spend_B", y="Vendor", orientation="h",
                    title="Top Vendors by Spend (B COP)",
                    labels={"Spend_B": "Spend (B COP)", "Vendor": "Vendor ID"}
                )
                st.plotly_chart(fig, use_container_width=True)

            monthly_risk = agency_df.groupby(
                agency_df["fecha_de_inicio_del_contrato"].dt.to_period("M")
            )["risk_score_calibrated"].mean().reset_index()
            monthly_risk["fecha"] = monthly_risk["fecha_de_inicio_del_contrato"].astype(str)
            fig = px.line(
                monthly_risk, x="fecha", y="risk_score_calibrated",
                title="Mean Risk Score Over Time",
                labels={"risk_score_calibrated": "Mean Risk Score", "fecha": "Month"}
            )
            fig.update_traces(line_color="#e74c3c")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("High-Risk Contracts")
            high_risk = agency_df[agency_df["risk_tier"] == "High"][[
                "id_contrato", "codigo_proveedor", "valor_del_contrato",
                "risk_score_calibrated", "process_anomaly_score",
                "splitting_score", "network_score", "risk_tier"
            ]].sort_values("risk_score_calibrated", ascending=False).head(50)

            if len(high_risk) == 0:
                st.info("No High-risk contracts for this agency with current filters.")
            else:
                st.dataframe(high_risk.reset_index(drop=True), use_container_width=True)


# ════════════════════════════════════════════════════════════════
# TAB 3 — CONTRACT EXPLORER
# ════════════════════════════════════════════════════════════════
with tab3:
    st.title("📄 Contract Explorer")
    st.caption("Search and filter all scored contracts")

    col1, col2, col3 = st.columns(3)
    with col1:
        search_vendor = st.text_input("Filter by Vendor ID", "")
    with col2:
        search_agency = st.text_input("Filter by Agency ID", "")
    with col3:
        min_risk = st.slider("Minimum risk score", 0.0, 1.0, 0.0, 0.01)

    # Build mask without copying full dataframe
    mask = df["year"].between(selected_years[0], selected_years[1])
    if selected_tiers:
        mask &= df["risk_tier"].isin(selected_tiers)
    if selected_sectors:
        mask &= df["sector"].isin(selected_sectors)
    if selected_dept:
        mask &= df["departamento"].isin(selected_dept)
    if search_vendor.strip():
        mask &= df["codigo_proveedor"].astype(str).str.contains(search_vendor.strip(), na=False)
    if search_agency.strip():
        mask &= df["codigo_entidad"].astype(str).str.contains(search_agency.strip(), na=False)
    if min_risk > 0:
        mask &= df["risk_score_calibrated"] >= min_risk

    display_cols = [
        "id_contrato", "codigo_entidad", "codigo_proveedor",
        "valor_del_contrato", "year", "sector",
        "risk_tier", "risk_score_calibrated",
        "process_anomaly_score", "splitting_score", "network_score",
        "is_direct", "is_modified"
    ]
    available_cols = [c for c in display_cols if c in df.columns]

    result = (
        df.loc[mask, available_cols]
        .sort_values("risk_score_calibrated", ascending=False)
        .head(200)
        .reset_index(drop=True)
    )

    st.caption(f"Showing {len(result):,} of {mask.sum():,} matching contracts")

    if len(result) == 0:
        st.warning("No contracts match the current filters.")
    else:
        st.dataframe(result, width="stretch")
        csv = result.to_csv(index=False)
        st.download_button(
            label="⬇️ Export as CSV",
            data=csv,
            file_name="auditlens_contracts.csv",
            mime="text/csv"
        )
# ════════════════════════════════════════════════════════════════
# TAB 4 — METHODOLOGY
# ════════════════════════════════════════════════════════════════
with tab4:
    st.title("📖 Methodology")
    st.divider()

    st.markdown("""
    ## What AuditLens Does

    AuditLens analyzes 1.5 million Colombian government contracts from SECOP II
    (2019–2022) to identify procurement patterns associated with value leakage —
    structural inefficiencies that cost governments money without necessarily
    involving explicit corruption.

    ## What the Risk Score Means

    Each contract receives a **composite risk score** between 0 and 1.
    A score of 0.85 means the contract is in the High-risk tier.
    Scores range: High (0.75–0.90), Medium (0.45–0.60), Low (0.15–0.30).

    **This score is not a fraud label.** It is an audit prioritization tool.

    ## The Three Sub-Scores

    ### 1. Process Anomaly Score
    Combines Isolation Forest and HBOS anomaly detection on 25 behavioral features
    including contract duration, vendor history, agency concentration, and timing
    patterns. Captures contracts that are unusual relative to their peer group.

    ### 2. Splitting Score
    Detects vendors receiving multiple contracts just below statutory audit thresholds
    within rolling 30, 60, and 90-day windows. Flags 764 suspicious vendor-agency
    pairs covering 7.2% of national spend.

    ### 3. Network Concentration Score
    Measures vendor-agency relationship concentration using a bipartite graph.
    Flags 692 agencies routing disproportionate spend to single vendors.

    ## Proxy Labels

    Ground truth fraud labels do not exist at scale in public procurement.
    AuditLens uses **auditor-endorsed proxy signals**:
    - **Strong proxy**: Direct award AND contract modified (15.8% base rate)

    These are structural risk indicators, not fraud labels.

    ## Key Results

    - **Precision@K (tier-aware)**: 24.0% vs 15.6% random = 1.54x lift
    - **Predictive ratio**: 1.48x — high-risk agencies show higher modification rates
    - **Temporal validation**: Model improves on 2022 holdout data

    ## Limitations

    - Scores reflect risk patterns, not confirmed wrongdoing
    - Small agencies (<20 contracts) have less reliable scores
    - COVID-era contracts (2020) reflect emergency procurement conditions
    - Contract duration features show drift in 2022 — monitor monthly
    - The word "fraud" does not appear in this system by design

    ## Ethical Framing

    | Intended use ✅ | Prohibited use ❌ |
    |---|---|
    | Audit prioritization | Individual accusation |
    | Resource allocation | Automated enforcement |
    | Pattern analysis | Public disclosure of vendors as fraudulent |
    | Policy research | Legal proceedings without further investigation |

    ## Data Source

    Colombia SECOP II — Contratos Electrónicos
    [datos.gov.co](https://www.datos.gov.co/resource/jbjy-vk9h.json)
    Updated daily · Open access · No credentials required
    """)