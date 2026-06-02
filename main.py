import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import (Dash, dash_table, dcc, html, Input, Output, State, callback,
                  ctx, ALL, no_update)

# ── Data ──────────────────────────────────────────────────────────────────────
individual = pd.read_csv("data/individual_results.csv")
pairs = pd.read_csv("data/pairs_results.csv")
teams = pd.read_csv("data/teams_results.csv")

YEARS = sorted(int(y) for y in individual["year"].unique())

# Brand palette (mirrors assets/style.css custom properties)
PRIMARY = "#2c3e50"
ACCENT = "#e67e22"
MUTED = "#6c757d"
SEQ = px.colors.sequential.Oranges

DATASETS = {"individual": individual, "pairs": pairs, "teams": teams}
CATEGORY_LABELS = {"individual": "Individual", "pairs": "Pairs", "teams": "Teams"}

# Map data country names → ISO-3166 alpha-3 codes for the choropleth. The
# "country names" locationmode is deprecated, so we drive the map with ISO-3.
# Entries with no code (e.g. "International Puzzlers") are dropped from the map.
COUNTRY_ISO3 = {
    "Albania": "ALB", "Andorra": "AND", "Argentina": "ARG", "Australia": "AUS",
    "Austria": "AUT", "Bangladesh": "BGD", "Barbados": "BRB", "Belarus": "BLR",
    "Belgium": "BEL", "Bolivia": "BOL", "Brazil": "BRA", "Bulgaria": "BGR",
    "Cameroon": "CMR", "Canada": "CAN", "Chile": "CHL", "China": "CHN",
    "Colombia": "COL", "Costa Rica": "CRI", "Croatia": "HRV", "Cuba": "CUB",
    "Cyprus": "CYP", "Czech Republic": "CZE", "Denmark": "DNK", "Dominica": "DMA",
    "Ecuador": "ECU", "Egypt": "EGY", "Estonia": "EST", "Finland": "FIN",
    "France": "FRA", "Germany": "DEU", "Greece": "GRC", "Guatemala": "GTM",
    "Honduras": "HND", "Hungary": "HUN", "Iceland": "ISL", "India": "IND",
    "Indonesia": "IDN", "Iran": "IRN", "Ireland": "IRL", "Israel": "ISR",
    "Italy": "ITA", "Japan": "JPN", "Latvia": "LVA", "Lithuania": "LTU",
    "Luxembourg": "LUX", "Malaysia": "MYS", "Malta": "MLT", "Mexico": "MEX",
    "New Zealand": "NZL", "Norway": "NOR", "Panama": "PAN", "Paraguay": "PRY",
    "Peru": "PER", "Poland": "POL", "Portugal": "PRT", "Romania": "ROU",
    "Russia": "RUS", "Saudi Arabia": "SAU", "Serbia": "SRB", "Singapore": "SGP",
    "Slovakia": "SVK", "Slovenia": "SVN", "South Africa": "ZAF",
    "South Korea": "KOR", "Spain": "ESP", "Sweden": "SWE", "Switzerland": "CHE",
    "Taiwan (Province of China)": "TWN", "Thailand": "THA",
    "The Netherlands": "NLD", "Trinidad and Tobago": "TTO", "Tunisia": "TUN",
    "Türkiye": "TUR", "USA": "USA", "Uganda": "UGA", "Ukraine": "UKR",
    "United Kingdom": "GBR", "Uruguay": "URY", "Venezuela": "VEN",
    "Vietnam": "VNM",
}

REAL_STAGES = {"A", "B", "C", "D", "E", "F", "S1", "S2", "S3", "final"}


# ── Helpers ─────────────────────────────────────────────────────────────────--

def stage_sort_key(s):
    """Order stages: group rounds (A–F) → semis (S1–S3) → final."""
    if s == "final":
        return (2, 0)
    if s.startswith("S"):
        return (1, int(s[1:]))
    return (0, ord(s[0]))


def stage_bucket(s):
    if s == "final":
        return "Final"
    if s.startswith("S"):
        return "Semi-finals"
    return "Group rounds"


LEVELS = ["Group rounds", "Semi-finals", "Final"]


def puzzle_series(df):
    """Label each finisher row by the distinct puzzle it solved.

    Within a stage, puzzles are numbered in first-appearance order (e.g. the
    2025 two-puzzle split → ``A·1``, ``A·2``); a stage with a single puzzle keeps
    its bare name (``B``, ``S1``, ``final``). Returns the frame with a
    ``puzzle_label`` column and an ordered ``{label: url}`` map.
    """
    df = df.copy()
    pair_to_label = {}        # (stage, url) → label
    label_url = {}            # label → url, in display order
    for stage in sorted(df["stage"].unique(), key=stage_sort_key):
        urls = list(dict.fromkeys(df[df["stage"] == stage]["puzzle_image_url"]
                                  .dropna()))
        for i, url in enumerate(urls):
            label = stage if len(urls) == 1 else f"{stage}·{i + 1}"
            pair_to_label[(stage, url)] = label
            label_url[label] = url
    df["puzzle_label"] = df.apply(
        lambda r: pair_to_label.get((r["stage"], r["puzzle_image_url"])), axis=1)
    return df, label_url


def fmt_time(seconds):
    """Total seconds → H:MM:SS (or M:SS under an hour)."""
    if pd.isna(seconds):
        return "DNF"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def competitor_label(category, row):
    if category == "individual":
        return row["name"]
    if category == "pairs":
        n2 = row.get("name2")
        return f"{row['name1']} & {n2}" if isinstance(n2, str) and n2 else row["name1"]
    return row["team_name"]


