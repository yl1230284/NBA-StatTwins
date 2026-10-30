"""
NBA Player Vector Similarity & Comparison Dashboard (Streamlit App)
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from similarity_engine import NBASimilarityEngine, normalize_player_name
from update_season_stats import get_sync_metadata, update_season

st.set_page_config(
    page_title="NBA Player Vector Similarity & Comparison Tool",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme styling & metric non-truncation
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 800; color: #10B981; margin-bottom: 0px; }
    .sub-title { font-size: 1.1rem; color: #9CA3AF; margin-bottom: 20px; }
    .target-card { background: linear-gradient(135deg, #1F2937 0%, #111827 100%); border-radius: 14px; padding: 20px; border: 1px solid #374151; margin-bottom: 25px; }
    .candidate-card { background-color: #1F2937; border-radius: 12px; padding: 18px; border: 1px solid #374151; margin-bottom: 15px; }
    .stat-badge { background-color: #059669; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; }
    .season-badge { background-color: #8B5CF6; color: white; padding: 3px 10px; border-radius: 6px; font-weight: bold; font-size: 0.9rem; }
    .sim-badge { background-color: #3B82F6; color: white; padding: 8px 16px; border-radius: 8px; font-weight: bold; font-size: 1.2rem; display: inline-block; }
    
    /* Prevent metric truncation (...) */
    [data-testid="stMetricValue"] {
        font-size: 1.35rem !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        white-space: nowrap !important;
    }
</style>
""", unsafe_allow_html=True)

# Load engine dynamically (un-cached to prevent stale RAM)
engine = NBASimilarityEngine()
player_season_list = engine.get_player_list()
seasons_available = engine.get_season_list()

# Sidebar Setup
st.sidebar.title("Navigation & Controls")
app_mode = st.sidebar.radio(
    "Select Feature",
    ["Vector Similarity Search", "Head-to-Head Comparison", "Salary vs. Production Matrix"]
)

stat_mode = st.sidebar.selectbox(
    "Stat Scaling Mode",
    ["Per Game", "Per 36 Minutes", "Per 100 Possessions"]
)

st.sidebar.markdown("### Search Settings")

unique_players_only = st.sidebar.checkbox(
    "Deduplicate Candidates (Single Best Season Only)",
    value=True,
    help="When checked, only the single highest-matching season for each unique player is shown."
)

allow_same_player = st.sidebar.checkbox(
    "Allow Same-Player Cross-Season Matches",
    value=False,
    help="When checked, other seasons of the same player (e.g. Luka 2024-25 vs Luka 2022-23) can appear in results."
)

similarity_metric = st.sidebar.selectbox(
    "Similarity Algorithm",
    ["Weighted Euclidean (Distance-Based - Recommended)", "Cosine Similarity (Playstyle Direction)"],
    index=0,
    help="Weighted Euclidean matches true statistics & volume (recommended, avoids false 100% matches when focusing on specific stats). Cosine Similarity compares the ratio of stats regardless of volume."
)
metric_mode = "euclidean" if "Euclidean" in similarity_metric else "cosine"

ALL_CARD_ATTRIBUTES = [
    "Games Played (GP)", "Points (PTS)", "Total Rebounds (REB)", "Offensive Rebounds (OREB)", "Defensive Rebounds (DREB)",
    "Assists (AST)", "Steals (STL)", "Blocks (BLK)", "3-Pointers (3PM)", "Free Throws (FTM)",
    "Field Goal % (FG%)", "3-Point % (3P%)", "Free Throw % (FT%)", "True Shooting (TS%)", "Effective FG (eFG%)",
    "Assist-to-Turnover (AST/TO)", "Fouls Drawn (PFD)", "Net Plus-Minus (+/-)",
    "Fantasy Points (Fantasy PTS)", "Age", "Salary"
]

selected_attributes = st.sidebar.multiselect(
    "Visible Player Card Attributes",
    options=ALL_CARD_ATTRIBUTES,
    default=["Points (PTS)", "Total Rebounds (REB)", "Assists (AST)", "True Shooting (TS%)", "Assist-to-Turnover (AST/TO)", "Salary"]
)

