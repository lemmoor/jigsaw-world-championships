import plotly.express as px
import plotly.graph_objects as go
from dash import (Input, Output, State, callback, ctx, dcc, html,
                  dash_table, ALL, no_update)

from ..data import DATASETS, PRIMARY, ACCENT, CATEGORY_LABELS
from ..domain import (LEVELS, BUCKET_ORDER, stage_bucket, stage_options,
                      stages_for, row_image_urls, round_puzzle_urls,
                      table_columns)
from ..theme import blank_fig
from ..components import category_control, year_control, stage_control, thumb


def results_tab():
    return html.Div(
        className="page-content",
        children=[
            html.H2("Round results"),
            html.P("Browse results for any round across all five championships. "
                   "The sidebar shows a round summary and elimination funnel. "
                   "Click a puzzle thumbnail to view it full-screen. "
                   "Select individual competitors to compare their career trajectories below.",
                   className="tab-intro"),
            html.Div(
                className="controls-bar",
                children=[
                    category_control("res-category"),
                    year_control("res-year"),
                    stage_control("res-stage"),
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
                            markdown_options={"html": True},
                            style_data_conditional=[
                                {"if": {"row_index": "odd"},
                                 "backgroundColor": "#f8f9fa"},
                            ],
                        ),
                    ),
                    html.Div(
                        className="split-side",
                        children=html.Div(
                            className="sidebar-sticky",
                            children=[
                                html.Div(id="results-detail", className="detail-card",
                                         children=html.P("Round summary appears "
                                                         "here.",
                                                         className="detail-empty")),
                                html.Div(className="detail-card", children=[
                                    html.H4("Elimination funnel",
                                            style={"margin": "0 0 8px 0",
                                                   "fontSize": "0.9rem",
                                                   "color": PRIMARY}),
                                    dcc.Graph(id="res-funnel",
                                              config={"displayModeBar": False},
                                              style={"height": "220px"}),
                                ]),
                            ],
                        ),
                    ),
                ],
            ),
            html.Div(
                id="results-career-section",
                style={"display": "none"},
                children=[
                    html.Hr(),
                    html.Div(
                        style={"display": "flex", "alignItems": "center",
                               "gap": "12px", "marginBottom": "4px"},
                        children=[
                            html.H4("Selected competitors: career trajectories",
                                    style={"margin": "0"}),
                            dcc.Dropdown(
                                id="results-career-metric",
                                options=[
                                    {"label": "Rank", "value": "rank"},
                                    {"label": "Finish time", "value": "time_seconds"},
                                ],
                                value="rank",
                                clearable=False,
                                style={"width": "140px", "fontSize": "0.85rem"},
                            ),
                        ],
                    ),
                    dcc.Graph(id="results-career-line"),
                ],
            ),
            html.Div(id="results-lightbox", className="lightbox hidden", children=[
                html.Div(id="results-lightbox-bg",
                         style={"position": "absolute", "inset": "0",
                                "zIndex": "1", "cursor": "pointer"}),
                html.Span("×", id="results-lightbox-close",
                          className="lightbox-close"),
                html.Div(id="results-lightbox-imgs", className="lightbox-imgs",
                         style={"position": "relative", "zIndex": "2"}),
            ]),
        ],
    )


@callback(
    Output("res-stage", "options"),
    Output("res-stage", "value"),
    Input("res-category", "value"),
    Input("res-year", "value"),
    State("res-stage", "value"),
)
def update_res_stages(category, year, current):
    stages = stages_for(category, year)
    return stage_options(stages, current=current)