def row_image_urls(category, row):
    """All puzzle box images for a results row. Teams solve several puzzles at
    once (pipe-separated URLs); individual/pairs have a single puzzle."""
    if category == "teams":
        urls = row.get("puzzle_image_urls")
        if isinstance(urls, str) and urls:
            return [u for u in urls.split("|") if u]
        return []
    url = row.get("puzzle_image_url")
    return [url] if isinstance(url, str) and url else []


def row_image_url(category, row):
    """First puzzle box image for a results row (None if absent)."""
    urls = row_image_urls(category, row)
    return urls[0] if urls else None


def round_puzzle_urls(category, dff):
    """Ordered, de-duplicated puzzle URLs used across a whole round."""
    seen = []
    for _, row in dff.iterrows():
        for u in row_image_urls(category, row):
            if u not in seen:
                seen.append(u)
    return seen


def table_columns(category):
    if category == "individual":
        cols = [("Rank", "rank"), ("Name", "name"), ("Country", "country"),
                ("Origin", "origin")]
    elif category == "pairs":
        cols = [("Rank", "rank"), ("Player 1", "name1"), ("Player 2", "name2"),
                ("Country", "country")]
    else:
        cols = [("Rank", "rank"), ("Team", "team_name"), ("Members", "members"),
                ("Country", "country")]
    cols += [("Time", "time"), ("Gap", "gap"),
             ("Pieces", "pieces_completed"), ("Qualified", "qualified")]
    spec = [{"name": n, "id": i} for n, i in cols]
    spec.append({"name": "Puzzle(s)", "id": "puzzles_md",
                 "presentation": "markdown"})
    return spec


def stages_for(category, year=None):
    df = DATASETS[category]
    if year is not None:
        df = df[df["year"] == year]
    return sorted(df["stage"].unique(), key=stage_sort_key)


# ── Layout: header ────────────────────────────────────────────────────────────

def header():
    return html.Header(
        className="app-header",
        children=[
            html.Div("JWC", className="app-logo"),
            html.Div(
                className="app-title",
                children=[
                    html.H1("Jigsaw World Championships"),
                    html.P("Valladolid, Spain · 2019 – 2025"),
                ],
            ),
        ],
    )


def category_control(component_id, value="individual"):
    return html.Div([
        html.Div("Category", className="control-label"),
        dcc.Dropdown(
            id=component_id,
            options=[{"label": v, "value": k} for k, v in CATEGORY_LABELS.items()],
            value=value, clearable=False, style={"width": "150px"},
        ),
    ])


def year_control(component_id, value=None, include_all=False, label="Year"):
    opts = ([{"label": "All years", "value": "All"}] if include_all else [])
    opts += [{"label": str(y), "value": y} for y in YEARS]
    return html.Div([
        html.Div(label, className="control-label"),
        dcc.Dropdown(id=component_id, options=opts,
                     value=value if value is not None else YEARS[-1],
                     clearable=False, style={"width": "130px"}),
    ])


# ── Tab 1: Results (datatable + puzzle image) ─────────────────────────────────

def results_tab():
    return html.Div(
        className="page-content",
        children=[
            html.H2("Round results"),
            html.P("Browse the full results of any round. The Puzzle(s) column "
                   "shows each row's puzzle photos; the panel on the right "
                   "summarises the selected round. Click any puzzle to view it "
                   "full-screen.", className="tab-intro"),
            html.Div(
                className="controls-bar",
                children=[
                    category_control("res-category"),
                    year_control("res-year"),
                    html.Div([
                        html.Div("Stage", className="control-label"),
                        dcc.Dropdown(id="res-stage", value="final",
                                     clearable=False, style={"width": "150px"}),
                    ]),
                ],
            ),
            html.Div(
                className="split-layout",
                children=[
                    html.Div(
                        className="split-main",
                        children=dash_table.DataTable(
                            id="results-table",
                            columns=table_columns("individual"),
                            data=[],
                            page_size=15,
                            page_action="native",
                            sort_action="native",
                            sort_mode="multi",
                            filter_action="native",
                            style_as_list_view=True,
                            style_table={"overflowX": "auto"},
                            style_cell={
                                "fontFamily": '"Inter", "Segoe UI", sans-serif',
                                "fontSize": "0.85rem", "padding": "8px 12px",
                                "textAlign": "left", "maxWidth": "220px",
                                "overflow": "hidden", "textOverflow": "ellipsis",
                            },
                            style_cell_conditional=[
                                {"if": {"column_id": "puzzles_md"},
                                 "maxWidth": "none", "overflow": "visible",
                                 "minWidth": "90px"},
                            ],
                            style_data_conditional=[
                                {"if": {"row_index": "odd"},
                                 "backgroundColor": "#f8f9fa"},
                                {"if": {"filter_query": "{qualified} = True"},
                                 "backgroundColor": "#d4edda"},
                            ],
                        ),
                    ),
                    html.Div(
                        className="split-side",
                        children=html.Div(id="results-detail", className="detail-card",
                                          children=html.P("Round summary appears "
                                                          "here.",
                                                          className="detail-empty")),
                    ),
                ],
            ),
            html.Div(id="results-lightbox", className="lightbox hidden", children=[
                html.Span("×", id="results-lightbox-close",
                          className="lightbox-close"),
                html.Div(id="results-lightbox-imgs", className="lightbox-imgs"),
            ]),
        ],
    )


