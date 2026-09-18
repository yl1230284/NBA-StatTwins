"""
ESPN NBA Data Scraper
Fetches team rosters, player bios, and statistics using ESPN's public endpoints.
"""

import requests
import pandas as pd
from typing import Dict, List, Any, Optional

class ESPNScraper:
    def __init__(self, timeout: int = 15):
        self.session = requests.Session()
        self.timeout = timeout
        self.teams_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"

    def get_teams(self) -> List[Dict[str, Any]]:
        """Fetch all NBA teams with IDs, names, and logos."""
        try:
            res = self.session.get(self.teams_url, timeout=self.timeout)
            if res.status_code != 200:
                print(f"[ESPN] HTTP {res.status_code} fetching teams")
                return []
            data = res.json()
            teams = []
            sports = data.get('sports', [])
            if sports:
                leagues = sports[0].get('leagues', [])
                if leagues:
                    for t in leagues[0].get('teams', []):
                        team_info = t.get('team', {})
                        teams.append({
                            'team_id': team_info.get('id'),
                            'abbreviation': team_info.get('abbreviation'),
                            'name': team_info.get('displayName'),
                            'short_name': team_info.get('shortDisplayName'),
                            'color': team_info.get('color'),
                            'alternate_color': team_info.get('alternateColor'),
                        })
            print(f"[ESPN] Retrieved {len(teams)} NBA teams.")
            return teams
        except Exception as e:
            print(f"[ESPN] Error fetching teams: {e}")
            return []

    def get_all_rosters(self) -> pd.DataFrame:
        """Fetch rosters for all 30 NBA teams."""
        teams = self.get_teams()
        all_players = []

        for team in teams:
            team_id = team['team_id']
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}?enable=roster"
            try:
                res = self.session.get(url, timeout=self.timeout)
                if res.status_code != 200:
                    continue
                data = res.json()
                team_data = data.get('team', {})
                athletes = team_data.get('athletes', [])
                for ath in athletes:
                    pos = ath.get('position', {})
                    headshot = ath.get('headshot', {}).get('href', '')
                    contract = ath.get('contract', {})
                    draft = ath.get('draft', {})
                    all_players.append({
                        'espn_id': ath.get('id'),
                        'name': ath.get('displayName'),
                        'full_name': ath.get('fullName'),
                        'jersey': ath.get('jersey'),
                        'position': pos.get('abbreviation'),
                        'position_name': pos.get('displayName'),
                        'height': ath.get('displayHeight'),
                        'weight': ath.get('displayWeight'),
                        'age': ath.get('age'),
                        'team_name': team['name'],
                        'team_abbr': team['abbreviation'],
                        'headshot_url': headshot,
                        'experience_years': ath.get('experience', {}).get('years'),
                        'salary': contract.get('salary'),
                        'years_remaining': contract.get('yearsRemaining'),
                        'draft_year': draft.get('year'),
                        'draft_round': draft.get('round'),
                        'draft_selection': draft.get('selection'),
                    })
            except Exception as e:
                print(f"[ESPN] Error fetching roster for team {team['name']}: {e}")

        df = pd.DataFrame(all_players)
        print(f"[ESPN] Retrieved {len(df)} total players across all rosters.")
        return df

    def get_player_overview(self, athlete_id: str) -> Dict[str, Any]:
        """Fetch detailed bio data for a specific athlete ID."""
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{athlete_id}"
        try:
            res = self.session.get(url, timeout=self.timeout)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"[ESPN] Error fetching athlete overview for {athlete_id}: {e}")
            return {}

if __name__ == "__main__":
    scraper = ESPNScraper()
    roster_df = scraper.get_all_rosters()
    if not roster_df.empty:
        print(roster_df.head())
