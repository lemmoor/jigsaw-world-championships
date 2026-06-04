import pandas as pd

from .data import DATASETS


LEVELS = ["Group rounds", "Semi-finals", "Final"]
BUCKET_ORDER = {lv: i for i, lv in enumerate(LEVELS)}


def stage_sort_key(s):
    """Order stages: group rounds (A-F) then semis (S1-S3) then final."""
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


def stage_options(stages, default="final", current=None):
    """Build (options, value) for a stage Dropdown."""
    opts = [{"label": "All", "value": "All"}] + \
           [{"label": s, "value": s} for s in stages]
    valid = list(stages) + ["All"]
    value = current if current in valid else (
        default if default in stages else stages[-1]
    )
    return opts, value


def puzzle_series(df):
    """Label each finisher row by the distinct puzzle it solved.

    Within a stage, puzzles are numbered in first-appearance order (e.g. the
    2025 two-puzzle split produces A·1, A·2); a stage with a single puzzle keeps
    its bare name (B, S1, final). Returns the frame with a puzzle_label column
    and an ordered {label: url} map.
    """
    df = df.copy()
    pair_to_label = {}
    label_url = {}
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
    """Total seconds to H:MM:SS (or M:SS under an hour)."""
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
    cols += [("Time", "time"), ("Gap", "gap"), ("Pieces", "pieces_completed")]
    spec = [{"name": n, "id": i} for n, i in cols]
    spec.append({"name": "Qualified", "id": "qualified",
                 "presentation": "markdown"})
    spec.append({"name": "Puzzle(s)", "id": "puzzles_md",
                 "presentation": "markdown"})
    return spec


def stages_for(category, year=None):
    df = DATASETS[category]
    if year is not None:
        df = df[df["year"] == year]
    return sorted(df["stage"].unique(), key=stage_sort_key)
