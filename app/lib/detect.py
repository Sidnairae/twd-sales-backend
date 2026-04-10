import re

FID_PATTERNS = [
    re.compile(r'\bfid\b.{0,40}(approv|taken|made|complet|grant|receiv|secur|pass|sanction|reach)', re.I),
    re.compile(r'(approv|taken|made|complet|grant|receiv|secur|pass).{0,40}\bfid\b', re.I),
    re.compile(r'final investment decision.{0,40}(approv|taken|made|grant|receiv|secur|sanction)', re.I),
    re.compile(r'(approv|taken|made|grant|receiv|secur|sanction).{0,40}final investment decision', re.I),
    re.compile(r'financial investment decision.{0,40}(approv|taken|made|grant)', re.I),
    re.compile(r'\b(project sanction|investment sanction|sanctioned project)\b', re.I),
]

CONTRACTOR_PATTERNS = [
    re.compile(r'\b(epc|epci|epcm) (contract|contractor).{0,60}(award|select|appoint|win|secure|choos)', re.I),
    re.compile(r'(award|select|appoint|win|secure|choos).{0,60}\b(epc|epci|epcm) (contract|contractor)\b', re.I),
    re.compile(r'contract.{0,30}(awarded|awarded to|won by|secured by|given to|let to)', re.I),
    re.compile(r'(awarded|appointed|selected|chosen).{0,40}(as|as the).{0,20}(contractor|epc|epci|consortium|joint venture)', re.I),
    re.compile(r'(main contractor|general contractor|prime contractor).{0,40}(is|are|has been|selected|appointed|awarded)', re.I),
    re.compile(r'\b(won|secured|awarded).{0,40}(construction|installation|epc|epci).{0,40}contract', re.I),
]

NAME_PATTERNS = [
    re.compile(r'(?:awarded to|contract awarded to|won by|secured by|appointed as contractor|selected as contractor)\s+([A-Z][A-Za-z0-9\s&\-\.,]+?)(?:\s+(?:for|to|with|and|in|on|at|\()|[,\.;]|$)'),
    re.compile(r'([A-Z][A-Za-z0-9\s&\-]+?)\s+(?:has been awarded|won the contract|secured the contract|has been selected as|has been appointed)'),
]

def detect_fid(description: str | None) -> bool:
    if not description:
        return False
    return any(p.search(description) for p in FID_PATTERNS)

def detect_contractor(description: str | None) -> tuple[bool, str | None]:
    if not description:
        return False, None
    detected = any(p.search(description) for p in CONTRACTOR_PATTERNS)
    if not detected:
        return False, None
    for pattern in NAME_PATTERNS:
        match = pattern.search(description)
        if match:
            name = match.group(1).strip()
            if 2 <= len(name) <= 60 and not re.match(r'^(the|a|an|its|their|this|that)$', name, re.I):
                return True, name
    return True, None
