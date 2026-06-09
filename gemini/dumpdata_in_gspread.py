from __future__ import annotations

import csv
import logging
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

import gspread
from gspread.exceptions import APIError, WorksheetNotFound
from gspread.utils import rowcol_to_a1
from gspread_formatting import (
    CellFormat, Color, TextFormat,
    format_cell_range, batch_updater
)
from google.oauth2.service_account import Credentials

# =========================
# CONFIGURATION
# =========================

SERVICE_ACCOUNT_FILE = Path(
    r"/Users/tshah/Documents/PVA Mappings/service_account.json"
)
SPREADSHEET_ID = "1UkVoXcVWArr1s3gR73hU1DDL79XAV_ULWrhsEXS6UR0"
INPUT_DIR = Path("/Users/tshah/Documents/PVA Mappings/gemini/colab_csv_2_improvement")

# Google auth scopes for Sheets + Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Upload behavior
VALUE_INPUT_OPTION = "RAW"
CLEAR_EXISTING_VALUES = True
FREEZE_HEADER_ROW = True

# Keep chunks reasonably small so API requests stay stable
BATCH_ROWS = 2000

# Google Sheets cell content limit is 50,000 characters.
# Keep a small buffer below that limit to avoid API failures.
MAX_CELL_CHARS = 49000

# Conservative safety limit per worksheet.
# If a CSV exceeds this, it will be split into multiple tabs.
MAX_ROWS_PER_WORKSHEET = 40000

# Optional: cap columns if you want to keep tabs manageable.
# If a CSV is wider than this, the script still uploads it; this is just used for sizing.
MIN_WORKSHEET_ROWS = 1000
MIN_WORKSHEET_COLS = 20

# Workbook presentation
CREATE_INDEX_SHEET = True
INDEX_SHEET_TITLE = "00_Index"

TAB_STYLE_MAP = {
    "Tab Inventory": {"tab_color": (0.10, 0.47, 0.78), "header_color": (0.10, 0.47, 0.78)},
    "Field Inventory": {"tab_color": (0.16, 0.63, 0.41), "header_color": (0.16, 0.63, 0.41)},
    "Field Mapping": {"tab_color": (0.55, 0.35, 0.75), "header_color": (0.55, 0.35, 0.75)},
    "Dropdown Values": {"tab_color": (0.92, 0.67, 0.11), "header_color": (0.92, 0.67, 0.11)},
    "Calculated Fields": {"tab_color": (0.86, 0.34, 0.24), "header_color": (0.86, 0.34, 0.24)},
    "Tab Relationships": {"tab_color": (0.15, 0.62, 0.74), "header_color": (0.15, 0.62, 0.74)},
    "Named Ranges": {"tab_color": (0.58, 0.47, 0.20), "header_color": (0.58, 0.47, 0.20)},
    "Notes Findings": {"tab_color": (0.45, 0.45, 0.45), "header_color": (0.45, 0.45, 0.45)},
    "WorkbookGraph": {"tab_color": (0.30, 0.30, 0.30), "header_color": (0.30, 0.30, 0.30)},
}

DEFAULT_STYLE = {"tab_color": (0.25, 0.58, 0.53), "header_color": (0.13, 0.59, 0.95)}

# Retry policy
MAX_RETRIES = 6
INITIAL_BACKOFF_SECONDS = 1.5
BACKOFF_MULTIPLIER = 2.0
MAX_BACKOFF_SECONDS = 30.0

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# =========================
# HELPERS
# =========================

def sanitize_sheet_title(title: str, max_len: int = 100) -> str:
    """
    Google Sheets tab names cannot contain: []:*?/\\
    """
    cleaned = re.sub(r"[\[\]\:\*\?\/\\]", "_", title).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = "Sheet"
    return cleaned[:max_len]


def unique_title(existing_titles: set[str], base_title: str) -> str:
    """
    Returns a unique sheet title within the 100-char limit.
    """
    base_title = sanitize_sheet_title(base_title)
    if base_title not in existing_titles:
        existing_titles.add(base_title)
        return base_title

    i = 2
    while True:
        suffix = f"__part_{i}"
        truncated_base = base_title[: max(1, 100 - len(suffix))]
        candidate = f"{truncated_base}{suffix}"
        if candidate not in existing_titles:
            existing_titles.add(candidate)
            return candidate
        i += 1


