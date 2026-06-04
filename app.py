from dash import Dash, Input, Output, callback, dcc, html

from jwc.components import header
# Importing tab modules registers their callbacks.
from jwc.tabs.results import results_tab
from jwc.tabs.countries import countries_tab
from jwc.tabs.times import times_tab
from jwc.tabs.about import about_tab

# IDs in tabs other than the default are created on demand by render_tab, so
# Dash must allow callbacks that reference not-yet-rendered components.
app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/7.0.1/css/all.min.css"
    ],
)
app.title = "Jigsaw World Championships"

TABS = [
    ("Results", "tab-results"),
    ("Countries", "tab-countries"),
    ("Times", "tab-times"),
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
        "tab-about": about_tab,
    }[tab]()


if __name__ == "__main__":
    app.run(debug=True)
