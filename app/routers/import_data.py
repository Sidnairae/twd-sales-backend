import io
import re
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

def parse_contacts(row: list, headers: list[str]) -> list[dict]:
    contacts = []
    for i in range(1, 7):
        name_idx  = find_col(headers, [f"key person name {i}", f"key_person_name_{i}"])
        title_idx = find_col(headers, [f"key contact {i}", f"key_contact_{i}", f"contact title {i}"])
        email_idx = find_col(headers, [f"email {i}", f"contact email {i}", f"key email {i}"])
        lin_idx   = find_col(headers, [f"linkedin {i}", f"linkedin url {i}"])

        name = row[name_idx] if name_idx is not None and name_idx < len(row) else None
        if not name or str(name).strip().lower() in ["", "nan", "none"]:
            continue
        contacts.append({
            "name":        str(name).strip(),
            "title":       str(row[title_idx]).strip() if title_idx is not None and title_idx < len(row) else "",
            "email":       str(row[email_idx]).strip() if email_idx is not None and email_idx < len(row) else None,
            "linkedin_url": str(row[lin_idx]).strip() if lin_idx is not None and lin_idx < len(row) else None,
        })
    return contacts

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
        if not file.filename or not file.filename.endswith(".xlsx"):
            errors.append(f"{file.filename}: not an xlsx file")
            continue

        content = await file.read()
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
            ws = wb.active
        except Exception as e:
            errors.append(f"{file.filename}: {e}")
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
        type_idx = col_map.get("project_type")

        projects_to_upsert = []
        contacts_to_insert = []

        for row in ws.iter_rows(min_row=header_row_idx + 2, values_only=True):
            if all(c is None for c in row):
                continue

            def get(field):
                idx = col_map.get(field)
                if idx is None or idx >= len(row):
                    return None
                val = row[idx]
                if val is None:
                    return None
                return str(val).strip() or None

            # Skip sub-projects
            ptype = get("project_type") or ""
            if "sub" in ptype.lower():
                total_subs += 1
                continue

            raw_id   = get("globaldata_id")
            name     = get("name") or "Unnamed project"
            desc     = get("description")
            country  = get("country")
            status   = get("status") or ""
            sector   = get("sector")

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
                "project_value_usd":   parse_value(get("project_value_usd")),
                "execution_date":      get("execution_date"),
                "description":         desc,
                "project_url":         get("project_url"),
                "momentum_score":      parse_value(get("momentum_score")),
                "fid_detected":        fid,
                "contractor_detected": contractor_detected,
                "contractor_name":     contractor_name,
                "key_contacts":        project_contacts,
            }
            projects_to_upsert.append(project)

            for c in project_contacts:
                contacts_to_insert.append({**c, "globaldata_id": project["globaldata_id"]})

        # Upsert projects
        if projects_to_upsert:
            supabase.table("projects").upsert(
                projects_to_upsert,
                on_conflict="globaldata_id,user_id",
            ).execute()

            # Upsert contacts (fetch project ids first)
            if contacts_to_insert:
                gd_ids = [p["globaldata_id"] for p in projects_to_upsert]
                proj_rows = supabase.table("projects").select("id, globaldata_id").in_(
                    "globaldata_id", gd_ids
                ).eq("user_id", user.id).execute()
                gd_to_id = {r["globaldata_id"]: r["id"] for r in proj_rows.data or []}

                final_contacts = []
                for c in contacts_to_insert:
                    pid = gd_to_id.get(c.pop("globaldata_id"))
                    if pid:
                        final_contacts.append({
                            "project_id":  pid,
                            "name":        c["name"],
                            "title":       c.get("title") or "",
                            "email":       c.get("email"),
                            "linkedin_url": c.get("linkedin_url"),
                            "source":      "globaldata",
                            "role_type":   "other",
                        })

                if final_contacts:
                    # Delete old globaldata contacts and re-insert
                    project_ids = list(gd_to_id.values())
                    supabase.table("contacts").delete().in_(
                        "project_id", project_ids
                    ).eq("source", "globaldata").execute()
                    supabase.table("contacts").insert(final_contacts).execute()

        total_imported += len(projects_to_upsert)

    return {
        "ok": True,
        "imported": total_imported,
        "sub_projects_removed": total_subs,
        "errors": errors,
    }
