"""
schemas.py — every Pydantic model used by the TWD Sales Assistant API.

This is the single file to open if you want to understand what data
flows in and out of each endpoint.

Layout:
  1. Shared building blocks  (reused across multiple models)
  2. Request  models         (what each endpoint accepts as input)
  3. Response models         (what each endpoint returns as JSON)

Each response model is named after its endpoint so it is easy to find:
  POST /api/login          → LoginResponse
  POST /api/import         → ImportResponse
  POST /api/sync           → SyncResponse
  GET  /api/projects       → ProjectsResponse
  PATCH /api/contacts/{id} → OkResponse
  GET  /api/favorites      → FavoritesResponse
  POST /api/favorites      → FavoriteToggleResponse
  POST /api/summarize      → SummarizeResponse
  POST /api/research       → ResearchResponse
  POST /api/meeting-prep   → MeetingPrepResponse
  DELETE /api/clear        → ClearResponse
"""

from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

class _Base(BaseModel):
    """
    Base config for all models.
    extra='ignore' means unexpected fields from Supabase are silently dropped
    rather than raising a validation error.
    """
    model_config = ConfigDict(extra="ignore")


class UserInfo(_Base):
    """Minimal user record returned after a successful login."""
    id:    str
    email: str


class ScoreBreakdown(_Base):
    """
    How a project's total priority score is broken down across dimensions.
    All values are points — see scoring.py for the full logic.
    """
    past_work:      float  # max 25 — prior work with this client
    execution_date: float  # max 25 — how soon the project needs to start
    project_value:  float  # max 20 — contract size (log scale)
    project_phase:  float  # max 20 — tender/FEED stages score highest
    relationship:   float  # max 10 — named contacts + deal history
    total:          float  # sum of above + bonuses (contractor, momentum)


class Contact(_Base):
    """A key contact associated with a project."""
    id:                    str
    project_id:            str
    name:                  str
    title:                 Optional[str]  = None
    email:                 Optional[str]  = None
    linkedin_url:          Optional[str]  = None
    source:                Optional[str]  = None  # "globaldata" or "manual"
    role_type:             Optional[str]  = None
    is_contractor_contact: Optional[bool] = None
    is_main_contact:       Optional[bool] = None  # only one per project
    outreach_sentiment:    Optional[str]  = None  # e.g. "positive", "neutral"
    outreach_notes:        Optional[str]  = None
    outreach_date:         Optional[str]  = None  # ISO date string


class ProjectDetail(_Base):
    """Full project record as stored in the database."""
    id:                  str
    name:                str
    company_name:        Optional[str]  = None
    sector:              Optional[str]  = None  # category ID from categories.py
    country:             Optional[str]  = None
    region:              Optional[str]  = None  # city/state within country
    world_region:        Optional[str]  = None  # e.g. "Middle East", "Europe"
    stage_normalized:    Optional[str]  = None  # normalised stage from categorize.py
    project_value_usd:   Optional[int]  = None
    execution_date:      Optional[str]  = None  # ISO date string
    description:         Optional[str]  = None
    status:              Optional[str]  = None  # raw status from GlobalData
    project_url:         Optional[str]  = None
    key_contacts:        Optional[list] = None  # raw JSON from GlobalData
    globaldata_id:       Optional[str]  = None
    fid_detected:        Optional[bool] = None  # Final Investment Decision signal
    contractor_detected: Optional[bool] = None  # contractor award signal
    contractor_name:     Optional[str]  = None  # named contractor if found


class ScoredProject(_Base):
    """
    A project with its current week's priority score and rank.
    This is the main item returned by GET /api/projects.
    """
    id:                  str
    rank:                int                      # 1 = highest priority this week
    score:               float
    breakdown:           ScoreBreakdown
    project_id:          str
    projects:            Optional[ProjectDetail] = None
    contacts:            list[Contact]            = []
    previous_rank:       Optional[int]            = None  # rank last week (None if new)
    previous_breakdown:  Optional[ScoreBreakdown] = None
    is_favorite:         bool                     = False


class FavoriteProject(_Base):
    """Minimal project snapshot stored inside a favourite record."""
    id:                Optional[str] = None
    name:              Optional[str] = None
    company_name:      Optional[str] = None
    country:           Optional[str] = None
    status:            Optional[str] = None
    project_value_usd: Optional[int] = None
    execution_date:    Optional[str] = None
    sector:            Optional[str] = None
    world_region:      Optional[str] = None
    stage_normalized:  Optional[str] = None
    project_url:       Optional[str] = None
    globaldata_id:     Optional[str] = None


class FavoriteItem(_Base):
    """A favourited project as returned by GET /api/favorites."""
    id:           str
    globaldata_id: str
    project_name: Optional[str]           = None
    company_name: Optional[str]           = None
    created_at:   Optional[str]           = None
    project_id:   Optional[str]           = None
    projects:     Optional[FavoriteProject] = None


