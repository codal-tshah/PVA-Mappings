from pathlib import Path
import re

import pandas as pd


# Update these paths in Colab if needed.
INPUT_DIR = Path("/Users/tshah/Documents/PVA Mappings/gpt_4_improvements_2")
OUTPUT_DIR = Path("/Users/tshah/Documents/PVA Mappings/gemini/colab_csv_2_improvement")


TARGET_CSV_FILES = [
    "Field Inventory.csv",
    "Calculated Fields.csv",
    "Dropdown Values.csv",
    "Field Mapping.csv",
    "Named Ranges.csv",
    "Notes Findings.csv",
    "ShowHide Usage.csv",
    "Tab Inventory.csv",
    "Tab Relationships.csv",
    "WorkbookGraph.csv",
]


DEFAULT_FILTER_RULES = {
    "exact_match": ["N/A"],
    "contains_match": [
        "VeryHidden",
        "Unknown_Field",
        "Choose",
        "column hidden by default",
        "This row hidden by default",
        "Hide",
        "Show",
        "Auto",
        "Yes",
        "No",
        "Sum",
        "All",
    ],
}


CSV_RULES = {
    "Field Inventory.csv": {
        "filter_conditions": {
            "Field Name": DEFAULT_FILTER_RULES,
        },
        "drop_duplicates_on": ["Tab Name", "Field Name", "Named Range", "Input", "Calculated"],
    },
    "Calculated Fields.csv": {
        "filter_conditions": {
            "Field Name": DEFAULT_FILTER_RULES,
        },
        "drop_duplicates_on": ["Tab Name", "Field Name", "Depends On (Source Fields)"],
    },
    "Dropdown Values.csv": {
        "filter_conditions": {
            "Field Name": {
                "exact_match": ["N/A"],
                "contains_match": [
                    "VeryHidden",
                    "Unknown_Field",
                    "Choose",
                    "column hidden by default",
                    "This row hidden by default",
                    "Hide",
                    "Show",
                    "Auto",
                    "Yes",
                    "No",
                    "Sum",
                    "All",
                ],
            }
        },
        "drop_duplicates_on": ["Tab Name", "Field Name", "All dropdown options", "Named ranges"],
    },
    "Field Mapping.csv": {
        "filter_conditions": {
            "Source Field": {
                "exact_match": ["N/A"],
                "contains_match": [
                    "VeryHidden",
                    "Unknown_Field",
                    "Choose",
                    "column hidden by default",
                    "This row hidden by default",
                    "Hide",
                    "Show",
                    "Auto",
                    "Yes",
                    "No",
                    "Sum",
                    "All",
                ],
            }
        },
        "drop_duplicates_on": ["Source Tab", "Source Field", "Used By Tab"],
    },
    "Named Ranges.csv": {
        "filter_conditions": {
            "Named Range": {
                "exact_match": ["N/A"],
                "contains_match": [
                    "Unknown_Field",
                    "VeryHidden",
                    "This row hidden by default",
                ],
            }
        },
        "drop_duplicates_on": ["Named Range", "Sheet", "Start Cell", "End Cell"],
    },
    "Notes Findings.csv": {
        "filter_conditions": {
            "Finding": {
                "exact_match": ["N/A"],
                "contains_match": [
                    "Unknown_Field",
                    "VeryHidden",
                ],
            }
        },
        "drop_duplicates_on": ["Tab Name", "Finding", "Open Question"],
    },
    "ShowHide Usage.csv": {
        "filter_conditions": {
            "Named Range": {
                "exact_match": ["N/A"],
                "contains_match": [
                    "Unknown_Field",
                    "VeryHidden",
                ],
            }
        },
        "drop_duplicates_on": ["Sheet", "Cell", "Named Range"],
    },
    "Tab Inventory.csv": {
        "filter_conditions": {},
        "drop_duplicates_on": ["Tab Name"],
    },
    "Tab Relationships.csv": {
        "filter_conditions": {},
        "drop_duplicates_on": ["Source Tab", "Target Tab", "Relationship Type"],
    },
    "WorkbookGraph.csv": {
        "filter_conditions": {},
        "drop_duplicates_on": ["Source Tab", "Target Tab", "Dependency Type", "Dependency Source"],
    },
}


