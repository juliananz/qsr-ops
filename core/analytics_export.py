"""
core/analytics_export.py
Outbound sync: push shift CSVs to GitHub, upload expense photos to Google Drive.
"""
import base64
import csv
import io
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

ANALYTICS_REPO = "juliananz/qsr-analytics-pricing"
CORTES_PATH    = "data/raw_data/cortes_validated.csv"
GASTOS_PATH    = "data/raw_data/gastos_validated.csv"
API_BASE       = "https://api.github.com"

CORTES_COLS = ["fecha", "ventas_efectivo", "ventas_tarjeta", "ventas_app",
               "gastos_caja", "ventas_sistema"]
GASTOS_COLS = ["fecha", "descripcion", "categoria", "monto", "elaboro"]


# ─── Internal CSV builders ────────────────────────────────────────────────────

def _build_cortes_csv(shift_id: int, db_conn) -> str:
    row = db_conn.execute(
        """
        SELECT s.shift_date,
               sc.efectivo_neto,
               sc.ventas_tarjeta,
               sc.ventas_app,
               sc.gastos_efectivo,
               sc.ventas_pos
        FROM shift_close sc
        JOIN shifts s ON s.id = sc.shift_id
        WHERE sc.shift_id = ?
        """,
        (shift_id,),
    ).fetchone()

    if row is None:
        raise ValueError(f"No se encontró cierre para turno {shift_id}")

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=CORTES_COLS)
    writer.writeheader()
    writer.writerow({
        "fecha":           str(row["shift_date"])[:10],
        "ventas_efectivo": float(row["efectivo_neto"]),
        "ventas_tarjeta":  float(row["ventas_tarjeta"]),
        "ventas_app":      float(row["ventas_app"]),
        "gastos_caja":     float(row["gastos_efectivo"]),
        "ventas_sistema":  float(row["ventas_pos"]) + float(row["ventas_app"]),
    })
    return out.getvalue()


def _build_gastos_csv(shift_id: int, db_conn) -> str:
    shift = db_conn.execute(
        "SELECT shift_date, cashier_name FROM shifts WHERE id = ?", (shift_id,)
    ).fetchone()
    if shift is None:
        raise ValueError(f"No se encontró turno {shift_id}")

    fecha   = str(shift["shift_date"])[:10]
    elaboro = shift["cashier_name"]

    expenses = db_conn.execute(
        "SELECT category, description, amount FROM expenses"
        " WHERE shift_id = ? AND amount > 0",
        (shift_id,),
    ).fetchall()

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=GASTOS_COLS)
    writer.writeheader()
    for e in expenses:
        writer.writerow({
            "fecha":       fecha,
            "descripcion": e["description"],
            "categoria":   e["category"],
            "monto":       float(e["amount"]),
            "elaboro":     elaboro,
        })
    return out.getvalue()


# ─── CSV merge helper ─────────────────────────────────────────────────────────

def _merge_csv(existing_csv: str, new_csv: str, date_col: str = "fecha") -> str:
    """
    Drop all rows in existing_csv whose date_col matches the date in new_csv,
    then append new_csv rows. Fieldnames follow new_csv (canonical schema).
    """
    new_rows = list(csv.DictReader(io.StringIO(new_csv)))
    if not new_rows:
        return existing_csv

    new_date   = new_rows[0][date_col]
    fieldnames = list(new_rows[0].keys())

    kept: list[dict] = []
    if existing_csv.strip():
        for row in csv.DictReader(io.StringIO(existing_csv)):
            if row.get(date_col) != new_date:
                kept.append({k: row.get(k, "") for k in fieldnames})

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(kept + new_rows)
    return out.getvalue()


# ─── GitHub API helpers ───────────────────────────────────────────────────────

