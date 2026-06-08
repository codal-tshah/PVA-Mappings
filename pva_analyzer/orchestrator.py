"""
PVA Workbench Analyzer — Main Orchestrator
Coordinates all extractors, state manager, and output writers.
"""
from __future__ import annotations
import sys
import time
import traceback
from pathlib import Path

# Add extractors dir to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "extractors"))

from config import (
    TARGET_TABS, OUTPUT_DIR,
    GSHEETS_ENABLED, GSHEETS_CREDENTIALS, GSHEETS_SPREADSHEET_ID,
)
from logger import get_logger
from state_manager import StateManager
from xlsb_reader import open_workbook_meta, load_sheet, WorkbookData
from output_writer import OutputWriter
from extractors.field_extractor import extract_fields
from extractors.dropdown_extractor import extract_dropdowns
from extractors.formula_extractor import extract_formulas
from extractors.metadata_extractor import extract_tab_inventory, extract_named_ranges
from extractors.mapping_extractor import extract_relationships

log = get_logger("orchestrator")


class Analyzer:
    def __init__(
        self,
        workbook_path: str,
        template_path: str | None = None,
        target_tabs: list[str] | None = None,
        resume: bool = True,
        gsheets: bool = False,
    ):
        self.wb_path      = workbook_path
        self.template     = template_path
        self.target_tabs  = target_tabs or TARGET_TABS
        self.resume       = resume

        wb_stem = Path(workbook_path).stem.replace(" ", "_")
        self.output_path  = str(OUTPUT_DIR / f"{wb_stem}_analysis.xlsx")

        self.state   = StateManager(workbook_path)
        self.writer  = OutputWriter(template_path, self.output_path)
        self.gs      = None

        if gsheets and GSHEETS_ENABLED:
            from gsheets_writer import make_gsheets_writer
            self.gs = make_gsheets_writer(
                str(GSHEETS_SPREADSHEET_ID),
                str(GSHEETS_CREDENTIALS),
            )

        # Accumulated data for cross-tab analysis
        self._all_relationships: list = []
        self._nr_tab_refs: dict[str, list[str]] = {}  # named_range -> [tabs]

    # ── Public entry point ─────────────────────────────────────────────────────

    def run(self):
        t0 = time.time()
        log.info("=" * 60)
        log.info(f"PVA Workbench Analyzer")
        log.info(f"Input:  {self.wb_path}")
        log.info(f"Output: {self.output_path}")
        log.info(f"Tabs:   {len(self.target_tabs)} target tabs")
        log.info("=" * 60)

        # 1 — open workbook metadata (fast, no sheet data loaded)
        try:
            wb_data = open_workbook_meta(self.wb_path)
        except Exception as e:
            log.error(f"Cannot open workbook: {e}")
            self._write_open_error(str(e))
            return

        self._log_workbook_summary(wb_data)

        # 2 — initialise output sheets
        self.writer.init_tab_inventory()
        self.writer.init_field_inventory()
        self.writer.init_dropdown_values()
        self.writer.init_calculated_fields()
        self.writer.init_field_mapping()
        self.writer.init_tab_relationships()
        self.writer.init_notes()
        self.writer.init_named_ranges()

        # 3 — process each target tab
        for tab in self.target_tabs:
            if self.resume and self.state.is_done(tab):
                log.info(f"  SKIP (already done): {tab}")
                continue
            self._process_tab(tab, wb_data)

        # 4 — write cross-tab outputs
        self._write_relationships()
        self._write_named_ranges(wb_data)
        self._write_final_notes(wb_data)

        # 5 — flush Google Sheets if enabled
        if self.gs:
            log.info("Flushing to Google Sheets…")
            self.gs.flush_all()

        # 6 — save final output
        self.writer.save()

        elapsed = time.time() - t0
        summary = self.state.summary()
        log.info("=" * 60)
        log.info(f"Done in {elapsed:.1f}s — "
                 f"{summary['completed']} completed, "
                 f"{summary['failed']} failed, "
                 f"{summary['skipped']} skipped")
        log.info(f"Output: {self.output_path}")
        log.info("=" * 60)

    # ── Per-tab processing ─────────────────────────────────────────────────────

    def _process_tab(self, tab: str, wb_data: WorkbookData):
        log.info(f"Processing: {tab}")
        t0 = time.time()

        try:
            # Load sheet data (one at a time to control memory)
            sheet = load_sheet(wb_data, tab)

            if sheet is None:
                self.state.mark_skipped(tab, "Sheet not found in workbook")
                self.writer.write_note(
                    tab,
                    f"Sheet '{tab}' not found in workbook. "
                    f"Available sheets: {', '.join(wb_data.all_sheet_names[:10])}…",
                    "Verify tab name spelling against workbook. Run Workbook_Audit VBA macro.",
                )
                return

            matched_name = sheet.meta.name

            # ── Extractors ────────────────────────────────────────────────────
            # 1. Dropdowns first (needed by field extractor)
            dropdown_recs, dv_map = extract_dropdowns(tab, sheet)

            # 2. Fields
            field_recs = extract_fields(tab, sheet, dv_map)

            # 3. Formulas
            formula_recs = extract_formulas(tab, sheet)

            # 4. Tab metadata
            inv_rec = extract_tab_inventory(tab, matched_name, sheet, wb_data)

            # 5. Relationships (uses formula cross-refs)
            rel_recs = extract_relationships(tab, formula_recs, wb_data.all_sheet_names)
            self._all_relationships.extend(rel_recs)

            # Track named range → tab refs
            for fr in formula_recs:
                for nr in fr.named_ranges_used:
                    self._nr_tab_refs.setdefault(nr, [])
                    if tab not in self._nr_tab_refs[nr]:
                        self._nr_tab_refs[nr].append(tab)

            # ── Write outputs ─────────────────────────────────────────────────
            self.writer.write_tab_inventory_row(inv_rec)

            for rec in field_recs:
                self.writer.write_field_inventory_row(rec)

            for rec in dropdown_recs:
                self.writer.write_dropdown_row(rec)

            for rec in formula_recs:
                self.writer.write_formula_row(rec)

            # Google Sheets incremental flush
            if self.gs:
                self.gs.buffer_tab_inventory(inv_rec)
                for r in field_recs:    self.gs.buffer_field(r)
                for r in dropdown_recs: self.gs.buffer_dropdown(r)
                for r in formula_recs:  self.gs.buffer_formula(r)
                for r in rel_recs:      self.gs.buffer_relationship(r)
                # Flush after each tab (incremental)
                for sname in ["Tab Inventory","Field Inventory","Dropdown Values",
                               "Calculated Fields","Field Mapping","Tab Relationships"]:
                    self.gs.flush_sheet(sname)

            # Intermediate save every tab
            self.writer.save_intermediate(f"progress_{tab.replace(' ', '_')[:15]}")

            elapsed = time.time() - t0
            self.state.mark_done(tab, {
                "fields":    len(field_recs),
                "dropdowns": len(dropdown_recs),
                "formulas":  len(formula_recs),
                "elapsed_s": round(elapsed, 1),
            })

            # Release sheet data (help GC)
            del sheet, field_recs, formula_recs, dropdown_recs

        except Exception as e:
            tb = traceback.format_exc()
            log.error(f"Error processing '{tab}': {e}\n{tb}")
            self.state.mark_failed(tab, str(e))
            self.writer.write_note(
                tab,
                f"ERROR during extraction: {e}",
                "Check logs for full traceback. Try re-running with --resume.",
            )

    # ── Cross-tab writes ───────────────────────────────────────────────────────

    def _write_relationships(self):
        seen: set[tuple] = set()
        for rec in self._all_relationships:
            key = (rec.source_tab, rec.target_tab, rec.relationship_type[:20], rec.what_flows[:30])
            if key in seen:
                continue
            seen.add(key)
            self.writer.write_relationship_row(rec)
            self.writer.write_tab_relationship_row(rec)
        log.info(f"Relationships written: {len(seen)}")

    def _write_named_ranges(self, wb_data: WorkbookData):
        nr_recs = extract_named_ranges(wb_data, self._nr_tab_refs)
        for rec in nr_recs:
            self.writer.write_named_range_row(rec)
            if self.gs:
                self.gs.buffer_named_range(rec)
        log.info(f"Named ranges written: {len(nr_recs)}")

    def _write_final_notes(self, wb_data: WorkbookData):
        # File corruption check
        from pathlib import Path
        wb_bytes = Path(self.wb_path).stat().st_size
        if wb_bytes < 1024:
            self.writer.write_note(
                "File Integrity",
                f"Workbook file is suspiciously small ({wb_bytes} bytes). "
                "File may be corrupted (all-zero bytes). Cannot extract data.",
                "Re-export the .xlsb from Excel/VM. Verify with 7-zip before uploading.",
            )

        # Tabs not found
        found_tabs = set(self.state.state.get("completed", []))
        skipped    = set(t["tab"] for t in self.state.state.get("skipped", []))
        failed     = set(t["tab"] for t in self.state.state.get("failed", []))
        missing    = (skipped | failed) - found_tabs
        if missing:
            self.writer.write_note(
                "Missing Tabs",
                f"These target tabs were not found or failed: {', '.join(sorted(missing))}",
                "Run Workbook_Audit VBA macro to list all sheet names with exact spelling.",
            )

        # Hidden/VeryHidden tabs
        very_hidden = [n for n, v in wb_data.sheet_visibility.items() if v == "VeryHidden"]
        if very_hidden:
            self.writer.write_note(
                "VeryHidden Sheets",
                f"{len(very_hidden)} VeryHidden sheets found. Cannot be unhidden by user — only VBA. "
                f"Examples: {', '.join(very_hidden[:8])}",
                "VeryHidden sheets CAN be written by openpyxl for API seeding even when hidden. "
                "Run Workbook_Audit VBA macro to see full list.",
            )

        # VBA/UDF warning
        self.writer.write_note(
            "VBA / UDF Dependency",
            "Workbook uses custom VBA UDFs: @Spell(), hideblankorerror(), "
            "DistanceBetweenLatLongPoints(), GetDropDownListFormula(). "
            "These ONLY execute in Excel with macros enabled — not in Python.",
            "When seeding via API: write only Input/Dropdown fields (blue/green). "
            "Leave Calculated fields (yellow) for Excel/VBA to compute on open.",
        )

        # Date field warning
        self.writer.write_note(
            "Date Field Encoding",
            "All date fields must be stored as Excel serial numbers (integer days since 1900-01-01), "
            "NOT text strings. e.g. 2025-12-15 = serial 45641.",
            "Python: from datetime import date; serial = (date(2025,12,15) - date(1900,1,1)).days + 2",
        )

        # Percentage field warning
        self.writer.write_note(
            "Percentage / Rate Fields",
            "Cap rates, V&CL%, assessment ratios, vacancy%, discount rates MUST be stored as "
            "decimals (0.055 = 5.5%), NOT whole numbers (5.5). "
            "Most common seeding error.",
            "Validate: assert 0 < cap_rate < 1 before writing.",
        )

        # pva* named ranges note
        self.writer.write_note(
            "pva* Named Ranges — CRITICAL",
            "65+ pva* named ranges drive ALL tab Show/Hide via VBA. "
            "When seeding via API, you MUST set both the cell value AND the named range "
            "definition using openpyxl DefinedName — VBA reads the named range, not the cell.",
            "Run Workbook_Audit VBA macro to get exact RefersTo cell refs for every pva* range. "
            "Use: wb.defined_names['pvaPropertyTypeKey'] = DefinedName('pvaPropertyTypeKey', attr_text=\"Settings!$G$5\")",
        )

    def _write_open_error(self, error: str):
        self.writer.init_notes()
        self.writer.write_note(
            "FATAL: Cannot Open Workbook",
            f"Error: {error}",
            "1) Verify file path is correct.\n"
            "2) If .xlsb — install pyxlsb: pip install pyxlsb\n"
            "3) If file is all-zero bytes — re-export from Excel.\n"
            "4) If .xlsx — ensure file is not password-protected.",
        )
        self.writer.save()

    def _log_workbook_summary(self, wb_data: WorkbookData):
        visible   = sum(1 for v in wb_data.sheet_visibility.values() if v == "Visible")
        hidden    = sum(1 for v in wb_data.sheet_visibility.values() if v == "Hidden")
        vhidden   = sum(1 for v in wb_data.sheet_visibility.values() if v == "VeryHidden")
        log.info(
            f"Workbook: {len(wb_data.all_sheet_names)} sheets "
            f"({visible} visible, {hidden} hidden, {vhidden} very-hidden), "
            f"{len(wb_data.named_ranges)} named ranges"
        )
        missing = []
        for tab in self.target_tabs:
            from xlsb_reader import _fuzzy_match
            if _fuzzy_match(tab, wb_data.all_sheet_names) is None:
                missing.append(tab)
        if missing:
            log.warning(f"Target tabs NOT found in workbook: {missing}")