def a1_range(start_row: int, end_row: int, start_col: int = 1, end_col: int = 4) -> str:
    """
    Build an A1-style rectangular range string.
    """
    return f"{rowcol_to_a1(start_row, start_col)}:{rowcol_to_a1(end_row, end_col)}"


def read_csv_file(filepath: Path) -> List[List[str]]:
    """
    Reads CSV preserving row order. UTF-8 BOM safe.
    """
    with filepath.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def normalize_matrix(matrix: Sequence[Sequence[str]], sheet_title: str = "") -> List[List[str]]:
    """
    Pads all rows to the same width for cleaner sheet updates.
    """
    if not matrix:
        return []

    width = max(len(row) for row in matrix)
    normalized: List[List[str]] = []
    for row_idx, row in enumerate(matrix, start=1):
        normalized_row: List[str] = []
        for col_idx, cell in enumerate(row, start=1):
            text = str(cell) if cell is not None else ""
            if len(text) > MAX_CELL_CHARS:
                cell_ref = rowcol_to_a1(row_idx, col_idx)
                logging.warning(
                    f"Truncating oversized cell in {sheet_title or 'sheet'}!{cell_ref} "
                    f"from {len(text)} to {MAX_CELL_CHARS} characters."
                )
                text = text[:MAX_CELL_CHARS]
            normalized_row.append(text)
        normalized.append(normalized_row + [""] * (width - len(row)))
    return normalized


def chunk_list(items: Sequence[List[str]], size: int) -> Iterable[List[List[str]]]:
    for i in range(0, len(items), size):
        yield list(items[i:i + size])


def is_transient_api_error(exc: Exception) -> bool:
    """
    Best-effort detection for retryable API errors.
    """
    if not isinstance(exc, APIError):
        return False

    status_code = None
    response = getattr(exc, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)

    if status_code in {429, 500, 502, 503, 504}:
        return True

    msg = str(exc).lower()
    return any(
        phrase in msg
        for phrase in [
            "rate limit",
            "internal server error",
            "backend error",
            "service unavailable",
            "too many requests",
            "gateway timeout"
        ]
    )


def with_retry(func, *args, **kwargs):
    """
    Retries transient Google API failures with exponential backoff.
    """
    backoff = INITIAL_BACKOFF_SECONDS
    last_exc = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if not is_transient_api_error(exc) or attempt == MAX_RETRIES:
                raise
            sleep_for = min(backoff, MAX_BACKOFF_SECONDS) + random.uniform(0, 0.5)
            logging.warning(
                f"Transient API error on attempt {attempt}/{MAX_RETRIES}: {exc}. "
                f"Retrying in {sleep_for:.1f}s..."
            )
            time.sleep(sleep_for)
            backoff *= BACKOFF_MULTIPLIER

    raise last_exc  # pragma: no cover


def split_csv_for_tabs(data: List[List[str]], max_rows_per_worksheet: int) -> List[List[List[str]]]:
    """
    Splits a CSV into multiple tab-sized chunks while repeating the header row.
    """
    if not data:
        return []

    if len(data) <= max_rows_per_worksheet:
        return [data]

    header = data[0]
    body = data[1:]
    body_chunk_size = max_rows_per_worksheet - 1

    parts: List[List[List[str]]] = []
    for body_chunk in chunk_list(body, body_chunk_size):
        parts.append([header] + body_chunk)

    return parts


def get_style_for_title(title: str):
    """
    Returns a tab/header color palette for a worksheet title.
    """
    if title == INDEX_SHEET_TITLE:
        return {"tab_color": (0.09, 0.09, 0.09), "header_color": (0.09, 0.09, 0.09)}

    for prefix, style in TAB_STYLE_MAP.items():
        if title.startswith(prefix):
            return style
    return DEFAULT_STYLE


def get_or_create_worksheet(spreadsheet: gspread.Spreadsheet, title: str, rows: int, cols: int):
    """
    Gets an existing worksheet or creates it with enough size.
    """
    try:
        ws = spreadsheet.worksheet(title)
        current_rows = getattr(ws, "row_count", 0)
        current_cols = getattr(ws, "col_count", 0)
        if current_rows < rows or current_cols < cols:
            with_retry(ws.resize, rows=max(current_rows, rows), cols=max(current_cols, cols))
        return ws
    except WorksheetNotFound:
        return with_retry(
            spreadsheet.add_worksheet,
            title=title,
            rows=str(rows),
            cols=str(cols)
        )