def _gh_get(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _gh_put(url: str, token: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ─── Public: GitHub CSV sync ─────────────────────────────────────────────────

def push_csvs_to_github(shift_id: int, db_conn, token: str) -> dict:
    """
    Build cortes + gastos CSVs from SQLite and push both files to
    juliananz/qsr-analytics-pricing via the GitHub Contents API.

    For each file:
      1. GET current SHA + content
      2. Drop rows matching this shift's date, append new rows
      3. PUT back with updated content + SHA

    Returns {"cortes": "ok"/"error", "gastos": "ok"/"error", "errors": [...]}
    """
    result: dict = {"cortes": "ok", "gastos": "ok", "errors": []}

    cortes_csv = _build_cortes_csv(shift_id, db_conn)
    gastos_csv = _build_gastos_csv(shift_id, db_conn)

    targets = [
        (CORTES_PATH, cortes_csv, "cortes"),
        (GASTOS_PATH, gastos_csv, "gastos"),
    ]

    for path, new_csv, key in targets:
        try:
            url = f"{API_BASE}/repos/{ANALYTICS_REPO}/contents/{path}"

            sha: Optional[str] = None
            existing_content   = ""
            try:
                current          = _gh_get(url, token)
                sha              = current["sha"]
                existing_content = base64.b64decode(
                    current["content"].replace("\n", "")
                ).decode("utf-8")
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    pass  # new file — sha stays None, existing_content stays ""
                else:
                    raise

            merged = (
                _merge_csv(existing_content, new_csv)
                if existing_content.strip()
                else new_csv
            )

            payload: dict = {
                "message": f"ops: sync {path.split('/')[-1]} from qsr-ops",
                "content": base64.b64encode(merged.encode("utf-8")).decode("utf-8"),
            }
            if sha:
                payload["sha"] = sha

            _gh_put(url, token, payload)

        except Exception as exc:
            result[key] = "error"
            result["errors"].append(str(exc))

    return result


# ─── Drive helpers ────────────────────────────────────────────────────────────

_MIME_MAP = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".pdf":  "application/pdf",
    ".heic": "image/heic",
}


def _drive_get_or_create_folder(service, name: str, parent_id: str) -> str:
    """Return Drive folder ID for `name` inside `parent_id`, creating it if absent."""
    q = (
        f"name='{name}' and '{parent_id}' in parents"
        " and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    res   = service.files().list(q=q, fields="files(id)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta   = {"name": name, "mimeType": "application/vnd.google-apps.folder",
               "parents": [parent_id]}
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


# ─── Public: Google Drive photo upload ───────────────────────────────────────

def upload_photos_to_drive(
    shift_id: int,
    db_conn,
    credentials_json_str: str,
    folder_id: str,
) -> dict:
    """
    Upload expense photos for shift_id to Google Drive.

    - Reads photos from disk via expenses.photo_path
    - Creates a YYYY-MM-DD subfolder inside folder_id (reuses if exists)
    - Uploads each photo named: HH-MM_{categoria}_{monto}.jpg
    - Saves Drive webViewLink back to expenses.drive_photo_url

    Returns {"uploaded": N, "errors": [...]}
    """
    import io as _io
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    from core.config import OPS_ROOT

    result: dict = {"uploaded": 0, "errors": []}

    creds = Credentials.from_service_account_info(
        json.loads(credentials_json_str),
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    shift = db_conn.execute(
        "SELECT shift_date FROM shifts WHERE id = ?", (shift_id,)
    ).fetchone()
    if shift is None:
        result["errors"].append(f"No se encontró turno {shift_id}")
        return result

    fecha = str(shift["shift_date"])[:10]

    expenses = db_conn.execute(
        "SELECT id, category, amount, photo_path, recorded_at"
        " FROM expenses WHERE shift_id = ? AND photo_path IS NOT NULL",
        (shift_id,),
    ).fetchall()

    if not expenses:
        return result

    try:
        subfolder_id = _drive_get_or_create_folder(service, fecha, folder_id)
    except Exception as exc:
        result["errors"].append(f"Error creando carpeta {fecha}: {exc}")
        return result

    for exp in expenses:
        try:
            full_path = OPS_ROOT / exp["photo_path"]
            if not full_path.exists():
                result["errors"].append(
                    f"Foto no encontrada en disco: {exp['photo_path']}"
                )
                continue

            # Filename: HH-MM_{categoria}_{monto}.jpg
            recorded_at = str(exp["recorded_at"])
            time_str    = (
                recorded_at[11:16].replace(":", "-")
                if len(recorded_at) >= 16 else "00-00"
            )
            safe_cat  = exp["category"].replace(" ", "_").replace("/", "-")[:20]
            monto_str = str(int(exp["amount"]))
            filename  = f"{time_str}_{safe_cat}_{monto_str}.jpg"

            ext      = Path(exp["photo_path"]).suffix.lower()
            mimetype = _MIME_MAP.get(ext, "application/octet-stream")

            media = MediaIoBaseUpload(
                _io.BytesIO(full_path.read_bytes()),
                mimetype=mimetype,
                resumable=False,
            )
            uploaded = service.files().create(
                body={"name": filename, "parents": [subfolder_id]},
                media_body=media,
                fields="id,webViewLink",
            ).execute()

            db_conn.execute(
                "UPDATE expenses SET drive_photo_url = ? WHERE id = ?",
                (uploaded.get("webViewLink", ""), exp["id"]),
            )
            result["uploaded"] += 1

        except Exception as exc:
            result["errors"].append(f"gasto {exp['id']}: {exc}")

    return result
