"""
Incremental NBA Season Stats Update Utility
Refreshes the ongoing season (e.g. 2026-27) stats from the NBA Stats API without
wiping historical season data (2022-26).
"""

import os
import json
import sqlite3
import argparse
import pandas as pd
from scrapers.nba_stats import NBAStatsScraper
from scrapers.historical_salaries import HistoricalSalaryScraper
from utils.exporter import DataExporter

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "nba_data.db")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

def update_season(season: str = "2026-27", update_salaries: bool = False):
    print("==================================================")
    print(f"      UPDATING NBA SEASON STATS: {season}         ")
    print("==================================================")
    
    exporter = DataExporter()
    nba = NBAStatsScraper()
    
    # 1. Fetch updated player stats for target season from NBA API
    print(f"\n[Step 1] Fetching live {season} box score & advanced stats...")
    new_stats_df = nba.get_single_season_player_stats(season)
    if new_stats_df.empty:
        print(f"[Error] Could not retrieve {season} stats from NBA API.")
        return
    print(f"Retrieved {len(new_stats_df)} player records for {season}.")

    # Load existing nba_season_stats from database to merge
    with sqlite3.connect(DB_PATH) as conn:
        try:
            existing_stats_df = pd.read_sql_query("SELECT * FROM nba_season_stats", conn)
        except Exception:
            existing_stats_df = pd.DataFrame()

    if not existing_stats_df.empty:
        # Keep past seasons and overwrite target season with fresh data
        past_seasons_df = existing_stats_df[existing_stats_df['SEASON'] != season].copy()
        combined_stats = pd.concat([past_seasons_df, new_stats_df], ignore_index=True)
    else:
        combined_stats = new_stats_df

    print(f"Total multi-season profiles after merge: {len(combined_stats)}")
    exporter.export_sqlite(combined_stats, "nba_season_stats")
    exporter.export_csv(combined_stats, "nba_season_stats.csv")
    exporter.export_json(combined_stats, "nba_season_stats.json")

    # 2. Update active players for target season
    print(f"\n[Step 2] Fetching active players index for {season}...")
    active_df = nba.get_active_players(season=season)
    if not active_df.empty:
        exporter.export_sqlite(active_df, "nba_active_players")
        exporter.export_csv(active_df, "nba_active_players.csv")

    # 3. Optional: Refresh salaries
    if update_salaries:
        print(f"\n[Step 3] Fetching contracts & salaries from ESPN...")
        rosters_json_path = os.path.join(OUTPUT_DIR, "espn_rosters.json")
        if os.path.exists(rosters_json_path):
            with open(rosters_json_path, "r", encoding="utf-8") as f:
                rosters = json.load(f)
            
            hist_scraper = HistoricalSalaryScraper(max_workers=25)
            new_sal_df = hist_scraper.scrape_all_historical_salaries(rosters)
            
            if not new_sal_df.empty:
                exporter.export_sqlite(new_sal_df, "espn_historical_salaries")
                exporter.export_csv(new_sal_df, "espn_historical_salaries.csv")
                exporter.export_json(new_sal_df, "espn_historical_salaries.json")

    print("\n==================================================")
    print(f" {season} Season Successfully Updated!           ")
    print("==================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update NBA Season Stats Incrementally")
    parser.add_argument("--season", type=str, default="2026-27", help="NBA Season to update (e.g., 2026-27)")
    parser.add_argument("--with-salaries", action="store_true", help="Also refresh player salaries from ESPN")
    args = parser.parse_args()

    update_season(season=args.season, update_salaries=args.with_salaries)