# ── Tab 2: Countries (map + ranked bar) ───────────────────────────────────────

def countries_tab():
    return html.Div(
        className="page-content",
        children=[
            html.H2("Countries"),
            html.P("Where do the world's best puzzlers come from? Click a country "
                   "on the map to focus the ranking.", className="tab-intro"),
            html.Div(
                className="controls-bar",
                children=[
                    category_control("ctry-category"),
                    year_control("ctry-year", value="All", include_all=True),
                    html.Div([
                        html.Div("Metric", className="control-label"),
                        dcc.Dropdown(
                            id="ctry-metric",
                            options=[
                                {"label": "Medals (top-3 finals)", "value": "medals"},
                                {"label": "Finalists", "value": "finalists"},
                                {"label": "Best finish time", "value": "best_time"},
                            ],
                            value="medals", clearable=False,
                            style={"width": "230px"}),
                    ]),
                ],
            ),
            html.Div(className="chart-grid", children=[
                html.Div(className="chart-card", children=[
                    dcc.Graph(id="ctry-map", clear_on_unhover=True)]),
                html.Div(className="chart-card", children=[
                    dcc.Graph(id="ctry-bar")]),
            ]),
        ],
    )


# ── Tab 3: Times (distribution + DNF) ─────────────────────────────────────────

def times_tab():
    return html.Div(
        className="page-content",
        children=[
            html.H2("Finishing times"),
            html.P("How fast — and how complete — are the solves? Times are only "
                   "comparable within a category (puzzle sizes differ).",
                   className="tab-intro"),
            html.Div(
                className="controls-bar",
                children=[
                    category_control("time-category"),
                    html.Div([
                        html.Div("Stage", className="control-label"),
                        dcc.Dropdown(id="time-stage", value="final",
                                     clearable=False, style={"width": "150px"}),
                    ]),
                ],
            ),
            html.Div(className="chart-grid", children=[
                html.Div(className="chart-card", children=[
                    html.H3("Finish-time distribution by year"),
                    dcc.Graph(id="time-dist")]),
                html.Div(className="chart-card", children=[
                    html.H3("Finishers vs. did-not-finish"),
                    dcc.Graph(id="time-dnf")]),
            ]),

            html.Hr(className="section-divider"),
            html.H2("Puzzle difficulty comparison"),
            html.P("At a single elimination level, different puzzles are used "
                   "(each group round has its own; in 2025 each round splits "
                   "across two). Comparing their finish-time distributions — and "
                   "how many finished at all — shows which puzzle was harder. "
                   "Click a box to highlight its puzzle; click a puzzle to enlarge.",
                   className="tab-intro"),
            html.Div(
                className="controls-bar",
                children=[
                    year_control("puz-year"),
                    html.Div([
                        html.Div("Level", className="control-label"),
                        dcc.Dropdown(
                            id="puz-level",
                            options=[{"label": lv, "value": lv} for lv in LEVELS],
                            value="Group rounds", clearable=False,
                            style={"width": "170px"}),
                    ]),
                    html.Div([
                        html.Div("Sort by", className="control-label"),
                        dcc.Dropdown(
                            id="puz-sort",
                            options=[
                                {"label": "Round order", "value": "round"},
                                {"label": "Median (slowest first)",
                                 "value": "median_desc"},
                                {"label": "Median (fastest first)",
                                 "value": "median_asc"},
                                {"label": "Completion % (lowest first)",
                                 "value": "comp_asc"},
                                {"label": "Completion % (highest first)",
                                 "value": "comp_desc"},
                                {"label": "Group size (largest first)",
                                 "value": "total_desc"},
                                {"label": "Group size (smallest first)",
                                 "value": "total_asc"},
                            ],
                            value="round", clearable=False,
                            style={"width": "210px"}),
                    ]),
                ],
            ),
            html.Div(className="chart-grid", children=[
                html.Div(className="chart-card", children=[
                    html.H3("Finish-time distribution"),
                    dcc.Graph(id="puz-box")]),
                html.Div(className="chart-card", children=[
                    html.H3("Finishers vs. did-not-finish"),
                    dcc.Graph(id="puz-completion")]),
            ]),
            html.Div(id="puz-gallery", className="puzzle-gallery"),
            dcc.Store(id="puz-selected"),
            html.Div(id="puz-lightbox", className="lightbox hidden", children=[
                html.Span("×", id="puz-lightbox-close", className="lightbox-close"),
                html.Img(id="puz-lightbox-img", className="lightbox-img"),
            ]),
        ],
    )


# ── Tab 4: Careers (trajectory + per-round table) ─────────────────────────────

