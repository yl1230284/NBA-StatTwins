# NBA StatTwins - Multi-Season Player Vector Similarity & Comparison Dashboard

An end-to-end Python data scraping pipeline and interactive Streamlit dashboard for vector similarity searching, multi-season player comparisons, skill radar overlays, and salary vs. box score production analytics across 4 NBA seasons (2022-23, 2023-24, 2024-25, and 2025-26).

---

## Key Features

* **4-Season Vector Space (2,119 Profiles)**: Season-disambiguated player entities (e.g. `Luka Dončić (2025-26)` vs `Luka Dončić (2023-24)`).
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

## Repository Structure

```
nba-stattwins/
├── app.py                      # Interactive Streamlit Dashboard UI
├── main.py                     # Multi-season data pipeline orchestrator
├── similarity_engine.py        # Vector similarity & Z-score feature scaling engine
├── requirements.txt            # Python dependencies
├── scrapers/
│   ├── espn.py                 # ESPN NBA rosters & bio scraper
│   ├── historical_salaries.py # Season-by-season player contract salary scraper
│   ├── hoopshype.py           # HoopsHype contract breakdown scraper
│   ├── nba_stats.py           # Multi-season NBA Stats API scraper (nba_api)
│   └── realgm.py              # RealGM backup scraper
├── utils/
│   └── exporter.py             # Data exporter (CSV, JSON, SQLite)
└── output/
    └── nba_data.db             # Consolidated SQLite database (2,119 player-season profiles)
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
