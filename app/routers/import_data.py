import io
import re
from datetime import datetime, date as date_type
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import List
import openpyxl
from app.lib.auth import get_current_user
from app.lib.supabase_client import get_admin_client
from app.lib.categorize import auto_categorize, normalize_stage
from app.lib.regions import get_world_region
from app.lib.detect import detect_fid, detect_contractor

router = APIRouter()

COLUMN_MAP = {
    "globaldata_id":     ["project id", "projectid", "id"],
    "name":              ["project name", "projectname", "name"],
    "company_name":      ["company name", "company", "client", "owner"],
    "country":           ["country"],
    "status":            ["project status", "status"],
    "project_value_usd": ["project value (usd)", "project value", "value (usd)", "value"],
    "execution_date":    ["execution date", "start date", "completion date"],
    "description":       ["project description", "description", "summary"],
    "project_url":       ["project url", "url", "link", "globaldata url"],
    "sector":            ["primary sector", "sector"],
    "momentum_score":    ["momentum score", "momentum"],
    "project_type":      ["project type", "type"],
    "city":              ["city"],
    "region":            ["region", "state", "province"],
}

def find_col(headers: list[str], keys: list[str]) -> int | None:
    for i, h in enumerate(headers):
        clean = re.sub(r'\s+', ' ', str(h).lower().strip())
        for key in keys:
            if key == clean or key in clean:
                return i
    return None

def parse_value(raw) -> int | None:
    if raw is None:
        return None
    try:
        return int(float(str(raw).replace(",", "").replace("$", "").strip()))
    except Exception:
        return None

def parse_date(raw) -> str | None:
    """Parse a cell value to ISO date string, handling Excel date objects."""
    if raw is None:
        return None
    # Excel gives us datetime/date objects directly
    if isinstance(raw, datetime):
        return raw.date().isoformat()
    if isinstance(raw, date_type):
        return raw.isoformat()
    s = str(raw).strip()
    if not s or s.lower() in ["none", "nan", ""]:
        return None
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%b %Y", "%B %Y"]:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return s  # return as-is; scoring will handle unknown formats gracefully

