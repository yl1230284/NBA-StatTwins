"""
RealGM Scraper
Extracts NBA rosters, player contract summaries, and pre-draft info from RealGM.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Dict, List, Any

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

class RealGMScraper:
    def __init__(self, timeout: int = 15):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.timeout = timeout
        self.base_url = "https://basketball.realgm.com"

    def get_active_players(self) -> pd.DataFrame:
        """Fetch active NBA players list from RealGM."""
        url = f"{self.base_url}/nba/players"
        try:
            res = self.session.get(url, timeout=self.timeout)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')
            
            table = soup.find('table', class_='tablesorter') or soup.find('table')
            if not table:
                print("[RealGM] No player table found.")
                return pd.DataFrame()

            headers = [th.text.strip() for th in table.find('thead').find_all('th')] if table.find('thead') else []
            rows = []
            for tr in table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')[1:]:
                cols = [td.text.strip() for td in tr.find_all('td')]
                if cols:
                    rows.append(cols)

            if headers and rows:
                df = pd.DataFrame(rows, columns=headers[:len(rows[0])])
            else:
                df = pd.DataFrame(rows)
            print(f"[RealGM] Retrieved {len(df)} active player profiles.")
            return df
        except Exception as e:
            print(f"[RealGM] Error fetching RealGM player data: {e}")
            return pd.DataFrame()

    def get_draft_history(self, year: int = 2023) -> pd.DataFrame:
        """Fetch NBA draft results for a given year."""
        url = f"{self.base_url}/nba/draft/past_drafts/{year}"
        try:
            res = self.session.get(url, timeout=self.timeout)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table', class_='tablesorter') or soup.find('table')
            if not table:
                return pd.DataFrame()

            headers = [th.text.strip() for th in table.find('thead').find_all('th')] if table.find('thead') else []
            rows = []
            for tr in table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')[1:]:
                cols = [td.text.strip() for td in tr.find_all('td')]
                if cols:
                    rows.append(cols)

            df = pd.DataFrame(rows, columns=headers[:len(rows[0])] if headers else None)
            print(f"[RealGM] Retrieved {len(df)} draft picks for year {year}.")
            return df
        except Exception as e:
            print(f"[RealGM] Error fetching draft history for {year}: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    scraper = RealGMScraper()
    players = scraper.get_active_players()
    if not players.empty:
        print(players.head())
