"""
Grid to Flag — How much of a Formula 1 result is decided before the lights go out?
COMP 4433 · Project 2

Run with:  python app.py     then open http://127.0.0.1:8050
"""

import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

os.makedirs("data", exist_ok=True)

if os.path.exists("data/f1_race_results.csv"):
    df = pd.read_csv("data/f1_race_results.csv")
else:
    BASE = "https://raw.githubusercontent.com/muharsyad/formula-one-datasets/main/"

    results  = pd.read_csv(BASE + "race_results.csv")
    races    = pd.read_csv(BASE + "races.csv")[["season", "round", "raceName", "circuitId"]]
    circuits = pd.read_csv(BASE + "circuits.csv")[["circuitId", "circuitName", "country"]]

    df = results.merge(races, on=["season", "round"], how="left") \
                .merge(circuits, on="circuitId", how="left")

    # 1. Drop cars that never took the start - they have no meaningful grid slot
    df = df[~df["status"].isin(["Did not qualify", "Did not prequalify", "Withdrew"])]

    # 2. Pit-lane starts are recorded as grid 0 - recode to one slot behind the last qualifier
    field_size = df.groupby(["season", "round"])["grid"].transform("max")
    df["grid"] = np.where(df["grid"] == 0, field_size + 1, df["grid"])
    df = df[df["grid"] > 0]
    df["field_size"] = field_size

    # 3. "Classified" (given a finishing position) is not the same as "finished"
    df["position"] = pd.to_numeric(df["position"], errors="coerce")
    df["classified"] = df["positionText"].astype(str).str.isdigit()
    df["dnf"] = ~df["classified"]

    # 4. Outcome flags and positions gained (positive = moved forward)
    df["positions_gained"] = np.where(df["classified"], df["grid"] - df["position"], np.nan)
    df["won"]    = (df["position"] == 1).fillna(False)
    df["podium"] = (df["position"] <= 3).fillna(False)
    df["top10"]  = (df["position"] <= 10).fillna(False)

    cols = ["season", "round", "raceName", "circuitName", "country", "driverName",
            "constructorName", "grid", "position", "points", "status", "field_size",
            "classified", "dnf", "positions_gained", "won", "podium", "top10"]
    df = df[cols].sort_values(["season", "round", "grid"])

    df.to_csv("data/f1_race_results.csv", index=False)

INK   = "#0E1117"   # page background
PANEL = "#161B24"   # card background
LINE  = "#2A3140"   # gridlines and borders
TEXT  = "#E8EAED"
MUTED = "#8B94A6"
AMBER = "#F2B33D"   # accent
CYAN  = "#4EC5C1"   # secondary

SANS = "'Inter', 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Consolas, monospace"

OUTCOMES = {
    "won":    ("Win", AMBER),
    "podium": ("Podium (top 3)", CYAN),
    "top10":  ("Top-10 finish", "#7C9CE8"),
}

PLOT_LAYOUT = dict(
    paper_bgcolor=PANEL,
    plot_bgcolor=PANEL,
    font=dict(family=SANS, color=TEXT, size=13),
    margin=dict(l=60, r=30, t=60, b=55),
    title=dict(font=dict(size=17, color=TEXT), x=0.01, xanchor="left"),
    xaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE),
    yaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE),
    hoverlabel=dict(bgcolor=INK, font=dict(family=MONO, color=TEXT), bordercolor=LINE),
)

def style_fig(fig, **kwargs):
    """Apply the house layout, letting per-figure settings override the defaults."""
    layout = dict(PLOT_LAYOUT)
    for key, value in kwargs.items():
        if key in ("xaxis", "yaxis") and isinstance(value, dict):
            merged = dict(layout.get(key, {}))
            merged.update(value)
            layout[key] = merged
        else:
            layout[key] = value
    fig.update_layout(**layout)
    return fig

def empty_fig(message="No races match these filters. Widen the season range."):
    """Shown instead of a misleading chart when a filter combination is too narrow."""
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False,
                       font=dict(family=SANS, size=15, color=MUTED))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return style_fig(fig, height=380)

# more filtering
SEASON_MIN, SEASON_MAX = int(df.season.min()), int(df.season.max())
CIRCUITS = sorted(df.circuitName.dropna().unique())

def filter_data(years, circuit, options):
    d = df[(df.season >= years[0]) & (df.season <= years[1])]
    if circuit != "ALL":
        d = d[d.circuitName == circuit]
    if "full_grids" in options:
        d = d[d.field_size >= 16]
    if "classified_only" in options:
        d = d[d.classified]
    return d

# quick check
test = filter_data([2000, 2024], "ALL", ["full_grids"])

