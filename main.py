"""
NBA Player Data Extraction Pipeline Main Entrypoint
Orchestrates data collection across NBA Stats, ESPN, HoopsHype, and RealGM over multiple seasons.
"""

import argparse
import sys
import os

# Add project root directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.nba_stats import NBAStatsScraper
from scrapers.espn import ESPNScraper
from scrapers.hoopshype import HoopsHypeScraper
from scrapers.realgm import RealGMScraper
from scrapers.historical_salaries import HistoricalSalaryScraper
from utils.exporter import DataExporter

DEFAULT_SEASONS = ["2022-23", "2023-24", "2024-25"]

def run_pipeline(sources: list, seasons: list = DEFAULT_SEASONS, export_format: str = "all"):
    exporter = DataExporter()

    print("==================================================")
    print("    MULTI-SEASON NBA PLAYER DATA PIPELINE         ")
    print(f"    Target Seasons: {seasons}                     ")
    print("==================================================")

    # 1. ESPN NBA Scraper & Historical Salaries
    if "espn" in sources or "all" in sources:
        print("\n--- Running ESPN NBA Scraper ---")
        espn = ESPNScraper()
        rosters_df = espn.get_all_rosters()
        if not rosters_df.empty:
            if export_format in ["csv", "all"]:
                exporter.export_csv(rosters_df, "espn_rosters.csv")
            if export_format in ["json", "all"]:
                exporter.export_json(rosters_df, "espn_rosters.json")
            if export_format in ["sqlite", "all"]:
                exporter.export_sqlite(rosters_df, "espn_rosters")

            # Scrape historical season-by-season salaries
            print("\n--- Running ESPN Historical Salaries Scraper ---")
            roster_list = rosters_df.to_dict(orient="records")
            hist_scraper = HistoricalSalaryScraper()
            hist_sal_df = hist_scraper.scrape_all_historical_salaries(roster_list)
            if not hist_sal_df.empty:
                if export_format in ["csv", "all"]:
                    exporter.export_csv(hist_sal_df, "espn_historical_salaries.csv")
                if export_format in ["json", "all"]:
                    exporter.export_json(hist_sal_df, "espn_historical_salaries.json")
                if export_format in ["sqlite", "all"]:
                    exporter.export_sqlite(hist_sal_df, "espn_historical_salaries")

    # 2. NBA Stats Scraper (Multi-Season)
    if "nba_stats" in sources or "all" in sources:
        print("\n--- Running NBA Stats API Scraper (Multi-Season) ---")
        nba = NBAStatsScraper()
        
        # Multi-season box score statistics
        stats_df = nba.get_multi_season_player_stats(seasons=seasons)
        if not stats_df.empty:
            if export_format in ["csv", "all"]:
                exporter.export_csv(stats_df, "nba_season_stats.csv")
            if export_format in ["json", "all"]:
                exporter.export_json(stats_df, "nba_season_stats.json")
            if export_format in ["sqlite", "all"]:
                exporter.export_sqlite(stats_df, "nba_season_stats")

        # Active players index for latest season
        latest_season = seasons[-1] if seasons else "2024-25"
        active_df = nba.get_active_players(season=latest_season)
        if not active_df.empty:
            if export_format in ["csv", "all"]:
                exporter.export_csv(active_df, "nba_active_players.csv")
            if export_format in ["sqlite", "all"]:
                exporter.export_sqlite(active_df, "nba_active_players")

    # 3. HoopsHype Salary Scraper
    if "hoopshype" in sources or "all" in sources:
        print("\n--- Running HoopsHype Salary Scraper ---")
        hh = HoopsHypeScraper()
        salaries_df = hh.get_player_salaries()
        if not salaries_df.empty:
            if export_format in ["csv", "all"]:
                exporter.export_csv(salaries_df, "hoopshype_salaries.csv")
            if export_format in ["json", "all"]:
                exporter.export_json(salaries_df, "hoopshype_salaries.json")
            if export_format in ["sqlite", "all"]:
                exporter.export_sqlite(salaries_df, "hoopshype_salaries")

    # 4. RealGM Scraper
    if "realgm" in sources or "all" in sources:
        print("\n--- Running RealGM Scraper ---")
        rgm = RealGMScraper()
        rgm_players_df = rgm.get_active_players()
        if not rgm_players_df.empty:
            if export_format in ["csv", "all"]:
                exporter.export_csv(rgm_players_df, "realgm_players.csv")
            if export_format in ["sqlite", "all"]:
                exporter.export_sqlite(rgm_players_df, "realgm_players")

    print("\n==================================================")
    print(" Pipeline Completed! Check the 'output/' directory. ")
    print("==================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NBA Player Data Scraping & Extraction Pipeline")
    parser.add_argument("--sources", nargs="+", default=["all"],
                        choices=["all", "espn", "nba_stats", "hoopshype", "realgm"],
                        help="Data sources to scrape")
    parser.add_argument("--seasons", nargs="+", default=DEFAULT_SEASONS, help="List of NBA Seasons (e.g., 2022-23 2023-24 2024-25)")
    parser.add_argument("--format", type=str, default="all", choices=["csv", "json", "sqlite", "all"],
                        help="Export format for extracted data")

    args = parser.parse_args()
    run_pipeline(sources=args.sources, seasons=args.seasons, export_format=args.format)