class DeletedCounts(_Base):
    """Summary of how many records were (or would be) deleted by /clear."""
    projects:           int
    scores:             int
    snapshots:          int
    favorites:          int
    contacts_and_cache: str  # always "all linked to above projects"


class OkResponse(_Base):
    """Generic success response used when there is nothing else to return."""
    ok: bool


# ---------------------------------------------------------------------------
# Request models  (what each endpoint accepts as input)
# ---------------------------------------------------------------------------

class LoginRequest(_Base):
    """Credentials for POST /api/login."""
    email:    str
    password: str


class SummarizeRequest(_Base):
    """Input for POST /api/summarize."""
    description: str = Field(
        ...,
        max_length=8_000,
        description="Project description to summarise (max 8 000 characters).",
    )


class ResearchRequest(_Base):
    """Input for POST /api/research."""
    project_id: str = Field(..., description="Internal UUID of the project to research.")


class ContactUpdate(_Base):
    """
    Fields that can be updated on a contact via PATCH /api/contacts/{id}.
    Only the fields you include in the request body will be changed.
    """
    is_main_contact:       Optional[bool] = Field(None, description="Set to true to mark as the primary contact (clears the flag on all others in the same project).")
    is_contractor_contact: Optional[bool] = Field(None, description="Flag this person as a contractor-side contact.")
    outreach_sentiment:    Optional[str]  = Field(None, description="e.g. 'positive', 'neutral', 'negative'")
    outreach_notes:        Optional[str]  = Field(None, description="Free-text notes on the outreach.")
    outreach_date:         Optional[str]  = Field(None, description="ISO date of last outreach (YYYY-MM-DD).")


class FavoriteToggle(_Base):
    """Input for POST /api/favorites — toggles the favourite state."""
    project_id:    Optional[str] = None
    globaldata_id: str           = Field(..., description="GlobalData project ID used as the stable toggle key.")
    project_name:  Optional[str] = None
    company_name:  Optional[str] = None


# ---------------------------------------------------------------------------
# Response models  (what each endpoint returns as JSON)
# ---------------------------------------------------------------------------

class LoginResponse(_Base):
    """Returned by POST /api/login on success."""
    access_token: str = Field(..., description="JWT Bearer token — include in Authorization header for all other requests.")
    user:         UserInfo


class ImportResponse(_Base):
    """Returned by POST /api/import."""
    ok:                   bool
    imported:             int       = Field(..., description="Number of projects successfully imported.")
    sub_projects_removed: int       = Field(..., description="Number of sub-projects skipped.")
    errors:               list[str] = Field(..., description="Per-file error messages, if any.")


class SyncResponse(_Base):
    """Returned by POST /api/sync."""
    ok:         bool
    synced:     int = Field(..., description="Number of projects scored and ranked.")
    week_start: str = Field(..., description="ISO date of the Monday this sync covers.")


class ProjectsResponse(_Base):
    """Returned by GET /api/projects."""
    scores:     list[ScoredProject]
    week_start: str            = Field(..., description="ISO date of the current week's Monday.")
    last_sync:  Optional[str]  = Field(None, description="Timestamp of the most recent sync run.")


class FavoritesResponse(_Base):
    """Returned by GET /api/favorites."""
    favorites: list[FavoriteItem]


class FavoriteToggleResponse(_Base):
    """Returned by POST /api/favorites."""
    ok:          bool
    is_favorite: bool = Field(..., description="True if the project is now favourited, False if it was removed.")


class SummarizeResponse(_Base):
    """Returned by POST /api/summarize."""
    summary: str = Field(..., description="2-3 sentence AI summary of the project description.")


class ResearchResponse(_Base):
    """Returned by POST /api/research."""
    research_card: str           = Field(..., description="Structured intelligence report generated by Claude.")
    cached:        bool          = Field(..., description="True if this result came from the cache.")
    searched_at:   Optional[str] = Field(None, description="Timestamp of when the research was last run.")


class MeetingPrepResponse(_Base):
    """Returned by POST /api/meeting-prep/{project_id}."""
    prep_card: str = Field(..., description="BD meeting preparation card generated by Claude.")


class ClearResponse(_Base):
    """
    Returned by DELETE /api/clear.

    Without ?confirm=true  → dry_run=True, would_delete is filled, ok is None.
    With    ?confirm=true  → ok=True, deleted is filled, dry_run is None.
    """
    dry_run:      Optional[bool]          = Field(None, description="True when this was a preview only — nothing was deleted.")
    message:      Optional[str]           = Field(None, description="Instructions shown during a dry run.")
    would_delete: Optional[DeletedCounts] = Field(None, description="What would be deleted (dry run only).")
    ok:           Optional[bool]          = Field(None, description="True when deletion was confirmed and completed.")
    deleted:      Optional[DeletedCounts] = Field(None, description="What was actually deleted (confirmed run only).")