def careers_tab():
    names = sorted(individual["name"].dropna().unique())
    default = "Alejandro Clemente León" if "Alejandro Clemente León" in names \
        else names[0]
    return html.Div(
        className="page-content",
        children=[
            html.H2("Competitor careers"),
            html.P("Track a single competitor across every championship they "
                   "entered (individual category).", className="tab-intro"),
            html.Div(
                className="controls-bar",
                children=[
                    html.Div([
                        html.Div("Competitor", className="control-label"),
                        dcc.Dropdown(
                            id="career-name",
                            options=[{"label": n, "value": n} for n in names],
                            value=default, clearable=False, searchable=True,
                            style={"width": "320px"}),
                    ]),
                    html.Div([
                        html.Div("Metric", className="control-label"),
                        dcc.Dropdown(
                            id="career-metric",
                            options=[{"label": "Finishing rank", "value": "rank"},
                                     {"label": "Finish time",
                                      "value": "time_seconds"}],
                            value="rank", clearable=False, style={"width": "190px"}),
                    ]),
                ],
            ),
            html.Div(className="chart-card", children=[dcc.Graph(id="career-line")]),
            html.H3("All rounds"),
            dash_table.DataTable(
                id="career-table",
                columns=[{"name": n, "id": i} for n, i in [
                    ("Year", "year"), ("Stage", "stage"), ("Rank", "rank"),
                    ("Time", "time"), ("Country", "country"),
                    ("Qualified", "qualified")]],
                data=[], page_size=12, sort_action="native",
                style_as_list_view=True,
                style_cell={"fontFamily": '"Inter", "Segoe UI", sans-serif',
                            "fontSize": "0.85rem", "padding": "8px 12px",
                            "textAlign": "left"},
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"}],
            ),
        ],
    )


# ── Tab 5: Progression (funnel + gap scatter) ─────────────────────────────────

def progression_tab():
    return html.Div(
        className="page-content",
        children=[
            html.H2("Tournament progression"),
            html.P("Follow the field from group rounds down to the final. Click a "
                   "point in the scatter to inspect that finalist.",
                   className="tab-intro"),
            html.Div(
                className="controls-bar",
                children=[
                    category_control("prog-category"),
                    year_control("prog-year"),
                ],
            ),
            html.Div(className="chart-grid", children=[
                html.Div(className="chart-card", children=[
                    html.H3("Elimination funnel"),
                    dcc.Graph(id="prog-funnel")]),
                html.Div(className="chart-card", children=[
                    html.H3("Final: rank vs. finish time"),
                    dcc.Graph(id="prog-scatter")]),
            ]),
            html.Div(id="prog-detail", className="detail-card",
                     children=html.P("Click a finalist in the scatter for details.",
                                     className="detail-empty")),
        ],
    )


# ── Tab 6: About ──────────────────────────────────────────────────────────────

def about_tab():
    return html.Div(
        className="page-content about",
        children=[
            html.H2("About this dashboard"),
            html.P("An interactive look at all five World Jigsaw Puzzle "
                   "Championships held in Valladolid, Spain (2019, 2022–2025). "
                   "Data was scraped from worldjigsawpuzzle.org."),
            html.H3("How the competition works"),
            html.P("Each category runs the same format: group rounds (A, B, C …) "
                   "split the field; the top finishers advance to semi-finals "
                   "(S1, S2 …) and then a final. The qualified flag marks "
                   "competitors who advanced; in the final no one qualifies."),
            html.Ul([
                html.Li("Individual — 500-piece puzzle, solo competitors."),
                html.Li("Pairs — 500 (2019) or 1,000 (2022+) pieces, two people."),
                html.Li("Teams — 2,000–5,000 pieces across two puzzles, four people."),
            ]),
            html.H3("Using the tabs"),
            html.Ul([
                html.Li("Results — full round tables; click a row to see the puzzle."),
                html.Li("Countries — map and ranking; click a country to focus it."),
                html.Li("Times — finish-time spread and did-not-finish rates."),
                html.Li("Careers — one competitor's path across the years."),
                html.Li("Progression — the elimination funnel and the final's spread."),
            ]),
            html.H3("Reading the data"),
            html.P("A row is a did-not-finish (DNF) when it has a piece count "
                   "instead of a time. Times are only comparable within a category "
                   "because puzzle sizes differ. Competitor names are consistent "
                   "within a year, but minor transliteration differences can occur "
                   "across years."),
        ],
    )


# ── App ───────────────────────────────────────────────────────────────────────
# IDs in tabs other than the default are created on demand by render_tab, so
# Dash must allow callbacks that reference not-yet-rendered components.
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Jigsaw World Championships"

TABS = [
    ("Results", "tab-results"),
    ("Countries", "tab-countries"),
    ("Times", "tab-times"),
    ("Careers", "tab-careers"),
    ("Progression", "tab-progression"),
    ("About", "tab-about"),
]

app.layout = html.Div([
    header(),
    html.Div(
        className="tab-container",
        children=dcc.Tabs(
            id="main-tabs", value="tab-results", className="custom-tabs",
            children=[dcc.Tab(label=lbl, value=val, className="custom-tab",
                              selected_className="custom-tab--selected")
                      for lbl, val in TABS],
        ),
    ),
    html.Div(id="tab-content"),
])


@callback(Output("tab-content", "children"), Input("main-tabs", "value"))
def render_tab(tab):
    return {
        "tab-results": results_tab,
        "tab-countries": countries_tab,
        "tab-times": times_tab,
        "tab-careers": careers_tab,
        "tab-progression": progression_tab,
        "tab-about": about_tab,
    }[tab]()


# ── Callbacks: Results ────────────────────────────────────────────────────────

@callback(
    Output("res-stage", "options"),
    Output("res-stage", "value"),
    Input("res-category", "value"),
    Input("res-year", "value"),
    State("res-stage", "value"),
)
def update_res_stages(category, year, current):
    stages = stages_for(category, year)
    opts = [{"label": "All", "value": "All"}] + \
           [{"label": s, "value": s} for s in stages]
    value = current if current in (list(stages) + ["All"]) else \
        ("final" if "final" in stages else stages[-1])
    return opts, value


