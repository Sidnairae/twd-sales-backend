import re

NORMALIZED_STAGES = [
    "Pre-design", "Design", "Pre-tender", "Tender", "EPC Award", "Execution",
]

CATEGORY_KEYWORDS = {
    "13": ["heavy lift", "heavy transport", "modular", "modules", "spmt", "waste to energy", "wte"],
    "1":  ["pier", "wharf", "jetty", "berth", "quay", "dock", "quayside"],
    "2":  ["breakwater", "seawall", "sea wall", "wave breaker", "wave deflector", "revetment", "rubble mound"],
    "3":  ["dolphin", "mooring", "fender"],
    "4":  ["diffuser", "intake", "outfall", "sea outfall", "water intake"],
    "5":  ["caisson"],
    "7":  ["immersed tunnel", "lock", "dyke", "dike", "flood barrier", "storm surge"],
    "9":  ["terminal", "lng terminal", "container terminal", "bulk terminal", "oil terminal", "gas terminal"],
    "10": ["loading", "offloading", "loading arm", "ship loader", "conveyor"],
    "12": ["bridge", "flyover", "overpass", "viaduct", "cable-stayed", "suspension bridge"],
}

STAGE_MAP = {
    "pre-feed": "Pre-design", "pre feed": "Pre-design", "concept": "Pre-design",
    "feasibility": "Pre-design", "scoping": "Pre-design", "planning": "Pre-design",
    "feed": "Design", "front end engineering": "Design", "basic design": "Design",
    "detailed design": "Design", "engineering": "Design",
    "pre-tender": "Pre-tender", "pre tender": "Pre-tender", "procurement": "Pre-tender",
    "bid": "Tender", "tender": "Tender", "rfp": "Tender", "rfq": "Tender",
    "invitation to bid": "Tender", "itb": "Tender",
    "award": "EPC Award", "awarded": "EPC Award", "contract award": "EPC Award",
    "epc award": "EPC Award", "loi": "EPC Award",
    "execution": "Execution", "construction": "Execution", "install": "Execution",
    "onstream": "Execution", "operating": "Execution", "commissioning": "Execution",
}

def auto_categorize(name: str, description: str | None, sector: str | None = None) -> str:
    text = f"{name} {description or ''} {sector or ''}".lower()
    for cat_id, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return cat_id
    return "1"  # default

def normalize_stage(raw_status: str | None) -> str | None:
    if not raw_status:
        return None
    s = raw_status.lower().strip()
    for key, normalized in STAGE_MAP.items():
        if key in s:
            return normalized
    return None
