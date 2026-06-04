from dash import dcc, html

from .data import CATEGORY_LABELS, YEARS


def header():
    return html.Header(
        className="app-header",
        children=[
            html.Div("JWC", className="app-logo"),
            html.Div(
                className="app-title",
                children=[
                    html.H1("Jigsaw World Championships"),
                    html.P("Valladolid, Spain · 2019 - 2025"),
                ],
            ),
        ],
    )


def labeled_dropdown(label, component_id, options, value, width="150px", **kwargs):
    return html.Div([
        html.Div(label, className="control-label"),
        dcc.Dropdown(id=component_id, options=options, value=value,
                     clearable=False, style={"width": width}, **kwargs),
    ])


def category_control(component_id, value="individual"):
    return labeled_dropdown(
        "Category", component_id,
        [{"label": v, "value": k} for k, v in CATEGORY_LABELS.items()],
        value, width="150px",
    )


def year_control(component_id, value=None, include_all=False, label="Year"):
    opts = ([{"label": "All years", "value": "All"}] if include_all else [])
    opts += [{"label": str(y), "value": y} for y in YEARS]
    return labeled_dropdown(label, component_id, opts,
                            value if value is not None else YEARS[-1],
                            width="130px")


def stage_control(component_id, value="final"):
    return labeled_dropdown("Stage", component_id, [], value, width="150px")


def thumb(type_id, index, label, url, selected=False):
    """Thumbnail button used in puzzle galleries (Results sidebar and Times tab)."""
    cls = "puzzle-thumb selected" if selected else "puzzle-thumb"
    return html.Button(
        id={"type": type_id, "index": index}, className=cls, n_clicks=0,
        children=[html.Img(src=url),
                  html.Div(label, className="puzzle-thumb-label")])
