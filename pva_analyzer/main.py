#!/usr/bin/env python3
"""
PVA Workbench Analyzer — CLI Entry Point

Usage examples:
  python main.py workbench.xlsb
  python main.py workbench.xlsb --template my_template.xlsx
  python main.py workbench.xlsb --tabs "File Info" "Settings" "Sales Grid"
  python main.py workbench.xlsb --no-resume          # force re-process all tabs
  python main.py workbench.xlsb --gsheets            # also write to Google Sheets
  python main.py workbench.xlsb --list-sheets        # just list all sheet names
  python main.py workbench.xlsb --audit              # generate audit CSV only
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "extractors"))


def cmd_analyze(args):
    from orchestrator import Analyzer
    analyzer = Analyzer(
        workbook_path=args.workbook,
        template_path=args.template,
        target_tabs=args.tabs or None,
        resume=not args.no_resume,
        gsheets=args.gsheets,
    )
    analyzer.run()


def cmd_list_sheets(args):
    from xlsb_reader import open_workbook_meta
    wb = open_workbook_meta(args.workbook)
    print(f"\nAll sheets in: {args.workbook}")
    print(f"{'#':>4}  {'Name':<45}  {'Visibility'}")
    print("-" * 65)
    for i, name in enumerate(wb.all_sheet_names, 1):
        vis = wb.sheet_visibility.get(name, "?")
        marker = "  ◀" if any(name.lower() == t.lower() for t in _default_tabs()) else ""
        print(f"{i:>4}  {name:<45}  {vis}{marker}")
    print(f"\nTotal: {len(wb.all_sheet_names)} sheets")
    print(f"Named ranges: {len(wb.named_ranges)}")


def cmd_audit(args):
    """Generate a quick audit CSV — all sheets + named ranges."""
    import csv
    from xlsb_reader import open_workbook_meta
    from config import OUTPUT_DIR

    wb = open_workbook_meta(args.workbook)
    stem = Path(args.workbook).stem

    # Sheets CSV
    sheets_csv = OUTPUT_DIR / f"{stem}_sheets.csv"
    with open(sheets_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Index", "Sheet Name", "Visible Status", "Is Target Tab"])
        target_lower = {t.lower() for t in _default_tabs()}
        for i, name in enumerate(wb.all_sheet_names, 1):
            vis = wb.sheet_visibility.get(name, "Unknown")
            is_target = "YES" if name.lower() in target_lower else ""
            w.writerow([i, name, vis, is_target])
    print(f"Sheets CSV: {sheets_csv}")

    # Named ranges CSV
    nr_csv = OUTPUT_DIR / f"{stem}_named_ranges.csv"
    with open(nr_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Name", "Refers To"])
        for name, ref in wb.named_ranges.items():
            w.writerow([name, ref])
    print(f"Named Ranges CSV: {nr_csv}")


def cmd_reset(args):
    from state_manager import StateManager
    sm = StateManager(args.workbook)
    sm.reset()
    print(f"State reset for: {args.workbook}")


def _default_tabs():
    from config import TARGET_TABS
    return TARGET_TABS


def main():
    parser = argparse.ArgumentParser(
        prog="pva_analyzer",
        description="PVA Workbench Analyzer — Extract field metadata from .xlsb workbooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("workbook", help="Path to .xlsb or .xlsx workbook file")
    parser.add_argument("--template",   default=None,  help="Path to output template .xlsx")
    parser.add_argument("--tabs",       nargs="+",     help="Specific tab names to process (default: all 28 target tabs)")
    parser.add_argument("--no-resume",  action="store_true", help="Re-process all tabs even if already done")
    parser.add_argument("--gsheets",    action="store_true", help="Also write to Google Sheets (requires credentials)")
    parser.add_argument("--list-sheets",action="store_true", help="List all sheet names and exit")
    parser.add_argument("--audit",      action="store_true", help="Generate audit CSVs and exit")
    parser.add_argument("--reset",      action="store_true", help="Reset saved state and exit")

    args = parser.parse_args()

    if not Path(args.workbook).exists():
        print(f"ERROR: File not found: {args.workbook}")
        sys.exit(1)

    if args.list_sheets:
        cmd_list_sheets(args)
    elif args.audit:
        cmd_audit(args)
    elif args.reset:
        cmd_reset(args)
    else:
        cmd_analyze(args)


if __name__ == "__main__":
    main()
