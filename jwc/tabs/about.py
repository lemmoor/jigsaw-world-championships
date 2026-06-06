from dash import html


# Year-by-year format facts, grounded in the result CSVs.
# Columns: year, individual entrants, total rounds (stages), pieces, time limit.
_FORMAT_ROWS = [
    ("2019", "199", "1", "Ind 500 · Pairs 500 · Teams 5000", "2:00 / 8:00 (teams)"),
    ("2022", "410", "4", "Ind 500 · Pairs 500-1000 · Teams 2000-2500", "1:30 / 3:00 (teams)"),
    ("2023", "1,108", "9", "Ind 500 · Pairs 500-1000 · Teams 2000", "1:30 / 3:00 (teams)"),
    ("2024", "1,644", "9", "Ind 500 · Pairs 500-1000 · Teams 2000", "1:15-1:30 / 3:00 (teams)"),
    ("2025", "1,711", "10", "Ind 500 · Pairs 500-1000 · Teams 2000", "1:00-1:30 / 3:00 (teams)"),
]


def _format_table():
    header = html.Tr([html.Th(c) for c in
                      ("Year", "Individual entrants", "Rounds",
                       "Puzzle pieces", "Time limit")])
    body = [html.Tr([html.Td(cell) for cell in row]) for row in _FORMAT_ROWS]
    return html.Table(className="about-table",
                      children=[html.Thead(header), html.Tbody(body)])


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
                html.Li("Pairs: 500 pieces in the group rounds, 1,000 pieces in "
                        "the final from 2022 onwards (500 throughout in 2019), "
                        "two people."),
                html.Li("Teams: a single 5,000-piece marathon in 2019, settling "
                        "at 2,000 pieces from 2023 onwards, four people."),
            ]),
            html.H3("How the format changed over time"),
            html.P("2019 was a one-off event: a single round per category and a "
                   "5,000-piece, eight-hour team marathon. From 2022 the "
                   "championship grew roughly eight-fold and matured into the "
                   "multi-round elimination ladder, with time limits tightening "
                   "as the field expanded. Because of this, times are only "
                   "loosely comparable across years."),
            _format_table(),
        ],
    )
