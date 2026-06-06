import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html, ctx, ALL, no_update

from ..data import DATASETS, PRIMARY, ACCENT
from ..domain import (LEVELS, stage_bucket, stage_options, puzzle_series,
                      stages_for)
from ..theme import blank_fig, style_fig, _rgba, LINE_DARK
from ..components import category_control, year_control, stage_control, thumb


def times_tab():
    return html.Div(
        className="page-content",
        children=[
            html.H2("Finishing times"),
            html.P("Finish-time distributions and DNF rates by year and stage. "
                   "Times are only comparable within a category since puzzle sizes differ.",
                   className="tab-intro"),
            html.Div(
                className="controls-bar",
                children=[
                    category_control("time-category"),
                    stage_control("time-stage"),
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
            html.P("Each group round uses its own puzzle; in 2025 individual group rounds, competitors "
                   "could choose 1 of 2 puzzles. Click a violin or a bar to highlight that puzzle "
                   "across both charts and the gallery. Click a thumbnail to enlarge.",
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
                html.Div(id="puz-lightbox-bg",
                         style={"position": "absolute", "inset": "0",
                                "zIndex": "1", "cursor": "pointer"}),
                html.Span("×", id="puz-lightbox-close", className="lightbox-close"),
                html.Img(id="puz-lightbox-img", className="lightbox-img",
                         style={"position": "relative", "zIndex": "2"}),
            ]),
        ],
    )


@callback(
    Output("time-stage", "options"),
    Output("time-stage", "value"),
    Input("time-category", "value"),
    State("time-stage", "value"),
)
def update_time_stages(category, current):
    stages = stages_for(category)
    return stage_options(stages, current=current)


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
        return blank_fig("No finishers for this selection")
    fig = go.Figure()
    for year in sorted(df["year"].unique()):
        y = df[df["year"] == year]["time_seconds"] / 60
        label = str(year)
        if len(y) >= 5:
            fig.add_trace(go.Violin(
                y=y, name=label, fillcolor=_rgba(PRIMARY, 0.55),
                box_visible=True, meanline_visible=False, points=False,
                marker_color=PRIMARY,
                line=dict(color=LINE_DARK, width=1.5)))
        else:
            fig.add_trace(go.Scatter(
                x=[label] * len(y), y=list(y), name=label, mode="markers",
                marker=dict(color=PRIMARY, size=10,
                            line=dict(color=LINE_DARK, width=2))))
    style_fig(fig, y_title="Finish time (minutes)", categorical_x=True,
              show_legend=False)
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
        return blank_fig("No data for this selection")
    fig = px.bar(counts, x="year", y="n", color="status",
                 color_discrete_map={"Finished": PRIMARY, "DNF": ACCENT})
    fig.update_layout(barmode="stack", legend_title=None)
    style_fig(fig, y_title="Competitors", categorical_x=True)
    return fig


# ── Puzzle comparison helpers ─────────────────────────────────────────────────

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
        }
    return stats


def _ordered_labels(label_url, stats, sort):
    labels = list(label_url)
    if sort == "round":
        return labels
    if sort in ("median_asc", "median_desc"):
        timed = [lb for lb in labels if stats[lb]["median"] is not None]
        rest = [lb for lb in labels if stats[lb]["median"] is None]
        timed.sort(key=lambda lb: stats[lb]["median"],
                   reverse=(sort == "median_desc"))
        return timed + rest
    if sort in ("total_asc", "total_desc"):
        labels.sort(key=lambda lb: stats[lb]["total"],
                    reverse=(sort == "total_desc"))
        return labels
    labels.sort(key=lambda lb: stats[lb]["completion"],
                reverse=(sort == "comp_desc"))
    return labels


def _violin_figure(df, order, selected):
    fig = go.Figure()
    for label in order:
        y = (df[df["puzzle_label"] == label]["time_seconds"].dropna() / 60)
        sel = label == selected
        base = ACCENT if sel else PRIMARY
        if len(y) >= 5:
            fig.add_trace(go.Violin(
                y=y, name=label, fillcolor=_rgba(base, 0.55),
                box_visible=True, meanline_visible=False, points=False,
                marker_color=base,
                line=dict(color=ACCENT if sel else LINE_DARK, width=3 if sel else 1.5)))
        else:
            # Too few points for a meaningful violin; show individual markers
            fig.add_trace(go.Scatter(
                x=[label] * len(y), y=list(y), name=label, mode="markers",
                marker=dict(color=base, size=10,
                            line=dict(color=ACCENT if sel else LINE_DARK, width=2))))
    style_fig(fig, x_title="Puzzle", y_title="Finish time (minutes)",
              show_legend=False)
    return fig


def _completion_figure(order, stats, selected):
    fin = [stats[lb]["finishers"] for lb in order]
    dnf = [stats[lb]["total"] - stats[lb]["finishers"] for lb in order]
    outline = [3 if lb == selected else 0 for lb in order]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=order, y=dnf, name="DNF", marker_color=ACCENT,
        marker_line=dict(color=ACCENT, width=outline)))
    fig.add_trace(go.Bar(
        x=order, y=fin, name="Finished", marker_color=PRIMARY,
        marker_line=dict(color=ACCENT, width=outline)))
    fig.update_layout(barmode="stack", legend_title=None)
    style_fig(fig, x_title="Puzzle", y_title="Competitors")
    return fig


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
        note = blank_fig("Puzzle comparison applies to Individual and Pairs "
                         "(teams solve two puzzles at once).")
        return note, blank_fig(), []

    df, label_url = _puzzle_data(category, year, level)
    stats = _puzzle_stats(df, label_url)
    order = _ordered_labels(label_url, stats, sort)
    gallery = [thumb("puz-thumb", lb, lb, label_url[lb], lb == selected)
               for lb in order]
    if not label_url:
        return (blank_fig("No data at this level for this selection"),
                blank_fig(), gallery)
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
    if trig in ("time-category", "puz-year", "puz-level"):
        return None
    click = box_click if trig == "puz-box" else \
        comp_click if trig == "puz-completion" else None
    label = _label_from_click(click, category, year, level, sort)
    if label is None:
        return no_update
    return None if label == current else label


@callback(
    Output("puz-lightbox", "className"),
    Output("puz-lightbox-img", "src"),
    Input({"type": "puz-thumb", "index": ALL}, "n_clicks"),
    Input("puz-lightbox-close", "n_clicks"),
    Input("puz-lightbox-bg", "n_clicks"),
    State("time-category", "value"),
    State("puz-year", "value"),
    State("puz-level", "value"),
)
def toggle_lightbox(thumb_clicks, close_clicks, bg_clicks, category, year, level):
    trig = ctx.triggered_id
    if trig in ("puz-lightbox-close", "puz-lightbox-bg"):
        return "lightbox hidden", no_update
    if isinstance(trig, dict) and trig.get("type") == "puz-thumb":
        # A real click has n_clicks >= 1; a gallery rebuild recreates thumbs
        # with n_clicks=0, so ignore those to avoid spurious lightbox opens.
        clicked = next((i for i in ctx.inputs_list[0] if i["id"] == trig), None)
        if not clicked or not clicked.get("value"):
            return no_update, no_update
        _, label_url = _puzzle_data(category, year, level)
        url = label_url.get(trig["index"])
        if url:
            return "lightbox", url
    return no_update, no_update
