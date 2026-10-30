"""
Incremental NBA Season Stats Update Utility (Phase 2)
Refreshes the ongoing season (e.g. 2026-27) stats from the NBA Stats API without
wiping historical season data (2022-26). Tracks sync metadata and supports both
CLI execution and programmatic invocation from the Streamlit UI.
"""

import os
import json
import sqlite3
import argparse
from datetime import datetime, timezone
import pandas as pd
from scrapers.nba_stats import NBAStatsScraper
from scrapers.historical_salaries import HistoricalSalaryScraper
from utils.exporter import DataExporter

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "nba_data.db")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
METADATA_FILE = os.path.join(OUTPUT_DIR, "sync_metadata.json")

def format_timestamp(iso_str: str) -> str:
    """Format ISO timestamp into human-readable string."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y at %I:%M %p UTC")
    except Exception:
        return iso_str

def get_sync_metadata() -> dict:
    """Retrieve the latest synchronization metadata from JSON or SQLite."""
    # 1. Try reading from sync_metadata.json
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                meta = json.load(f)
                meta["last_sync_formatted"] = format_timestamp(meta.get("last_sync", ""))
                return meta
        except Exception:
            pass

    # 2. Try reading from SQLite table
    if os.path.exists(DB_PATH):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_metadata'")
                if cursor.fetchone():
                    df = pd.read_sql_query("SELECT * FROM sync_metadata ORDER BY last_sync DESC LIMIT 1", conn)
                    if not df.empty:
                        row = df.iloc[0].to_dict()
                        row["last_sync_formatted"] = format_timestamp(str(row.get("last_sync", "")))
                        return row
        except Exception:
            pass

    # 3. Fallback: inspect nba_season_stats table for 2026-27
    count_2026_27 = 0
    mod_time_iso = datetime.now(timezone.utc).isoformat()
    if os.path.exists(DB_PATH):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM nba_season_stats WHERE SEASON='2026-27'")
                res = cursor.fetchone()
                if res:
                    count_2026_27 = res[0]
            mtime = os.path.getmtime(DB_PATH)
            mod_time_iso = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
        except Exception:
            pass

    fallback_meta = {
        "season": "2026-27",
        "last_sync": mod_time_iso,
        "last_sync_formatted": format_timestamp(mod_time_iso),
        "records_count": count_2026_27,
        "status": "SUCCESS",
        "message": f"Initial dataset loaded with {count_2026_27} players."
    }
    return fallback_meta

def save_sync_metadata(metadata: dict):
    """Save sync metadata to JSON and SQLite table."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"[Sync Metadata] Warning: Could not write JSON: {e}")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            meta_df = pd.DataFrame([{
                "season": metadata.get("season", "2026-27"),
                "last_sync": metadata.get("last_sync", datetime.now(timezone.utc).isoformat()),
                "records_count": metadata.get("records_count", 0),
                "status": metadata.get("status", "SUCCESS"),
                "message": metadata.get("message", "")
            }])
            meta_df.to_sql("sync_metadata", conn, if_exists="replace", index=False)
    except Exception as e:
        print(f"[Sync Metadata] Warning: Could not write to SQLite: {e}")

def update_season(season: str = "2026-27", update_salaries: bool = False, verbose: bool = True) -> dict:
    """
    Incrementally refreshes player stats for target season from the NBA API,
    merging results with historical data in SQLite and output CSV/JSON files.
    """
    start_time = datetime.now(timezone.utc)
    if verbose:
        print("==================================================")
        print(f"      UPDATING NBA SEASON STATS: {season}         ")
        print("==================================================")

    exporter = DataExporter()
    nba = NBAStatsScraper()

    # 1. Fetch updated player stats for target season from NBA API
    if verbose:
        print(f"\n[Step 1/3] Fetching live {season} box score & advanced stats...")
    new_stats_df = nba.get_single_season_player_stats(season)

    if new_stats_df.empty:
        error_msg = f"Could not retrieve {season} stats from NBA API."
        if verbose:
            print(f"[Error] {error_msg}")
        failure_meta = {
            "season": season,
            "last_sync": start_time.isoformat(),
            "records_count": 0,
            "status": "ERROR",
            "message": error_msg
        }
        save_sync_metadata(failure_meta)
        return {"success": False, "records": 0, "season": season, "timestamp": start_time.isoformat(), "message": error_msg}

    record_count = len(new_stats_df)
    if verbose:
        print(f"Retrieved {record_count} player records for {season}.")

    # 2. Merge with existing historical seasons in SQLite
    with sqlite3.connect(DB_PATH) as conn:
        try:
            existing_stats_df = pd.read_sql_query("SELECT * FROM nba_season_stats", conn)
        except Exception:
            existing_stats_df = pd.DataFrame()

    if not existing_stats_df.empty:
        past_seasons_df = existing_stats_df[existing_stats_df['SEASON'] != season].copy()
        combined_stats = pd.concat([past_seasons_df, new_stats_df], ignore_index=True)
    else:
        combined_stats = new_stats_df

    if verbose:
        print(f"Total multi-season profiles after merge: {len(combined_stats)}")

    exporter.export_sqlite(combined_stats, "nba_season_stats")
    exporter.export_csv(combined_stats, "nba_season_stats.csv")
    exporter.export_json(combined_stats, "nba_season_stats.json")

    # 3. Update active players for target season
    if verbose:
        print(f"\n[Step 2/3] Fetching active players index for {season}...")
    active_df = nba.get_active_players(season=season)
    if not active_df.empty:
        exporter.export_sqlite(active_df, "nba_active_players")
        exporter.export_csv(active_df, "nba_active_players.csv")

    # 4. Optional: Refresh salaries
    if update_salaries:
        if verbose:
            print(f"\n[Step 3/3] Fetching contracts & salaries from ESPN...")
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

    # Record sync metadata
    success_meta = {
        "season": season,
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "records_count": record_count,
        "status": "SUCCESS",
        "message": f"Successfully updated {record_count} players for {season}."
    }
    save_sync_metadata(success_meta)

    if verbose:
        print("\n==================================================")
        print(f" {season} Season Successfully Updated! ({record_count} players) ")
        print("==================================================")

    return {
        "success": True,
        "records": record_count,
        "season": season,
        "timestamp": success_meta["last_sync"],
        "message": success_meta["message"]
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update NBA Season Stats Incrementally")
    parser.add_argument("--season", type=str, default="2026-27", help="NBA Season to update (e.g., 2026-27)")
    parser.add_argument("--with-salaries", action="store_true", help="Also refresh player salaries from ESPN")
    parser.add_argument("--check", action="store_true", help="Display current sync metadata status without updating")
    parser.add_argument("--silent", action="store_true", help="Run without printing progress to console")
    args = parser.parse_args()

    if args.check:
        meta = get_sync_metadata()
        print("==================================================")
        print("          NBA DATA SYNC STATUS                    ")
        print("==================================================")
        print(f" Season:        {meta.get('season')}")
        print(f" Status:        {meta.get('status')}")
        print(f" Last Refreshed:{meta.get('last_sync_formatted')}")
        print(f" Players Tracked:{meta.get('records_count')}")
        print(f" Details:       {meta.get('message')}")
        print("==================================================")
    else:
        update_season(season=args.season, update_salaries=args.with_salaries, verbose=not args.silent)
