WORLD_REGIONS = [
    "Middle East",
    "Africa",
    "APAC",
    "Europe",
    "South and Central Asia",
    "North America",
    "South America",
]

COUNTRY_REGION_MAP = {
    # Middle East
    "saudi arabia": "Middle East", "uae": "Middle East", "united arab emirates": "Middle East",
    "qatar": "Middle East", "kuwait": "Middle East", "bahrain": "Middle East",
    "oman": "Middle East", "iraq": "Middle East", "iran": "Middle East",
    "jordan": "Middle East", "israel": "Middle East", "egypt": "Middle East",
    "lebanon": "Middle East", "syria": "Middle East", "yemen": "Middle East",
    # Africa
    "nigeria": "Africa", "south africa": "Africa", "mozambique": "Africa",
    "angola": "Africa", "tanzania": "Africa", "kenya": "Africa",
    "ghana": "Africa", "senegal": "Africa", "cameroon": "Africa",
    "gabon": "Africa", "republic of congo": "Africa", "democratic republic of congo": "Africa",
    "ethiopia": "Africa", "mauritania": "Africa", "morocco": "Africa",
    "algeria": "Africa", "libya": "Africa", "sudan": "Africa",
    "namibia": "Africa", "madagascar": "Africa",
    # APAC
    "china": "APAC", "japan": "APAC", "south korea": "APAC", "korea": "APAC",
    "australia": "APAC", "indonesia": "APAC", "malaysia": "APAC",
    "singapore": "APAC", "thailand": "APAC", "vietnam": "APAC",
    "philippines": "APAC", "taiwan": "APAC", "myanmar": "APAC",
    "cambodia": "APAC", "laos": "APAC", "new zealand": "APAC",
    "papua new guinea": "APAC", "timor-leste": "APAC", "brunei": "APAC",
    # Europe
    "netherlands": "Europe", "germany": "Europe", "france": "Europe",
    "united kingdom": "Europe", "uk": "Europe", "norway": "Europe",
    "denmark": "Europe", "sweden": "Europe", "finland": "Europe",
    "belgium": "Europe", "spain": "Europe", "portugal": "Europe",
    "italy": "Europe", "greece": "Europe", "turkey": "Europe",
    "poland": "Europe", "russia": "Europe", "ukraine": "Europe",
    "romania": "Europe", "croatia": "Europe", "cyprus": "Europe",
    "switzerland": "Europe", "austria": "Europe",
    # South and Central Asia
    "india": "South and Central Asia", "pakistan": "South and Central Asia",
    "bangladesh": "South and Central Asia", "sri lanka": "South and Central Asia",
    "kazakhstan": "South and Central Asia", "uzbekistan": "South and Central Asia",
    "turkmenistan": "South and Central Asia", "azerbaijan": "South and Central Asia",
    "nepal": "South and Central Asia",
    # North America
    "united states": "North America", "usa": "North America", "us": "North America",
    "canada": "North America", "mexico": "North America",
    # South America
    "brazil": "South America", "argentina": "South America", "colombia": "South America",
    "chile": "South America", "peru": "South America", "venezuela": "South America",
    "ecuador": "South America", "guyana": "South America", "suriname": "South America",
    "trinidad and tobago": "South America", "uruguay": "South America",
}

def get_world_region(country: str | None) -> str | None:
    if not country:
        return None
    return COUNTRY_REGION_MAP.get(country.lower().strip())
