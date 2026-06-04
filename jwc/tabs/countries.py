import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, callback, html, dcc

from ..data import DATASETS, COUNTRY_ISO3, PRIMARY, ACCENT, SEQ
from ..domain import fmt_time
from ..theme import blank_fig
from ..components import category_control, year_control


def countries_tab():
    return html.Div(
        className="page-content",
        children=[
            html.H2("Countries"),
            html.P("Where do the world's best puzzlers come from? "
                   "Switch between medals, finalist appearances, and finish times using the metric dropdown. "
                   "Click a country on the map to highlight it in the ranking.",
                   className="tab-intro"),
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
                                {"label": "Average finish time", "value": "avg_time"},
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


def _country_stats(category, year, metric):
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
    elif metric == "best_time":
        fin = finals.dropna(subset=["time_seconds"])
        agg = fin.groupby("country")["time_seconds"].min() \
            .rename("value").reset_index()
        title = "Best finish time (lower = better)"
    else:
        fin = finals.dropna(subset=["time_seconds"])
        agg = fin.groupby("country")["time_seconds"].mean() \
            .rename("value").reset_index()
        title = "Average finish time (lower = better)"
    agg["iso3"] = agg["country"].map(COUNTRY_ISO3)
    agg = agg.dropna(subset=["iso3"])
    return agg, title


@callback(
    Output("ctry-map", "figure"),
    Input("ctry-category", "value"),
    Input("ctry-year", "value"),
    Input("ctry-metric", "value"),
)
def update_country_map(category, year, metric):
    agg, title = _country_stats(category, year, metric)
    if agg.empty:
        fig = blank_fig("No data for this selection")
    else:
        fig = px.choropleth(
            agg, locations="iso3", locationmode="ISO-3",
            color="value", hover_name="country",
            color_continuous_scale=SEQ if metric not in ("best_time", "avg_time") else SEQ[::-1],
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
    agg, title = _country_stats(category, year, metric)
    if agg.empty:
        fig = blank_fig("No data for this selection")
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        return fig
    ascending = metric in ("best_time", "avg_time")
    agg = agg.sort_values("value", ascending=ascending).head(15)
    selected = None
    if click and click.get("points"):
        pt = click["points"][0]
        selected = pt.get("hovertext") or pt.get("location")
    iso_to_country = dict(zip(agg["iso3"], agg["country"]))
    selected_country = iso_to_country.get(selected, selected)
    colors = [ACCENT if (selected_country and c == selected_country) else PRIMARY
              for c in agg["country"]]
    fig = go.Figure(go.Bar(
        x=agg["value"], y=agg["country"], orientation="h",
        marker_color=colors,
        text=[fmt_time(v) for v in agg["value"]] if metric in ("best_time", "avg_time")
        else agg["value"],
    ))
    fig.update_layout(
        title=f"Top countries - {title}",
        yaxis=dict(autorange="reversed"),
        xaxis=dict(visible=False),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white", plot_bgcolor="white", height=480,
    )
    return fig