def delete_existing_part_tabs(spreadsheet: gspread.Spreadsheet, base_title: str) -> None:
    """
    Removes old leftover tabs like 'Field Inventory__part_2' before re-uploading.
    """
    pattern = re.compile(rf"^{re.escape(base_title)}__part_\d+$")
    worksheets = spreadsheet.worksheets()

    for ws in worksheets:
        if pattern.match(ws.title):
            logging.info(f"Deleting stale tab: {ws.title}")
            with_retry(spreadsheet.del_worksheet, ws)


def ensure_index_sheet(spreadsheet: gspread.Spreadsheet) -> None:
    """
    Create or refresh a landing page with links and a color legend.
    """
    try:
        ws = spreadsheet.worksheet(INDEX_SHEET_TITLE)
    except WorksheetNotFound:
        ws = with_retry(
            spreadsheet.add_worksheet,
            title=INDEX_SHEET_TITLE,
            rows="100",
            cols="8"
        )

    rows = [
        ["Workbook Workbench Mappings"],
        ["Last refreshed", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        [""],
        ["Tab", "Purpose", "Open", "Color"],
        ["Tab Inventory", "Workbook metadata and sheet summary", "", "Blue"],
        ["Field Inventory", "Extracted field catalog", "", "Green"],
        ["Field Mapping", "Cross-sheet source mapping", "", "Purple"],
        ["Dropdown Values", "Resolved dropdown options", "", "Amber"],
        ["Calculated Fields", "Formula breakdown", "", "Red"],
        ["Tab Relationships", "Sheet dependency graph", "", "Cyan"],
        ["Named Ranges", "Named range catalog and usage", "", "Gold"],
        ["Notes Findings", "Open questions and findings", "", "Gray"],
        ["WorkbookGraph", "Workbook dependency graph export", "", "Slate"],
    ]

    with_retry(ws.clear)
    with_retry(ws.resize, rows=100, cols=8)
    last_row = len(rows)
    with_retry(
        ws.update,
        range_name=a1_range(1, last_row, 1, 4),
        values=normalize_matrix(rows, sheet_title=INDEX_SHEET_TITLE),
        value_input_option="USER_ENTERED"
    )

    try:
        with batch_updater(spreadsheet) as b:
            title_format = CellFormat(
                backgroundColor=Color(0.09, 0.09, 0.09),
                textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
                horizontalAlignment="CENTER"
            )
            header_format = CellFormat(
                backgroundColor=Color(0.18, 0.18, 0.18),
                textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1))
            )
            b.format_cell_range(ws, a1_range(1, 1, 1, 4), title_format)
            b.format_cell_range(ws, a1_range(4, 4, 1, 4), header_format)

        with_retry(ws.freeze, rows=4)
        with_retry(ws.columns_auto_resize, 0, 4)
        with_retry(
            ws.spreadsheet.batch_update,
            {
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": ws.id,
                                "tabColor": {"red": 0.09, "green": 0.09, "blue": 0.09},
                                "index": 0,
                            },
                            "fields": "tabColor,index",
                        }
                    }
                ]
            }
        )
    except Exception as exc:
        logging.warning(f"Could not fully format index sheet: {exc}")


