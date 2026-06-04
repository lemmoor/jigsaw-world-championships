from dash import html


def about_tab():
    return html.Div(
        className="page-content about",
        children=[
            html.H2("About this dashboard"),
            html.P("An interactive look at all five World Jigsaw Puzzle "
                   "Championships held in Valladolid, Spain (2019, 2022-2025). "
                   "Data was scraped from worldjigsawpuzzle.org."),
            html.H3("How the competition works"),
            html.P("Each category runs the same format: group rounds (A, B, C ...) "
                   "split the field; the top finishers advance to semi-finals "
                   "(S1, S2 ...) and then a final. The qualified flag marks "
                   "competitors who advanced; in the final no one qualifies."),
            html.Ul([
                html.Li("Individual: 500-piece puzzle, solo competitors."),
                html.Li("Pairs: 500 (2019) or 1,000 (2022+) pieces, two people."),
                html.Li("Teams: 2,000-5,000 pieces across two puzzles, four people."),
            ]),
            html.H3("Using the tabs"),
            html.Ul([
                html.Li("Results: full round tables with elimination funnel; click a row to see the puzzle."),
                html.Li("Countries: map and ranking; click a country to focus it."),
                html.Li("Times: finish-time spread and did-not-finish rates."),
            ]),
            html.H3("Reading the data"),
            html.P("A row is a did-not-finish (DNF) when it has a piece count "
                   "instead of a time. Times are only comparable within a category "
                   "because puzzle sizes differ. Competitor names are consistent "
                   "within a year, but minor transliteration differences can occur "
                   "across years."),
        ],
    )