def control_block(label, hint, component):
    """A labelled control with a one-line explanation of why it matters."""
    return html.Div([
        html.Label(label, className="ctl-label"),
        html.Span(hint, className="ctl-hint"),
        component,
    ], className="ctl-block")

def stat_card(label, value_id, note_id):
    """One statistic in the answer panel. IDs let the callback fill it in."""
    return html.Div([
        html.Div(label, className="stat-label"),
        html.Div("--", id=value_id, className="stat-value"),
        html.Div("", id=note_id, className="stat-note"),
    ], className="stat-card")

app = Dash(__name__, title="Grid to Flag | F1 starting position analysis")
server = app.server   # exposed for deployment

MARK_STYLE = {"color": "#FFFFFF", "fontSize": "11.5px",
              "fontFamily": "'JetBrains Mono', monospace"}
READOUT = {"fontFamily": MONO, "fontSize": "28px", "fontWeight": "700",
           "color": "#FFFFFF", "letterSpacing": "-.01em", "margin": "0 0 14px"}

app.layout = html.Div([

    # ---------------- Header: state the question ----------------
    html.Header([
        html.Div([
            html.Div("COMP 4433 · Project 2", className="eyebrow"),
            html.H1("GRID TO FLAG"),
            html.P("How much of a Formula 1 result is decided before the lights go out?",
                   className="thesis"),
            html.P([
                "Qualifying sets the order cars line up in. This dashboard measures how much "
                "that starting order determines the finishing order — across 75 seasons, at any "
                "circuit, for any starting slot you pick.",
                html.Br(),
                html.Strong("Set your filters below, then read the answer panel."),
            ], className="intro"),
        ], className="head-text"),
        html.Img(src="/assets/car.svg", className="car", alt="Formula 1 car illustration"),
    ]),

    # ---------------- Step 1: controls ----------------
    html.Section([
        html.H2("1 · Choose the races you want to study", className="step-head"),
        html.P("The app opens on 2000–2024 at every circuit, which is a good starting point. "
               "Every control below filters the same set of races, and everything further down "
               "the page updates as you change them.", className="section-note"),
        html.Div([

            control_block(
                "Seasons",
                "Drag either handle. Regulations changed enormously over 75 years, so era matters. "
                "Pick a range of several seasons — a single year won't have enough races to chart "
                "a trend.",
                html.Div([
                    html.Div(id="season-readout", style=READOUT),
                    dcc.RangeSlider(
                        id="season-range", min=SEASON_MIN, max=SEASON_MAX,
                        value=[2000, SEASON_MAX], step=1,
                        marks={y: {"label": str(y), "style": MARK_STYLE}
                               for y in range(1950, SEASON_MAX + 1, 10)},
                        className="amber-slider",
                    ),
                ]),
            ),

            html.Div([
                control_block(
                    "Circuit",
                    "Some tracks are far harder to overtake at than others. Start with all "
                    "circuits, then narrow to one — but keep the season range wide, since a "
                    "single track only hosts one race a year.",
                    dcc.Dropdown(
                        id="circuit-pick",
                        options=[{"label": "All circuits", "value": "ALL"}]
                                + [{"label": c, "value": c} for c in CIRCUITS],
                        value="ALL", clearable=False,
                    ),
                ),
                control_block(
                    "Outcome to measure",
                    "What counts as success. Wins are the sharpest test of the qualifying "
                    "advantage; top-10 finishes show how the midfield fares.",
                    dcc.RadioItems(
                        id="outcome-pick",
                        options=[{"label": v[0], "value": k} for k, v in OUTCOMES.items()],
                        value="podium", className="radio-row",
                    ),
                ),
            ], className="ctl-pair"),

            html.Div([
                control_block(
                    "Filters",
                    "Mechanical failures are not a driving outcome — drop DNFs to isolate "
                    "on-track position changes. Full grids only removes the sparse early years, "
                    "when some races had barely a dozen starters.",
                    dcc.Checklist(
                        id="filter-opts",
                        options=[
                            {"label": "Classified finishers only (drop DNFs)", "value": "classified_only"},
                            {"label": "Full grids only (16+ starters)", "value": "full_grids"},
                        ],
                        value=["full_grids"], className="check-col",
                    ),
                ),
                control_block(
                    "Your starting slot",
                    "The answer panel is calculated for this grid position. Slots near the back "
                    "have far fewer starts, so pair them with a wide season range.",
                    html.Div([
                        html.Div(id="grid-readout", style=READOUT),
                        dcc.Slider(
                            id="grid-pick", min=1, max=20, step=1, value=1,
                            marks={i: {"label": str(i), "style": MARK_STYLE}
                                   for i in [1, 5, 10, 15, 20]},
                            className="amber-slider",
                        ),
                    ]),
                ),
            ], className="ctl-pair"),

        ], className="control-panel"),
    ]),

    # ---------------- Step 2: the answer ----------------
    html.Section([
        html.H2("2 · The answer for your selection", className="step-head"),
        html.P("Rates are only shown when at least five cars started from your chosen slot. "
               "If you see a message instead of numbers, widen the seasons or move the slot "
               "forward.", className="section-note"),
        html.P(id="answer-sentence", className="answer-sentence"),
        html.Div([
            stat_card("Win rate",         "kpi-win", "kpi-win-note"),
            stat_card("Podium rate",      "kpi-pod", "kpi-pod-note"),
            stat_card("Median finish",    "kpi-med", "kpi-med-note"),
            stat_card("Failed to finish", "kpi-dnf", "kpi-dnf-note"),
        ], className="stat-row"),
    ], className="answer-block"),

    # ---------------- Step 3: the evidence ----------------
    html.Section([
        html.H2("3 · The evidence", className="step-head"),
        html.P("Each chart responds to the same controls above. Hover any point for the "
               "underlying counts. Charts that would rest on too little data say so rather "
               "than drawing a misleading line.", className="section-note"),
        html.Div([
            html.Div([
                dcc.Graph(id="fig-bar", config={"displayModeBar": False}),
                html.P("Read this as: of every car that started in slot P, this share achieved "
                       "the chosen outcome. The drop-off from the front row is the size of the "
                       "qualifying advantage. Slots with fewer than 10 starts are omitted.",
                       className="caption"),
            ], className="card"),

            html.Div([
                dcc.Graph(id="fig-heat", config={"displayModeBar": False}),
                html.P("Each column is one starting slot, normalised to 100%. A bright diagonal "
                       "means cars finish roughly where they started; a smeared column means the "
                       "race reshuffles that slot.", className="caption"),
            ], className="card"),

            html.Div([
                dcc.Graph(id="fig-line", config={"displayModeBar": False}),
                html.P("The long view: how reliably pole position converted into a win, season by "
                       "season. Rule changes, tyre wars and reliability eras all show up here. "
                       "Needs at least two seasons selected.", className="caption"),
            ], className="card card-wide"),
        ], className="chart-grid"),
    ]),

    html.Footer([
        html.P("Data: Ergast-derived Formula 1 race results, 1950–2024 (25,155 race entries). "
               "Pit-lane starts are recoded to one slot behind the last qualifier. Entries that "
               "failed to qualify are excluded, and cars that retired are counted as unclassified "
               "rather than given a finishing position.")
    ]),

], className="page")