st.sidebar.markdown("---")
with st.sidebar.container(border=True):
    sync_meta = get_sync_metadata()
    sync_status = sync_meta.get("status", "SUCCESS")
    status_label = "Active" if sync_status == "SUCCESS" else "Offline"
    last_sync = sync_meta.get("last_sync_formatted", "Recently")
    players_tracked = sync_meta.get("records_count", 0)

    st.markdown(f"""
    <div style="margin-bottom: 8px;">
        <div style="font-size: 0.95rem; font-weight: 700; color: #10B981; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 8px;">
            2026-27 Live Stat Sync
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 5px 0; border-bottom: 1px solid #374151; font-size: 0.85rem;">
            <span style="color: #9CA3AF;">Roster Status:</span>
            <span style="background: rgba(16, 185, 129, 0.18); color: #10B981; padding: 2px 8px; border-radius: 4px; font-weight: 600;">{status_label} ({players_tracked} players)</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 0.82rem;">
            <span style="color: #9CA3AF;">Last Synced:</span>
            <span style="color: #F3F4F6; font-weight: 500;">{last_sync}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Refresh 2026-27 Stats Now", use_container_width=True, help="Fetches updated ongoing box score stats from the NBA Stats API without resetting historical data."):
        with st.spinner("Fetching latest 2026-27 player statistics from NBA API..."):
            sync_result = update_season(season="2026-27", verbose=False)
            if sync_result.get("success"):
                st.success(f"Refreshed {sync_result.get('records', 0)} players!")
                st.rerun()
            else:
                st.error(f"{sync_result.get('message', 'Sync failed')}")

st.sidebar.markdown("---")
st.sidebar.info("Vector Tip: Set Max Salary in the candidate filter section to discover bargain replacement targets.")

st.markdown("<div class='main-title'>NBA Player Vector Similarity & Comparison Tool</div>", unsafe_allow_html=True)
metric_label = "Weighted Euclidean" if metric_mode == "euclidean" else "Cosine Distance"
if seasons_available:
    earliest_s = seasons_available[-1]
    latest_s = seasons_available[0]
    season_range_str = f"{earliest_s} to {latest_s}"
else:
    season_range_str = "Multi-Season"
st.markdown(f"<div class='sub-title'><b>Multi-Season Dataset ({season_range_str})</b> | Vector Similarity ({stat_mode}) | Metric: <b>{metric_label}</b></div>", unsafe_allow_html=True)

if not player_season_list:
    st.error("No player data loaded. Please make sure the SQLite database output/nba_data.db exists.")
    st.stop()

# Helper to format stat strings based on user checklist
def format_card_stats(row, selected_attrs):
    stat_parts = []
    
    pts_val = row.get('ACTIVE_PTS') if 'ACTIVE_PTS' in row and pd.notnull(row.get('ACTIVE_PTS')) else row.get('PTS', 0)
    oreb_val = row.get('ACTIVE_OREB') if 'ACTIVE_OREB' in row and pd.notnull(row.get('ACTIVE_OREB')) else row.get('OREB', 0)
    dreb_val = row.get('ACTIVE_DREB') if 'ACTIVE_DREB' in row and pd.notnull(row.get('ACTIVE_DREB')) else row.get('DREB', 0)
    reb_val = row.get('ACTIVE_REB') if 'ACTIVE_REB' in row and pd.notnull(row.get('ACTIVE_REB')) else row.get('REB', 0)
    ast_val = row.get('ACTIVE_AST') if 'ACTIVE_AST' in row and pd.notnull(row.get('ACTIVE_AST')) else row.get('AST', 0)
    stl_val = row.get('ACTIVE_STL') if 'ACTIVE_STL' in row and pd.notnull(row.get('ACTIVE_STL')) else row.get('STL', 0)
    blk_val = row.get('ACTIVE_BLK') if 'ACTIVE_BLK' in row and pd.notnull(row.get('ACTIVE_BLK')) else row.get('BLK', 0)
    fg3m_val = row.get('ACTIVE_FG3M') if 'ACTIVE_FG3M' in row and pd.notnull(row.get('ACTIVE_FG3M')) else row.get('FG3M', 0)
    ftm_val = row.get('ACTIVE_FTM') if 'ACTIVE_FTM' in row and pd.notnull(row.get('ACTIVE_FTM')) else row.get('FTM', 0)
    pfd_val = row.get('ACTIVE_PFD') if 'ACTIVE_PFD' in row and pd.notnull(row.get('ACTIVE_PFD')) else row.get('PFD', 0)
    fpts_val = row.get('ACTIVE_NBA_FANTASY_PTS') if 'ACTIVE_NBA_FANTASY_PTS' in row and pd.notnull(row.get('ACTIVE_NBA_FANTASY_PTS')) else row.get('NBA_FANTASY_PTS', 0)
    
    ts_val = (row.get('TS_PCT', 0) or 0) * 100
    efg_val = (row.get('eFG_PCT', 0) or 0) * 100
    fg_val = (row.get('FG_PCT', 0) or 0) * 100
    fg3_val = (row.get('FG3_PCT', 0) or 0) * 100
    ft_val = (row.get('FT_PCT', 0) or 0) * 100
    ast_to_val = row.get('AST_TO_RATIO', 0) or 0
    
    if "Points (PTS)" in selected_attrs:
        stat_parts.append(f"**PTS**: {float(pts_val):.1f}")
    if "Total Rebounds (REB)" in selected_attrs:
        stat_parts.append(f"**REB**: {float(reb_val):.1f}")
    if "Offensive Rebounds (OREB)" in selected_attrs:
        stat_parts.append(f"**OREB**: {float(oreb_val):.1f}")
    if "Defensive Rebounds (DREB)" in selected_attrs:
        stat_parts.append(f"**DREB**: {float(dreb_val):.1f}")
    if "Assists (AST)" in selected_attrs:
        stat_parts.append(f"**AST**: {float(ast_val):.1f}")
    if "Steals (STL)" in selected_attrs:
        stat_parts.append(f"**STL**: {float(stl_val):.1f}")
    if "Blocks (BLK)" in selected_attrs:
        stat_parts.append(f"**BLK**: {float(blk_val):.1f}")
    if "3-Pointers (3PM)" in selected_attrs:
        stat_parts.append(f"**3PM**: {float(fg3m_val):.1f}")
    if "Free Throws (FTM)" in selected_attrs:
        stat_parts.append(f"**FTM**: {float(ftm_val):.1f}")
    if "Field Goal % (FG%)" in selected_attrs:
        stat_parts.append(f"**FG%**: {float(fg_val):.1f}%")
    if "3-Point % (3P%)" in selected_attrs:
        stat_parts.append(f"**3P%**: {float(fg3_val):.1f}%")
    if "Free Throw % (FT%)" in selected_attrs:
        stat_parts.append(f"**FT%**: {float(ft_val):.1f}%")
    if "True Shooting (TS%)" in selected_attrs:
        stat_parts.append(f"**TS%**: {float(ts_val):.1f}%")
    if "Effective FG (eFG%)" in selected_attrs:
        stat_parts.append(f"**eFG%**: {float(efg_val):.1f}%")
    if "Assist-to-Turnover (AST/TO)" in selected_attrs:
        stat_parts.append(f"**AST/TO**: {float(ast_to_val):.2f}")
    if "Fouls Drawn (PFD)" in selected_attrs:
        stat_parts.append(f"**PFD**: {float(pfd_val):.1f}")
    if "Net Plus-Minus (+/-)" in selected_attrs:
        stat_parts.append(f"**+/-**: {float(row.get('PLUS_MINUS', 0)):+.1f}")
    if "Games Played (GP)" in selected_attrs:
        stat_parts.append(f"**GP**: {int(row.get('GP', 0))}")
    if "Fantasy Points (Fantasy PTS)" in selected_attrs:
        stat_parts.append(f"**FPTS**: {float(fpts_val):.1f}")
    if "Age" in selected_attrs:
        stat_parts.append(f"**Age**: {row.get('AGE', 'N/A')}")
        
    return " | ".join(stat_parts)

# -----------------------------------------------------------------------------
# TAB 1: VECTOR SIMILARITY / REPLACEMENT SEARCH
# -----------------------------------------------------------------------------
if app_mode == "Vector Similarity Search":
    st.subheader("Find Statistical Twins & Replacement Candidates")

    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        target_season_opts = ["All Seasons", "2026-27 (Current Ongoing)"] + [s for s in seasons_available if s != "2026-27"]
        target_season_sel = st.selectbox("Browse Players by Season", target_season_opts, index=0, help="Filter the player list below by season to easily find players of the desired season.")
        sel_s = "2026-27" if "2026-27" in target_season_sel else (None if target_season_sel == "All Seasons" else target_season_sel)
        try:
            filtered_player_list = engine.get_player_list(season=sel_s)
        except TypeError:
            filtered_player_list = engine.get_player_list()

        default_name = "Luka Dončić (2026-27)" if "Luka Dončić (2026-27)" in filtered_player_list else ("Luka Dončić (2023-24)" if "Luka Dončić (2023-24)" in filtered_player_list else (filtered_player_list[0] if filtered_player_list else ""))
        default_idx = filtered_player_list.index(default_name) if default_name in filtered_player_list else 0
        target_player_season = st.selectbox("Select a Player-Season Profile", filtered_player_list, index=default_idx)
        
        top_n = st.slider("Number of Similar Players", min_value=3, max_value=15, value=5)

        # EXPANDABLE HARD RANGE FILTERS (Min / Max Textboxes for All Stats)
        with st.expander("Filter Candidate Criteria (Min / Max Textboxes for All Stats)"):
            st.markdown("Set exact minimum and maximum stat boundaries or season filters to narrow candidate matches.")

            season_filter_opts = ["All Seasons"] + seasons_available
            season_filter = st.selectbox(
                "Filter Matches By Season",
                season_filter_opts,
                index=0,
                help="Filter by candidate players from a specific season (or All Seasons)."
            )

            f_cols1, f_cols2 = st.columns(2)
            with f_cols1:
                with st.expander("Financials & Bio", expanded=False):
                    c_s1, c_s2 = st.columns(2)
                    min_sal = c_s1.number_input("Min Salary ($M)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 0")
                    max_sal = c_s2.number_input("Max Salary ($M)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 30")

                    c_a1, c_a2 = st.columns(2)
                    min_age = c_a1.number_input("Min Age", value=None, min_value=18, max_value=45, step=1, placeholder="e.g. 19")
                    max_age = c_a2.number_input("Max Age", value=None, min_value=18, max_value=45, step=1, placeholder="e.g. 35")

                    c_gp1, c_gp2 = st.columns(2)
                    min_gp = c_gp1.number_input("Min Games Played (GP)", value=None, min_value=1, max_value=82, step=1, placeholder="e.g. 5")
                    max_gp = c_gp2.number_input("Max Games Played (GP)", value=None, min_value=1, max_value=82, step=1, placeholder="e.g. 82")

                with st.expander("Box Score Stats", expanded=False):
                    c_pts1, c_pts2 = st.columns(2)
                    min_pts = c_pts1.number_input("Min Points (PTS)", value=None, min_value=0.0, max_value=40.0, step=0.5, placeholder="e.g. 15.0")
                    max_pts = c_pts2.number_input("Max Points (PTS)", value=None, min_value=0.0, max_value=40.0, step=0.5, placeholder="e.g. 35.0")

                    c_reb1, c_reb2 = st.columns(2)
                    min_reb = c_reb1.number_input("Min Total Rebounds (REB)", value=None, min_value=0.0, max_value=20.0, step=0.5, placeholder="e.g. 5.0")
                    max_reb = c_reb2.number_input("Max Total Rebounds (REB)", value=None, min_value=0.0, max_value=20.0, step=0.5, placeholder="e.g. 15.0")

                    c_oreb1, c_oreb2 = st.columns(2)
                    min_oreb = c_oreb1.number_input("Min Off Rebounds (OREB)", value=None, min_value=0.0, max_value=10.0, step=0.1, placeholder="e.g. 1.0")
                    max_oreb = c_oreb2.number_input("Max Off Rebounds (OREB)", value=None, min_value=0.0, max_value=10.0, step=0.1, placeholder="e.g. 5.0")

                    c_dreb1, c_dreb2 = st.columns(2)
                    min_dreb = c_dreb1.number_input("Min Def Rebounds (DREB)", value=None, min_value=0.0, max_value=15.0, step=0.5, placeholder="e.g. 4.0")
                    max_dreb = c_dreb2.number_input("Max Def Rebounds (DREB)", value=None, min_value=0.0, max_value=15.0, step=0.5, placeholder="e.g. 12.0")

                    c_ast1, c_ast2 = st.columns(2)
                    min_ast = c_ast1.number_input("Min Assists (AST)", value=None, min_value=0.0, max_value=15.0, step=0.5, placeholder="e.g. 4.0")
                    max_ast = c_ast2.number_input("Max Assists (AST)", value=None, min_value=0.0, max_value=15.0, step=0.5, placeholder="e.g. 12.0")

                    c_stl1, c_stl2 = st.columns(2)
                    min_stl = c_stl1.number_input("Min Steals (STL)", value=None, min_value=0.0, max_value=5.0, step=0.1, placeholder="e.g. 1.0")
                    max_stl = c_stl2.number_input("Max Steals (STL)", value=None, min_value=0.0, max_value=5.0, step=0.1, placeholder="e.g. 3.0")

                    c_blk1, c_blk2 = st.columns(2)
                    min_blk = c_blk1.number_input("Min Blocks (BLK)", value=None, min_value=0.0, max_value=5.0, step=0.1, placeholder="e.g. 0.5")
                    max_blk = c_blk2.number_input("Max Blocks (BLK)", value=None, min_value=0.0, max_value=5.0, step=0.1, placeholder="e.g. 3.0")

            with f_cols2:
                with st.expander("Shooting Efficiency (%)", expanded=False):
                    c_fg3m1, c_fg3m2 = st.columns(2)
                    min_fg3m = c_fg3m1.number_input("Min 3-Pointers Made (3PM)", value=None, min_value=0.0, max_value=6.0, step=0.1, placeholder="e.g. 1.5")
                    max_fg3m = c_fg3m2.number_input("Max 3-Pointers Made (3PM)", value=None, min_value=0.0, max_value=6.0, step=0.1, placeholder="e.g. 5.0")

                    c_ts1, c_ts2 = st.columns(2)
                    min_ts = c_ts1.number_input("Min True Shooting (TS%)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 55.0")
                    max_ts = c_ts2.number_input("Max True Shooting (TS%)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 70.0")

                    c_efg1, c_efg2 = st.columns(2)
                    min_efg = c_efg1.number_input("Min Effective FG (eFG%)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 50.0")
                    max_efg = c_efg2.number_input("Max Effective FG (eFG%)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 65.0")

                    c_fg1, c_fg2 = st.columns(2)
                    min_fg = c_fg1.number_input("Min Field Goal % (FG%)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 45.0")
                    max_fg = c_fg2.number_input("Max Field Goal % (FG%)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 60.0")

                    c_fg31, c_fg32 = st.columns(2)
                    min_fg3 = c_fg31.number_input("Min 3-Point % (3P%)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 35.0")
                    max_fg3 = c_fg32.number_input("Max 3-Point % (3P%)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 45.0")

                    c_ft1, c_ft2 = st.columns(2)
                    min_ft = c_ft1.number_input("Min Free Throw % (FT%)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 75.0")
                    max_ft = c_ft2.number_input("Max Free Throw % (FT%)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 95.0")

                with st.expander("Impact & Advanced", expanded=False):
                    c_astto1, c_astto2 = st.columns(2)
                    min_ast_to = c_astto1.number_input("Min Assist-to-Turnover (AST/TO)", value=None, min_value=0.0, max_value=10.0, step=0.1, placeholder="e.g. 2.0")
                    max_ast_to = c_astto2.number_input("Max Assist-to-Turnover (AST/TO)", value=None, min_value=0.0, max_value=10.0, step=0.1, placeholder="e.g. 5.0")

                    c_pm1, c_pm2 = st.columns(2)
                    min_pm = c_pm1.number_input("Min Plus-Minus (+/-)", value=None, min_value=-20.0, max_value=20.0, step=0.5, placeholder="e.g. -2.0")
                    max_pm = c_pm2.number_input("Max Plus-Minus (+/-)", value=None, min_value=-20.0, max_value=20.0, step=0.5, placeholder="e.g. +10.0")

                    c_pfd1, c_pfd2 = st.columns(2)
                    min_pfd = c_pfd1.number_input("Min Fouls Drawn (PFD)", value=None, min_value=0.0, max_value=12.0, step=0.1, placeholder="e.g. 2.0")
                    max_pfd = c_pfd2.number_input("Max Fouls Drawn (PFD)", value=None, min_value=0.0, max_value=12.0, step=0.1, placeholder="e.g. 8.0")

        # EXPANDABLE ATTRIBUTE FOCUS WEIGHTS (Category Weights + Advanced Detailed Sliders)
        with st.expander("Customize Attribute Focus Weights", expanded=False):
            st.markdown("Select a **Category Focus Preset** or adjust the **Category Sliders** below to tune similarity matching without adjusting dozens of sliders. Advanced users can expand fine-tuned individual sliders.")

            # Default Category State Values
            default_cat_vals = {
                'cat_scoring': 1.0,
                'cat_playmaking': 1.0,
                'cat_defense': 1.0,
                'cat_rebound': 1.0,
                'cat_impact': 1.0,
                'cat_age': 0.5
            }
            for k, def_v in default_cat_vals.items():
                if k not in st.session_state:
                    st.session_state[k] = def_v

            # Detailed individual stat keys
            weight_keys_all = [
                'w_pts', 'w_fg3m', 'w_ftm', 'w_fg_pct', 'w_fg3_pct', 'w_ft_pct', 'w_efg_pct', 'w_ts_pct',
                'w_ast', 'w_ast_to', 'w_stl', 'w_blk', 'w_pfd',
                'w_reb', 'w_oreb', 'w_dreb', 'w_pm', 'w_fantasy', 'w_age'
            ]

            def apply_preset(c_pts, c_ast, c_def, c_reb, c_imp, c_age=0.5):
                st.session_state['cat_scoring'] = float(c_pts)
                st.session_state['cat_playmaking'] = float(c_ast)
                st.session_state['cat_defense'] = float(c_def)
                st.session_state['cat_rebound'] = float(c_reb)
                st.session_state['cat_impact'] = float(c_imp)
                st.session_state['cat_age'] = float(c_age)
                # Synchronize detailed keys
                for k in ['w_pts', 'w_fg3m', 'w_ftm', 'w_fg_pct', 'w_fg3_pct', 'w_ft_pct', 'w_efg_pct', 'w_ts_pct']:
                    st.session_state[k] = float(c_pts)
                for k in ['w_ast', 'w_ast_to']:
                    st.session_state[k] = float(c_ast)
                for k in ['w_stl', 'w_blk']:
                    st.session_state[k] = float(c_def)
                for k in ['w_reb', 'w_oreb', 'w_dreb']:
                    st.session_state[k] = float(c_reb)
                for k in ['w_pm', 'w_pfd', 'w_fantasy']:
                    st.session_state[k] = float(c_imp)
                st.session_state['w_age'] = float(c_age)

            st.markdown("#### Focus Categories & Presets")
            p_cols = st.columns(6)
            if p_cols[0].button("Balanced", use_container_width=True, help="All categories weighted equally (1.0)"):
                apply_preset(1.0, 1.0, 1.0, 1.0, 1.0, 0.5)
                st.rerun()
            if p_cols[1].button("Scoring", use_container_width=True, help="Scoring & shooting focus (PTS, 3PM, shooting efficiency)"):
                apply_preset(1.5, 0.0, 0.0, 0.0, 0.0, 0.0)
                st.rerun()
            if p_cols[2].button("Playmaking", use_container_width=True, help="Playmaking & ball control focus (AST, AST/TO)"):
                apply_preset(0.5, 2.0, 0.0, 0.0, 0.0, 0.0)
                st.rerun()
            if p_cols[3].button("Defense", use_container_width=True, help="Defensive focus (STL, BLK, Def Rebounds)"):
                apply_preset(0.0, 0.0, 2.0, 1.0, 0.5, 0.0)
                st.rerun()
            if p_cols[4].button("Rebounding", use_container_width=True, help="Rebounding focus (Total REB, OREB, DREB)"):
                apply_preset(0.0, 0.0, 1.0, 2.0, 0.5, 0.0)
                st.rerun()
            if p_cols[5].button("Clear All", use_container_width=True, help="Set all categories to 0.0"):
                apply_preset(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
                st.rerun()

            st.write("")
            st.markdown("#### Core Category Sliders")
            cat_c1, cat_c2 = st.columns(2)
            with cat_c1:
                cat_scoring = st.slider("Scoring & Shooting (PTS, 3PM, FTM, FG%, 3P%, FT%, eFG%, TS%)", 0.0, 2.0, step=0.1, key="cat_scoring")
                cat_playmaking = st.slider("Playmaking (AST, AST/TO Ratio)", 0.0, 2.0, step=0.1, key="cat_playmaking")
                cat_defense = st.slider("Defense (STL, BLK)", 0.0, 2.0, step=0.1, key="cat_defense")
            with cat_c2:
                cat_rebound = st.slider("Rebounding (Total REB, Off OREB, Def DREB)", 0.0, 2.0, step=0.1, key="cat_rebound")
                cat_impact = st.slider("Net Impact & Fantasy (+/-, Fouls Drawn PFD, Fantasy PTS)", 0.0, 2.0, step=0.1, key="cat_impact")
                cat_age = st.slider("Player Age", 0.0, 2.0, step=0.1, key="cat_age")

            # Active categories badge feedback
            active_cats = []
            if cat_scoring > 0: active_cats.append(f"Scoring ({cat_scoring:.1f})")
            if cat_playmaking > 0: active_cats.append(f"Playmaking ({cat_playmaking:.1f})")
            if cat_defense > 0: active_cats.append(f"Defense ({cat_defense:.1f})")
            if cat_rebound > 0: active_cats.append(f"Rebounds ({cat_rebound:.1f})")
            if cat_impact > 0: active_cats.append(f"Impact ({cat_impact:.1f})")
            if cat_age > 0: active_cats.append(f"Age ({cat_age:.1f})")

            if active_cats:
                st.caption("Active Categories: " + " • ".join(active_cats))
            else:
                st.caption("⚠️ All category weights are 0.0. Engine will use equal weighting fallback.")

            # Optional detailed fine-tuning expander
            use_detailed = st.checkbox(
                "Fine-Tune Individual Stats (Expand All 19 Detailed Sliders)",
                value=st.session_state.get('use_detailed_weights', False),
                key='use_detailed_weights',
                help="Check this box if you want to override category weights with individual stat sliders."
            )

            if use_detailed:
                st.info("Individual stat weights below are active and overriding category-level weights.")
                # Ensure all detailed keys are initialized
                for k in weight_keys_all:
                    if k not in st.session_state:
                        if k in ['w_pts', 'w_fg3m', 'w_ftm', 'w_fg_pct', 'w_fg3_pct', 'w_ft_pct', 'w_efg_pct', 'w_ts_pct']:
                            st.session_state[k] = cat_scoring
                        elif k in ['w_ast', 'w_ast_to']:
                            st.session_state[k] = cat_playmaking
                        elif k in ['w_stl', 'w_blk']:
                            st.session_state[k] = cat_defense
                        elif k in ['w_reb', 'w_oreb', 'w_dreb']:
                            st.session_state[k] = cat_rebound
                        elif k in ['w_pm', 'w_pfd', 'w_fantasy']:
                            st.session_state[k] = cat_impact
                        elif k == 'w_age':
                            st.session_state[k] = cat_age

                col_w1, col_w2, col_w3 = st.columns(3)
                with col_w1:
                    st.markdown("##### Scoring & Shooting")
                    w_pts = st.slider("Points (PTS)", 0.0, 2.0, step=0.1, key="w_pts")
                    w_fg3m = st.slider("3-Pointers Made (3PM)", 0.0, 2.0, step=0.1, key="w_fg3m")
                    w_ftm = st.slider("Free Throws Made (FTM)", 0.0, 2.0, step=0.1, key="w_ftm")
                    w_fg_pct = st.slider("Field Goal % (FG%)", 0.0, 2.0, step=0.1, key="w_fg_pct")
                    w_fg3_pct = st.slider("3-Point % (3P%)", 0.0, 2.0, step=0.1, key="w_fg3_pct")
                    w_ft_pct = st.slider("Free Throw % (FT%)", 0.0, 2.0, step=0.1, key="w_ft_pct")
                    w_efg_pct = st.slider("Effective FG % (eFG%)", 0.0, 2.0, step=0.1, key="w_efg_pct")
                    w_ts_pct = st.slider("True Shooting % (TS%)", 0.0, 2.0, step=0.1, key="w_ts_pct")

                with col_w2:
                    st.markdown("##### Playmaking & Defense")
                    w_ast = st.slider("Assists (AST)", 0.0, 2.0, step=0.1, key="w_ast")
                    w_ast_to = st.slider("Assist-to-Turnover (AST/TO)", 0.0, 2.0, step=0.1, key="w_ast_to")
                    w_stl = st.slider("Steals (STL)", 0.0, 2.0, step=0.1, key="w_stl")
                    w_blk = st.slider("Blocks (BLK)", 0.0, 2.0, step=0.1, key="w_blk")
                    w_pfd = st.slider("Fouls Drawn (PFD)", 0.0, 2.0, step=0.1, key="w_pfd")

                with col_w3:
                    st.markdown("##### Rebounds, Impact & Bio")
                    w_reb = st.slider("Total Rebounds (REB)", 0.0, 2.0, step=0.1, key="w_reb")
                    w_oreb = st.slider("Offensive Rebounding (OREB)", 0.0, 2.0, step=0.1, key="w_oreb")
                    w_dreb = st.slider("Defensive Rebounding (DREB)", 0.0, 2.0, step=0.1, key="w_dreb")
                    w_pm = st.slider("Net Plus-Minus (+/-)", 0.0, 2.0, step=0.1, key="w_pm")
                    w_fantasy = st.slider("NBA Fantasy Points", 0.0, 2.0, step=0.1, key="w_fantasy")
                    w_age = st.slider("Age", 0.0, 2.0, step=0.1, key="w_age")
            else:
                w_pts = cat_scoring
                w_fg3m = cat_scoring
                w_ftm = cat_scoring
                w_fg_pct = cat_scoring
                w_fg3_pct = cat_scoring
                w_ft_pct = cat_scoring
                w_efg_pct = cat_scoring
                w_ts_pct = cat_scoring

                w_ast = cat_playmaking
                w_ast_to = cat_playmaking

                w_stl = cat_defense
                w_blk = cat_defense

                w_reb = cat_rebound
                w_oreb = cat_rebound
                w_dreb = cat_rebound

                w_pm = cat_impact
                w_pfd = cat_impact
                w_fantasy = cat_impact

                w_age = cat_age

    weights = {
        'PTS': w_pts, 'PER36_PTS': w_pts, 'PER100_PTS': w_pts,
        'REB': w_reb, 'PER36_REB': w_reb, 'PER100_REB': w_reb,
        'OREB': w_oreb, 'PER36_OREB': w_oreb, 'PER100_OREB': w_oreb,
        'DREB': w_dreb, 'PER36_DREB': w_dreb, 'PER100_DREB': w_dreb,
        'AST': w_ast, 'PER36_AST': w_ast, 'PER100_AST': w_ast,
        'AST_TO_RATIO': w_ast_to,
        'STL': w_stl, 'PER36_STL': w_stl, 'PER100_STL': w_stl,
        'BLK': w_blk, 'PER36_BLK': w_blk, 'PER100_BLK': w_blk,
        'FG3M': w_fg3m, 'PER36_FG3M': w_fg3m, 'PER100_FG3M': w_fg3m,
        'FTM': w_ftm, 'PER36_FTM': w_ftm, 'PER100_FTM': w_ftm,
        'PFD': w_pfd, 'PER36_PFD': w_pfd, 'PER100_PFD': w_pfd,
        'FG_PCT': w_fg_pct,
        'FG3_PCT': w_fg3_pct,
        'FT_PCT': w_ft_pct,
        'eFG_PCT': w_efg_pct,
        'TS_PCT': w_ts_pct,
        'PLUS_MINUS': w_pm,
        'NBA_FANTASY_PTS': w_fantasy, 'PER36_NBA_FANTASY_PTS': w_fantasy, 'PER100_NBA_FANTASY_PTS': w_fantasy,
        'AGE': w_age
    }

    stat_filters_dict = {
        'salary': (min_sal, max_sal),
        'AGE': (min_age, max_age),
        'GP': (min_gp, max_gp),
        'PTS': (min_pts, max_pts),
        'REB': (min_reb, max_reb),
        'OREB': (min_oreb, max_oreb),
        'DREB': (min_dreb, max_dreb),
        'AST': (min_ast, max_ast),
        'STL': (min_stl, max_stl),
        'BLK': (min_blk, max_blk),
        'FG3M': (min_fg3m, max_fg3m),
        'FG_PCT': (min_fg, max_fg),
        'FG3_PCT': (min_fg3, max_fg3),
        'FT_PCT': (min_ft, max_ft),
        'TS_PCT': (min_ts, max_ts),
        'eFG_PCT': (min_efg, max_efg),
        'AST_TO_RATIO': (min_ast_to, max_ast_to),
        'PLUS_MINUS': (min_pm, max_pm),
        'PFD': (min_pfd, max_pfd),
    }

    # Run Vector Similarity Search with Hard Range Filters
    results = engine.find_similar_players(
        target_player_season,
        top_n=top_n,
        stat_mode=stat_mode,
        target_season_filter=season_filter,
        allow_same_player=allow_same_player,
        unique_players_only=unique_players_only,
        stat_filters=stat_filters_dict,
        weights=weights,
        metric=metric_mode
    )

    # Fetch updated target player row (with ACTIVE_* stat columns populated)
    norm_target = normalize_player_name(target_player_season)
    target_match = engine.df[engine.df['norm_display_season'] == norm_target]
    if target_match.empty:
        target_match = engine.df[engine.df['norm_name'] == norm_target]

    if not target_match.empty:
        target_row = target_match.iloc[0]
        with top_col2:
            st.markdown(f"### Target Profile: **{target_row.get('DISPLAY_NAME_SEASON', target_player_season)}** (`{target_row.get('TEAM_ABBREVIATION', 'N/A')}`)")
            
            salary_val = target_row.get('salary', np.nan)
            salary_str = f"${salary_val/1e6:.2f}M" if pd.notnull(salary_val) and salary_val > 0 else "N/A"

            t_pts = target_row.get('ACTIVE_PTS') if 'ACTIVE_PTS' in target_row and pd.notnull(target_row.get('ACTIVE_PTS')) else target_row.get('PTS', 0)
            t_oreb = target_row.get('ACTIVE_OREB') if 'ACTIVE_OREB' in target_row and pd.notnull(target_row.get('ACTIVE_OREB')) else target_row.get('OREB', 0)
            t_dreb = target_row.get('ACTIVE_DREB') if 'ACTIVE_DREB' in target_row and pd.notnull(target_row.get('ACTIVE_DREB')) else target_row.get('DREB', 0)
            t_ast = target_row.get('ACTIVE_AST') if 'ACTIVE_AST' in target_row and pd.notnull(target_row.get('ACTIVE_AST')) else target_row.get('AST', 0)

            # 2 rows of 3 metrics dynamically scaled to selected stat_mode
            m1, m2, m3 = st.columns(3)
            m1.metric(f"Points ({stat_mode})", f"{float(t_pts):.1f}")
            m2.metric(f"Off Rebounds ({stat_mode})", f"{float(t_oreb):.1f}")
            m3.metric(f"Def Rebounds ({stat_mode})", f"{float(t_dreb):.1f}")

            st.write("") # Spacer
            m4, m5, m6 = st.columns(3)
            m4.metric(f"Assists ({stat_mode})", f"{float(t_ast):.1f}")
            m5.metric("True Shooting %", f"{target_row.get('TS_PCT', 0)*100:.1f}%")
            m6.metric("Salary", salary_str)

    st.markdown("---")

    if not results.empty:
        st.markdown(f"### Top {top_n} Vector Similarity Matches ({stat_mode}):")

        for idx, row in results.iterrows():
            with st.container():
                c_col1, c_col2, c_col3 = st.columns([1, 4, 2])
                with c_col1:
                    img_url = row.get('headshot_url', '')
                    if pd.notnull(img_url) and str(img_url).startswith('http'):
                        st.image(img_url, width=100)
                    else:
                        st.markdown("Player")
                with c_col2:
                    p_title = row.get('DISPLAY_NAME_SEASON', row.get('PLAYER_NAME'))
                    is_live = row.get('SEASON') == '2026-27'
                    live_tag = "<span style='background-color: #10B981; color: white; padding: 2px 7px; border-radius: 4px; font-weight: 600; font-size: 0.75rem; margin-left: 6px;'>Live 2026-27</span>" if is_live else ""
                    st.markdown(f"### {p_title} (`{row.get('TEAM_ABBREVIATION', '')}`) {live_tag}", unsafe_allow_html=True)
                    card_summary = format_card_stats(row, selected_attrs=selected_attributes)
                    st.write(card_summary if card_summary else "*(No attributes checked in sidebar checklist)*")
                with c_col3:
                    st.markdown(f"<div class='sim-badge'>{row.get('SIMILARITY_SCORE', 0)}% Match</div>", unsafe_allow_html=True)
                    if "Salary" in selected_attributes:
                        r_sal = row.get('salary', np.nan)
                        if pd.notnull(r_sal) and r_sal > 0:
                            st.caption(f"Salary: **${r_sal/1e6:.2f}M**")
                        else:
                            st.caption("Salary: N/A")
            st.markdown("---")
    else:
        st.warning(f"No vector matches found for {target_player_season} with the current filter criteria.")

# -----------------------------------------------------------------------------
# TAB 2: HEAD-TO-HEAD RADAR COMPARISON
# -----------------------------------------------------------------------------
elif app_mode == "Head-to-Head Comparison":
    st.subheader("Head-to-Head Player-Season Comparison & Radar Chart")

    col1, col2 = st.columns(2)
    with col1:
        s1_opts = ["All Seasons", "2026-27 (Current Ongoing)"] + [s for s in seasons_available if s != "2026-27"]
        s1_sel = st.selectbox("Browse Player 1 by Season", s1_opts, index=0, key="h2h_s1_filter", help="Filter the player list below by season to easily find players of the desired season.")
        s1_val = "2026-27" if "2026-27" in s1_sel else (None if s1_sel == "All Seasons" else s1_sel)
        try:
            p1_list = engine.get_player_list(season=s1_val)
        except TypeError:
            p1_list = engine.get_player_list()
        p1_default = p1_list.index("Nikola Jokić (2024-25)") if "Nikola Jokić (2024-25)" in p1_list else 0
        player1 = st.selectbox("Select Player-Season 1", p1_list, index=p1_default)
    with col2:
        s2_opts = ["All Seasons", "2026-27 (Current Ongoing)"] + [s for s in seasons_available if s != "2026-27"]
        s2_sel = st.selectbox("Browse Player 2 by Season", s2_opts, index=0, key="h2h_s2_filter", help="Filter the player list below by season to easily find players of the desired season.")
        s2_val = "2026-27" if "2026-27" in s2_sel else (None if s2_sel == "All Seasons" else s2_sel)
        try:
            p2_list = engine.get_player_list(season=s2_val)
        except TypeError:
            p2_list = engine.get_player_list()
        p2_default = p2_list.index("Giannis Antetokounmpo (2024-25)") if "Giannis Antetokounmpo (2024-25)" in p2_list else (min(1, len(p2_list)-1) if len(p2_list) > 1 else 0)
        player2 = st.selectbox("Select Player-Season 2", p2_list, index=p2_default)

    p1_match = engine.df[engine.df['norm_display_season'] == normalize_player_name(player1)]
    p2_match = engine.df[engine.df['norm_display_season'] == normalize_player_name(player2)]

    if not p1_match.empty and not p2_match.empty:
        p1_data = p1_match.iloc[0]
        p2_data = p2_match.iloc[0]

        # Display side-by-side metric comparison
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"### Player 1: {player1} ({p1_data.get('TEAM_ABBREVIATION', '')})")
            st.write(f"**PTS**: {p1_data.get('PTS', 0):.1f} | **OREB**: {p1_data.get('OREB', 0):.1f} | **DREB**: {p1_data.get('DREB', 0):.1f} | **AST**: {p1_data.get('AST', 0):.1f} | **STL**: {p1_data.get('STL', 0):.1f} | **BLK**: {p1_data.get('BLK', 0):.1f}")
            st.write(f"**FG%**: {p1_data.get('FG_PCT', 0)*100:.1f}% | **3P%**: {p1_data.get('FG3_PCT', 0)*100:.1f}% | **TS%**: {p1_data.get('TS_PCT', 0)*100:.1f}% | **AST/TO**: {p1_data.get('AST_TO_RATIO', 0):.2f}")
        with c2:
            st.markdown(f"### Player 2: {player2} ({p2_data.get('TEAM_ABBREVIATION', '')})")
            st.write(f"**PTS**: {p2_data.get('PTS', 0):.1f} | **OREB**: {p2_data.get('OREB', 0):.1f} | **DREB**: {p2_data.get('DREB', 0):.1f} | **AST**: {p2_data.get('AST', 0):.1f} | **STL**: {p2_data.get('STL', 0):.1f} | **BLK**: {p2_data.get('BLK', 0):.1f}")
            st.write(f"**FG%**: {p2_data.get('FG_PCT', 0)*100:.1f}% | **3P%**: {p2_data.get('FG3_PCT', 0)*100:.1f}% | **TS%**: {p2_data.get('TS_PCT', 0)*100:.1f}% | **AST/TO**: {p2_data.get('AST_TO_RATIO', 0):.2f}")

        st.markdown("### Skill Radar Overlay")
        categories = ['Scoring (PTS)', 'Off Rebounding (OREB)', 'Def Rebounding (DREB)', 'Playmaking (AST)', 'Defense (STL+BLK)', 'True Shooting (TS%)', '3P Shooting (3PM)']
        
        def get_radar_values(row):
            pts_norm = min(100, (row.get('PTS', 0) / 35.0) * 100)
            oreb_norm = min(100, (row.get('OREB', 0) / 5.0) * 100)
            dreb_norm = min(100, (row.get('DREB', 0) / 11.0) * 100)
            ast_norm = min(100, (row.get('AST', 0) / 11.0) * 100)
            def_norm = min(100, ((row.get('STL', 0) + row.get('BLK', 0)) / 3.5) * 100)
            ts_norm = min(100, row.get('TS_PCT', 0) * 100)
            fg3_norm = min(100, (row.get('FG3M', 0) / 4.5) * 100)
            return [pts_norm, oreb_norm, dreb_norm, ast_norm, def_norm, ts_norm, fg3_norm]

        r1 = get_radar_values(p1_data)
        r2 = get_radar_values(p2_data)

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=r1, theta=categories, fill='toself', name=player1, line_color='#3B82F6'))
        fig.add_trace(go.Scatterpolar(r=r2, theta=categories, fill='toself', name=player2, line_color='#F97316'))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            template="plotly_dark",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 3: SALARY VS PRODUCTION MATRIX
# -----------------------------------------------------------------------------
elif app_mode == "Salary vs. Production Matrix":
    st.subheader("Salary vs. Box Score Production Analytics")
    st.markdown("Identify bargain contracts and top-value player performances across the league.")

    m_season_opts = ["All Seasons", "2026-27 (Current Ongoing)"] + [s for s in seasons_available if s != "2026-27"]
    matrix_season = st.selectbox("Filter Matrix by Season", m_season_opts, index=0, help="Isolate the ongoing 2026-27 season to view active bargain performers, or analyze across all multi-season data.")

    plot_df = engine.df.dropna(subset=['salary', 'PTS']).copy()
    if matrix_season != "All Seasons":
        sel_s = "2026-27" if "2026-27" in matrix_season else matrix_season
        plot_df = plot_df[plot_df['SEASON'] == sel_s]

    plot_df['Salary_Millions'] = plot_df['salary'] / 1e6
    plot_df = plot_df[plot_df['Salary_Millions'] > 0]

    if plot_df.empty:
        st.warning("No salary data available for plotting. Make sure `espn_rosters` or `hoopshype_salaries` contain salary figures.")
    else:
        fig = px.scatter(
            plot_df,
            x="Salary_Millions",
            y="PTS",
            size="REB",
            color="TEAM_ABBREVIATION",
            hover_name="DISPLAY_NAME_SEASON",
            hover_data=["AST", "TS_PCT", "OREB", "position"],
            labels={"Salary_Millions": "Salary ($ Millions)", "PTS": "Points Per Game (PPG)"},
            title="Player Salary ($M) vs. Points Per Game (Bubble Size = Rebounds)",
            template="plotly_dark",
            height=600
        )
        st.plotly_chart(fig, use_container_width=True)
