SAVED_SEARCHES = {
    "1":  {"label": "Pier / Wharf / Jetty / Berth / Quay / Dock",          "short": "Pier & Berth",        "color": "#3b82f6"},
    "2":  {"label": "Breakwater / Seawall / Wave Breaker / Wave Deflector", "short": "Breakwater",          "color": "#10b981"},
    "3":  {"label": "Dolphin / Mooring / Fender",                          "short": "Dolphin & Mooring",   "color": "#8b5cf6"},
    "4":  {"label": "Diffuser / Intake / Outfall",                         "short": "Diffuser & Outfall",  "color": "#06b6d4"},
    "5":  {"label": "Caisson",                                             "short": "Caisson",             "color": "#f59e0b"},
    "7":  {"label": "Immersed Tunnel / Lock / Dyke / Dike",                "short": "Tunnel, Lock & Dyke", "color": "#84cc16"},
    "9":  {"label": "Terminal",                                            "short": "Terminal",            "color": "#f97316"},
    "10": {"label": "Loading Facilities",                                  "short": "Loading Facilities",  "color": "#14b8a6"},
    "12": {"label": "Bridge / Flyover / Overpass",                         "short": "Bridge",              "color": "#a78bfa"},
    "13": {"label": "Heavy Lift & Transport Design",                       "short": "Heavy Lift",          "color": "#e11d48"},
}

def get_category_label(saved_search_id: str) -> str:
    return SAVED_SEARCHES.get(saved_search_id, {}).get("short", f"Search {saved_search_id}")

def get_category_color(saved_search_id: str) -> str:
    return SAVED_SEARCHES.get(saved_search_id, {}).get("color", "#6b7280")
