# NBA StatTwins - UI / UX Roadmap & TODO List

Tracking planned UI / UX fixes and visual enhancements for the **NBA StatTwins** Streamlit dashboard.

Tracked GitHub Issue: [#1 - UI / UX Roadmap: Improvements & Fixes for NBA StatTwins Dashboard](https://github.com/yl1230284/NBA-StatTwins/issues/1)

---

### 1. Vector Similarity Search & Results Cards
- [ ] **Player Card Styling**: Properly wrap candidate cards with `.candidate-card` CSS container styling (currently missing custom container class).
- [ ] **Metric Badges / Pills**: Replace raw pipe-separated text (`**PTS**: 24.2 | **REB**: 7.8`) with structured, styled stat pill badges.
- [ ] **Headshot Fallback Avatar**: Display a sleek silhouette or team logo placeholder when a player headshot URL is missing or returns a 404.
- [ ] **Target Player Headshot**: Display the target player's ESPN headshot inside the Target Profile card (currently only candidates render images).
- [ ] **Stat Delta Comparison**: Add visual `+ / -` difference indicators comparing the candidate's stats directly against the target player's stats.
- [ ] **Export Matches**: Add a one-click **"Export Matches to CSV"** button in the similarity results section.

---

### 2. Filter Controls & Focus Weight Sliders
- [ ] **Tabbed / Categorized Weights**: Organize the 19 individual attribute sliders into clean sub-tabs (e.g. *Scoring*, *Playmaking*, *Defense*, *Rebounding & Impact*) to minimize vertical scrolling fatigue.
- [ ] **Active Weight Summary**: Display a quick badge counter showing how many stats are currently non-zero / custom-weighted.
- [ ] **Hard Range Filter Reset**: Add a one-click **"Reset All Filters"** button for Candidate Criteria (Min/Max inputs).
- [ ] **Compact Number Inputs**: Reduce whitespace in the candidate criteria filter section for better density on standard laptop screens.

---

### 3. Head-to-Head Comparison & Radar Chart
- [ ] **Player Avatars in H2H**: Surface player headshots, team badges, position, and contract salary for Player 1 and Player 2 side-by-side.
- [ ] **Dynamic Radar Scaling**: Replace hardcoded stat maximums with dynamic percentiles or min-max normalization based on active league stats.
- [ ] **Stat Leader Highlighting**: Add visual green/accent indicator badges on whichever player leads each box score category.
- [ ] **Expanded H2H Metrics**: Add defensive box score metrics and advanced shooting splits (FT%, FTM, PFD) into the H2H table.

---

### 4. Salary vs. Production Matrix
- [ ] **Dynamic Axis Selectors**: Allow users to select custom X-axis, Y-axis, and Bubble Size metrics (e.g. Salary vs. True Shooting %, Salary vs. Fantasy Points).
- [ ] **Team & Conference Filters**: Add team multiselect and Eastern/Western conference filters to isolate specific rosters on the scatter plot.
- [ ] **Value Trendline**: Add an expected value / regression trendline to instantly highlight players performing above or below their contract expectations.

---

### 5. Layout, Responsiveness & Theming
- [ ] **Mobile & Responsive Layout**: Optimize column layouts (`st.columns`) for narrow viewports to avoid metric truncation or horizontal scrollbars.
- [ ] **Consistent Dark Theme**: Ensure all custom CSS classes harmonize smoothly with native Streamlit dark/light theme switching.
- [ ] **Progress / Loading Feedback**: Add `st.spinner()` during similarity vector recomputation.
