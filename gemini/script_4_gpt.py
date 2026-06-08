import csv
import logging
import os
import re
from collections import defaultdict
from datetime import date, datetime

import openpyxl
from openpyxl.utils import get_column_letter, range_boundaries

# --- CONFIGURATION ---
FILE_PATH = "Mixed Use Copy zip real.xlsm"  # Ensure this points to your file
OUTPUT_DIR = "Workbench_Analysis_gpt1"

TARGET_TABS = [
    "File Info", "Settings", "Dates, Premises", "Contracts, History", "Scope",
    "Site", "Zoning", "Improvements", "Assessment", "Land Grid",
    "Land Valuation", "Land Comp Profiles", "Cost Approach Setup", "Sales Grid",
    "Sales Approach", "Sale Comp Profiles", "Income Approach Setup", "Rent Roll Input",
    "Rent Roll Config", "Lease Grid", "Market Rent", "MF Market Rent",
    "Rent Comp Profiles", "Capitalization and Multipliers",
    "Investor Survey Input", "Investor Survey Output", "MF Lease Up",
    "DirectCapConclusion"
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class WorkbenchAnalyzer:
    def __init__(self, filepath, target_tabs, out_dir):
        self.filepath = filepath
        self.target_tabs = target_tabs
        self.out_dir = out_dir
        self.wb = None

        # Map "Sheet!A1" -> named range name
        self.named_range_map = {}
        self.named_range_cell_map = {}

        # Track relationships between tabs and their types
        self.relationships = defaultdict(set)

        # Track how many named ranges each sheet has
        self.sheet_named_range_count = defaultdict(int)

        if os.path.exists(out_dir):
            self._clear_existing_csvs()
        else:
            os.makedirs(out_dir)

        self._init_csv_headers()

    def _clear_existing_csvs(self):
        """Delete old CSVs so reruns do not append duplicate output."""
        for filename in os.listdir(self.out_dir):
            if filename.lower().endswith(".csv"):
                try:
                    os.remove(os.path.join(self.out_dir, filename))
                except Exception as exc:
                    logging.warning(f"Could not remove {filename}: {exc}")

    def _init_csv_headers(self):
        """Initializes the CSV files with their headers."""
        headers = {
            "Workbook Inventory.csv": [
                "Sheet",
                "Visibility",
                "Hidden",
                "Rows",
                "Columns",
                "Formula Count",
                "Named Range Count"
            ],

            "Tab Inventory.csv": [
                "Tab Name",
                "Category",
                "Purpose",
                "Input / Calc / Output",
                "Notes",
                "Visibility",
                "Tab Color"
            ],

            "Field Inventory.csv": [
                "Tab Name",
                "Field Name",
                "Named Range",
                "Input",
                "Calculated",
                "Dropdown",
                "Formula Type",
                "Data Type",
                "Required",
                "Notes",
                "Cell Ref"
            ],

            "Field Mapping.csv": [
                "Source Tab",
                "Source Field",
                "Used By Tab",
                "Used For"
            ],

            "Dropdown Values.csv": [
                "Tab Name",
                "Field Name",
                "All dropdown options",
                "Named ranges",
                "Cell Ref"
            ],

            "Calculated Fields.csv": [
                "Tab Name",
                "Field Name",
                "Formula Logic",
                "Depends On (Source Fields)",
                "Named Range Dependencies",
                "Cell Ref"
            ],

            "Named Ranges.csv": [
                "Named Range",
                "Sheet",
                "Cell",
                "Reference"
            ],

            "ShowHide Controls.csv": [
                "Named Range",
                "Reference"
            ],

            "ShowHide Usage.csv": [
                "Sheet",
                "Cell",
                "Formula",
                "Named Range"
            ],

            "Tab Relationships.csv": [
                "Source Tab",
                "Target Tab",
                "Relationship Type",
                "Relationship"
            ],

            "Notes Findings.csv": [
                "Tab Name",
                "Finding",
                "Open Question"
            ]
        }

        for filename, cols in headers.items():
            filepath = os.path.join(self.out_dir, filename)
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(cols)

    def _append_to_csv(self, filename, row_data):
        filepath = os.path.join(self.out_dir, filename)
        with open(filepath, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([str(item) if item is not None else "" for item in row_data])

    def load_workbook(self):
        logging.info(f"Loading workbook {self.filepath} (This may take several minutes)...")
        self.wb = openpyxl.load_workbook(self.filepath, data_only=False, keep_vba=True)
        logging.info("Workbook loaded successfully.")
        self._build_named_range_map()

    def _iter_defined_names(self):
        """
        Returns a uniform iterable of (name, defined_name_object) across openpyxl versions.
        """
        try:
            return list(self.wb.defined_names.items())
        except AttributeError:
            return [
                (dn.name, dn)
                for dn in getattr(self.wb.defined_names, "definedName", [])
            ]

    def _iter_defined_name_destinations(self, dn):
        """
        Yields (sheet_name, cell_or_range) for a named range.
        Uses dn.destinations when available; otherwise falls back to parsing dn.value / dn.attr_text.
        """
        try:
            destinations = list(dn.destinations)
            if destinations:
                for sheet_name, coord in destinations:
                    yield sheet_name, coord
                return
        except Exception:
            pass

        raw = getattr(dn, "value", None) or getattr(dn, "attr_text", None) or str(dn)
        raw = str(raw)

        # Handles:
        #   'Sheet Name'!$A$1
        #   Sheet1!$A$1:$C$3
        pattern = r"(?:'([^']+)'|([^'!]+))!\$?([A-Za-z]+)\$?([0-9]+)(?::\$?([A-Za-z]+)\$?([0-9]+))?"
        for match in re.finditer(pattern, raw):
            quoted_sheet, unquoted_sheet, c1, r1, c2, r2 = match.groups()
            sheet_name = quoted_sheet if quoted_sheet else unquoted_sheet
            cell_ref = f"{c1}{r1}"
            if c2 and r2:
                cell_ref = f"{cell_ref}:{c2}{r2}"
            yield sheet_name, cell_ref

    def _get_defined_name(self, name):
        """
        Return a defined name object by name across openpyxl versions.
        """
        try:
            return self.wb.defined_names[name]
        except Exception:
            for dn_name, dn in self._iter_defined_names():
                if dn_name == name:
                    return dn
        return None

    def _resolve_cell_range_values(self, ws, coord):
        """
        Resolve a single cell or range into a list of non-empty string values.
        """
        resolved_values = []

        try:
            if ":" in coord:
                for row in ws[coord]:
                    for cell in row:
                        if cell.value is not None:
                            resolved_values.append(str(cell.value).strip())
            else:
                value = ws[coord].value
                if value is not None:
                    resolved_values.append(str(value).strip())
        except Exception:
            return []

        return [value for value in resolved_values if value != ""]

    def resolve_dropdown_options(self, formula1, current_sheet=None):
        """
        Resolve data validation list formulas into actual dropdown options.

        Returns:
            (resolved_options, named_range_source, is_resolved)
        """
        if not formula1:
            return "", "", False

        ref = str(formula1).strip().lstrip("=")
        if not ref:
            return "", "", False

        # Hardcoded list validation, e.g. "A,B,C"
        if "!" not in ref and ("," in ref or '"' in ref):
            return ref.replace('"', ""), "", True

        # Dynamic cascaded dropdowns are intentionally skipped.
        if "INDIRECT" in ref.upper():
            return "", "", False

        # Named range validation.
        dn = self._get_defined_name(ref)
        if dn is not None:
            resolved_values = []
            try:
                for sheet_name, coord in self._iter_defined_name_destinations(dn):
                    if sheet_name in self.wb.sheetnames:
                        resolved_values.extend(
                            self._resolve_cell_range_values(self.wb[sheet_name], coord)
                        )
            except Exception:
                resolved_values = []

            if resolved_values:
                return ", ".join(resolved_values), ref, True
            return "", ref, False

        # Direct sheet range reference, e.g. 'Sheet Name'!$A$1:$A$5
        pattern = r"(?:'([^']+)'|([^'!]+))!\$?([A-Za-z]+)\$?([0-9]+)(?::\$?([A-Za-z]+)\$?([0-9]+))?"
        match = re.fullmatch(pattern, ref)
        if match:
            quoted_sheet, unquoted_sheet, c1, r1, c2, r2 = match.groups()
            sheet_name = quoted_sheet if quoted_sheet else unquoted_sheet
            if sheet_name in self.wb.sheetnames:
                coord = f"{c1}{r1}"
                if c2 and r2:
                    coord = f"{coord}:{c2}{r2}"
                resolved_values = self._resolve_cell_range_values(self.wb[sheet_name], coord)
                if resolved_values:
                    return ", ".join(resolved_values), "", True

        return "", "", False

    def _build_named_range_map(self):
        """Maps named ranges to cell coordinates (e.g., 'File Info!I13' -> 'Z_FileInfo_Date')."""
        logging.info("Building Named Range index...")
        self.named_range_map.clear()
        self.named_range_cell_map.clear()

        for name, dn in self._iter_defined_names():
            try:
                # Ignore print areas and external names
                if getattr(dn, "type", "REGION") != "REGION" or getattr(dn, "is_external", False):
                    continue

                for sheet_name, coord in self._iter_defined_name_destinations(dn):
                    if not sheet_name or not coord:
                        continue

                    self.sheet_named_range_count[sheet_name] += 1

                    # For field-label lookup, exact single-cell destinations are most useful.
                    # If a range is defined, map the top-left cell and every covered cell.
                    top_left = coord
                    if ":" in coord:
                        try:
                            min_col, min_row, _, _ = range_boundaries(coord)
                            top_left = f"{get_column_letter(min_col)}{min_row}"
                            max_col, max_row = range_boundaries(coord)[2], range_boundaries(coord)[3]
                            for row in range(min_row, max_row + 1):
                                for col in range(min_col, max_col + 1):
                                    cell_key = f"{sheet_name}!{get_column_letter(col)}{row}"
                                    self.named_range_cell_map.setdefault(cell_key, name)
                        except Exception:
                            continue
                    else:
                        self.named_range_cell_map.setdefault(f"{sheet_name}!{top_left}", name)

                    key = f"{sheet_name}!{top_left}"
                    # Keep the first named range encountered for a cell
                    self.named_range_map.setdefault(key, name)

            except Exception:
                continue

        logging.info(f"Named range index built: {len(self.named_range_map)} cell mappings found.")

    def get_named_range_for_cell(self, ws, row, col):
        coord_key = f"{ws.title}!{get_column_letter(col)}{row}"
        return self.named_range_cell_map.get(coord_key, "")

    def infer_data_type(self, cell, is_dropdown=False):
        """
        Infer a human-readable field data type from cell value and formatting.
        """
        if is_dropdown:
            return "dropdown"

        value = cell.value
        if value is None:
            return ""

        if isinstance(value, str) and value.startswith("="):
            fmt = (cell.number_format or "").lower()
            if self._looks_like_currency_format(fmt):
                return "currency"
            if self._looks_like_date_format(fmt):
                return "date"
            if "%" in fmt:
                return "percentage"
            return "formula"

        if isinstance(value, bool):
            return "boolean"

        if getattr(cell, "is_date", False) or self._looks_like_date_format(cell.number_format):
            return "date"

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            fmt = (cell.number_format or "").lower()
            if self._looks_like_currency_format(fmt):
                return "currency"
            if "%" in fmt:
                return "percentage"
            if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
                return "integer"
            return "decimal"

        if isinstance(value, (datetime, date)):
            return "date"

        if isinstance(value, str):
            return "text"

        return "text"

    def _looks_like_date_format(self, number_format):
        fmt = (number_format or "").lower()
        if not fmt:
            return False

        # Skip plain numeric formats that use "m" as minute/month in other contexts.
        return any(token in fmt for token in ["yy", "yyyy", "dd", "mmm", "hh", "mm/dd", "dd/mm", "m/d"])

    def _looks_like_currency_format(self, number_format):
        fmt = (number_format or "").lower()
        return any(symbol in fmt for symbol in ["$", "€", "£", "¥", "₹"])

    def infer_required_status(self, cell, is_formula=False, is_dropdown=False, dropdown_meta=None):
        """
        Classify a field as required, optional, calculated, or conditional.
        """
        if is_formula:
            formula = str(cell.value or "").upper()
            if any(token in formula for token in ["IF(", "IFS(", "SWITCH(", "CHOOSE(", "INDIRECT("]):
                return "conditional"
            return "calculated"

        if is_dropdown:
            if dropdown_meta and not dropdown_meta.get("resolved", True):
                return "conditional"
            return "required"

        if not cell.protection.locked:
            if cell.value is None or str(cell.value).strip() == "":
                return "optional"
            return "required"

        return "optional"

    def infer_relationship_type(self, formula):
        """
        Classify the relationship implied by a formula.
        """
        formula_str = str(formula)
        if self.is_pass_through(formula_str):
            return "Pass-Through"

        formula_upper = formula_str.upper()
        if any(token in formula_upper for token in ["XLOOKUP(", "VLOOKUP(", "INDEX(", "MATCH("]):
            return "Lookup"
        if any(token in formula_upper for token in ["SUM(", "AVERAGE(", "COUNT(", "COUNTA(", "MIN(", "MAX("]):
            return "Aggregation"
        if any(token in formula_upper for token in ["IF(", "IFS(", "SWITCH(", "CHOOSE(", "INDIRECT("]):
            return "Conditional"
        return "Formula Reference"

    def add_relationship(self, source_tab, target_tab, relationship_type):
        """
        Store a typed relationship between two tabs.
        """
        if not source_tab or not target_tab:
            return
        self.relationships[(source_tab, target_tab)].add(relationship_type or "Formula Reference")

    def find_field_label(self, ws, row, col):
        coord_key = f"{ws.title}!{get_column_letter(col)}{row}"
        if coord_key in self.named_range_map:
            return self.named_range_map[coord_key]

        candidates = []

        # search left 15 columns
        for c in range(max(1, col - 15), col):
            val = self.get_effective_value(ws, row, c)
            if (
                isinstance(val, str)
                and val.strip()
                and not val.startswith("=")
                and len(val) < 120
            ):
                candidates.append((col - c, val.strip()))

        # search upward 8 rows
        for r in range(max(1, row - 8), row):
            val = self.get_effective_value(ws, r, col)
            if (
                isinstance(val, str)
                and val.strip()
                and not val.startswith("=")
                and len(val) < 120
            ):
                candidates.append((100 + (row - r), val.strip()))

        if candidates:
            candidates.sort()
            return candidates[0][1]

        return f"Unknown_Field_{get_column_letter(col)}{row}"

    def is_pass_through(self, formula):
        """
        Identifies direct-reference formulas that simply pass values through.
        Examples:
          =A1
          =$A$1
          ='Sheet Name'!A1
          =+A1
        """
        formula = str(formula).strip()

        patterns = [
            r"^=\+?\$?[A-Za-z]+\$?[0-9]+$",
            r"^=\+?'[^']+'!\$?[A-Za-z]+\$?[0-9]+$",
            r"^=\+?[A-Za-z0-9_ .\-]+!\$?[A-Za-z]+\$?[0-9]+$"
        ]

        return any(re.match(p, formula) for p in patterns)

    def classify_formula(self, formula):
        formula = str(formula).upper()

        if self.is_pass_through(formula):
            return "PassThrough"
        if "XLOOKUP(" in formula:
            return "Lookup"
        if "VLOOKUP(" in formula:
            return "Lookup"
        if "INDEX(" in formula:
            return "Lookup"
        if "MATCH(" in formula:
            return "Lookup"
        if "SUM(" in formula:
            return "Aggregation"
        if "AVERAGE(" in formula:
            return "Aggregation"
        if "IF(" in formula:
            return "Conditional"

        return "Calculation"

    def extract_named_range_dependencies(self, formula):
        """
        Case-insensitive search for named ranges used in a formula.
        Uses boundary-aware matching to reduce false positives.
        """
        formula_upper = str(formula).upper()
        found = []

        for nr in set(self.named_range_map.values()):
            nr_upper = str(nr).upper()
            pattern = rf"(?<![A-Z0-9_]){re.escape(nr_upper)}(?![A-Z0-9_])"
            if re.search(pattern, formula_upper):
                found.append(nr)

        return sorted(set(found))

    def extract_source_field_dependencies(self, ws, formula):
        """
        Resolve formula references into source field labels.

        This keeps the dependency output at the field level instead of sheet level
        for the Calculated Fields export.
        """
        formula_str = str(formula)
        deps = []
        seen = set()

        def add_dep(sheet_name, row_num, col_letter):
            if sheet_name not in self.wb.sheetnames:
                return

            source_ws = self.wb[sheet_name]
            col_idx = openpyxl.utils.column_index_from_string(col_letter)
            label = self.find_field_label(source_ws, row_num, col_idx)
            value = label if label else f"{sheet_name}!{col_letter}{row_num}"

            if value not in seen:
                seen.add(value)
                deps.append(value)

        # Sheet-qualified ranges and single-cell refs.
        sheet_ref_pattern = r"(?:'([^']+)'|([A-Za-z0-9_ .\-]+))!\$?([A-Za-z]+)\$?([0-9]+)(?::\$?([A-Za-z]+)\$?([0-9]+))?"
        for quoted_sheet, unquoted_sheet, start_col, start_row, end_col, end_row in re.findall(sheet_ref_pattern, formula_str):
            sheet_name = quoted_sheet if quoted_sheet else unquoted_sheet
            if not sheet_name:
                continue

            try:
                min_col, min_row = openpyxl.utils.column_index_from_string(start_col), int(start_row)
                if end_col and end_row:
                    max_col, max_row = openpyxl.utils.column_index_from_string(end_col), int(end_row)
                else:
                    max_col, max_row = min_col, min_row
            except Exception:
                continue

            for row_num in range(min_row, max_row + 1):
                for col_idx in range(min_col, max_col + 1):
                    add_dep(sheet_name.strip(), row_num, get_column_letter(col_idx))

        # Same-sheet cell refs, e.g. =A1 + B2
        same_sheet_pattern = r"(?<![A-Z0-9_!])\$?([A-Z]{1,3})\$?([0-9]+)(?![A-Z0-9_])"
        for col_letter, row_num in re.findall(same_sheet_pattern, formula_str):
            try:
                add_dep(ws.title, int(row_num), col_letter)
            except Exception:
                continue

        return deps

    def extract_field_mappings_from_formula(self, ws, formula):
        """
        Resolve formula references into (source tab, source field) pairs.

        This is used for Field Mapping.csv so the Source Field column contains
        actual labels instead of a placeholder.
        """
        formula_str = str(formula)
        mappings = []
        seen = set()

        def add_mapping(sheet_name, row_num, col_letter):
            if sheet_name not in self.wb.sheetnames:
                return

            source_ws = self.wb[sheet_name]
            col_idx = openpyxl.utils.column_index_from_string(col_letter)
            label = self.find_field_label(source_ws, row_num, col_idx)
            source_field = label if label else f"{sheet_name}!{col_letter}{row_num}"
            key = (sheet_name, source_field)
            if key not in seen:
                seen.add(key)
                mappings.append(key)

        sheet_ref_pattern = r"(?:'([^']+)'|([A-Za-z0-9_ .\-]+))!\$?([A-Za-z]+)\$?([0-9]+)(?::\$?([A-Za-z]+)\$?([0-9]+))?"
        for quoted_sheet, unquoted_sheet, start_col, start_row, end_col, end_row in re.findall(sheet_ref_pattern, formula_str):
            sheet_name = quoted_sheet if quoted_sheet else unquoted_sheet
            if not sheet_name:
                continue

            try:
                min_col, min_row = openpyxl.utils.column_index_from_string(start_col), int(start_row)
                if end_col and end_row:
                    max_col, max_row = openpyxl.utils.column_index_from_string(end_col), int(end_row)
                else:
                    max_col, max_row = min_col, min_row
            except Exception:
                continue

            for row_num in range(min_row, max_row + 1):
                for col_idx in range(min_col, max_col + 1):
                    add_mapping(sheet_name.strip(), row_num, get_column_letter(col_idx))

        same_sheet_pattern = r"(?<![A-Z0-9_!])\$?([A-Z]{1,3})\$?([0-9]+)(?![A-Z0-9_])"
        for col_letter, row_num in re.findall(same_sheet_pattern, formula_str):
            try:
                add_mapping(ws.title, int(row_num), col_letter)
            except Exception:
                continue

        return mappings

    def extract_dependencies_from_formula(self, formula):
        """
        Extract sheet-level dependencies from formulas.
        Handles quoted sheet names and sheet names with spaces / punctuation.
        """
        pattern = r"(?:'([^']+)'|([A-Za-z0-9_ .\-]+))!\$?[A-Za-z]+\$?[0-9]+"
        matches = re.findall(pattern, str(formula))

        deps = set()
        for quoted, unquoted in matches:
            sheet = quoted if quoted else unquoted
            if sheet:
                deps.add(sheet.strip())

        return sorted(deps)

    def get_effective_value(self, ws, row, col):
        cell = ws.cell(row=row, column=col)
        if cell.value is not None:
            return cell.value

        for merged in ws.merged_cells.ranges:
            if (row, col) in merged.cells:
                return ws.cell(merged.min_row, merged.min_col).value

        return None

    def export_named_ranges(self):
        logging.info("Exporting Named Ranges...")

        for name, dn in self._iter_defined_names():
            try:
                raw = getattr(dn, "value", None) or getattr(dn, "attr_text", None) or str(dn)
                raw = str(raw)

                for sheet_name, coord in self._iter_defined_name_destinations(dn):
                    self._append_to_csv(
                        "Named Ranges.csv",
                        [
                            name,
                            sheet_name,
                            coord,
                            raw
                        ]
                    )

                # if "_SHOWHIDE" in name.upper():
                #     self._append_to_csv(
                #         "ShowHide Controls.csv",
                #         [
                #             name,
                #             raw
                #         ]
                #     )

            except Exception:
                pass

    # def export_workbook_inventory(self):
    #     for ws in self.wb.worksheets:
    #         formula_count = 0

    #         for row in ws.iter_rows():
    #             for cell in row:
    #                 if isinstance(cell.value, str) and cell.value.startswith("="):
    #                     formula_count += 1

    #         # visibility = ws.sheet_state
    #         # hidden = visibility != "visible"
    #         # named_range_count = self.sheet_named_range_count.get(ws.title, 0)

    #         # self._append_to_csv(
    #         #     "Workbook Inventory.csv",
    #         #     [
    #         #         ws.title,
    #         #         visibility,
    #         #         "Yes" if hidden else "No",
    #         #         ws.max_row,
    #         #         ws.max_column,
    #         #         formula_count,
    #         #         named_range_count
    #         #     ]
    #         # )

    def analyze(self):
        self.load_workbook()
        self.export_named_ranges()
        # self.export_workbook_inventory()

        for sheet_name in self.target_tabs:
            if sheet_name not in self.wb.sheetnames:
                logging.warning(f"Tab '{sheet_name}' not found. Skipping.")
                continue

            logging.info(f"Analyzing sheet: {sheet_name}")
            ws = self.wb[sheet_name]
            self.analyze_sheet(ws)
            logging.info(f"Finished saving data for: {sheet_name}")

        logging.info("Analysis complete! Generating final Tab Relationships...")
        self._write_relationships()

    def analyze_sheet(self, ws):
        sheet_name = ws.title
        visibility = ws.sheet_state
        tab_color = ws.sheet_properties.tabColor.rgb if ws.sheet_properties.tabColor else "None"

        self._append_to_csv(
            "Tab Inventory.csv",
            [
                sheet_name,
                "Uncategorized",
                "Auto-extracted",
                "",
                "",
                visibility,
                tab_color
            ]
        )

        dropdowns = {}
        validations = getattr(ws.data_validations, "dataValidation", [])

        for dv in validations:
            if dv.type == "list":
                for cell_range in dv.sqref.ranges:
                    for row in range(cell_range.min_row, cell_range.max_row + 1):
                        for col in range(cell_range.min_col, cell_range.max_col + 1):
                            coord = f"{get_column_letter(col)}{row}"
                            resolved_options, named_range, is_resolved = self.resolve_dropdown_options(
                                dv.formula1,
                                current_sheet=sheet_name
                            )
                            dropdowns[coord] = {
                                "all_dropdown_options": resolved_options,
                                "named_ranges": named_range,
                                "resolved": is_resolved
                            }

        max_r, max_c = ws.max_row, ws.max_column
        if max_r > 5000:
            max_r = 5000

        for row_cells in ws.iter_rows(min_row=1, max_row=max_r, max_col=max_c):
            row = row_cells[0].row

            row_dim = ws.row_dimensions.get(row)
            is_hidden_row = bool(row_dim and row_dim.hidden)

            for cell in row_cells:
                col = cell.column
                col_letter = get_column_letter(col)

                col_dim = ws.column_dimensions.get(col_letter)
                is_hidden_col = bool(col_dim and col_dim.hidden)

                val = cell.value
                coord = cell.coordinate

                if val is None:
                    continue

                is_formula = isinstance(val, str) and val.startswith("=")
                is_dropdown = coord in dropdowns
                is_unlocked = not cell.protection.locked

                # Capture:
                #   - formulas
                #   - dropdowns
                #   - unlocked cells (text or numeric inputs)
                if is_formula or is_dropdown or is_unlocked:
                    label = self.find_field_label(ws, row, col)
                    notes = []
                    if is_hidden_row or is_hidden_col:
                        notes.append("[HIDDEN CELL]")
                    if is_formula and self.is_pass_through(val):
                        notes.append("[PASS-THROUGH]")

                    notes_str = " | ".join(notes)

                    named_range = self.get_named_range_for_cell(ws, row, col)

                    formula_type = self.classify_formula(val) if is_formula else ""
                    required_status = self.infer_required_status(
                        cell,
                        is_formula=is_formula,
                        is_dropdown=is_dropdown,
                        dropdown_meta=dropdowns.get(coord)
                    )
                    inferred_data_type = self.infer_data_type(cell, is_dropdown=is_dropdown)

                    self._append_to_csv(
                        "Field Inventory.csv",
                        [
                            sheet_name,
                            label,
                            named_range,
                            "Yes" if not is_formula else "No",
                            "Yes" if is_formula else "No",
                            "Yes" if is_dropdown else "No",
                            formula_type,
                            inferred_data_type,
                            required_status,
                            notes_str,
                            coord
                        ]
                    )

                    if is_dropdown:
                        dropdown_meta = dropdowns[coord]
                        if not dropdown_meta["resolved"]:
                            continue

                        self._append_to_csv(
                            "Dropdown Values.csv",
                            [
                                sheet_name,
                                label,
                                dropdown_meta["all_dropdown_options"],
                                dropdown_meta["named_ranges"],
                                coord
                            ]
                        )

                    if is_formula:
                        source_fields = self.extract_source_field_dependencies(ws, val)
                        deps = self.extract_dependencies_from_formula(val)
                        named_deps = self.extract_named_range_dependencies(val)
                        relationship_type = self.infer_relationship_type(val)

                        self._append_to_csv(
                            "Calculated Fields.csv",
                            [
                                sheet_name,
                                label,
                                val,
                                ", ".join(source_fields),
                                ", ".join(named_deps),
                                coord
                            ]
                        )

                        # ShowHide usage capture
                        showhide_named_deps = [
                            dep for dep in named_deps
                            if "_SHOWHIDE" in dep.upper()
                        ]
                        if "_SHOWHIDE" in str(val).upper() or showhide_named_deps:
                            if showhide_named_deps:
                                for dep in showhide_named_deps:
                                    self._append_to_csv(
                                        "ShowHide Usage.csv",
                                        [
                                            sheet_name,
                                            coord,
                                            val,
                                            dep
                                        ]
                                    )
                            else:
                                self._append_to_csv(
                                    "ShowHide Usage.csv",
                                    [
                                        sheet_name,
                                        coord,
                                        val,
                                        ""
                                    ]
                                )

                        for dep in deps:
                            if dep != sheet_name:
                                self.add_relationship(dep, sheet_name, relationship_type)
                        for source_tab, source_field in self.extract_field_mappings_from_formula(ws, val):
                            if source_tab != sheet_name:
                                self.add_relationship(source_tab, sheet_name, relationship_type)
                            self._append_to_csv(
                                "Field Mapping.csv",
                                [
                                    source_tab,
                                    source_field,
                                    sheet_name,
                                    ""
                                ]
                            )

    def _write_relationships(self):
        for source, target in sorted(self.relationships):
            relationship_types = ", ".join(sorted(self.relationships[(source, target)]))
            self._append_to_csv(
                "Tab Relationships.csv",
                [
                    source,
                    target,
                    relationship_types,
                    f"'{target}' pulls data from '{source}'"
                ]
            )


if __name__ == "__main__":
    analyzer = WorkbenchAnalyzer(FILE_PATH, TARGET_TABS, OUTPUT_DIR)
    analyzer.analyze()
