import pandas as pd
import plotly.express as px

individual = pd.read_csv("data/individual_results.csv")
pairs = pd.read_csv("data/pairs_results.csv")
teams = pd.read_csv("data/teams_results.csv")

YEARS = sorted(int(y) for y in individual["year"].unique())

DATASETS = {"individual": individual, "pairs": pairs, "teams": teams}
CATEGORY_LABELS = {"individual": "Individual", "pairs": "Pairs", "teams": "Teams"}

REAL_STAGES = {"A", "B", "C", "D", "E", "F", "S1", "S2", "S3", "final"}

# Map data country names to ISO-3166 alpha-3 codes for the choropleth.
# "country names" locationmode is deprecated, so we drive the map with ISO-3.
# Entries with no code (e.g. "International Puzzlers") are dropped from the map.
COUNTRY_ISO3 = {
    "Albania": "ALB", "Andorra": "AND", "Argentina": "ARG", "Australia": "AUS",
    "Austria": "AUT", "Bangladesh": "BGD", "Barbados": "BRB", "Belarus": "BLR",
    "Belgium": "BEL", "Bolivia": "BOL", "Brazil": "BRA", "Bulgaria": "BGR",
    "Cameroon": "CMR", "Canada": "CAN", "Chile": "CHL", "China": "CHN",
    "Colombia": "COL", "Costa Rica": "CRI", "Croatia": "HRV", "Cuba": "CUB",
    "Cyprus": "CYP", "Czech Republic": "CZE", "Denmark": "DNK", "Dominica": "DMA",
    "Ecuador": "ECU", "Egypt": "EGY", "Estonia": "EST", "Finland": "FIN",
    "France": "FRA", "Germany": "DEU", "Greece": "GRC", "Guatemala": "GTM",
    "Honduras": "HND", "Hungary": "HUN", "Iceland": "ISL", "India": "IND",
    "Indonesia": "IDN", "Iran": "IRN", "Ireland": "IRL", "Israel": "ISR",
    "Italy": "ITA", "Japan": "JPN", "Latvia": "LVA", "Lithuania": "LTU",
    "Luxembourg": "LUX", "Malaysia": "MYS", "Malta": "MLT", "Mexico": "MEX",
    "New Zealand": "NZL", "Norway": "NOR", "Panama": "PAN", "Paraguay": "PRY",
    "Peru": "PER", "Poland": "POL", "Portugal": "PRT", "Romania": "ROU",
    "Russia": "RUS", "Saudi Arabia": "SAU", "Serbia": "SRB", "Singapore": "SGP",
    "Slovakia": "SVK", "Slovenia": "SVN", "South Africa": "ZAF",
    "South Korea": "KOR", "Spain": "ESP", "Sweden": "SWE", "Switzerland": "CHE",
    "Taiwan (Province of China)": "TWN", "Thailand": "THA",
    "The Netherlands": "NLD", "Trinidad and Tobago": "TTO", "Tunisia": "TUN",
    "Türkiye": "TUR", "USA": "USA", "Uganda": "UGA", "Ukraine": "UKR",
    "United Kingdom": "GBR", "Uruguay": "URY", "Venezuela": "VEN",
    "Vietnam": "VNM",
}

# Brand palette (mirrors assets/style.css custom properties)
PRIMARY = "#2c3e50"
ACCENT = "#e67e22"
MUTED = "#6c757d"
SEQ = px.colors.sequential.Oranges
