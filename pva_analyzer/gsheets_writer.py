"""
PVA Workbench Analyzer — Google Sheets Writer (optional)
Writes extracted data to a Google Sheets spreadsheet using a service account.
Set GSHEETS_ENABLED = True and provide credentials in config.py to activate.
"""
from __future__ import annotations
from typing import Any

from logger import get_logger

log = get_logger("gsheets_writer")

# Sheet name → column headers mapping (matches output_writer.py structure)
SHEET_HEADERS: dict[str, list[str]] = {
    "Tab Inventory": [
        "Tab Name","Matched Sheet Name","Visible?","Tab Color","Used Range",
        "Total Cells","Formula Cells","Merged Cells","Hidden Rows","Hidden Cols",
        "Tables","DV Count","Named Ranges Referenced","Notes",
    ],
    "Field Inventory": [
        "Tab","Field / Label","Input","Calc","DD",
        "Data Type","Required?","Cell Ref","Named Ranges Used","API Seed?","Notes",
    ],
    "Dropdown Values": [
        "Tab","Cell Ref","Field Label","DV Type","All Options (pipe-separated)","Source / Notes",
    ],
    "Calculated Fields": [
        "Tab","Cell Ref","Field / Label","Category","Formula","UDFs / Named Ranges","Cross-Sheet Refs",
    ],
    "Field Mapping": [
        "Source Tab","Source Field","Target Tab","Relationship Type","What Flows / How","Confidence",
    ],
    "Tab Relationships": [
        "Source Tab","Target Tab","Type","What Flows",
    ],
    "Notes & Findings": [
        "Area","Finding / Detail","Recommendation / Action",
    ],
    "Named Ranges": [
        "Named Range","Prefix","Refers To","Purpose / What It Controls",
    ],
}

# Color maps for conditional formatting (Google Sheets background RGB)
FIELD_TYPE_COLORS: dict[str, tuple] = {
    "input":      (219, 234, 254),   # blue
    "calculated": (254, 243, 199),   # amber
    "dropdown":   (209, 250, 229),   # green
}


class GSheetsWriter:
    def __init__(self, spreadsheet_id: str, credentials_path: str):
        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError:
            raise ImportError("Install: pip install gspread google-auth")

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        self._gc = gspread.authorize(creds)
        self._ss = self._gc.open_by_key(spreadsheet_id)
        self._buffers: dict[str, list[list]] = {k: [] for k in SHEET_HEADERS}
        log.info(f"Connected to Google Sheets: {self._ss.title}")

    def _get_or_create_sheet(self, name: str):
        try:
            return self._ss.worksheet(name)
        except Exception:
            ws = self._ss.add_worksheet(title=name, rows=5000, cols=20)
            log.debug(f"Created Google Sheet tab: {name}")
            return ws

    def _write_headers(self, ws, sheet_name: str):
        headers = SHEET_HEADERS.get(sheet_name, [])
        if headers:
            ws.update("A1", [headers])

    def buffer_tab_inventory(self, rec):
        self._buffers["Tab Inventory"].append([
            rec.tab, rec.matched_name, rec.visible, rec.tab_color,
            rec.used_range, rec.total_cells, rec.formula_cells,
            rec.merged_cells, rec.hidden_rows, rec.hidden_cols,
            rec.tables, rec.data_validations,
            rec.named_ranges_referenced, rec.notes,
        ])

    def buffer_field(self, rec):
        self._buffers["Field Inventory"].append([
            rec.tab, rec.label,
            "Y" if rec.field_type == "input" else "",
            "Y" if rec.field_type == "calculated" else "",
            "Y" if rec.field_type == "dropdown" else "",
            rec.data_type, rec.is_required, rec.cell_ref,
            ", ".join(rec.named_ranges_used[:5]),
            "N" if rec.field_type == "calculated" else "Y",
            rec.notes,
        ])

    def buffer_dropdown(self, rec):
        self._buffers["Dropdown Values"].append([
            rec.tab, rec.cell_ref, rec.field_label,
            rec.validation_type, rec.options_str,
            rec.source_range or rec.notes,
        ])

    def buffer_formula(self, rec):
        self._buffers["Calculated Fields"].append([
            rec.tab, rec.cell_ref, rec.label, rec.formula_category,
            rec.formula[:300],
            ", ".join(rec.udfs_used + rec.named_ranges_used[:4]),
            ", ".join(rec.cross_sheet_refs[:5]),
        ])

    def buffer_relationship(self, rec):
        self._buffers["Field Mapping"].append([
            rec.source_tab, rec.source_field, rec.target_tab,
            rec.relationship_type, rec.what_flows, rec.confidence,
        ])
        self._buffers["Tab Relationships"].append([
            rec.source_tab, rec.target_tab,
            rec.relationship_type, rec.what_flows,
        ])

    def buffer_note(self, area: str, finding: str, recommendation: str = ""):
        self._buffers["Notes & Findings"].append([area, finding, recommendation])

    def buffer_named_range(self, rec):
        self._buffers["Named Ranges"].append([
            rec.name, rec.prefix, rec.refers_to, rec.purpose,
        ])

    def flush_all(self):
        """Write all buffered data to Google Sheets in batch."""
        import time
        for sheet_name, rows in self._buffers.items():
            if not rows:
                continue
            try:
                ws = self._get_or_create_sheet(sheet_name)
                ws.clear()
                self._write_headers(ws, sheet_name)
                # Write in chunks of 500 to avoid API limits
                chunk_size = 500
                start_row = 2  # after headers
                for i in range(0, len(rows), chunk_size):
                    chunk = rows[i:i + chunk_size]
                    start = f"A{start_row + i}"
                    ws.update(start, chunk)
                    time.sleep(0.5)  # rate limit courtesy
                log.info(f"GSheets '{sheet_name}': {len(rows)} rows written")
            except Exception as e:
                log.error(f"GSheets write failed for '{sheet_name}': {e}")

    def flush_sheet(self, sheet_name: str):
        """Write a single sheet's buffer (call after each tab for incremental updates)."""
        import time
        rows = self._buffers.get(sheet_name, [])
        if not rows:
            return
        try:
            ws = self._get_or_create_sheet(sheet_name)
            # Append below existing data
            existing = ws.get_all_values()
            start_row = len(existing) + 1
            if start_row == 1:
                self._write_headers(ws, sheet_name)
                start_row = 2
            ws.update(f"A{start_row}", rows)
            self._buffers[sheet_name] = []  # clear after flush
            time.sleep(0.3)
        except Exception as e:
            log.error(f"GSheets flush failed for '{sheet_name}': {e}")


def make_gsheets_writer(spreadsheet_id: str, credentials_path: str) -> GSheetsWriter | None:
    """Factory — returns None if credentials file missing."""
    from pathlib import Path
    if not Path(credentials_path).exists():
        log.warning(f"GSheets credentials not found: {credentials_path}. Skipping GSheets output.")
        return None
    try:
        return GSheetsWriter(spreadsheet_id, credentials_path)
    except Exception as e:
        log.error(f"GSheets init failed: {e}")
        return None
