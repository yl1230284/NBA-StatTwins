"""
NBA.com Stats Scraper / Data Extractor
Extracts active NBA player list, traditional season stats, and bio metrics across multiple seasons using NBA.com API endpoints.
"""

import json
import time
import requests
import pandas as pd
from typing import List, Dict, Any, Optional

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://www.nba.com',
    'Referer': 'https://www.nba.com/stats',
    'Connection': 'keep-alive',
}

class NBAStatsScraper:
    def __init__(self, timeout: int = 35):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.timeout = timeout

    def get_active_players(self, season: str = "2025-26") -> pd.DataFrame:
        """Fetch list of all active NBA players for a season."""
        try:
            from nba_api.stats.endpoints import commonallplayers
            endpoint = commonallplayers.CommonAllPlayers(is_only_current_season=1, season=season, timeout=self.timeout)
            df = endpoint.get_data_frames()[0]
            df['SEASON'] = season
            print(f"[NBA Stats] Retrieved {len(df)} active players for {season} via nba_api.")
            return df
        except Exception as ex:
            print(f"[NBA Stats] nba_api attempt failed: {ex}, attempting direct API call...")

        url = f"https://stats.nba.com/stats/commonallplayers?IsOnlyCurrentSeason=1&LeagueID=00&Season={season}"
        try:
            res = self.session.get(url, timeout=self.timeout)
            res.raise_for_status()
            data = res.json()
            result_set = data['resultSets'][0]
            df = pd.DataFrame(result_set['rowSet'], columns=result_set['headers'])
            df['SEASON'] = season
            print(f"[NBA Stats] Retrieved {len(df)} active players for {season} via direct API.")
            return df
        except Exception as e:
            print(f"[NBA Stats] Error fetching active players: {e}")
            return pd.DataFrame()

    def get_single_season_player_stats(self, season: str, per_mode: str = "PerGame") -> pd.DataFrame:
        """Fetch player stats and advanced PACE/POSS for a single season."""
        base_df = pd.DataFrame()
        adv_df = pd.DataFrame()

        try:
            from nba_api.stats.endpoints import leaguedashplayerstats
            base_endpoint = leaguedashplayerstats.LeagueDashPlayerStats(season=season, per_mode_detailed=per_mode, timeout=self.timeout)
            base_df = base_endpoint.get_data_frames()[0]
            
            try:
                adv_endpoint = leaguedashplayerstats.LeagueDashPlayerStats(season=season, measure_type_detailed_defense='Advanced', timeout=self.timeout)
                adv_df = adv_endpoint.get_data_frames()[0]
            except Exception as adv_e:
                print(f"[NBA Stats] Advanced stats fetch error for {season}: {adv_e}")

            if not base_df.empty:
                base_df['SEASON'] = season
                base_df['DISPLAY_NAME_SEASON'] = base_df['PLAYER_NAME'] + " (" + season + ")"

                if not adv_df.empty and 'PLAYER_ID' in adv_df.columns:
                    adv_cols = [c for c in ['PLAYER_ID', 'PACE', 'POSS'] if c in adv_df.columns]
                    adv_subset = adv_df[adv_cols].drop_duplicates(subset=['PLAYER_ID'])
                    base_df = pd.merge(base_df, adv_subset, on='PLAYER_ID', how='left')

                print(f"[NBA Stats] Retrieved stats (Base + Advanced PACE/POSS) for {len(base_df)} players ({season}) via nba_api.")
                return base_df
        except Exception as ex:
            print(f"[NBA Stats] nba_api leaguedashplayerstats failed for {season}: {ex}, attempting direct API call...")

        url = (
            f"https://stats.nba.com/stats/leaguedashplayerstats?"
            f"College=&Conference=&Country=&DateFrom=&DateTo=&Division=&DraftPick=&"
            f"DraftYear=&GameScope=&GameSegment=&Height=&LastNGames=0&LeagueID=00&"
            f"Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&"
            f"PORound=0&PaceAdjust=N&PerMode={per_mode}&Period=0&PlayerExperience=&"
            f"PlayerPosition=&PlusMinus=N&Rank=N&Season={season}&SeasonSegment=&"
            f"SeasonType=Regular+Season&ShotClockRange=&StarterBench=&TeamID=0&"
            f"VsConference=&VsDivision=&Weight="
        )
        try:
            res = self.session.get(url, timeout=self.timeout)
            res.raise_for_status()
            data = res.json()
            result_set = data['resultSets'][0]
            df = pd.DataFrame(result_set['rowSet'], columns=result_set['headers'])
            df['SEASON'] = season
            df['DISPLAY_NAME_SEASON'] = df['PLAYER_NAME'] + " (" + season + ")"
            print(f"[NBA Stats] Retrieved stats for {len(df)} players ({season}).")
            return df
        except Exception as e:
            print(f"[NBA Stats] Error fetching player season stats for {season}: {e}")
            return pd.DataFrame()

    def get_multi_season_player_stats(self, seasons: List[str], per_mode: str = "PerGame") -> pd.DataFrame:
        """Fetch player stats across multiple seasons and concatenate results."""
        dfs = []
        for season in seasons:
            time.sleep(1) # Friendly delay between API requests
            df = self.get_single_season_player_stats(season=season, per_mode=per_mode)
            if not df.empty:
                dfs.append(df)
        
        if dfs:
            combined_df = pd.concat(dfs, ignore_index=True)
            print(f"[NBA Stats] Combined total {len(combined_df)} player-season records across {len(seasons)} seasons.")
            return combined_df
        return pd.DataFrame()

if __name__ == "__main__":
    scraper = NBAStatsScraper()
    multi_df = scraper.get_multi_season_player_stats(["2022-23", "2023-24", "2024-25", "2025-26"])
    if not multi_df.empty:
        print(multi_df[['DISPLAY_NAME_SEASON', 'PTS', 'REB', 'AST']].head())
