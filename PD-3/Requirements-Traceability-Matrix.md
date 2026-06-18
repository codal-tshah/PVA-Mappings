# Requirements Traceability & Gap Matrix

**Spike:** Define Similarity Score Approach for Comp Search
**Source of truth:** Jira ticket (in spike brief) ↔ `PVA Trial Test.xlsx` → `Sheet1` (requirements matrix)
**Companion:** `Similarity-Score-Approach-Spike.md`
**Date:** 2026-06-11
◊
---

## 1. Jira → Excel FR-ID mapping

The Jira ticket names four "Relevant P0 Requirements." Each is confirmed present in the Excel requirements matrix:

| Jira-named requirement | Excel row | Excel title | Priority | Direct hit? |
|---|---|---|---|---|
| **FR27.1** | `Sheet1!R2` | Unified Comps Database – Sales | P0 – MVP | ✅ Exact |
| **FR27.2.1** | `Sheet1!R3` | Unified Comps Database – Leases | P0 – MVP | ✅ Exact |
| **FR27.2.2** | `Sheet1!R4` | Unified Comps Database – Unit Rents | P0 – MVP | ✅ Exact |
| **FR28.GAP4** | `Sheet1!R17` | Comp Ranking | P0 – MVP | ✅ Exact |

✅ **All four Jira-referenced requirement IDs exist in the Excel file with matching priority (P0).** No naming mismatch or missing ID.

---

## 2. Jira "Expected Output" / "Acceptance Criteria" → spike-document coverage

Every Jira deliverable maps to a section of `Similarity-Score-Approach-Spike.md`:

| Jira expected output / AC | Covered in spike § | Status |
|---|---|---|
| Recommended similarity scoring approach | §3 | ✅ |
| Candidate scoring inputs | §4 | ✅ |
| Filtering vs ranking fields | §5 | ✅ |
| Property-type considerations | §6 | ✅ |
| Comp-type considerations | §7 | ✅ |
| Similarity calculation approach | §3.1, §8 (worked example) | ✅ |
| Storage & auditability approach | §9 | ✅ |
| UI presentation approach | §10 (+ ASCII wireframe) | ✅ |
| Open questions requiring validation | §13 | ✅ |
| POC — example display to end users | §11 + `poc/similarity-results-mockup.html` | ✅ |
| P0 similarity & ranking requirements reviewed | §2.1 | ✅ |

---

## 3. Supporting P0 requirements (implied by Jira scope, present in Excel)

The Jira "Scope" section says to review *Comp Search, Suggested Comps, Ranking, Relevance Score, Similarity Indexation*. These supporting FRs are part of that surface and are reviewed in the spike:

| Excel row | FR ID | Title | Relationship to scoring |
|---|---|---|---|
| R5 | FR27.8 | Comp Search UI – Basic | Hosts results & ranking; <3s perf target |
| R6 | FR28.1 | Search Filter – Property Type | Filter + Property-Type rank input (dual-role) |
| R7 | FR28.2 | Search Filter – Location | Filter + Proximity/Submarket rank inputs (dual-role) |
| R8 | FR28.3 | Search Filter – Size Range | Filter + Size rank input (dual-role) |
| R9 | FR28.7.1 | Additional Filters | Feed filters + Quality/Class, Recency context |
| R10 | FR28.8.1 | Results – List View | Score column; default sort = relevance |
| R11 | FR28.8.2 | Results – Map/Summary View | "Most similar in rank order"; rank-styled pins |
| R12 | FR28.8.3 | Results – Adjustment Grid View | Comps ordered by relevance/recency |
| R13 | FR28.10 | Comp Detail View | Hosts "explain this score" breakdown |
| R14 | FR28.11 | Select Comps for Project | "times used" → feeds Prior-Usage input |
| R15 | FR28.12 | Manual Comp Entry | Manual comps must also be scorable |
| R16 | FR28.14 | Quick Report Generation | Open question: score in client deliverables? |

---

## 4. "Suggested Comps" / "Similarity Indexation" — where it already lives in the spec

The Jira scope calls out *Suggested Comps* and *Similarity Indexation*. These are **not separate FRs** — they are embedded as acceptance criteria inside the database FRs, which is an important traceability finding:

| Embedded requirement | Located in | Exact language |
|---|---|---|
| Suggest comps via algorithm + preset, user-alterable weightings | FR27.1 AC | *"Can suggest comps using basic algorithm and preset weightings that can be altered by the user"* |
| Similarity indexation for lease comps | FR27.2.1 AC | *"Lease comps can be suggested based on algorithm/similarity indexation including location (distance + submarket), quality (class, amenities), size, tenancy, vintage"* |
| Similarity indexation for unit-rent comps | FR27.2.2 AC | *"Rent comps can be suggested based on algorithm/similarity indexation including location, quality, size, vintage, unit mix"* |
| Comp quality + completeness scores | FR27.1 AC ("Ideally") | *"Ideally would create a comp 'Quality Score' and 'Completeness Score'"* |

➡️ **Implication:** the similarity score is a **DB-layer capability surfaced in the UI**, not a UI-only feature. FR28.GAP4 (Ranking) is the *presentation/ordering* of what FR27.1/27.2.x's "similarity indexation" produces.

---

## 5. Gap analysis

| # | Gap | Evidence | Severity | Recommended resolution |
|---|---|---|---|---|
| G1 | **FR28.GAP4 itself is a gap** — no original FR backs the "Rank" step | Excel: *"The process flow has Rank as its own step between Filter and Select, but there is no dedicated FR for ranking"* | High | This spike defines the approach; formalize FR28.GAP4 as a first-class P0 FR. |
| G2 | **Default weight ownership undefined** | No FR specifies who sets per-type default weights | Medium | Appraiser-SME workshop to set default profiles (Open Q#1). |
| G3 | **Submarket definition source undefined** | FR28.2 references "market(s)" but no canonical source | Medium | Decide source (CoStar/RealPage/internal/LightBox) before Submarket sub-score build (Open Q#2). |
| G4 | **FR28.GAP4 ↔ FR32.4 governance undefined** | Excel notes both "could coexist" but no rule | Medium | Stakeholder decision: separate, gated, or blended (Open Q#5). |
| G5 | **Min-completeness "usable" threshold not an FR** | Kickoff note: *"a minimum threshold below which a comp cannot be actively used"* — not captured as a requirement | Medium | Capture as a new FR; define per-type floor (Open Q#6). |
| G6 | **Portfolio multi-subject ranking under-specified** | FR28.GAP4 says "relative to currently selected subject(s)" without rule | Low–Med | Define per-subject vs blended vs user-choice (Open Q#9). |
| G7 | **Lease-structure normalization (NNN/Gross) under-specified** | FR27.2.1 flags it as ambiguity but no normalization rule | Medium | Define effective-rent normalization before lease-comp size/rent sub-scores (§7.2). |
| G8 | **Score disclosure in deliverables undefined** | FR28.14 doesn't say if the score appears in client reports | Low | Default off; explicit opt-in (Open Q#12). |

---

## 6. Coverage summary

- **4/4** Jira-named FRs found in Excel and reviewed. ✅
- **12** supporting FRs identified and reviewed. ✅
- **All 11** Jira Expected-Output/AC items mapped to spike sections. ✅
- **8** gaps identified, each with a recommended resolution and (where relevant) an Open Question reference. ✅

*See `Similarity-Score-Approach-Spike.md` for the full approach and `poc/similarity-results-mockup.html` for the POC.*
