from datetime import date, datetime
from dataclasses import dataclass
import math

WEIGHTS = {"past_work": 25, "execution_date": 25, "project_value": 20, "project_phase": 20, "relationship": 10}

def get_week_start(d: date | None = None) -> str:
    d = d or date.today()
    diff = (d.weekday())  # Monday=0
    monday = d.fromordinal(d.toordinal() - diff)
    return monday.isoformat()

@dataclass
class ScoreBreakdown:
    past_work: float
    execution_date: float
    project_value: float
    project_phase: float
    relationship: float
    total: float

    def to_dict(self) -> dict:
        return {
            "past_work": self.past_work,
            "execution_date": self.execution_date,
            "project_value": self.project_value,
            "project_phase": self.project_phase,
            "relationship": self.relationship,
            "total": self.total,
        }

def score_project(
    project_value_usd: int | None,
    execution_date_str: str | None,
    status: str,
    key_contacts_count: int,
    momentum_score: float | None,
    fid_detected: bool = False,
    contractor_detected: bool = False,
    contractor_name: str | None = None,
    history_deals: int = 0,
    history_total_value: float = 0,
    history_last_deal: str | None = None,
    today: date | None = None,
) -> ScoreBreakdown:
    today = today or date.today()

    # 1. Past work (25 pts)
    past_work = 0.0
    if history_deals > 0:
        past_work = 15
        past_work += min(7, history_deals * 2)
        if history_last_deal:
            try:
                last = date.fromisoformat(history_last_deal)
                days_since = (today - last).days
                if days_since < 365:   past_work += 3
                elif days_since < 730: past_work += 1.5
            except Exception:
                pass
        past_work = min(WEIGHTS["past_work"], past_work)

    # 2. Execution date urgency (25 pts)
    execution_date = 0.0
    if execution_date_str:
        try:
            exec_date = date.fromisoformat(execution_date_str)
            days_until = (exec_date - today).days
            if   days_until <= 0:   execution_date = 5
            elif days_until <= 90:  execution_date = 25
            elif days_until <= 180: execution_date = 22
            elif days_until <= 365: execution_date = 18
            elif days_until <= 730: execution_date = 12
            else:                   execution_date = 5
        except Exception:
            execution_date = 8
    else:
        execution_date = 8

    # 3. Project value (20 pts)
    project_value = 0.0
    if project_value_usd and project_value_usd > 0:
        log_val = math.log10(project_value_usd)
        normalised = max(0, min(1, (log_val - 6) / 3))
        project_value = normalised * WEIGHTS["project_value"]
    else:
        project_value = 5

    # 4. Project phase (20 pts)
    s = (status or "").lower()
    if any(k in s for k in ["bid", "tender", "rfp", "rfq", "feed"]):
        project_phase = 20.0
    elif any(k in s for k in ["concept", "planning", "pre-feed", "pre feed", "study"]):
        project_phase = 16.0
    elif any(k in s for k in ["award", "select", "approved", "sanction"]):
        project_phase = 10.0
    elif any(k in s for k in ["execut", "construct", "install", "onstream", "operat"]):
        project_phase = 3.0
    elif any(k in s for k in ["cancel", "suspend", "defer", "on hold"]):
        project_phase = 0.0
    else:
        project_phase = 8.0

    if fid_detected:
        project_phase = min(WEIGHTS["project_phase"], project_phase + 5)

    # 5. Relationship (10 pts)
    relationship = 0.0
    if history_deals > 0:   relationship += 6
    if key_contacts_count > 0:  relationship += 3
    if key_contacts_count >= 3: relationship += 1
    relationship = min(WEIGHTS["relationship"], relationship)

    # Contractor bonus
    contractor_bonus = 5.0 if contractor_name else (3.0 if contractor_detected else 0.0)

    # Momentum bonus
    momentum_bonus = (momentum_score / 100) * 5 if momentum_score is not None else 0.0

    total = past_work + execution_date + project_value + project_phase + relationship + momentum_bonus + contractor_bonus

    return ScoreBreakdown(
        past_work=round(past_work, 1),
        execution_date=round(execution_date, 1),
        project_value=round(project_value, 1),
        project_phase=round(project_phase, 1),
        relationship=round(relationship, 1),
        total=round(total, 1),
    )
