from dash import html


def about_tab():
    return html.Div(
        className="page-content about",
        children=[
            html.H2("About this dashboard"),
            html.P(["An interactive look at all five World Jigsaw Puzzle "
                    "Championships held in Valladolid, Spain (2019, 2022-2025). "
                    "Data was scraped from ",
                    html.A("worldjigsawpuzzle.org",
                           href="https://worldjigsawpuzzle.org/",
                           target="_blank"),
                    "."]),
            html.H3("How the competition works"),
            html.P("Each category runs the same elimination format: group rounds "
                   "(A, B, C ...) split the field; the top finishers advance to "
                   "semi-finals (S1, S2 ...) and then a single final."),
            html.H3("Categories"),
            html.Ul([
                html.Li("Individual: 500-piece puzzle, solo competitors."),
                html.Li("Pairs: 500 pieces in 2019, 1,000 pieces from 2022 onwards, two people."),
                html.Li("Teams: 2,000-5,000 pieces across two puzzles, four people."),
            ]),
        ],
    )
