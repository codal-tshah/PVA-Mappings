# Workbook Documentation.xlsx

## Sheet 1: Tab Inventory

Purpose: High-level understanding of each tab.

| Tab Name | Category | Purpose | Input / Calc / Output | Notes |
| -------- | -------- | ------- | --------------------- | ----- |

### Example

| Tab Name            | Category         | Purpose                   | Input / Calc / Output | Notes            |
| ------------------- | ---------------- | ------------------------- | --------------------- | ---------------- |
| File Info           | Setup            | Subject property details  | Input                 | Starting point   |
| Site                | Property Data    | Site characteristics      | Input                 | User entered     |
| Sales Grid          | Comparable Data  | Sales comps               | Input + Calc          | Imported via API |
| Sales Approach      | Valuation        | Sales comparison analysis | Calc                  | Uses Sales Grid  |
| DirectCapConclusion | Valuation Output | Final value conclusion    | Output                | End result       |

---

## Sheet 2: Field Inventory

Purpose: Main deliverable for the spike.

| Tab Name | Field Name | Input | Calculated | Dropdown | Data Type | Notes |

 Tab Name  Field Name  Input  Calculated  Dropdown  Data Type  Notes 
| -------- | ---------- | ----- | ---------- | -------- | --------- | ----- |

### Example

| Tab Name        | Field Name    | Input | Calculated | Dropdown | Data Type | Notes                 |
| --------------- | ------------- | ----- | ---------- | -------- | --------- | --------------------- |
| File Info       | Property Name | Yes   | No         | No       | Text      | User entered          |
| File Info       | Property Type | Yes   | No         | Yes      | Text      | Drives template logic |
| Site            | Site Area     | Yes   | No         | No       | Number    | Acres / SF            |
| Income Approach | NOI           | No    | Yes        | No       | Currency  | Calculated value      |

---

## Sheet 3: Field Mapping

Purpose: Show where a field is used.

| Source Tab | Source Field | Used By Tab | Used For |
| ---------- | ------------ | ----------- | -------- |
Source Tab Source Field Used By Tab Used For

### Example

| Source Tab      | Source Field  | Used By Tab         | Used For               |
| --------------- | ------------- | ------------------- | ---------------------- |
| File Info       | Property Type | Market Rent         | Property filtering     |
| Site            | Site Area     | Land Valuation      | Land value calculation |
| Income Approach | NOI           | DirectCapConclusion | Final valuation        |

---

## Sheet 4: Dropdown Values

Purpose: Capture all dropdown options.

| Tab Name | Field Name | Dropdown Values |
| -------- | ---------- | --------------- |

### Example

| Tab Name  | Field Name      | Dropdown Values                         |
| --------- | --------------- | --------------------------------------- |
| File Info | Property Type   | Office, Retail, Industrial, Multifamily |
| Scope     | Assignment Type | Full, Restricted                        |

---

## Sheet 5: Calculated Fields

Purpose: Capture important business calculations only.

| Tab Name | Field Name | Formula Logic | Depends On |
| -------- | ---------- | ------------- | ---------- |

### Example

| Tab Name            | Field Name          | Formula Logic            | Depends On        |
| ------------------- | ------------------- | ------------------------ | ----------------- |
| Sales Approach      | Adjusted Sale Price | Sale Price + Adjustments | Sale Price        |
| Income Approach     | NOI                 | Revenue - Expenses       | Revenue, Expenses |
| DirectCapConclusion | Value               | NOI / Cap Rate           | NOI, Cap Rate     |

---

## Sheet 6: Tab Relationships

Purpose: Show workflow between tabs.

| Source Tab | Target Tab | Relationship |
| ---------- | ---------- | ------------ |

### Example

| Source Tab      | Target Tab          | Relationship        |
| --------------- | ------------------- | ------------------- |
| File Info       | Site                | Property setup      |
| Site            | Land Valuation      | Input data          |
| Sales Grid      | Sales Approach      | Comparable analysis |
| Income Approach | DirectCapConclusion | Valuation output    |

---

## Sheet 7: Notes / Findings

Purpose: Capture discoveries during analysis.

| Tab Name | Finding | Open Question |
| -------- | ------- | ------------- |

### Example

| Tab Name    | Finding                            | Open Question                    |
| ----------- | ---------------------------------- | -------------------------------- |
| Sales Grid  | Data imported through Lightbox API | Is manual entry supported?       |
| Market Rent | Uses Property Type extensively     | Which dropdown values are valid? |
| }           |                                    |                                  |