def normalize_text_series(series: pd.Series, case_sensitive: bool) -> pd.Series:
    values = series.fillna("").astype(str)
    return values if case_sensitive else values.str.lower()


def apply_filters(df: pd.DataFrame, filter_conditions: dict, case_sensitive: bool = False) -> pd.DataFrame:
    if not filter_conditions:
        return df

    rows_to_remove_mask = pd.Series(False, index=df.index)

    for col_name, conditions in filter_conditions.items():
        if col_name not in df.columns:
            print(f"Warning: Column '{col_name}' not found. Skipping filter for this column.")
            continue

        current_col = normalize_text_series(df[col_name], case_sensitive)

        exact_matches = conditions.get("exact_match", [])
        if exact_matches:
            matches = exact_matches if case_sensitive else [value.lower() for value in exact_matches]
            rows_to_remove_mask |= current_col.isin(matches)

        contains_matches = conditions.get("contains_match", [])
        if contains_matches:
            pattern = "|".join(re.escape(value) for value in contains_matches if value)
            if pattern:
                rows_to_remove_mask |= current_col.str.contains(pattern, case=case_sensitive, na=False, regex=True)

    return df[~rows_to_remove_mask].copy()


def drop_duplicates(df: pd.DataFrame, subset: list | None) -> pd.DataFrame:
    if subset:
        missing = [column for column in subset if column not in df.columns]
        if missing:
            print(f"Warning: duplicate subset columns missing: {missing}. Falling back to all columns.")
            return df.drop_duplicates(keep="first")
        return df.drop_duplicates(subset=subset, keep="first")
    return df.drop_duplicates(keep="first")


def clean_csv_file(input_path: Path, output_path: Path, filter_conditions: dict, drop_duplicates_on: list | None = None,
                   case_sensitive: bool = False) -> pd.DataFrame:
    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        print(f"Skipping missing file: {input_path}")
        return pd.DataFrame()
    except Exception as exc:
        print(f"Error loading '{input_path}': {exc}")
        return pd.DataFrame()

    print(f"Loaded {input_path.name} with {len(df)} rows and {len(df.columns)} columns.")

    filtered_df = apply_filters(df, filter_conditions, case_sensitive=case_sensitive)
    print(f"Rows after filtering: {len(filtered_df)}")

    deduped_df = drop_duplicates(filtered_df, drop_duplicates_on)
    print(f"Rows after removing duplicates: {len(deduped_df)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    deduped_df.to_csv(output_path, index=False)
    print(f"Saved cleaned file to: {output_path}")

    return deduped_df


def build_jobs() -> list[dict]:
    jobs = []
    for file_name in TARGET_CSV_FILES:
        config = CSV_RULES.get(file_name, {})
        jobs.append(
            {
                "input_path": INPUT_DIR / file_name,
                "output_path": OUTPUT_DIR / f"{file_name}",
                "filter_conditions": config.get("filter_conditions", {}),
                "drop_duplicates_on": config.get("drop_duplicates_on"),
                "case_sensitive": config.get("case_sensitive", False),
            }
        )
    return jobs


def main():
    print(f"Input folder: {INPUT_DIR}")
    print(f"Output folder: {OUTPUT_DIR}")

    for job in build_jobs():
        clean_csv_file(
            input_path=job["input_path"],
            output_path=job["output_path"],
            filter_conditions=job["filter_conditions"],
            drop_duplicates_on=job["drop_duplicates_on"],
            case_sensitive=job["case_sensitive"],
        )


if __name__ == "__main__":
    main()