def refresh_index_sheet(spreadsheet: gspread.Spreadsheet) -> None:
    """
    Rebuild the index sheet with actual jump links to the mapped tabs.
    """
    try:
        ws = spreadsheet.worksheet(INDEX_SHEET_TITLE)
    except WorksheetNotFound:
        return

    rows = [
        ["Workbook Workbench Mappings"],
        ["Last refreshed", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        [""],
        ["Tab", "Purpose", "Open", "Color"],
    ]

    legend = [
        ("Tab Inventory", "Workbook metadata and sheet summary", "Blue"),
        ("Field Inventory", "Extracted field catalog", "Green"),
        ("Field Mapping", "Cross-sheet source mapping", "Purple"),
        ("Dropdown Values", "Resolved dropdown options", "Amber"),
        ("Calculated Fields", "Formula breakdown", "Red"),
        ("Tab Relationships", "Sheet dependency graph", "Cyan"),
        ("Named Ranges", "Named range catalog and usage", "Gold"),
        ("Notes Findings", "Open questions and findings", "Gray"),
        ("WorkbookGraph", "Workbook dependency graph export", "Slate"),
    ]

    gid_by_title = {}
    for worksheet in spreadsheet.worksheets():
        gid_by_title[worksheet.title] = worksheet.id

    for title, purpose, color_name in legend:
        gid = gid_by_title.get(title)
        open_formula = f'=HYPERLINK("#gid={gid}", "Open")' if gid is not None else "Missing"
        rows.append([title, purpose, open_formula, color_name])

    with_retry(ws.clear)
    with_retry(ws.resize, rows=100, cols=8)
    last_row = len(rows)
    with_retry(
        ws.update,
        range_name=a1_range(1, last_row, 1, 4),
        values=normalize_matrix(rows, sheet_title=INDEX_SHEET_TITLE),
        value_input_option="USER_ENTERED"
    )

    try:
        with batch_updater(spreadsheet) as b:
            title_format = CellFormat(
                backgroundColor=Color(0.09, 0.09, 0.09),
                textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
                horizontalAlignment="CENTER"
            )
            header_format = CellFormat(
                backgroundColor=Color(0.18, 0.18, 0.18),
                textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1))
            )
            link_format = CellFormat(
                textFormat=TextFormat(bold=True, foregroundColor=Color(0.13, 0.59, 0.95))
            )
            b.format_cell_range(ws, a1_range(1, 1, 1, 4), title_format)
            b.format_cell_range(ws, a1_range(4, 4, 1, 4), header_format)
            if last_row >= 5:
                b.format_cell_range(ws, a1_range(5, last_row, 3, 3), link_format)
        with_retry(ws.freeze, rows=4)
        with_retry(ws.columns_auto_resize, 0, 4)
        with_retry(
            ws.spreadsheet.batch_update,
            {
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": ws.id,
                                "index": 0,
                            },
                            "fields": "index",
                        }
                    }
                ]
            }
        )
    except Exception as exc:
        logging.warning(f"Could not refresh index sheet: {exc}")


def clear_and_upload_matrix(
    worksheet,
    data: List[List[str]],
    sheet_title: str
) -> None:
    """
    Clears a worksheet and uploads the matrix in chunks.
    """
    if not data:
        logging.info(f"Skipping empty tab: {sheet_title}")
        return

    data = normalize_matrix(data, sheet_title=sheet_title)
    rows = len(data)
    cols = max(len(r) for r in data) if data else 1

    rows_to_allocate = max(rows + 50, MIN_WORKSHEET_ROWS)
    cols_to_allocate = max(cols + 5, MIN_WORKSHEET_COLS)

    if CLEAR_EXISTING_VALUES:
        with_retry(worksheet.clear)

    with_retry(worksheet.resize, rows=rows_to_allocate, cols=cols_to_allocate)

    for start_index in range(0, rows, BATCH_ROWS):
        chunk = data[start_index:start_index + BATCH_ROWS]
        start_row = start_index + 1
        end_row = start_row + len(chunk) - 1
        end_col = max(len(r) for r in chunk) if chunk else 1

        start_a1 = rowcol_to_a1(start_row, 1)
        end_a1 = rowcol_to_a1(end_row, end_col)
        range_name = f"{start_a1}:{end_a1}"

        logging.info(
            f"Uploading {sheet_title}: rows {start_row}-{end_row} "
            f"({len(chunk)} rows)"
        )

        with_retry(
            worksheet.update,
            range_name=range_name,
            values=chunk,
            value_input_option=VALUE_INPUT_OPTION
        )

    if FREEZE_HEADER_ROW:
        try:
            with_retry(worksheet.freeze, rows=1)
        except Exception as exc:
            logging.warning(f"Could not freeze header row for {sheet_title}: {exc}")

    style = get_style_for_title(sheet_title)

    # ── PROFESSIONAL FORMATTING ──────────────────────────────────────────
    try:
        header_format = CellFormat(
            backgroundColor=Color(*style["header_color"]),
            textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
            horizontalAlignment="CENTER"
        )

        with batch_updater(worksheet.spreadsheet) as b:
            last_col_ltr = rowcol_to_a1(1, cols).split('1')[0]
            header_range = f"A1:{last_col_ltr}1"
            b.format_cell_range(worksheet, header_range, header_format)

        try:
            with_retry(
                worksheet.spreadsheet.batch_update,
                {
                    "requests": [
                        {
                            "setBasicFilter": {
                                "filter": {
                                    "range": {
                                        "sheetId": worksheet.id,
                                        "startRowIndex": 0,
                                        "endRowIndex": rows,
                                        "startColumnIndex": 0,
                                        "endColumnIndex": cols,
                                    }
                                }
                            }
                        }
                    ]
                }
            )
        except Exception as exc:
            logging.warning(f"Could not set filter for {sheet_title}: {exc}")

        with_retry(worksheet.columns_auto_resize, 0, cols)

        with_retry(
            worksheet.spreadsheet.batch_update,
            {
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": worksheet.id,
                                "tabColor": {
                                    "red": style["tab_color"][0],
                                    "green": style["tab_color"][1],
                                    "blue": style["tab_color"][2],
                                },
                            },
                            "fields": "tabColor",
                        }
                    }
                ]
            }
        )

        logging.info(f"Formatted {sheet_title} with professional styles.")

    except Exception as exc:
        logging.warning(f"Formatting failed for {sheet_title}: {exc}")


