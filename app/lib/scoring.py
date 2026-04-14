"""
scoring.py — project priority scoring logic.

Each project is scored out of ~100 points across five dimensions.
Weights are defined in config.py so they can be tuned in one place.

Score breakdown:
  - past_work      (25 pts)  Have we worked with this client before?
  - execution_date (25 pts)  How soon does the project need to start?
  - project_value  (20 pts)  How large is the contract (log scale)?
  - project_phase  (20 pts)  Is the project at a stage TWD can influence?
  - relationship   (10 pts)  Do we have contacts and history?

Bonus points (small, not capped against the 100):
  - momentum_bonus     up to +5  if GlobalData momentum score is high
  - contractor_bonus      +5     if a named contractor is known
                          +3     if a contractor is detected but unnamed
"""

import math
import logging
from datetime import date
from dataclasses import dataclass

from app.config import SCORE_WEIGHTS

logger = logging.getLogger(__name__)


def get_week_start(d: date | None = None) -> str:
    """Return the ISO date string of the Monday of the given (or current) week."""
    d = d or date.today()
    monday = d.fromordinal(d.toordinal() - d.weekday())  # weekday(): Mon=0, Sun=6
    return monday.isoformat()


@dataclass
class ScoreBreakdown:
    past_work:      float
    execution_date: float
    project_value:  float
    project_phase:  float
    relationship:   float
    total:          float

    def to_dict(self) -> dict:
        return {
            "past_work":      self.past_work,
            "execution_date": self.execution_date,
            "project_value":  self.project_value,
            "project_phase":  self.project_phase,
            "relationship":   self.relationship,
            "total":          self.total,
        }


def score_project(
    project_value_usd:   int | None,
    execution_date_str:  str | None,
    status:              str,
    key_contacts_count:  int,
    momentum_score:      float | None,
    fid_detected:        bool = False,
    contractor_detected: bool = False,
    contractor_name:     str | None = None,
    history_deals:       int = 0,
    history_last_deal:   str | None = None,
    today:               date | None = None,
) -> ScoreBreakdown:
    """
    Score a single project and return a breakdown.

    All parameters are optional/nullable — missing values score zero for
    that dimension so the function never crashes on incomplete data.
    """
    today = today or date.today()

    # ------------------------------------------------------------------
    # 1. Past work  (max 25 pts)
    #    Base 15 pts for any prior engagement, +2 per deal (capped at 7),
    #    +3 if the last deal was within a year, +1.5 if within two years.
    # ------------------------------------------------------------------
    past_work = 0.0
    if history_deals > 0:
        past_work = 15.0
        past_work += min(7.0, history_deals * 2.0)
        if history_last_deal:
            try:
                last = date.fromisoformat(history_last_deal)
                days_since = (today - last).days
                if days_since < 365:
                    past_work += 3.0
                elif days_since < 730:
                    past_work += 1.5
            except ValueError:
                logger.warning("Could not parse history_last_deal date: %s", history_last_deal)
        past_work = min(SCORE_WEIGHTS["past_work"], past_work)

    # ------------------------------------------------------------------
    # 2. Execution date urgency  (max 25 pts)
    #    Closer start date = higher score.  Unknown date = 8 pts.
    # ------------------------------------------------------------------
    execution_date = 0.0
    if execution_date_str:
        try:
            exec_date  = date.fromisoformat(execution_date_str)
            days_until = (exec_date - today).days
            if   days_until <= 0:    execution_date = 5.0   # already started / overdue
            elif days_until <= 90:   execution_date = 25.0
            elif days_until <= 180:  execution_date = 22.0
            elif days_until <= 365:  execution_date = 18.0
            elif days_until <= 730:  execution_date = 12.0
            else:                    execution_date = 5.0
        except ValueError:
            logger.warning("Could not parse execution_date: %s", execution_date_str)
            execution_date = 8.0
    else:
        execution_date = 8.0

    # ------------------------------------------------------------------
    # 3. Project value  (max 20 pts, log scale)
    #    $1 M → 0 pts,  $1 B → 20 pts.  Unknown value → 5 pts.
    # ------------------------------------------------------------------
    project_value = 0.0
    if project_value_usd and project_value_usd > 0:
        log_val    = math.log10(project_value_usd)
        normalised = max(0.0, min(1.0, (log_val - 6) / 3))  # 10^6 = $1M, 10^9 = $1B
        project_value = normalised * SCORE_WEIGHTS["project_value"]
    else:
        project_value = 5.0

    # ------------------------------------------------------------------
    # 4. Project phase  (max 20 pts)
    #    Tender/FEED stages score highest — that is where TWD can win work.
    #    Already in execution or cancelled = low score.
    # ------------------------------------------------------------------
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
        # Final Investment Decision confirmed → bump phase score
        project_phase = min(SCORE_WEIGHTS["project_phase"], project_phase + 5.0)

    # ------------------------------------------------------------------
    # 5. Relationship  (max 10 pts)
    #    Do we have prior dealings and named contacts for this company?
    # ------------------------------------------------------------------
    relationship = 0.0
    if history_deals > 0:
        relationship += 6.0
    if key_contacts_count > 0:
        relationship += 3.0
    if key_contacts_count >= 3:
        relationship += 1.0
    relationship = min(SCORE_WEIGHTS["relationship"], relationship)

    # ------------------------------------------------------------------
    # Bonus: contractor known
    #   +5 if contractor is named  |  +3 if detected but unnamed
    # ------------------------------------------------------------------
    contractor_bonus = 5.0 if contractor_name else (3.0 if contractor_detected else 0.0)

    # ------------------------------------------------------------------
    # Bonus: GlobalData momentum  (0–100 score → up to +5 pts)
    # ------------------------------------------------------------------
    momentum_bonus = (momentum_score / 100.0) * 5.0 if momentum_score is not None else 0.0

    total = (
        past_work + execution_date + project_value +
        project_phase + relationship +
        contractor_bonus + momentum_bonus
    )

    return ScoreBreakdown(
        past_work=      round(past_work,      1),
        execution_date= round(execution_date, 1),
        project_value=  round(project_value,  1),
        project_phase=  round(project_phase,  1),
        relationship=   round(relationship,   1),
        total=          round(total,          1),
    )