def safe_str(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ["none", "nan"] else None

def parse_contacts(row: list, headers: list[str]) -> list[dict]:
    contacts = []
    for i in range(1, 7):
        name_idx  = find_col(headers, [f"key person name {i}", f"key_person_name_{i}"])
        title_idx = find_col(headers, [f"key contact {i}", f"key_contact_{i}", f"contact title {i}"])
        email_idx = find_col(headers, [f"email {i}", f"contact email {i}", f"key email {i}"])
        lin_idx   = find_col(headers, [f"linkedin {i}", f"linkedin url {i}"])

        name = row[name_idx] if name_idx is not None and name_idx < len(row) else None
        name = safe_str(name)
        if not name:
            continue
        contacts.append({
            "name":         name,
            "title":        safe_str(row[title_idx]) if title_idx is not None and title_idx < len(row) else "",
            "email":        safe_str(row[email_idx]) if email_idx is not None and email_idx < len(row) else None,
            "linkedin_url": safe_str(row[lin_idx])  if lin_idx is not None and lin_idx < len(row) else None,
        })
    return contacts

def chunk(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

@router.post("/import")
async def import_projects(
    files: List[UploadFile] = File(...),
    user=Depends(get_current_user),
):
    supabase = get_admin_client()
    total_imported = 0
    total_subs = 0
    errors = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".xlsx"):
            errors.append(f"{file.filename}: not an xlsx file")
            continue

        content = await file.read()
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
            ws = wb.active
        except Exception as e:
            errors.append(f"{file.filename}: failed to open — {e}")
            continue

        # Find header row (search rows 1-12)
        headers = []
        header_row_idx = None
        for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=12, values_only=True)):
            row_vals = [str(c).lower().strip() if c is not None else "" for c in row]
            if any("project" in v or "name" in v or "country" in v for v in row_vals):
                headers = [str(c).lower().strip() if c is not None else "" for c in row]
                header_row_idx = row_idx + 1
                break

        if not headers or header_row_idx is None:
            errors.append(f"{file.filename}: could not find header row")
            continue

        col_map = {field: find_col(headers, keys) for field, keys in COLUMN_MAP.items()}

        projects_to_upsert = []
        contacts_to_insert = []

        for row in ws.iter_rows(min_row=header_row_idx + 2, values_only=True):
            if all(c is None for c in row):
                continue

            def get(field):
                idx = col_map.get(field)
                if idx is None or idx >= len(row):
                    return None
                return safe_str(row[idx])

            def get_raw(field):
                idx = col_map.get(field)
                if idx is None or idx >= len(row):
                    return None
                return row[idx]

            # Skip sub-projects
            ptype = get("project_type") or ""
            if "sub" in ptype.lower():
                total_subs += 1
                continue

            raw_id  = get("globaldata_id")
            name    = get("name") or "Unnamed project"
            desc    = get("description")
            country = get("country")
            status  = get("status") or ""
            sector  = get("sector")

            fid = detect_fid(desc)
            contractor_detected, contractor_name = detect_contractor(desc)

            row_list = list(row)
            project_contacts = parse_contacts(row_list, headers)

            project = {
                "globaldata_id":       raw_id or f"gd-imp-{total_imported}",
                "user_id":             user.id,
                "name":                name,
                "company_name":        get("company_name"),
                "country":             country,
                "region":              " ".join(filter(None, [get("city"), get("region")])) or None,
                "world_region":        get_world_region(country),
                "sector":              auto_categorize(name, desc, sector),
                "stage_normalized":    normalize_stage(status),
                "status":              status,
                "project_value_usd":   parse_value(get_raw("project_value_usd")),
                "execution_date":      parse_date(get_raw("execution_date")),
                "description":         desc,
                "project_url":         get("project_url"),
                "momentum_score":      parse_value(get_raw("momentum_score")),
                "fid_detected":        fid,
                "contractor_detected": contractor_detected,
                "contractor_name":     contractor_name,
                "key_contacts":        project_contacts,
            }
            projects_to_upsert.append(project)

            for c in project_contacts:
                contacts_to_insert.append({**c, "globaldata_id": project["globaldata_id"]})

        if projects_to_upsert:
            # Upsert in chunks to avoid payload limits
            for batch in chunk(projects_to_upsert, 200):
                supabase.table("projects").upsert(
                    batch, on_conflict="globaldata_id,user_id"
                ).execute()

            if contacts_to_insert:
                gd_ids = [p["globaldata_id"] for p in projects_to_upsert]
                proj_rows = supabase.table("projects").select("id, globaldata_id").in_(
                    "globaldata_id", gd_ids
                ).eq("user_id", user.id).execute()
                gd_to_id = {r["globaldata_id"]: r["id"] for r in proj_rows.data or []}

                final_contacts = []
                seen_gd_ids = set()
                for c in contacts_to_insert:
                    gd_id = c.pop("globaldata_id")
                    pid = gd_to_id.get(gd_id)
                    if pid:
                        final_contacts.append({
                            "project_id":   pid,
                            "name":         c["name"],
                            "title":        c.get("title") or "",
                            "email":        c.get("email"),
                            "linkedin_url": c.get("linkedin_url"),
                            "source":       "globaldata",
                            "role_type":    "other",
                        })
                        seen_gd_ids.add(gd_id)

                if final_contacts:
                    project_ids = list(gd_to_id.values())
                    # Delete old globaldata contacts and re-insert
                    for id_batch in chunk(project_ids, 200):
                        supabase.table("contacts").delete().in_(
                            "project_id", id_batch
                        ).eq("source", "globaldata").execute()
                    for batch in chunk(final_contacts, 200):
                        supabase.table("contacts").insert(batch).execute()

        total_imported += len(projects_to_upsert)

    return {
        "ok": True,
        "imported": total_imported,
        "sub_projects_removed": total_subs,
        "errors": errors,
    }
