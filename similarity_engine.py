"""
NBA Player Vector Similarity Engine (Multi-Season Support + Unicode Name Normalization + Player Deduplication + Hard Range Filtering)
Handles dataset querying, stat normalization (Per Game, Per 36, Per 100),
and Scikit-Learn vector similarity search across multiple seasons.
"""

import os
import sqlite3
import re
import unicodedata
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Tuple, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "nba_data.db")

CORE_METRICS = [
    'PTS', 'REB', 'OREB', 'DREB', 'AST', 'STL', 'BLK',
    'FG_PCT', 'FG3_PCT', 'FT_PCT',
    'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'TOV',
    'PF', 'PFD', 'PLUS_MINUS', 'NBA_FANTASY_PTS', 'DD2', 'TD3', 'AGE'
]

def normalize_player_name(name: str) -> str:
    """Normalize player names by converting diacritics to ASCII (e.g., Dončić -> doncic)."""
    if not name:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(name))
    ascii_name = "".join([c for c in nfkd if not unicodedata.combining(c)])
    clean = ascii_name.lower().replace(".", "").replace("-", " ").replace("'", "").strip()
    clean = re.sub(r'\s+(jr|sr|iii|ii|iv)$', '', clean)
    return clean

class NBASimilarityEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.df = pd.DataFrame()
        self.load_and_prepare_data()

    def load_and_prepare_data(self):
        """Load stats and roster info from SQLite, compute derived metrics."""
        if not os.path.exists(self.db_path):
            print(f"[Similarity Engine] Error: Database not found at {self.db_path}")
            return

        with sqlite3.connect(self.db_path) as conn:
            stats_df = pd.read_sql_query("SELECT * FROM nba_season_stats", conn)
            try:
                rosters_df = pd.read_sql_query("SELECT * FROM espn_rosters", conn)
            except Exception:
                rosters_df = pd.DataFrame()
            try:
                hist_sal_df = pd.read_sql_query("SELECT * FROM espn_historical_salaries", conn)
            except Exception:
                hist_sal_df = pd.DataFrame()
            try:
                hh_df = pd.read_sql_query("SELECT * FROM hoopshype_salaries", conn)
            except Exception:
                hh_df = pd.DataFrame()

        if stats_df.empty:
            print("[Similarity Engine] Warning: nba_season_stats table is empty.")
            return

        # Ensure SEASON and DISPLAY_NAME_SEASON columns exist
        if 'SEASON' not in stats_df.columns:
            stats_df['SEASON'] = "2023-24"
            
        if 'DISPLAY_NAME_SEASON' not in stats_df.columns:
            stats_df['DISPLAY_NAME_SEASON'] = stats_df['PLAYER_NAME'].astype(str) + " (" + stats_df['SEASON'].astype(str) + ")"

        # Ensure numeric types
        for col in CORE_METRICS + ['GP', 'MIN']:
            if col in stats_df.columns:
                stats_df[col] = pd.to_numeric(stats_df[col], errors='coerce').fillna(0)

        # Filter out players with minimal minutes (e.g. < 5 total minutes)
        if 'MIN' in stats_df.columns:
            stats_df = stats_df[stats_df['MIN'] >= 5.0].copy()

        # Unicode Normalized Name for robust multi-table joining
        stats_df['norm_name'] = stats_df['PLAYER_NAME'].apply(normalize_player_name)
        stats_df['norm_display_season'] = stats_df['DISPLAY_NAME_SEASON'].apply(normalize_player_name)

        # Merge ESPN Roster Info (Bio & Headshots)
        if not rosters_df.empty and 'name' in rosters_df.columns:
            rosters_df['norm_name'] = rosters_df['name'].apply(normalize_player_name)
            roster_subset = rosters_df[['norm_name', 'headshot_url', 'salary', 'position', 'height', 'weight']].drop_duplicates(subset=['norm_name'])
            merged = pd.merge(stats_df, roster_subset, on='norm_name', how='left')
        else:
            merged = stats_df
            merged['headshot_url'] = ''
            merged['salary'] = np.nan
            merged['position'] = ''
            merged['height'] = ''
            merged['weight'] = ''

        # Merge Season-Specific Historical Salaries (espn_historical_salaries)
        if not hist_sal_df.empty and 'PLAYER_NAME' in hist_sal_df.columns:
            hist_sal_df['norm_name'] = hist_sal_df['PLAYER_NAME'].apply(normalize_player_name)
            hist_subset = hist_sal_df[['norm_name', 'SEASON', 'salary']].rename(columns={'salary': 'season_hist_salary'}).drop_duplicates(subset=['norm_name', 'SEASON'])
            merged = pd.merge(merged, hist_subset, on=['norm_name', 'SEASON'], how='left')
            merged['salary'] = merged['season_hist_salary'].fillna(merged['salary'])

        # Merge HoopsHype Salary Backup
        if not hh_df.empty and 'Player' in hh_df.columns:
            hh_df['norm_name'] = hh_df['Player'].apply(normalize_player_name)
            
            sal_col = None
            for c in hh_df.columns:
                if '202' in c or 'col' in c:
                    sal_col = c
                    break
            
            if sal_col:
                def parse_hh_sal(v):
                    if not v: return np.nan
                    clean_str = re.sub(r'[^0-9.]', '', str(v))
                    try: return float(clean_str)
                    except: return np.nan

                hh_df['hh_sal'] = hh_df[sal_col].apply(parse_hh_sal)
                hh_subset = hh_df[['norm_name', 'hh_sal']].dropna(subset=['hh_sal']).drop_duplicates(subset=['norm_name'])
                
                merged = pd.merge(merged, hh_subset, on='norm_name', how='left')
                merged['salary'] = merged['salary'].fillna(merged['hh_sal'])

        # Advanced Efficiency Calculations
        merged['eFG_PCT'] = np.where(merged['FGA'] > 0, (merged['FGM'] + 0.5 * merged['FG3M']) / merged['FGA'], 0.0)
        
        ts_denom = 2 * (merged['FGA'] + 0.44 * merged['FTA'])
        merged['TS_PCT'] = np.where(ts_denom > 0, merged['PTS'] / ts_denom, 0.0)

        merged['AST_TO_RATIO'] = np.where(merged['TOV'] > 0, merged['AST'] / merged['TOV'], merged['AST'])

        # Per 36 Minutes calculations
        min_factor = np.maximum(merged['MIN'], 1.0)
        merged['PER36_PTS'] = (merged['PTS'] / min_factor) * 36
        merged['PER36_REB'] = (merged['REB'] / min_factor) * 36
        merged['PER36_OREB'] = (merged['OREB'] / min_factor) * 36
        merged['PER36_DREB'] = (merged['DREB'] / min_factor) * 36
        merged['PER36_AST'] = (merged['AST'] / min_factor) * 36
        merged['PER36_STL'] = (merged['STL'] / min_factor) * 36
        merged['PER36_BLK'] = (merged['BLK'] / min_factor) * 36
        merged['PER36_FG3M'] = (merged['FG3M'] / min_factor) * 36
        merged['PER36_FTM'] = (merged['FTM'] / min_factor) * 36
        merged['PER36_PFD'] = (merged['PFD'] / min_factor) * 36

        # Per 100 Possessions calculations using player-specific on-court PACE and total POSS
        if 'PACE' in merged.columns:
            pace_factor = np.where(pd.to_numeric(merged['PACE'], errors='coerce') > 0, pd.to_numeric(merged['PACE'], errors='coerce'), 98.5)
        else:
            pace_factor = 98.5

        merged['PER100_PTS'] = (merged['PTS'] / min_factor) * 48 * (100 / pace_factor)
        merged['PER100_REB'] = (merged['REB'] / min_factor) * 48 * (100 / pace_factor)
        merged['PER100_OREB'] = (merged['OREB'] / min_factor) * 48 * (100 / pace_factor)
        merged['PER100_DREB'] = (merged['DREB'] / min_factor) * 48 * (100 / pace_factor)
        merged['PER100_AST'] = (merged['AST'] / min_factor) * 48 * (100 / pace_factor)
        merged['PER100_STL'] = (merged['STL'] / min_factor) * 48 * (100 / pace_factor)
        merged['PER100_BLK'] = (merged['BLK'] / min_factor) * 48 * (100 / pace_factor)
        merged['PER100_FG3M'] = (merged['FG3M'] / min_factor) * 48 * (100 / pace_factor)
        merged['PER100_FTM'] = (merged['FTM'] / min_factor) * 48 * (100 / pace_factor)
        merged['PER100_PFD'] = (merged['PFD'] / min_factor) * 48 * (100 / pace_factor)

        self.df = merged.reset_index(drop=True)
        print(f"[Similarity Engine] Successfully loaded & prepared multi-season vector space for {len(self.df)} player-season profiles.")

    def get_player_list(self) -> List[str]:
        """Get sorted list of all available player-season names (DISPLAY_NAME_SEASON)."""
        if self.df.empty or 'DISPLAY_NAME_SEASON' not in self.df.columns:
            return []
        return sorted(self.df['DISPLAY_NAME_SEASON'].dropna().unique().tolist())

    def get_season_list(self) -> List[str]:
        """Get sorted list of available seasons."""
        if self.df.empty or 'SEASON' not in self.df.columns:
            return []
        return sorted(self.df['SEASON'].dropna().unique().tolist(), reverse=True)

    def get_feature_columns(self, stat_mode: str = "Per Game") -> List[str]:
        """Return expanded metric column names based on selected stat mode."""
        if stat_mode == "Per 36 Minutes":
            return [
                'PER36_PTS', 'PER36_REB', 'PER36_OREB', 'PER36_DREB', 'PER36_AST',
                'PER36_STL', 'PER36_BLK', 'PER36_FG3M', 'PER36_FTM', 'PER36_PFD',
                'FG_PCT', 'FG3_PCT', 'FT_PCT', 'eFG_PCT', 'TS_PCT', 'AST_TO_RATIO',
                'PLUS_MINUS', 'AGE'
            ]
        elif stat_mode == "Per 100 Possessions":
            return [
                'PER100_PTS', 'PER100_REB', 'PER100_OREB', 'PER100_DREB', 'PER100_AST',
                'PER100_STL', 'PER100_BLK', 'PER100_FG3M', 'PER100_FTM', 'PER100_PFD',
                'FG_PCT', 'FG3_PCT', 'FT_PCT', 'eFG_PCT', 'TS_PCT', 'AST_TO_RATIO',
                'PLUS_MINUS', 'AGE'
            ]
        else: # Per Game
            return [
                'PTS', 'REB', 'OREB', 'DREB', 'AST', 'STL', 'BLK',
                'FG3M', 'FTM', 'PFD', 'FG_PCT', 'FG3_PCT', 'FT_PCT',
                'eFG_PCT', 'TS_PCT', 'AST_TO_RATIO', 'PLUS_MINUS',
                'NBA_FANTASY_PTS', 'AGE'
            ]

    def find_similar_players(self, target_player_season: str, top_n: int = 5,
                             stat_mode: str = "Per Game",
                             target_season_filter: Optional[str] = "All",
                             allow_same_player: bool = False,
                             unique_players_only: bool = True,
                             max_salary: Optional[float] = None, min_salary: Optional[float] = None,
                             min_pts: Optional[float] = None, max_pts: Optional[float] = None,
                             min_reb: Optional[float] = None, max_reb: Optional[float] = None,
                             min_oreb: Optional[float] = None, max_oreb: Optional[float] = None,
                             min_dreb: Optional[float] = None, max_dreb: Optional[float] = None,
                             min_ast: Optional[float] = None, max_ast: Optional[float] = None,
                             min_stl: Optional[float] = None, max_stl: Optional[float] = None,
                             min_blk: Optional[float] = None, max_blk: Optional[float] = None,
                             min_fg3m: Optional[float] = None, max_fg3m: Optional[float] = None,
                             min_fg_pct: Optional[float] = None, max_fg_pct: Optional[float] = None,
                             min_fg3_pct: Optional[float] = None, max_fg3_pct: Optional[float] = None,
                             min_ft_pct: Optional[float] = None, max_ft_pct: Optional[float] = None,
                             min_ts_pct: Optional[float] = None, max_ts_pct: Optional[float] = None,
                             min_efg_pct: Optional[float] = None, max_efg_pct: Optional[float] = None,
                             min_ast_to: Optional[float] = None, max_ast_to: Optional[float] = None,
                             min_plus_minus: Optional[float] = None, max_plus_minus: Optional[float] = None,
                             min_pfd: Optional[float] = None, max_pfd: Optional[float] = None,
                             min_age: Optional[float] = None, max_age: Optional[float] = None,
                             stat_filters: Optional[Dict[str, Tuple[Optional[float], Optional[float]]]] = None,
                             weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
        """
        Find top_n statistically similar player-seasons using Cosine Similarity over Z-score normalized vectors.
        Includes min/max range text constraints for all 18 NBA stats & salary.
        """
        if self.df.empty:
            return pd.DataFrame()

        norm_target = normalize_player_name(target_player_season)
        target_mask = self.df['norm_display_season'] == norm_target

        if not target_mask.any():
            target_mask = self.df['norm_name'] == norm_target

        if not target_mask.any():
            print(f"[Similarity Engine] Player '{target_player_season}' not found.")
            return pd.DataFrame()

        target_idx = self.df[target_mask].index[0]
        target_norm_name = self.df.iloc[target_idx]['norm_name']
        feature_cols = self.get_feature_columns(stat_mode)

        # Standardize active display metric columns across dataset
        if stat_mode == "Per 36 Minutes":
            self.df['ACTIVE_PTS'] = self.df['PER36_PTS']
            self.df['ACTIVE_REB'] = self.df['PER36_REB']
            self.df['ACTIVE_OREB'] = self.df['PER36_OREB']
            self.df['ACTIVE_DREB'] = self.df['PER36_DREB']
            self.df['ACTIVE_AST'] = self.df['PER36_AST']
            self.df['ACTIVE_STL'] = self.df['PER36_STL']
            self.df['ACTIVE_BLK'] = self.df['PER36_BLK']
            self.df['ACTIVE_FG3M'] = self.df['PER36_FG3M']
            self.df['ACTIVE_FTM'] = self.df['PER36_FTM']
            self.df['ACTIVE_PFD'] = self.df['PER36_PFD']
        elif stat_mode == "Per 100 Possessions":
            self.df['ACTIVE_PTS'] = self.df['PER100_PTS']
            self.df['ACTIVE_REB'] = self.df['PER100_REB']
            self.df['ACTIVE_OREB'] = self.df['PER100_OREB']
            self.df['ACTIVE_DREB'] = self.df['PER100_DREB']
            self.df['ACTIVE_AST'] = self.df['PER100_AST']
            self.df['ACTIVE_STL'] = self.df['PER100_STL']
            self.df['ACTIVE_BLK'] = self.df['PER100_BLK']
            self.df['ACTIVE_FG3M'] = self.df['PER100_FG3M']
            self.df['ACTIVE_FTM'] = self.df['PER100_FTM']
            self.df['ACTIVE_PFD'] = self.df['PER100_PFD']
        else: # Per Game
            self.df['ACTIVE_PTS'] = self.df['PTS']
            self.df['ACTIVE_REB'] = self.df['REB']
            self.df['ACTIVE_OREB'] = self.df['OREB']
            self.df['ACTIVE_DREB'] = self.df['DREB']
            self.df['ACTIVE_AST'] = self.df['AST']
            self.df['ACTIVE_STL'] = self.df['STL']
            self.df['ACTIVE_BLK'] = self.df['BLK']
            self.df['ACTIVE_FG3M'] = self.df['FG3M']
            self.df['ACTIVE_FTM'] = self.df['FTM']
            self.df['ACTIVE_PFD'] = self.df['PFD']

        # Extract & scale feature matrix
        X = self.df[feature_cols].copy().fillna(0).values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Apply custom weights if provided
        if weights:
            weight_vector = np.array([weights.get(col, 1.0) for col in feature_cols])
            X_scaled = X_scaled * weight_vector

        # Compute cosine similarity
        target_vec = X_scaled[target_idx].reshape(1, -1)
        sim_scores = cosine_similarity(target_vec, X_scaled)[0]

        # Filter candidates
        candidate_indices = list(range(len(self.df)))

        # Season filter
        if target_season_filter and target_season_filter != "All Seasons" and target_season_filter != "All":
            candidate_indices = [i for i in candidate_indices if self.df.iloc[i]['SEASON'] == target_season_filter]

        # Exclude target player itself
        if allow_same_player:
            candidate_indices = [i for i in candidate_indices if i != target_idx]
        else:
            candidate_indices = [i for i in candidate_indices if self.df.iloc[i]['norm_name'] != target_norm_name]

        # Consolidate Range Filters dictionary
        filters = dict(stat_filters) if stat_filters else {}
        kwarg_map = {
            'salary': (min_salary, max_salary),
            'AGE': (min_age, max_age),
            'PTS': (min_pts, max_pts),
            'REB': (min_reb, max_reb),
            'OREB': (min_oreb, max_oreb),
            'DREB': (min_dreb, max_dreb),
            'AST': (min_ast, max_ast),
            'STL': (min_stl, max_stl),
            'BLK': (min_blk, max_blk),
            'FG3M': (min_fg3m, max_fg3m),
            'FG_PCT': (min_fg_pct, max_fg_pct),
            'FG3_PCT': (min_fg3_pct, max_fg3_pct),
            'FT_PCT': (min_ft_pct, max_ft_pct),
            'TS_PCT': (min_ts_pct, max_ts_pct),
            'eFG_PCT': (min_efg_pct, max_efg_pct),
            'AST_TO_RATIO': (min_ast_to, max_ast_to),
            'PLUS_MINUS': (min_plus_minus, max_plus_minus),
            'PFD': (min_pfd, max_pfd),
        }
        for k, v in kwarg_map.items():
            if (v[0] is not None or v[1] is not None) and k not in filters:
                filters[k] = v

        # Apply Range Filters across ALL stats
        for stat_key, (min_v, max_v) in filters.items():
            if min_v is None and max_v is None:
                continue

            if stat_key == 'salary':
                if min_v is not None:
                    candidate_indices = [i for i in candidate_indices if pd.notnull(self.df.iloc[i]['salary']) and (self.df.iloc[i]['salary'] / 1e6) >= min_v]
                if max_v is not None:
                    candidate_indices = [i for i in candidate_indices if pd.notnull(self.df.iloc[i]['salary']) and (self.df.iloc[i]['salary'] / 1e6) <= max_v]
            elif stat_key in ['FG_PCT', 'FG3_PCT', 'FT_PCT', 'TS_PCT', 'eFG_PCT']:
                if min_v is not None:
                    candidate_indices = [i for i in candidate_indices if (self.df.iloc[i][stat_key] * 100) >= min_v]
                if max_v is not None:
                    candidate_indices = [i for i in candidate_indices if (self.df.iloc[i][stat_key] * 100) <= max_v]
            else:
                col_name = f"ACTIVE_{stat_key}" if f"ACTIVE_{stat_key}" in self.df.columns else stat_key
                if col_name in self.df.columns:
                    if min_v is not None:
                        candidate_indices = [i for i in candidate_indices if self.df.iloc[i][col_name] >= min_v]
                    if max_v is not None:
                        candidate_indices = [i for i in candidate_indices if self.df.iloc[i][col_name] <= max_v]

        if not candidate_indices:
            return pd.DataFrame()

        # Sort candidate indices by similarity score descending
        cand_scores = sim_scores[candidate_indices]
        sorted_cand_indices = [candidate_indices[i] for i in np.argsort(cand_scores)[::-1]]

        # Deduplicate candidates by unique player if unique_players_only is True
        if unique_players_only:
            seen_names = set()
            unique_top_indices = []
            for idx in sorted_cand_indices:
                p_norm_name = self.df.iloc[idx]['norm_name']
                if p_norm_name not in seen_names:
                    seen_names.add(p_norm_name)
                    unique_top_indices.append(idx)
                    if len(unique_top_indices) >= top_n:
                        break
            top_indices = unique_top_indices
        else:
            top_indices = sorted_cand_indices[:top_n]

        results = self.df.iloc[top_indices].copy()
        results['SIMILARITY_SCORE'] = (sim_scores[top_indices] * 100).round(1)

        # Create standardized active display metric columns
        if stat_mode == "Per 36 Minutes":
            results['ACTIVE_PTS'] = results['PER36_PTS']
            results['ACTIVE_REB'] = results['PER36_REB']
            results['ACTIVE_OREB'] = results['PER36_OREB']
            results['ACTIVE_DREB'] = results['PER36_DREB']
            results['ACTIVE_AST'] = results['PER36_AST']
            results['ACTIVE_STL'] = results['PER36_STL']
            results['ACTIVE_BLK'] = results['PER36_BLK']
            results['ACTIVE_FG3M'] = results['PER36_FG3M']
            results['ACTIVE_FTM'] = results['PER36_FTM']
            results['ACTIVE_PFD'] = results['PER36_PFD']
        elif stat_mode == "Per 100 Possessions":
            results['ACTIVE_PTS'] = results['PER100_PTS']
            results['ACTIVE_REB'] = results['PER100_REB']
            results['ACTIVE_OREB'] = results['PER100_OREB']
            results['ACTIVE_DREB'] = results['PER100_DREB']
            results['ACTIVE_AST'] = results['PER100_AST']
            results['ACTIVE_STL'] = results['PER100_STL']
            results['ACTIVE_BLK'] = results['PER100_BLK']
            results['ACTIVE_FG3M'] = results['PER100_FG3M']
            results['ACTIVE_FTM'] = results['PER100_FTM']
            results['ACTIVE_PFD'] = results['PER100_PFD']
        else: # Per Game
            results['ACTIVE_PTS'] = results['PTS']
            results['ACTIVE_REB'] = results['REB']
            results['ACTIVE_OREB'] = results['OREB']
            results['ACTIVE_DREB'] = results['DREB']
            results['ACTIVE_AST'] = results['AST']
            results['ACTIVE_STL'] = results['STL']
            results['ACTIVE_BLK'] = results['BLK']
            results['ACTIVE_FG3M'] = results['FG3M']
            results['ACTIVE_FTM'] = results['FTM']
            results['ACTIVE_PFD'] = results['PFD']

        return results

if __name__ == "__main__":
    engine = NBASimilarityEngine()
    players = engine.get_player_list()
    if players:
        # Test max_salary=30 ($30M) constraint
        matches = engine.find_similar_players('Devin Booker (2023-24)', top_n=5, max_salary=30.0)
        print("Matches for Devin Booker under $30M:")
        print(matches[['DISPLAY_NAME_SEASON', 'SIMILARITY_SCORE', 'salary']])
