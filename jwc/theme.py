import plotly.graph_objects as go

from .data import PRIMARY, ACCENT

LINE_DARK = "#161616"


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def blank_fig(message=""):
    fig = go.Figure()
    if message:
        fig.add_annotation(text=message, showarrow=False)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10),
                      paper_bgcolor="white", plot_bgcolor="white")
    return fig


def style_fig(fig, *, x_title=None, y_title=None, categorical_x=False,
              height=None, margin_top=10, show_legend=True):
    updates = dict(
        margin=dict(l=10, r=10, t=margin_top, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    if x_title is not None:
        updates["xaxis_title"] = x_title
    if y_title is not None:
        updates["yaxis_title"] = y_title
    if categorical_x:
        updates.setdefault("xaxis", {})
        updates["xaxis"] = dict(type="category")
    if height is not None:
        updates["height"] = height
    if not show_legend:
        updates["showlegend"] = False
    fig.update_layout(**updates)
    return fig
