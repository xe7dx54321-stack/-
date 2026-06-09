"""Visual Command Center - Streamlit App."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import streamlit as st
from worldcup_campaign.visual_command_center import build_visual_snapshot, render_visual_json

st.set_page_config(page_title="WorldCup Campaign Command Center", layout="wide")

# Safety banner
st.markdown("""
<div style="background:#1a3a1a;border:2px solid #2d5a2d;padding:10px 20px;border-radius:8px;margin-bottom:20px">
<span style="color:#4caf50;font-weight:bold;margin-right:20px">ANALYSIS ONLY</span>
<span style="color:#4caf50;font-weight:bold;margin-right:20px">SIMULATION ONLY</span>
<span style="color:#4caf50;font-weight:bold;margin-right:20px">NOT BETTING ADVICE</span>
<span style="color:#4caf50;font-weight:bold">REAL MONEY EXECUTION: FALSE</span>
</div>
""", unsafe_allow_html=True)

st.title("WorldCup Campaign - Visual Command Center")

snap = build_visual_snapshot()

# Sidebar
with st.sidebar:
    st.header("Controls")
    if st.button("Refresh Data"):
        st.rerun()
    st.metric("Sources Available", snap.artifact_source_count)
    st.caption("Local URL: " + snap.local_url)

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Today", "Candidates", "Reviews", "Bankroll", "Freeze"])

with tab1:
    if snap.status_summary:
        ss = snap.status_summary
        cols = st.columns(len(ss.status_cards))
        for i, card in enumerate(ss.status_cards):
            with cols[i]:
                color_map = {"green":"#1a3a1a","yellow":"#3a3a1a","orange":"#3a2a1a","red":"#3a1a1a","gray":"#2a2a2a"}
                bg = color_map.get(card.color, "#2a2a2a")
                st.markdown(f'<div style="background:{bg};padding:12px;border-radius:8px;text-align:center"><small>{card.label}</small><br><b>{card.status}</b></div>', unsafe_allow_html=True)
    st.metric("Overall Status", ss.overall_status if snap.status_summary else "N/A")

with tab2:
    if snap.candidate_summary:
        cs = snap.candidate_summary
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total", cs.candidate_count)
        c2.metric("Core", cs.core_count)
        c3.metric("Edge", cs.edge_count)
        c4.metric("Attack", cs.attack_count)
        st.dataframe([{
            "Match": c.match_id, "Market": c.market_type, "Selection": c.selection_label,
            "Bucket": c.bucket, "Score": f"{c.campaign_score:.3f}", "Budget": c.simulation_budget_preview
        } for c in cs.candidate_cards[:50]], use_container_width=True)
    else:
        st.info("No candidate data available")

with tab3:
    if snap.review_summary:
        rs = snap.review_summary
        st.metric("Total Reviews", rs.review_count)
        st.dataframe([{
            "ID": r.review_id, "Type": r.review_type, "Severity": r.severity,
            "Reason": r.reason, "Status": r.status
        } for r in rs.review_cards[:50]], use_container_width=True)
    else:
        st.info("No review data available")

with tab4:
    if snap.bankroll_series and snap.bankroll_series.point_count > 0:
        import pandas as pd
        df = pd.DataFrame({"date": snap.bankroll_series.dates, "bankroll": snap.bankroll_series.values})
        st.line_chart(df.set_index("date"))
    else:
        st.info("No bankroll data available")

with tab5:
    st.json(render_visual_json(snap))

st.markdown("---")
st.caption("Simulation/analysis only. Not betting advice. real_money_execution_ready=false.")