@app.callback(
    Output("season-readout", "children"),
    Output("grid-readout", "children"),
    Output("answer-sentence", "children"),
    Output("kpi-win", "children"), Output("kpi-win-note", "children"),
    Output("kpi-pod", "children"), Output("kpi-pod-note", "children"),
    Output("kpi-med", "children"), Output("kpi-med-note", "children"),
    Output("kpi-dnf", "children"), Output("kpi-dnf-note", "children"),
    Input("season-range", "value"),
    Input("circuit-pick", "value"),
    Input("filter-opts", "value"),
    Input("grid-pick", "value"),
)
def update_answer(years, circuit, options, slot):
    d = filter_data(years, circuit, options)
    slot_d = d[d.grid == slot]
    where = "every circuit" if circuit == "ALL" else circuit

    season_readout = f"{years[0]} — {years[1]}"
    grid_readout   = f"P{slot}"

    # Refuse to quote a percentage from a handful of races
    if len(slot_d) < 5:
        msg = (f"Only {len(slot_d)} car(s) started P{slot} at {where} between {years[0]} and "
               f"{years[1]} — too few to quote a rate. Widen the seasons or pick another slot.")
        return (season_readout, grid_readout, msg,
                "--", "", "--", "", "--", "", "--", "")

    n   = len(slot_d)
    win = slot_d.won.mean() * 100
    pod = slot_d.podium.mean() * 100
    dnf = slot_d.dnf.mean() * 100
    med = slot_d.position.median()
    med_txt = "--" if pd.isna(med) else f"P{med:.0f}"

    sentence = (f"Starting P{slot} at {where}, {years[0]}–{years[1]}: across {n:,} race starts, "
                f"{win:.1f}% ended in victory and {pod:.1f}% ended on the podium.")

    return (
        season_readout, grid_readout, sentence,
        f"{win:.1f}%", f"{int(slot_d.won.sum()):,} wins from {n:,} starts",
        f"{pod:.1f}%", f"{int(slot_d.podium.sum()):,} podiums from {n:,} starts",
        med_txt,      "midpoint of classified finishes",
        f"{dnf:.1f}%", "retired or unclassified",
    )

