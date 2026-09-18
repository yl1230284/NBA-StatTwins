"""
HoopsHype Scraper
Extracts player salaries and multi-year contract breakdowns from HoopsHype.
"""

import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Optional, List, Dict, Any

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

class HoopsHypeScraper:
    def __init__(self, timeout: int = 15):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.timeout = timeout
        self.salaries_url = "https://hoopshype.com/salaries/players/"

    def get_player_salaries(self) -> pd.DataFrame:
        """Fetch current and multi-year salary data for NBA players."""
        try:
            res = self.session.get(self.salaries_url, timeout=self.timeout)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')
            
            table = soup.find('table', class_=re.compile(r'hh-salaries-ranking-table|salaries-table|hh-salaries-table'))
            if not table:
                # Find any table with salary rows
                tables = soup.find_all('table')
                for t in tables:
                    if 'Player' in t.text or 'Salary' in t.text or '$' in t.text:
                        table = t
                        break

            if not table:
                print("[HoopsHype] Could not locate salary table on page.")
                return pd.DataFrame()

            # Parse headers
            headers = []
            header_row = table.find('tr')
            if header_row:
                headers = [th.text.strip() for th in header_row.find_all(['th', 'td'])]
            
            if not headers or len(headers) < 2:
                headers = ['Rank', 'Player', '2023-24', '2024-25', '2025-26', '2026-27']

            rows_data = []
            for tr in table.find_all('tr')[1:]:
                cols = [td.text.strip() for td in tr.find_all('td')]
                if len(cols) >= 2:
                    rows_data.append(cols)

            # Clean columns to match row length
            max_cols = max(len(r) for r in rows_data) if rows_data else 0
            if len(headers) < max_cols:
                headers.extend([f"Col_{i}" for i in range(len(headers), max_cols)])
            elif len(headers) > max_cols:
                headers = headers[:max_cols]

            df = pd.DataFrame(rows_data, columns=headers)
            print(f"[HoopsHype] Retrieved salary records for {len(df)} players.")
            return df
        except Exception as e:
            print(f"[HoopsHype] Error scraping player salaries: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    scraper = HoopsHypeScraper()
    df = scraper.get_player_salaries()
    if not df.empty:
        print(df.head())
