# Repository Name: PoletoFlag (GridToFlag repo name was taken)

**How much of a Formula 1 result is decided before the lights go out?**

An interactive Dash application measuring how strongly a car's starting grid position determines where it finishes, across 75 seasons of Formula 1 (1950–2024, 25,155 race entries). Pick an era, a circuit and a starting slot, and the app returns an empirical answer: odds of winning, of a podium, median finish, and chance of not finishing.

Built for **COMP 3433 · Project 2**.

---

## Quick start

```bash
git clone https://github.com/Driszs/PoleToFlag.git
cd PoleToFlag

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

The app opens a browser tab at **http://127.0.0.1:8050**. Stop it with `Ctrl + C`.

### Notebook version

`f1_grid.ipynb` is the same application in documented cells. Open it in VS Code, select the `.venv` kernel, and Run All. The final cell starts the server and prints a link.

---

## What it does

The app is structured as a three step argument rather than a free form explorer:

1. **Choose the races** — season range, circuit, which outcome counts as success, and two data filters.
2. **The answer** — a plain English sentence plus win rate, podium rate, median finish and DNF rate, calculated live for the grid slot you picked.
3. **The evidence** — three linked charts driven by the same controls.

### Charts

| Chart | Plotly type | Question it answers |
|---|---|---|
| Outcome rate by starting slot | Bar | How steeply do a car's chances fall off with each grid slot back? |
| Grid vs finish matrix | Heatmap (`px.imshow`) | Do cars finish where they started, or does the race reshuffle them? |
| Win rate from the front by season | Line (2 traces) | Has the qualifying advantage grown or shrunk over 75 years? |

### Assignment requirements

- **Dash Core Components (6):** `RangeSlider` (seasons), `Dropdown` (circuit), `RadioItems` (outcome metric), `Checklist` (data filters), `Slider` (starting slot), `Graph` (×3).
- **Callbacks (2):** one drives the answer panel and its four statistics, one redraws all three figures.
- **Plotly plot types (3):** bar, heatmap, line.
- **Narrative:** a stated thesis in the header, numbered step headings, hint text under every control, and a caption under every chart explaining how to read it.

---

## Data

`data/f1_race_results.csv` is the cleaned analysis file the app reads. It is committed to the repo, so the app runs with no internet connection. If that file is deleted, the notebook's data cell rebuilds it by downloading the source tables.

Source: Ergast-derived Formula 1 CSVs from [muharsyad/formula-one-datasets](https://github.com/muharsyad/formula-one-datasets). The notebook downloads `race_results.csv`, `races.csv` and `circuits.csv`, joins them, and writes the flat file used by the dashboard.

### Cleaning decisions worth knowing

These affect how the numbers should be read:

- **Pit-lane starts.** Recorded as grid `0` in the source data. Recoded to one slot behind the last qualifier so the grid axis stays ordinal.
- **Did-not-qualify entries are dropped.** A car that never took the start has no meaningful grid slot. This matters most for 1950s–1980s races, which often had more entrants than starters.
- **Classified vs finished.** A car can be classified (given a finishing position) while several laps down. `dnf` means unclassified.
- **Positions gained** is `grid − finish`, so a positive number means the car moved forward. Null for cars that did not finish.
- **Small samples are suppressed.** Grid slots with fewer than 10 starts are dropped from the bar chart, and the answer panel refuses to quote a rate on fewer than 5 starts. Narrow filters show a "widen your selection" message rather than a misleading percentage.

---

## Project structure

```
PoleToFlag/
├── app.py                    # the Dash application
├── f1_grid.ipynb             # same app as an annotated notebook
├── requirements.txt
├── README.md
├── assets/
│   ├── style.css             # auto-loaded by Dash
│   └── car.svg
└── data/
    └── f1_race_results.csv   # cleaned dataset
```

`assets/style.css` is loaded automatically by Dash because of the folder name. Do not rename that directory or the app will render unstyled.

---

## Notes and known limits

- Requires Python 3.9+. On Dash 3.x the run command is `app.run()`; older tutorials use `app.run_server()`, which has been removed.
- If port 8050 is already in use, free it with `lsof -ti:8050 | xargs kill -9` on macOS/Linux, or change the last line of `app.py` to `app.run(port=8060)`.
- Selecting a single season empties the season-trend chart by design — a trend needs at least two points, and the chart says so rather than drawing a misleading single marker.
- `app.py` is generated from the notebook by its final export cell. To change the app, edit the notebook and re-run that cell rather than editing `app.py` directly.