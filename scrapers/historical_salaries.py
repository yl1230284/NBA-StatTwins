"""
Historical Salary Scraper Module
Extracts season-by-season contract salaries for NBA players across historical seasons (2022-23 to 2025-26)
using ESPN's athlete contract API.
"""

import os
import json
import requests
import sqlite3
import pandas as pd
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "nba_data.db")
ROSTERS_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "espn_rosters.json")

SEASON_YEAR_MAP = {
    "2022-23": 2023,
    "2023-24": 2024,
    "2024-25": 2025,
    "2025-26": 2026
}

class HistoricalSalaryScraper:
    def __init__(self, max_workers: int = 25):
        self.max_workers = max_workers

    def fetch_player_historical_salaries(self, player_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        espn_id = player_dict.get('espn_id')
        name = player_dict.get('name') or player_dict.get('full_name')
        if not espn_id or not name:
            return []

        salaries = []
        for season_label, year_code in SEASON_YEAR_MAP.items():
            url = f"http://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes/{espn_id}/contracts/{year_code}?lang=en&region=us"
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    sal = data.get('salary', None)
                    if sal and float(sal) > 0:
                        salaries.append({
                            'espn_id': str(espn_id),
                            'PLAYER_NAME': name,
                            'SEASON': season_label,
                            'salary': float(sal)
                        })
            except Exception:
                pass
        return salaries

    def scrape_all_historical_salaries(self, rosters: List[Dict[str, Any]]) -> pd.DataFrame:
        print(f"[Historical Salary Scraper] Fetching season-by-season salaries for {len(rosters)} players...")
        all_records = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.fetch_player_historical_salaries, p) for p in rosters]
            for f in futures:
                all_records.extend(f.result())

        if not all_records:
            print("[Historical Salary Scraper] Warning: No historical salary records fetched.")
            return pd.DataFrame()

        df = pd.DataFrame(all_records)
        print(f"[Historical Salary Scraper] Successfully retrieved {len(df)} historical salary records across seasons.")
        return df

if __name__ == "__main__":
    if os.path.exists(ROSTERS_JSON):
        with open(ROSTERS_JSON, "r") as f:
            roster_data = json.load(f)
        scraper = HistoricalSalaryScraper()
        df_sal = scraper.scrape_all_historical_salaries(roster_data)
        if not df_sal.empty:
            print(df_sal.head(15))
