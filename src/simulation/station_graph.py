"""
Subway Network Topology — Station Graph.

Models TTC subway lines as ordered lists of stations with baseline travel times.
MVP scope: Line 1 (Yonge-University) only.

Used by the Monte Carlo simulator to compute routes and baseline travel times.
"""

# ============================================================================
# Line 1: Yonge-University (U-shape)
# Ordered: Finch → southbound on Yonge → Union → northbound on University → VMC
# ============================================================================
LINE_1_STATIONS = [
    "Finch",
    "North York Centre",
    "Sheppard-Yonge",
    "York Mills",
    "Lawrence",
    "Eglinton",
    "Davisville",
    "St Clair",
    "Summerhill",
    "Rosedale",
    "Bloor-Yonge",
    "Wellesley",
    "College",
    "TMU",
    "Queen",
    "King",
    "Union",
    "St Andrew",
    "Osgoode",
    "St Patrick",
    "Queen's Park",
    "Museum",
    "St George",
    "Spadina",
    "Dupont",
    "St Clair West",
    "Cedarvale",
    "Glencairn",
    "Lawrence West",
    "Yorkdale",
    "Wilson",
    "Sheppard West",
    "Downsview Park",
    "Finch West",
    "York University",
    "Pioneer Village",
    "Highway 407",
    "Vaughan Metropolitan Centre",
]

# ============================================================================
# Line 2: Bloor-Danforth (for future use, not in MVP)
# ============================================================================
LINE_2_STATIONS = [
    "Kipling", "Islington", "Royal York", "Old Mill", "Jane",
    "Runnymede", "High Park", "Keele", "Dundas West", "Lansdowne",
    "Dufferin", "Ossington", "Christie", "Bathurst", "Spadina",
    "St George", "Bay", "Bloor-Yonge", "Sherbourne", "Castle Frank",
    "Broadview", "Chester", "Pape", "Donlands", "Greenwood",
    "Coxwell", "Woodbine", "Main Street", "Victoria Park",
    "Warden", "Kennedy",
]

# ============================================================================
# Baseline travel time (minutes) between adjacent stations
# Average across TTC subway system; typical range is 1.5–3.0 min
# ============================================================================
BASELINE_SEGMENT_TIME = 2.0  # minutes per segment


def get_route(origin: str, destination: str,
              line: list[str] = None) -> list[str]:
    """
    Get ordered list of stations from origin to destination on a given line.

    Args:
        origin: Starting station name (must match canonical name)
        destination: Ending station name (must match canonical name)
        line: Ordered list of station names. Defaults to LINE_1_STATIONS.

    Returns:
        List of station names from origin to destination (inclusive).

    Raises:
        ValueError: If origin or destination not found on the line.
    """
    if line is None:
        line = LINE_1_STATIONS

    try:
        i_start = line.index(origin)
    except ValueError:
        raise ValueError(
            f"Origin station '{origin}' not found on the line. "
            f"Available stations: {line}"
        )

    try:
        i_end = line.index(destination)
    except ValueError:
        raise ValueError(
            f"Destination station '{destination}' not found on the line. "
            f"Available stations: {line}"
        )

    if i_start <= i_end:
        return line[i_start:i_end + 1]
    else:
        # Traveling in reverse direction
        return line[i_end:i_start + 1][::-1]


def get_baseline_time(origin: str, destination: str,
                      line: list[str] = None) -> float:
    """
    Calculate baseline (no-delay) travel time between two stations.

    Returns:
        Travel time in minutes.
    """
    route = get_route(origin, destination, line)
    n_segments = len(route) - 1
    return n_segments * BASELINE_SEGMENT_TIME


def list_stations(line: list[str] = None) -> list[str]:
    """Return all stations on a line (default Line 1)."""
    return list(line or LINE_1_STATIONS)
