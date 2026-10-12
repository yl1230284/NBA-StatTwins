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
    "Points (PTS)", "Total Rebounds (REB)", "Offensive Rebounds (OREB)", "Defensive Rebounds (DREB)",
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
st.sidebar.info("Vector Tip: Set Max Salary in the candidate filter section to discover bargain replacement targets.")

# Title Header
st.markdown("<div class='main-title'>NBA Player Vector Similarity & Comparison Tool</div>", unsafe_allow_html=True)
metric_label = "Weighted Euclidean" if metric_mode == "euclidean" else "Cosine Distance"
st.markdown(f"<div class='sub-title'><b>Multi-Season Dataset (2022-23 to 2025-26)</b> | Vector Similarity ({stat_mode}) | Metric: <b>{metric_label}</b></div>", unsafe_allow_html=True)

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
        default_name = "Luka Dončić (2023-24)"
        default_idx = player_season_list.index(default_name) if default_name in player_season_list else 0
        target_player_season = st.selectbox("Select Target Player-Season", player_season_list, index=default_idx)
        
        season_filter_opts = ["All Seasons"] + seasons_available
        season_filter = st.selectbox("Filter Matches By Season", season_filter_opts, index=0)
        
        top_n = st.slider("Number of Similar Players", min_value=3, max_value=15, value=5)

        # EXPANDABLE HARD RANGE FILTERS (Min / Max Textboxes for All Stats)
        with st.expander("Filter Candidate Criteria (Min / Max Textboxes for All Stats)"):
            st.markdown("Set exact minimum and maximum stat boundaries to filter candidate matches.")

            f_cols1, f_cols2 = st.columns(2)
            with f_cols1:
                st.markdown("#### Financials & Bio")
                c_s1, c_s2 = st.columns(2)
                min_sal = c_s1.number_input("Min Salary ($M)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 0")
                max_sal = c_s2.number_input("Max Salary ($M)", value=None, min_value=0.0, max_value=100.0, step=1.0, placeholder="e.g. 30")

                c_a1, c_a2 = st.columns(2)
                min_age = c_a1.number_input("Min Age", value=None, min_value=18, max_value=45, step=1, placeholder="e.g. 19")
                max_age = c_a2.number_input("Max Age", value=None, min_value=18, max_value=45, step=1, placeholder="e.g. 35")

                st.markdown("#### Box Score Stats")
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
                st.markdown("#### Shooting Efficiency (%)")
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

                st.markdown("#### Impact & Advanced")
                c_astto1, c_astto2 = st.columns(2)
                min_ast_to = c_astto1.number_input("Min Assist-to-Turnover (AST/TO)", value=None, min_value=0.0, max_value=10.0, step=0.1, placeholder="e.g. 2.0")
                max_ast_to = c_astto2.number_input("Max Assist-to-Turnover (AST/TO)", value=None, min_value=0.0, max_value=10.0, step=0.1, placeholder="e.g. 5.0")

                c_pm1, c_pm2 = st.columns(2)
                min_pm = c_pm1.number_input("Min Plus-Minus (+/-)", value=None, min_value=-20.0, max_value=20.0, step=0.5, placeholder="e.g. -2.0")
                max_pm = c_pm2.number_input("Max Plus-Minus (+/-)", value=None, min_value=-20.0, max_value=20.0, step=0.5, placeholder="e.g. +10.0")

                c_pfd1, c_pfd2 = st.columns(2)
                min_pfd = c_pfd1.number_input("Min Fouls Drawn (PFD)", value=None, min_value=0.0, max_value=12.0, step=0.1, placeholder="e.g. 2.0")
                max_pfd = c_pfd2.number_input("Max Fouls Drawn (PFD)", value=None, min_value=0.0, max_value=12.0, step=0.1, placeholder="e.g. 8.0")

        # EXPANDABLE ATTRIBUTE FOCUS WEIGHTS (All 19 Stats Individually Controllable)
        with st.expander("Customize Attribute Focus Weights (All 19 Stats)"):
            st.markdown("Adjust individual stat weights (0.0 to 2.0). Setting a weight to 0 completely removes it from similarity calculation.")

            # Quick Preset Buttons
            weight_keys_all = [
                'w_pts', 'w_fg3m', 'w_ftm', 'w_fg_pct', 'w_fg3_pct', 'w_ft_pct', 'w_efg_pct', 'w_ts_pct',
                'w_ast', 'w_ast_to', 'w_stl', 'w_blk', 'w_pfd',
                'w_reb', 'w_oreb', 'w_dreb', 'w_pm', 'w_fantasy', 'w_age'
            ]
            for k in weight_keys_all:
                if k not in st.session_state:
                    st.session_state[k] = 0.5 if k == 'w_age' else 1.0

            p_col1, p_col2, p_col3, p_col4 = st.columns(4)
            if p_col1.button("Balanced (All 1.0)", use_container_width=True):
                for k in weight_keys_all:
                    st.session_state[k] = 0.5 if k == 'w_age' else 1.0
                st.rerun()
            if p_col2.button("Scoring Only (PTS=1)", use_container_width=True):
                for k in weight_keys_all:
                    st.session_state[k] = 1.0 if k == 'w_pts' else 0.0
                st.rerun()
            if p_col3.button("Playmaking Focus", use_container_width=True):
                for k in weight_keys_all:
                    st.session_state[k] = 1.0 if k in ['w_ast', 'w_ast_to'] else 0.0
                st.rerun()
            if p_col4.button("Zero All (0.0)", use_container_width=True):
                for k in weight_keys_all:
                    st.session_state[k] = 0.0
                st.rerun()

            st.write("")

            col_w1, col_w2, col_w3 = st.columns(3)
            with col_w1:
                st.markdown("#### Scoring & Shooting")
                w_pts = st.slider("Scoring (PTS)", 0.0, 2.0, step=0.1, key="w_pts")
                w_fg3m = st.slider("3-Pointers Made (3PM)", 0.0, 2.0, step=0.1, key="w_fg3m")
                w_ftm = st.slider("Free Throws Made (FTM)", 0.0, 2.0, step=0.1, key="w_ftm")
                w_fg_pct = st.slider("Field Goal % (FG%)", 0.0, 2.0, step=0.1, key="w_fg_pct")
                w_fg3_pct = st.slider("3-Point % (3P%)", 0.0, 2.0, step=0.1, key="w_fg3_pct")
                w_ft_pct = st.slider("Free Throw % (FT%)", 0.0, 2.0, step=0.1, key="w_ft_pct")
                w_efg_pct = st.slider("Effective FG % (eFG%)", 0.0, 2.0, step=0.1, key="w_efg_pct")
                w_ts_pct = st.slider("True Shooting % (TS%)", 0.0, 2.0, step=0.1, key="w_ts_pct")

            with col_w2:
                st.markdown("#### Playmaking & Defense")
                w_ast = st.slider("Playmaking (AST)", 0.0, 2.0, step=0.1, key="w_ast")
                w_ast_to = st.slider("Assist-to-Turnover (AST/TO)", 0.0, 2.0, step=0.1, key="w_ast_to")
                w_stl = st.slider("Steals (STL)", 0.0, 2.0, step=0.1, key="w_stl")
                w_blk = st.slider("Blocks (BLK)", 0.0, 2.0, step=0.1, key="w_blk")
                w_pfd = st.slider("Fouls Drawn (PFD)", 0.0, 2.0, step=0.1, key="w_pfd")

            with col_w3:
                st.markdown("#### Rebounds, Impact & Bio")
                w_reb = st.slider("Total Rebounds (REB)", 0.0, 2.0, step=0.1, key="w_reb")
                w_oreb = st.slider("Offensive Rebounding (OREB)", 0.0, 2.0, step=0.1, key="w_oreb")
                w_dreb = st.slider("Defensive Rebounding (DREB)", 0.0, 2.0, step=0.1, key="w_dreb")
                w_pm = st.slider("Net Impact (+/-)", 0.0, 2.0, step=0.1, key="w_pm")
                w_fantasy = st.slider("NBA Fantasy Points", 0.0, 2.0, step=0.1, key="w_fantasy")
                w_age = st.slider("Player Age", 0.0, 2.0, step=0.1, key="w_age")

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
                    st.markdown(f"### {p_title} (`{row.get('TEAM_ABBREVIATION', '')}`)")
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
        p1_default = player_season_list.index("Nikola Jokić (2024-25)") if "Nikola Jokić (2024-25)" in player_season_list else 0
        player1 = st.selectbox("Select Player-Season 1", player_season_list, index=p1_default)
    with col2:
        p2_default = player_season_list.index("Giannis Antetokounmpo (2024-25)") if "Giannis Antetokounmpo (2024-25)" in player_season_list else min(1, len(player_season_list)-1)
        player2 = st.selectbox("Select Player-Season 2", player_season_list, index=p2_default)

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

    plot_df = engine.df.dropna(subset=['salary', 'PTS']).copy()
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