# =========================
# MAIN UPLOADER
# =========================

def upload_csvs_to_gsheets() -> None:
    if not SERVICE_ACCOUNT_FILE.exists():
        raise FileNotFoundError(f"Service account JSON not found: {SERVICE_ACCOUNT_FILE}")

    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"Input directory not found: {INPUT_DIR}")

    creds = Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE),
        scopes=SCOPES
    )

    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    existing_titles = {ws.title for ws in spreadsheet.worksheets()}
    logging.info(f"Connected to Google Sheet: {spreadsheet.title}")

    if CREATE_INDEX_SHEET:
        ensure_index_sheet(spreadsheet)

    csv_files = sorted(
        f for f in INPUT_DIR.iterdir()
        if f.is_file() and f.suffix.lower() == ".csv" and not f.name.startswith("~$")
    )

    if not csv_files:
        logging.warning(f"No CSV files found in: {INPUT_DIR}")
        return

    for csv_path in csv_files:
        base_title = sanitize_sheet_title(csv_path.stem)
        logging.info(f"Processing file: {csv_path.name}")

        data = read_csv_file(csv_path)
        if not data:
            logging.warning(f"Empty CSV skipped: {csv_path.name}")
            continue

        # If the CSV is too large, split it into multiple worksheet tabs.
        parts = split_csv_for_tabs(data, MAX_ROWS_PER_WORKSHEET)

        # Clean up old part tabs so reruns don't leave stale sheets behind.
        delete_existing_part_tabs(spreadsheet, base_title)

        if len(parts) == 1:
            worksheet_title = base_title
            worksheet = get_or_create_worksheet(
                spreadsheet,
                worksheet_title,
                rows=max(len(parts[0]) + 50, MIN_WORKSHEET_ROWS),
                cols=max(max(len(r) for r in parts[0]) + 5, MIN_WORKSHEET_COLS)
            )
            clear_and_upload_matrix(worksheet, parts[0], worksheet_title)
            continue

        # Multiple tabs for one CSV
        for idx, part_data in enumerate(parts, start=1):
            if idx == 1:
                worksheet_title = base_title
            else:
                worksheet_title = unique_title(existing_titles, f"{base_title}__part_{idx}")

            worksheet = get_or_create_worksheet(
                spreadsheet,
                worksheet_title,
                rows=max(len(part_data) + 50, MIN_WORKSHEET_ROWS),
                cols=max(max(len(r) for r in part_data) + 5, MIN_WORKSHEET_COLS)
            )
            clear_and_upload_matrix(worksheet, part_data, worksheet_title)

    if CREATE_INDEX_SHEET:
        refresh_index_sheet(spreadsheet)

    logging.info("All CSVs successfully synced to Google Sheets.")


if __name__ == "__main__":
    upload_csvs_to_gsheets()