@callback(
    Output("results-table", "data"),
    Output("results-table", "columns"),
    Input("res-category", "value"),
    Input("res-year", "value"),
    Input("res-stage", "value"),
)
def update_results_table(category, year, stage):
    dff = DATASETS[category]
    dff = dff[dff["year"] == year]
    if stage != "All":
        dff = dff[dff["stage"] == stage]
    records = dff.to_dict("records")
    for rec in records:
        rec["puzzles_md"] = " ".join(f"![]({u})"
                                     for u in row_image_urls(category, rec))
    return records, table_columns(category)


@callback(
    Output("results-detail", "children"),
    Input("res-category", "value"),
    Input("res-year", "value"),
    Input("res-stage", "value"),
)
def show_round_summary(category, year, stage):
    empty = html.P("Round summary appears here.", className="detail-empty")
    dff = DATASETS[category]
    dff = dff[dff["year"] == year]
    if stage != "All":
        dff = dff[dff["stage"] == stage]
    if dff.empty:
        return empty

    n = len(dff)
    qualified = int(dff["qualified"].sum())
    finishers = int(dff["time_seconds"].notna().sum())
    dnf = n - finishers
    fin_pct = round(100 * finishers / n) if n else 0
    dnf_pct = 100 - fin_pct if n else 0
    fin = dff[dff["time_seconds"].notna()]
    win = fin.loc[fin["time_seconds"].idxmin(), "time"] if not fin.empty else "—"
    unit = "teams" if category == "teams" else \
        ("pairs" if category == "pairs" else "competitors")
    stage_label = "All rounds" if stage == "All" else stage

    # Round metadata is constant within a (year, stage); read it off any row.
    # For "All", piece/limit/date can vary, so omit those per-round fields.
    rows = [("Category", CATEGORY_LABELS[category]),
            ("Year", str(year)), ("Round", stage_label)]
    if stage != "All":
        first = dff.iloc[0]
        rows += [("Date", str(first.get("date", "") or "—")),
                 ("Pieces", str(first.get("puzzle_pieces", "") or "—")),
                 ("Time limit", str(first.get("time_limit", "") or "—"))]
    rows += [("Entrants", f"{n} {unit}")]
    if stage != "final":  # no one qualifies out of the final
        rows.append(("Qualified", str(qualified)))
    rows += [("Finishers", f"{finishers} ({fin_pct}%)"),
             ("DNF", f"{dnf} ({dnf_pct}%)"),
             ("Winning time", str(win or "—"))]

    urls = round_puzzle_urls(category, dff)
    gallery = [
        html.Button(
            id={"type": "results-puz-thumb", "index": u}, className="puzzle-thumb",
            n_clicks=0,
            children=[html.Img(src=u),
                      html.Div(f"Puzzle {i}", className="puzzle-thumb-label")])
        for i, u in enumerate(urls, start=1)
    ]
    return [
        html.H3("Round summary", className="detail-title"),
        html.Table(className="detail-meta",
                   children=[html.Tr([html.Td(k), html.Td(v)]) for k, v in rows]),
        html.Div(f"Puzzle{'s' if len(urls) != 1 else ''} used",
                 className="detail-subhead") if urls else None,
        html.Div(gallery, className="puzzle-gallery") if urls else None,
    ]


@callback(
    Output("results-lightbox", "className"),
    Output("results-lightbox-imgs", "children"),
    Input("results-table", "active_cell"),
    Input({"type": "results-puz-thumb", "index": ALL}, "n_clicks"),
    Input("results-lightbox-close", "n_clicks"),
    State("results-table", "derived_viewport_data"),
    State("res-category", "value"),
)
def toggle_results_lightbox(active_cell, thumb_clicks, close_clicks,
                            viewport, category):
    trig = ctx.triggered_id
    if trig == "results-lightbox-close":
        return "lightbox hidden", no_update

    # Sidebar puzzle thumbnail → show that single puzzle.
    if isinstance(trig, dict) and trig.get("type") == "results-puz-thumb":
        # Ignore the n_clicks=0 values produced when the gallery is rebuilt.
        clicked = next((i for i in ctx.inputs_list[1] if i["id"] == trig), None)
        if not clicked or not clicked.get("value"):
            return no_update, no_update
        return "lightbox", [html.Img(src=trig["index"])]

    # Table image cell → show that row's puzzle(s) side by side.
    if trig == "results-table":
        if not active_cell or active_cell.get("column_id") != "puzzles_md":
            return no_update, no_update
        try:
            row = viewport[active_cell["row"]]
        except (IndexError, KeyError, TypeError):
            return no_update, no_update
        urls = row_image_urls(category, row)
        if not urls:
            return no_update, no_update
        return "lightbox", [html.Img(src=u) for u in urls]

    return no_update, no_update


# ── Callbacks: Countries ──────────────────────────────────────────────────────

def country_stats(category, year, metric):
    df = DATASETS[category]
    if year != "All":
        df = df[df["year"] == year]
    finals = df[df["stage"] == "final"]
    if metric == "medals":
        sub = finals[finals["rank"].isin([1, 2, 3])]
        agg = sub.groupby("country").size().rename("value").reset_index()
        title = "Medals (top-3 final finishes)"
    elif metric == "finalists":
        agg = finals.groupby("country").size().rename("value").reset_index()
        title = "Finalist appearances"
    else:  # best_time
        fin = finals.dropna(subset=["time_seconds"])
        agg = fin.groupby("country")["time_seconds"].min() \
            .rename("value").reset_index()
        title = "Best finish time (lower = better)"
    agg["iso3"] = agg["country"].map(COUNTRY_ISO3)
    agg = agg.dropna(subset=["iso3"])  # drop non-country entries from the map
    return agg, title