@callback(
    Output("results-table", "data"),
    Output("results-table", "columns"),
    Output("results-table", "row_selectable"),
    Output("results-table", "selected_rows"),
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
        if rec.get("stage") == "final":
            rec["qualified"] = ""
        elif rec.get("qualified") is True or rec.get("qualified") == "True":
            rec["qualified"] = '<i class="fa-solid fa-circle-check" style="color:#27ae60"></i>'
        else:
            rec["qualified"] = '<i class="fa-solid fa-circle-xmark" style="color:#e74c3c"></i>'
    row_selectable = "multi" if category == "individual" else False
    return records, table_columns(category), row_selectable, []


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
    win = fin.loc[fin["time_seconds"].idxmin(), "time"] if not fin.empty else "-"
    unit = "teams" if category == "teams" else \
        ("pairs" if category == "pairs" else "competitors")
    stage_label = "All rounds" if stage == "All" else stage

    rows = [("Category", CATEGORY_LABELS[category]),
            ("Year", str(year)), ("Round", stage_label)]
    if stage != "All":
        first = dff.iloc[0]
        rows += [("Date", str(first.get("date", "") or "-")),
                 ("Pieces", str(first.get("puzzle_pieces", "") or "-")),
                 ("Time limit", str(first.get("time_limit", "") or "-"))]
    rows += [("Entrants", f"{n} {unit}")]
    if stage != "final":
        rows.append(("Qualified", str(qualified)))
    rows += [("Finishers", f"{finishers} ({fin_pct}%)"),
             ("DNF", f"{dnf} ({dnf_pct}%)"),
             ("Winning time", str(win or "-"))]

    urls = round_puzzle_urls(category, dff)
    gallery = [thumb("results-puz-thumb", u, f"Puzzle {i}", u)
               for i, u in enumerate(urls, start=1)]
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
    Input("results-lightbox-bg", "n_clicks"),
    State("results-table", "derived_viewport_data"),
    State("res-category", "value"),
)
def toggle_results_lightbox(active_cell, thumb_clicks, close_clicks, bg_clicks,
                            viewport, category):
    trig = ctx.triggered_id
    if trig in ("results-lightbox-close", "results-lightbox-bg"):
        return "lightbox hidden", no_update

    if isinstance(trig, dict) and trig.get("type") == "results-puz-thumb":
        clicked = next((i for i in ctx.inputs_list[1] if i["id"] == trig), None)
        if not clicked or not clicked.get("value"):
            return no_update, no_update
        return "lightbox", [html.Img(src=trig["index"])]

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


@callback(
    Output("results-career-section", "style"),
    Output("results-career-line", "figure"),
    Input("results-table", "selected_rows"),
    Input("results-career-metric", "value"),
    State("results-table", "data"),
    State("res-category", "value"),
)
def update_results_career(selected_rows, metric, data, category):
    hidden = {"display": "none"}
    blank = blank_fig()

    if category != "individual" or not selected_rows or not data:
        return hidden, blank

    individual = DATASETS["individual"]
    names = list(dict.fromkeys(
        data[i]["name"] for i in selected_rows if i < len(data)
    ))
    df = individual[individual["name"].isin(names)].copy()
    if df.empty:
        return hidden, blank

    df["bucket"] = df["stage"].map(stage_bucket)

    if metric == "time_seconds":
        col, agg, ytitle, reverse = "time_seconds", "min", "Finish time (minutes)", False
    else:
        col, agg, ytitle, reverse = "rank", "min", "Rank (lower = better)", True

    plot = df.dropna(subset=[col]).copy()
    if plot.empty:
        return hidden, blank

    plot = (plot.groupby(["name", "year", "bucket"], as_index=False)
            .agg({col: agg, "stage": "first"}))
    if metric == "time_seconds":
        plot = plot.rename(columns={col: "time_min"})
        plot["time_min"] = plot["time_min"] / 60
        col = "time_min"
    plot["bucket_order"] = plot["bucket"].map(BUCKET_ORDER)
    plot = plot.sort_values(["year", "bucket_order"])
    plot["x"] = plot["year"].astype(str) + " · " + plot["bucket"]
    x_order = list(dict.fromkeys(plot["x"]))

    val_label = "Time (min)" if metric == "time_seconds" else "Rank"
    val_fmt   = ".2f"        if metric == "time_seconds" else ".0f"

    fig = px.line(plot, x="x", y=col, color="name", markers=True,
                  category_orders={"x": x_order},
                  custom_data=["name", "year", "stage", "bucket", col])
    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Year: %{customdata[1]}<br>"
            "Stage: %{customdata[2]} (%{customdata[3]})<br>"
            f"{val_label}: %{{customdata[4]:{val_fmt}}}<extra></extra>"
        )
    )
    fig.update_layout(
        xaxis_title=None, yaxis_title=ytitle,
        legend_title=None,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="white", plot_bgcolor="white",
    )
    if reverse:
        fig.update_yaxes(autorange="reversed")
    return {"display": "block"}, fig


@callback(
    Output("res-funnel", "figure"),
    Input("res-category", "value"),
    Input("res-year", "value"),
)
def update_res_funnel(category, year):
    df = DATASETS[category]
    df = df[df["year"] == year].copy()
    df["bucket"] = df["stage"].map(stage_bucket)
    counts = df.groupby("bucket").size()
    counts = counts.reindex([b for b in LEVELS if b in counts.index])
    fig = go.Figure(go.Funnel(
        y=counts.index, x=counts.values,
        marker_color=ACCENT, textinfo="value+percent initial"))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="white",
                      font=dict(size=11))
    return fig
