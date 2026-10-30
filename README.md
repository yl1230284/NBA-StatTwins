# NBA StatTwins - Multi-Season Player Vector Similarity & Comparison Dashboard

An end-to-end Python data scraping pipeline and interactive Streamlit dashboard for vector similarity searching, multi-season player comparisons, skill radar overlays, and salary vs. box score production analytics across 5 NBA seasons (2022-23, 2023-24, 2024-25, 2025-26, and 2026-27).

---

## Key Features

* **5-Season Vector Space**: Season-disambiguated player entities (e.g. `Luka Dončić (2026-27)` vs `Luka Dončić (2023-24)`).
* **Historical Season-Specific Salaries**: Multi-threaded contract extraction matching real historical contract salaries for each respective season.
* **Vector Cosine Similarity Search**: Scikit-learn Z-score feature scaling across scoring, rebounding, playmaking, shooting efficiency, and defense metrics.
* **Comprehensive Range Filters**: Min/Max numeric text inputs for all 18 NBA statistics and salary.
* **Search Controls**:
  * **Candidate Deduplication (Default: ON)**: Shows only the single highest-matching season for each unique candidate player.
  * **Same-Player Cross-Season Toggle**: Option to allow/disallow comparing a player against their own past/future seasons.
* **Head-to-Head Skill Radar Chart**: Side-by-side metric comparison and Plotly Scatterpolar overlay.
* **Salary vs. Production Matrix**: Interactive bubble chart mapping salary ($M) against Points Per Game and total rebounds.

---

## Quick Start

### 1. Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/yl1230284/NBA-StatTwins.git
cd NBA-StatTwins
pip install -r requirements.txt
```

### 2. Run Data Pipeline (Optional)

To scrape latest stats, rosters, and historical contract data:

```bash
python main.py --seasons 2022-23 2023-24 2024-25 2025-26 --sources espn nba_stats hoopshype
```

### 3. Launch Dashboard

Run the Streamlit web app:

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Automated Live Stats Updates

To ensure the 2026-27 dataset automatically stays up-to-date as new games are played:

### 1. Cloud Automation (GitHub Actions)
A preconfigured workflow (`.github/workflows/daily_nba_sync.yml`) runs daily at **09:00 UTC (4:00 AM EST)** after west coast games conclude. It pulls fresh box scores and advanced PACE/POSS stats from the NBA Stats API, updates SQLite, CSV, and JSON files, and automatically commits the new data back to the repo (`[skip ci]`).
* **Manual Trigger**: Navigate to the **Actions** tab on GitHub, select **Daily NBA Stats Sync**, and click **Run workflow**.

### 2. In-App Refresh (Streamlit UI)
The sidebar includes a dedicated **2026-27 Live Stat Sync** card displaying the roster status and timestamp. Click **Refresh 2026-27 Stats Now** to refresh player stats directly from the web browser.

### 3. Fast CLI Incremental Sync
```bash
# Update ongoing season in ~5 seconds (preserves historical 2022-26 seasons)
python update_season_stats.py

# Check current sync timestamp and record count
python update_season_stats.py --check

# Or via main pipeline entrypoint
python main.py --sync-live
```

### 4. Local Background Scheduler
```bash
# Run daily at 04:00 AM local time
python schedule_sync.py --daily-at 04:00

# Or repeat every 12 hours
python schedule_sync.py --interval-hours 12
```

---

## Repository Structure

```
nba-stattwins/
├── .github/
│   └── workflows/
│       └── daily_nba_sync.yml      # Automated GitHub Actions daily sync workflow
├── app.py                          # Interactive Streamlit Dashboard UI
├── main.py                         # Multi-season data pipeline orchestrator
├── update_season_stats.py          # Fast incremental season stats update utility
├── schedule_sync.py                # Local background schedule runner
├── similarity_engine.py            # Vector similarity & Z-score feature scaling engine
├── requirements.txt                # Python dependencies
├── scrapers/
│   ├── espn.py                     # ESPN NBA rosters & bio scraper
│   ├── historical_salaries.py     # Season-by-season player contract salary scraper
│   ├── hoopshype.py               # HoopsHype contract breakdown scraper
│   ├── nba_stats.py               # Multi-season NBA Stats API scraper (nba_api)
│   └── realgm.py                  # RealGM backup scraper
├── utils/
│   └── exporter.py                 # Data exporter (CSV, JSON, SQLite)
└── output/
    ├── nba_data.db                 # Consolidated SQLite database (2,687 player-season profiles)
    └── sync_metadata.json          # Synchronization history and status
```

---

## Tech Stack

* **Language**: Python 3.10+
* **Dashboard Framework**: Streamlit
* **Vector Engine**: Scikit-Learn (StandardScaler, cosine_similarity)
* **Data Processing**: Pandas, NumPy
* **Visualization**: Plotly Express & Plotly Graph Objects
* **Data Scraping**: nba_api, requests, BeautifulSoup4, Concurrent ThreadPoolExecutor
* **Database**: SQLite3