@callback(
    Output("ctry-map", "figure"),
    Input("ctry-category", "value"),
    Input("ctry-year", "value"),
    Input("ctry-metric", "value"),
)
def update_country_map(category, year, metric):
    agg, title = country_stats(category, year, metric)
    if agg.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data for this selection", showarrow=False)
    else:
        fig = px.choropleth(
            agg, locations="iso3", locationmode="ISO-3",
            color="value", hover_name="country",
            color_continuous_scale=SEQ if metric != "best_time" else SEQ[::-1],
        )
    fig.update_layout(
        title=title, margin=dict(l=0, r=0, t=40, b=0),
        coloraxis_colorbar_title=None, geo=dict(showframe=False),
        paper_bgcolor="white",
    )
    return fig


@callback(
    Output("ctry-bar", "figure"),
    Input("ctry-category", "value"),
    Input("ctry-year", "value"),
    Input("ctry-metric", "value"),
    Input("ctry-map", "clickData"),
)
def update_country_bar(category, year, metric, click):
    agg, title = country_stats(category, year, metric)
    if agg.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data for this selection", showarrow=False)
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="white")
        return fig
    ascending = metric == "best_time"
    agg = agg.sort_values("value", ascending=ascending).head(15)
    selected = None
    if click and click.get("points"):
        pt = click["points"][0]
        selected = pt.get("hovertext") or pt.get("location")
    # clickData carries the ISO-3 code (or hover country name); map back to name.
    iso_to_country = dict(zip(agg["iso3"], agg["country"]))
    selected_country = iso_to_country.get(selected, selected)
    colors = [ACCENT if (selected_country and c == selected_country) else PRIMARY
              for c in agg["country"]]
    fig = go.Figure(go.Bar(
        x=agg["value"], y=agg["country"], orientation="h",
        marker_color=colors,
        text=[fmt_time(v) for v in agg["value"]] if metric == "best_time"
        else agg["value"],
    ))
    fig.update_layout(
        title=f"Top countries — {title}",
        yaxis=dict(autorange="reversed"), margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white", plot_bgcolor="white", height=480,
    )
    return fig


# ── Callbacks: Times ──────────────────────────────────────────────────────────

@callback(
    Output("time-stage", "options"),
    Output("time-stage", "value"),
    Input("time-category", "value"),
    State("time-stage", "value"),
)
def update_time_stages(category, current):
    stages = stages_for(category)
    opts = [{"label": "All", "value": "All"}] + \
           [{"label": s, "value": s} for s in stages]
    value = current if current in (list(stages) + ["All"]) else "final"
    return opts, value


@callback(
    Output("time-dist", "figure"),
    Input("time-category", "value"),
    Input("time-stage", "value"),
)
def update_time_dist(category, stage):
    df = DATASETS[category]
    if stage != "All":
        df = df[df["stage"] == stage]
    df = df.dropna(subset=["time_seconds"]).copy()
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No finishers for this selection", showarrow=False)
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="white")
        return fig
    df["minutes"] = df["time_seconds"] / 60
    fig = px.violin(df, x="year", y="minutes", box=True, points=False)
    fig.update_traces(fillcolor=_rgba(PRIMARY, 0.55), line_color=LINE_DARK,
                      marker_color=PRIMARY)
    fig.update_layout(
        showlegend=False, xaxis_title=None, yaxis_title="Finish time (minutes)",
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="white", plot_bgcolor="white", xaxis=dict(type="category"),
    )
    return fig


@callback(
    Output("time-dnf", "figure"),
    Input("time-category", "value"),
    Input("time-stage", "value"),
)
def update_time_dnf(category, stage):
    df = DATASETS[category].copy()
    if stage != "All":
        df = df[df["stage"] == stage]
    df["status"] = df["pieces_completed"].notna().map(
        {True: "DNF", False: "Finished"})
    counts = df.groupby(["year", "status"]).size().rename("n").reset_index()
    if counts.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data for this selection", showarrow=False)
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="white")
        return fig
    fig = px.bar(counts, x="year", y="n", color="status",
                 color_discrete_map={"Finished": PRIMARY, "DNF": ACCENT})
    fig.update_layout(
        barmode="stack", xaxis_title=None, yaxis_title="Competitors",
        legend_title=None, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="white", plot_bgcolor="white", xaxis=dict(type="category"),
    )
    return fig


# ── Callbacks: Puzzle comparison (Times tab) ──────────────────────────────────

def _blank_fig(message=""):
    fig = go.Figure()
    if message:
        fig.add_annotation(text=message, showarrow=False)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="white",
                      plot_bgcolor="white")
    return fig


def _puzzle_data(category, year, level):
    """All rows (finishers + DNF) at one level, labelled per distinct puzzle."""
    df = DATASETS[category]
    df = df[(df["year"] == year) & (df["stage"].map(stage_bucket) == level)].copy()
    df, label_url = puzzle_series(df)
    return df[df["puzzle_label"].notna()], label_url


def _puzzle_stats(df, label_url):
    stats = {}
    for label in label_url:
        sub = df[df["puzzle_label"] == label]
        fin = sub["time_seconds"].dropna()
        total = len(sub)
        stats[label] = {
            "finishers": len(fin),
            "total": total,
            "completion": (len(fin) / total) if total else 0.0,
            "median": fin.median() if len(fin) else None,
            "q1": fin.quantile(0.25) if len(fin) else None,
            "q3": fin.quantile(0.75) if len(fin) else None,
        }
    return stats