@app.callback(
    Output("fig-bar", "figure"),
    Output("fig-heat", "figure"),
    Output("fig-line", "figure"),
    Input("season-range", "value"),
    Input("circuit-pick", "value"),
    Input("outcome-pick", "value"),
    Input("filter-opts", "value"),
)
def update_figures(years, circuit, outcome, options):
    d = filter_data(years, circuit, options)
    label, colour = OUTCOMES[outcome]
    span  = f"{years[0]}–{years[1]}"
    where = "all circuits" if circuit == "ALL" else circuit

    if len(d) < 30:
        blank = empty_fig()
        return blank, blank, blank

    # Chart 1: bar, outcome rate by starting slot
    by_slot = (d[d.grid <= 22].groupby("grid")
               .agg(rate=(outcome, "mean"), starts=(outcome, "size"), hits=(outcome, "sum"))
               .reset_index())
    by_slot = by_slot[by_slot.starts >= 10]
    by_slot["rate"] *= 100

    fig_bar = go.Figure(go.Bar(
        x=by_slot.grid, y=by_slot.rate,
        marker=dict(color=by_slot.rate, colorscale=[[0, LINE], [1, colour]], line_width=0),
        customdata=np.stack([by_slot.hits, by_slot.starts], axis=-1),
        hovertemplate="Started <b>P%{x}</b><br>%{y:.1f}% achieved it"
                      "<br>%{customdata[0]:,} of %{customdata[1]:,} starts<extra></extra>",
    ))
    style_fig(fig_bar, height=380,
              title=f"Chance of a {label.lower()} by starting slot · {where}, {span}",
              xaxis_title="Starting grid position", yaxis_title=f"{label} rate (%)",
              showlegend=False)
    fig_bar.update_xaxes(dtick=1)
    fig_bar.update_yaxes(ticksuffix="%")

    # Chart 2: heatmap, grid vs finish
    h = d[(d.grid <= 20) & (d.position <= 20)].dropna(subset=["position"])
    if len(h) >= 50:
        mat = pd.crosstab(h.position.astype(int), h.grid.astype(int), normalize="columns") * 100
        fig_heat = px.imshow(
            mat,
            labels=dict(x="Starting grid position", y="Finishing position", color="Share"),
            color_continuous_scale=[[0, PANEL], [0.5, "#3E5A6B"], [1, CYAN]],
            aspect="auto", origin="upper",
        )
        fig_heat.update_traces(hovertemplate="Started P%{x} → finished P%{y}"
                                             "<br>%{z:.1f}% of that slot's finishers<extra></extra>")
        style_fig(fig_heat, height=430,
                  title=f"Where each grid slot actually finishes · {where}, {span}",
                  coloraxis_colorbar=dict(title="% of<br>column", ticksuffix="%"))
        fig_heat.update_xaxes(dtick=2)
        fig_heat.update_yaxes(dtick=2)
    else:
        fig_heat = empty_fig("Not enough classified finishes to build the grid-vs-finish matrix.")

    # Chart 3: line, win rate from the front by season
    pole  = d[d.grid == 1].groupby("season").agg(rate=("won", "mean"), n=("won", "size"))
    pole  = pole[pole.n >= 3].reset_index()
    front = d[d.grid <= 3].groupby("season").agg(rate=("won", "mean"), n=("won", "size"))
    front = front[front.n >= 6].reset_index()

    if len(pole) >= 2:
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=pole.season, y=pole.rate * 100, mode="lines+markers", name="Pole sitter",
            line=dict(color=AMBER, width=2.5), marker=dict(size=6),
            hovertemplate="%{x}<br>Pole won %{y:.0f}% of races<extra></extra>"))
        fig_line.add_trace(go.Scatter(
            x=front.season, y=front.rate * 100, mode="lines", name="Top-3 starter",
            line=dict(color=CYAN, width=2, dash="dash"),
            hovertemplate="%{x}<br>Top-3 starters won %{y:.0f}% of the time<extra></extra>"))
        style_fig(fig_line, height=380,
                  title=f"Win rate from the front, season by season · {where}",
                  xaxis_title="Season", yaxis_title="Share of races won (%)",
                  legend=dict(orientation="h", y=1.02, x=1, xanchor="right",
                              yanchor="bottom", bgcolor="rgba(0,0,0,0)"))
        fig_line.update_yaxes(ticksuffix="%", rangemode="tozero")
    else:
        fig_line = empty_fig("Select at least two seasons to see the trend over time.")

    return fig_bar, fig_heat, fig_line

# # test before running the server
# figs = update_figures([2000, 2024], "ALL", "podium", ["full_grids"])
# print("chart types:", [f.data[0].type for f in figs])


if __name__ == "__main__":
    import webbrowser, threading
    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:8050")).start()
    app.run(debug=False)