def _ordered_labels(label_url, stats, sort):
    labels = list(label_url)
    if sort == "round":
        return labels
    if sort in ("median_asc", "median_desc"):
        timed = [l for l in labels if stats[l]["median"] is not None]
        rest = [l for l in labels if stats[l]["median"] is None]
        timed.sort(key=lambda l: stats[l]["median"],
                   reverse=(sort == "median_desc"))
        return timed + rest
    if sort in ("total_asc", "total_desc"):
        labels.sort(key=lambda l: stats[l]["total"],
                    reverse=(sort == "total_desc"))
        return labels
    labels.sort(key=lambda l: stats[l]["completion"],
                reverse=(sort == "comp_desc"))
    return labels


# Single colour for every puzzle (colour no longer encodes identity); the
# selected puzzle is the only one drawn in the accent colour.
FILL = "#2c3e50"          # PRIMARY
LINE_DARK = "#161616"     # violin outline + median, visible on the fill


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _violin_figure(df, order, selected):
    fig = go.Figure()
    for label in order:
        y = (df[df["puzzle_label"] == label]["time_seconds"].dropna() / 60)
        sel = label == selected
        base = ACCENT if sel else FILL
        fig.add_trace(go.Violin(
            y=y, name=label, fillcolor=_rgba(base, 0.55),
            box_visible=True, meanline_visible=False, points=False,
            marker_color=base,
            line=dict(color=ACCENT if sel else LINE_DARK, width=3 if sel else 1.5)))
    fig.update_layout(
        showlegend=False, xaxis_title="Puzzle",
        yaxis_title="Finish time (minutes)",
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="white", plot_bgcolor="white")
    return fig


def _completion_figure(order, stats, selected):
    fin = [stats[l]["finishers"] for l in order]
    dnf = [stats[l]["total"] - stats[l]["finishers"] for l in order]
    outline = [3 if l == selected else 0 for l in order]
    fig = go.Figure()
    # DNF on the bottom, finishers on top; selected puzzle outlined in accent.
    fig.add_trace(go.Bar(
        x=order, y=dnf, name="DNF", marker_color=ACCENT,
        marker_line=dict(color=ACCENT, width=outline)))
    fig.add_trace(go.Bar(
        x=order, y=fin, name="Finished", marker_color=PRIMARY,
        marker_line=dict(color=ACCENT, width=outline)))
    fig.update_layout(
        barmode="stack", xaxis_title="Puzzle", yaxis_title="Competitors",
        legend_title=None, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="white", plot_bgcolor="white")
    return fig


def _thumb(label, url, selected):
    cls = "puzzle-thumb selected" if selected else "puzzle-thumb"
    return html.Button(
        id={"type": "puz-thumb", "index": label}, className=cls, n_clicks=0,
        children=[html.Img(src=url),
                  html.Div(label, className="puzzle-thumb-label")])


@callback(
    Output("puz-box", "figure"),
    Output("puz-completion", "figure"),
    Output("puz-gallery", "children"),
    Input("time-category", "value"),
    Input("puz-year", "value"),
    Input("puz-level", "value"),
    Input("puz-sort", "value"),
    Input("puz-selected", "data"),
)
def draw_puzzles(category, year, level, sort, selected):
    if category == "teams":
        note = _blank_fig("Puzzle comparison applies to Individual and Pairs "
                          "(teams solve two puzzles at once).")
        return note, _blank_fig(), []

    df, label_url = _puzzle_data(category, year, level)
    stats = _puzzle_stats(df, label_url)
    order = _ordered_labels(label_url, stats, sort)
    gallery = [_thumb(l, label_url[l], l == selected) for l in order]
    if len(label_url) < 2:
        msg = ("No data at this level for this selection" if not label_url
               else "Only one puzzle used at this level — nothing to compare")
        return _blank_fig(msg), _blank_fig(), gallery
    return (_violin_figure(df, order, selected),
            _completion_figure(order, stats, selected), gallery)


def _label_from_click(click, category, year, level, sort):
    """Resolve a violin/bar clickData point to its puzzle label."""
    if not click or not click.get("points"):
        return None
    pt = click["points"][0]
    df, label_url = _puzzle_data(category, year, level)
    x = pt.get("x")
    if x in label_url:
        return x
    order = _ordered_labels(label_url, _puzzle_stats(df, label_url), sort)
    cn = pt.get("curveNumber")
    return order[cn] if (cn is not None and cn < len(order)) else None


@callback(
    Output("puz-selected", "data"),
    Input("puz-box", "clickData"),
    Input("puz-completion", "clickData"),
    Input("time-category", "value"),
    Input("puz-year", "value"),
    Input("puz-level", "value"),
    State("puz-sort", "value"),
    State("puz-selected", "data"),
)
def set_puz_selected(box_click, comp_click, category, year, level, sort, current):
    trig = ctx.triggered_id
    # Changing the puzzle set clears selection; sorting keeps it (sort is State).
    if trig in ("time-category", "puz-year", "puz-level"):
        return None
    click = box_click if trig == "puz-box" else \
        comp_click if trig == "puz-completion" else None
    label = _label_from_click(click, category, year, level, sort)
    if label is None:
        return no_update
    return None if label == current else label  # click again to clear


@callback(
    Output("puz-lightbox", "className"),
    Output("puz-lightbox-img", "src"),
    Input({"type": "puz-thumb", "index": ALL}, "n_clicks"),
    Input("puz-lightbox-close", "n_clicks"),
    State("time-category", "value"),
    State("puz-year", "value"),
    State("puz-level", "value"),
)
def toggle_lightbox(thumb_clicks, close_clicks, category, year, level):
    trig = ctx.triggered_id
    if trig == "puz-lightbox-close":
        return "lightbox hidden", no_update
    if isinstance(trig, dict) and trig.get("type") == "puz-thumb":
        # Read the triggered thumb's n_clicks from inputs_list (reliable for
        # wildcard inputs). A real click has n_clicks ≥ 1; a gallery rebuild
        # recreates thumbs with n_clicks 0 → ignore.
        clicked = next((i for i in ctx.inputs_list[0] if i["id"] == trig), None)
        if not clicked or not clicked.get("value"):
            return no_update, no_update
        _, label_url = _puzzle_data(category, year, level)
        url = label_url.get(trig["index"])
        if url:
            return "lightbox", url
    return no_update, no_update


# ── Callbacks: Careers ────────────────────────────────────────────────────────

@callback(
    Output("career-line", "figure"),
    Output("career-table", "data"),
    Input("career-name", "value"),
    Input("career-metric", "value"),
)
def update_career(name, metric):
    df = individual[individual["name"] == name].copy()
    df["order"] = df.apply(
        lambda r: (r["year"],) + stage_sort_key(r["stage"]), axis=1)
    df = df.sort_values("order")
    df["x"] = df["year"].astype(str) + " · " + df["stage"]

    if metric == "time_seconds":
        plot = df.dropna(subset=["time_seconds"]).copy()
        plot["y"] = plot["time_seconds"] / 60
        ytitle = "Finish time (minutes)"
        reversed_axis = False
    else:
        plot = df.dropna(subset=["rank"]).copy()
        plot["y"] = plot["rank"]
        ytitle = "Rank (lower = better)"
        reversed_axis = True

    if plot.empty:
        fig = go.Figure()
        fig.add_annotation(text="No finish data for this competitor",
                           showarrow=False)
    else:
        fig = px.line(plot, x="x", y="y", markers=True,
                      color_discrete_sequence=[ACCENT])
    fig.update_layout(
        title=f"{name} — {ytitle}", xaxis_title=None, yaxis_title=ytitle,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="white", plot_bgcolor="white",
    )
    if reversed_axis:
        fig.update_yaxes(autorange="reversed")

    table = df[["year", "stage", "rank", "time", "country", "qualified"]] \
        .to_dict("records")
    return fig, table


# ── Callbacks: Progression ────────────────────────────────────────────────────

@callback(
    Output("prog-funnel", "figure"),
    Input("prog-category", "value"),
    Input("prog-year", "value"),
)
def update_funnel(category, year):
    df = DATASETS[category]
    df = df[df["year"] == year].copy()
    df["bucket"] = df["stage"].map(stage_bucket)
    order = ["Group rounds", "Semi-finals", "Final"]
    counts = df.groupby("bucket").size()
    counts = counts.reindex([b for b in order if b in counts.index])
    fig = go.Figure(go.Funnel(
        y=counts.index, x=counts.values,
        marker_color=ACCENT, textinfo="value+percent initial"))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="white")
    return fig


@callback(
    Output("prog-scatter", "figure"),
    Input("prog-category", "value"),
    Input("prog-year", "value"),
)
def update_scatter(category, year):
    df = DATASETS[category]
    df = df[(df["year"] == year) & (df["stage"] == "final")].copy()
    df = df.dropna(subset=["time_seconds"])
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No final-round finishers for this selection",
                           showarrow=False)
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="white")
        return fig
    df["minutes"] = df["time_seconds"] / 60
    df["label"] = df.apply(lambda r: competitor_label(category, r), axis=1)
    df["img"] = df.apply(lambda r: row_image_url(category, r) or "", axis=1)
    df["gap_str"] = df["gap"].fillna("—")
    fig = px.scatter(
        df, x="rank", y="minutes", color="country", hover_name="label",
        custom_data=["label", "country", "gap_str", "img", "rank", "time"],
    )
    fig.update_traces(marker=dict(size=11, line=dict(width=1, color="white")))
    fig.update_layout(
        xaxis_title="Rank", yaxis_title="Finish time (minutes)",
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="white", plot_bgcolor="white", legend_title="Country",
    )
    return fig


@callback(
    Output("prog-detail", "children"),
    Input("prog-scatter", "clickData"),
)
def show_scatter_detail(click):
    if not click or not click.get("points"):
        return html.P("Click a finalist in the scatter for details.",
                      className="detail-empty")
    label, country, gap, img, rank, time = click["points"][0]["customdata"]
    return html.Div(className="detail-row", children=[
        (html.Img(src=img, className="detail-img-sm") if img
         else html.Div("No image", className="detail-noimg")),
        html.Div([
            html.H3(label, className="detail-title"),
            html.Table(className="detail-meta", children=[
                html.Tr([html.Td("Country"), html.Td(str(country))]),
                html.Tr([html.Td("Rank"), html.Td(str(rank))]),
                html.Tr([html.Td("Time"), html.Td(str(time))]),
                html.Tr([html.Td("Gap to 1st"), html.Td(str(gap or "—"))]),
            ]),
        ]),
    ])


if __name__ == "__main__":
    app.run(debug=True)
