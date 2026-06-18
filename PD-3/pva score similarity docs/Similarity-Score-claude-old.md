# Spike: Define Similarity / Relevance Score Approach for Comparable Property Search

**Project:** PVA (Property Valuation & Appraisal) Platform
**Spike:** *Define Similarity Score Approach for Comp Search*
**Primary requirement:** **FR28.GAP4 — Comp Ranking**
**Related P0 requirements:** FR27.1, FR27.2.1, FR27.2.2 (+ supporting: FR27.8, FR28.1–28.7.1, FR28.8.1–8.3, FR28.10–28.14)
**Status:** Discovery / Design spike — *no production scoring logic.* POC only.
**Date:** 2026-06-11
**Authored as:** Product Architect · Solution Architect · Business Analyst · Senior Engineer (combined lens)

---

## 1. Executive Summary

P0 requires the platform to **rank comparable property records by their relevance to a subject property** so appraisers see the best comps first ("similarity indexation / relevance score"). This spike defines *how that score should be calculated, stored, and presented* across all P0-supported property types and comp types — and surfaces the open questions that need PVA-stakeholder and appraiser validation before build.

**Recommendation in one line:** Adopt a **transparent, configurable weighted-additive relevance score** — `RelevanceScore = Σ (weightᵢ × subScoreᵢ)`, normalized to 0–100 — where each input is a normalized per-criterion sub-score, weights are defaulted per *property-type × comp-type* and are appraiser-adjustable, and **every component of every score is explainable and auditable.**

This model is recommended over opaque distance metrics or machine-learned ranking because comp selection in appraisal is a **regulated, defensible activity (USPAP)**: an appraiser must be able to justify *why* a comp was chosen. A score they can read, decompose, and tune protects that defensibility. Machine-learned "learning-to-rank" is documented as a deliberate **future evolution** (§3.4), not a P0 approach.

Crucially, the score does **not** replace appraiser judgment — it **orders the candidate set** that the appraiser then curates. The workflow is:

> **Search → Filter (hard include/exclude) → RANK (relevance score) → Select (appraiser judgment) → Report**

The single most important design distinction this spike draws (and that the requirements demand) is **filtering vs. ranking**: filters decide *which* comps are eligible; the relevance score decides *what order* eligible comps appear in. The two use overlapping but differently-purposed fields (§5).

---

## 2. Scope & Requirements Reviewed

### 2.1 P0 comp requirements reviewed (from `PVA Trial Test.xlsx`, `Sheet1`)

The 17 P0 comp requirements form a coherent **Search → Filter → Rank → Select → Report** workflow. The four **bold** rows are named directly in the Jira ticket.

| Req ID | Title | Process step | Relevance to this spike |
|---|---|---|---|
| **FR27.1** | **Unified Comps Database – Sales** | Database | Defines the **sale-comp fields** the score reads (incl. per-type "Dynamic Physical attributes"); AC explicitly asks to *"suggest comps using basic algorithm and preset weightings that can be altered by the user."* |
| **FR27.2.1** | **Unified Comps Database – Leases** | Database | AC explicitly requires *"suggested based on algorithm/similarity indexation including location (distance + submarket), quality (class, amenities), size, tenancy, vintage."* |
| **FR27.2.2** | **Unified Comps Database – Unit Rents** | Database | AC requires per-unit-type similarity (location, quality, size, vintage, **unit mix**) for MF / MHC / self-storage / seniors / student housing. |
| **FR28.GAP4** | **Comp Ranking** | **Rank** | **Core requirement.** Composite *relevance score*; configurable criteria (proximity, recency, size, type, completeness, prior usage); default rank + re-sort + drag-reorder; persists per project/session; re-ranks on subject change. |
| FR27.8 | Comp Search UI – Basic | Search | Search surface that hosts results & ranking; <3s performance target. |
| FR28.1 | Search Filter – Property Type | Filter | Hierarchical multi-select type/subtype — a **filter** *and* a rank input. |
| FR28.2 | Search Filter – Location | Filter | Radius / polygon / state / market — **filter** *and* source of proximity & submarket rank inputs. |
| FR28.3 | Search Filter – Size Range | Filter | Size range — **filter**; size *closeness* is a rank input. |
| FR28.7.1 | Additional Filters | Filter | Year built, class, cap rate, $/SF, status, rights, occupancy, etc. — feed both filters and several sub-scores. |
| FR28.8.1 | Results – List View | Results | Sortable list; default sort = relevance; shows score column. |
| FR28.8.2 | Results – Map / Summary View | Results | Split map + summary; *"most similar comps displayed in rank order."* |
| FR28.8.3 | Results – Adjustment Grid View | Results | Comps as columns; default left-to-right ordering relates to rank/recency. |
| FR28.10 | Comp Detail View | Detail | Detail panel can host the per-criterion score breakdown ("explain this score"). |
| FR28.11 | Select Comps for Project | Select | Selection follows ranking; snapshots comp data; increments "times used" (feeds *Prior Usage* input). |
| FR28.12 | Manual Comp Entry | Manual | Manually entered comps must also be scorable. |
| FR28.14 | Quick Report Generation | Report | Whether the relevance score appears in client deliverables is an open question (§13). |

### 2.2 In scope for this spike
Defining: the scoring model, candidate inputs, filter-vs-rank split, per-property-type and per-comp-type considerations, the calculation method, storage/auditability model, UI presentation, a worked POC, and the open questions for validation.

### 2.3 Out of scope (explicit)
Production scoring engine, real geocoding/submarket integration, live DB schema migration, ML model training, and wiring the POC to real data. These are named as follow-on epics with rough estimates in §14.

---

## 3. Recommended Approach — Transparent Weighted-Additive Relevance Score

### 3.1 The model

For a given **subject property** *S*, a **candidate comp** *C*, and an active **weight profile** *W*:

```
RelevanceScore(S, C, W) = 100 × Σ ( wᵢ × subScoreᵢ(S, C) )   for i in active criteria
                          ─────────────────────────────────
                                    Σ wᵢ  (active criteria only)
```

- Each **`subScoreᵢ(S, C) ∈ [0, 1]`** is produced by a defined, documented per-criterion function (§4).
- Each **`wᵢ ≥ 0`**; weights are defined as a **profile** that defaults per *property-type × comp-type* and is **appraiser-adjustable** (FR28.GAP4 "configurable", FR27.1 "preset weightings that can be altered by the user").
- Result is normalized to a **0–100 score** (presented as a ★ badge), making it comparable across searches.

### 3.2 Why weighted-additive (the recommendation)

| Criterion | Weighted-additive (recommended) | Pure distance metric (e.g. raw Gower) | ML learning-to-rank |
|---|---|---|---|
| **Explainability** | ✅ Each term visible & attributable | ⚠️ Single opaque distance | ❌ Black box |
| **USPAP defensibility** | ✅ Appraiser can justify each comp | ⚠️ Hard to narrate | ❌ Very hard to defend |
| **Appraiser tunability** | ✅ Adjust weights, see effect live | ⚠️ Limited | ❌ Requires retraining |
| **Maps to existing mental model** | ✅ Mirrors the adjustment grid | ⚠️ Partial | ❌ No |
| **Cold-start (no history)** | ✅ Works on day 1 | ✅ Works on day 1 | ❌ Needs training data |
| **Implementation cost (P0)** | ✅ Low–moderate | ✅ Low | ❌ High |
| **Captures non-linear interactions** | ⚠️ Only if engineered | ⚠️ Limited | ✅ Yes |

The appraisal domain already reasons in *additive adjustment grids* — the workbench's **Land Valuation** tab literally has one adjustment row per element (Rights, Financing, Conditions, Market/time, **Location**, **Size**, Shape, Topography, Utilities, **Zoning/Density**), and **Improvements** carries **Quality (A/B/C)** and **Condition**. A weighted-additive relevance score is the same shape of reasoning applied *before* adjustment — it is intuitive, teachable, and defensible.

> **Note (Gower):** We still borrow Gower's idea of **per-attribute normalization for mixed data types** (continuous, ordinal, categorical, set) — each `subScoreᵢ` is effectively a Gower-style per-attribute similarity. The recommendation is "weighted-additive *over Gower-style normalized sub-scores*," combining the explainability of additive weighting with principled mixed-type handling.

### 3.3 Missing-data handling (important, often overlooked)

Comp data completeness varies by source. The model must **not silently treat a missing field as a zero sub-score** (that would unfairly bury good-but-sparsely-documented comps). Recommended rule:

1. If an input field is **missing**, drop that criterion from the active set and **re-normalize** the remaining weights (the denominator `Σ wᵢ` is over *active* criteria only).
2. Separately compute a **Data-Completeness sub-score** and (a) use it as a **secondary tie-breaker**, and (b) **surface it in the UI** so the appraiser knows a high score was computed on thinner evidence.
3. Configurable floor (open question §13): below some completeness threshold a comp may be **flagged "insufficient to rank"** rather than scored — echoing the kickoff note *"a minimum threshold below which a comp cannot be actively used."*

### 3.4 Documented future evolution (not P0)

Once a corpus of **historical comp-selection decisions** exists (which comps appraisers actually kept vs. discarded, per FR28.11's "times used" + de-selection notes), a **learning-to-rank** model could *suggest* weight profiles or re-rank within the transparent envelope. This is explicitly deferred because of: (a) cold-start (no data on day 1), (b) explainability/defensibility risk, and (c) **feedback-loop bias** (the model learns to prefer what was historically chosen, entrenching habits). If pursued, keep the transparent score as the **system of record** and treat ML as an *advisory overlay*.

---

## 4. Candidate Scoring Inputs

The nine inputs below are the union of the Jira-listed candidate inputs and the FR27.2.1 / FR27.2.2 "similarity indexation" language. For each: the **source field(s)** in the comps DB, the **sub-score function**, an **illustrative default weight** (MF sale-comp profile), and notes.

| # | Input | Source field(s) (FR27.1/2.x) | Sub-score function (→ [0,1]) | Illustrative default weight | Notes |
|---|---|---|---|---|---|
| 1 | **Proximity** | `latitude/longitude` (geocoded) | Distance decay: `max(0, 1 − d/d_max)` or exponential `e^(−d/h)` (h = half-distance) | **0.25** | Haversine on stored lat/long. `d_max`/`h` configurable per market density (urban vs rural). |
| 2 | **Submarket** | submarket / MSA (source TBD) | Categorical: exact submarket = 1.0; adjacent = 0.5; same MSA = 0.25; else 0 | **0.10** | Complements proximity (two comps equidistant can be in different submarkets). Submarket source is an open question (§13). |
| 3 | **Property Type / Subtype** | `property_type`, `property_subtype`, `tag(s)` | Hierarchical: exact subtype = 1.0; same type/other subtype = 0.7; adjacent type = 0.3; else 0 | **0.15** | Type is usually also a *filter*; sub-score handles within-filter subtype closeness. |
| 4 | **Size** | type-appropriate metric (see §6) | Ratio closeness: `1 − min(1, |ln(C_size / S_size)|)` or tolerance band | **0.20** | Metric switches by type: **units** (MF), **SF** (office/industrial/retail), **keys** (hotel), **sites** (MHC), **NRSF** (self-storage). |
| 5 | **Recency** | `sale_date` / `lease_date` vs effective date | Time decay: ≤6 mo = 1.0 → linear/exp decay → 0 at 24–36 mo | **0.15** | Horizon is market-condition sensitive; configurable. For sales, recency ≈ "market conditions" adjustment. |
| 6 | **Quality / Class** | `quality` (A/B/C), `condition` (Excellent…Poor) | Ordinal distance: `1 − classGap/maxGap` | **0.05** | Maps to Improvements tab fields. For office/industrial, class is highly material. |
| 7 | **Amenities** | project/unit amenity rating, amenity set | Jaccard overlap of amenity set, or rating proximity | **0.05** | Strongest signal for MF/seniors; near-irrelevant for land. |
| 8 | **Data Completeness** | meta: % decision fields populated | `populated / expected` for the type | **0.03** (tie-breaker) | Kept **distinct** from FR32.4 quality score; secondary by design (§3.3). |
| 9 | **Prior Usage** | `times_used`, usage history (FR28.11) | Bounded boost: `min(1, usesInSimilarContext / k)` | **0.02** | Small by design; **flagged for feedback-loop/circularity risk** — recommend optional/off by default in regulated work. |

> Weights above sum to 1.00 and are **illustrative defaults for an MF sale comp**. Each property-type × comp-type pairing gets its own default profile (§6, §7), and appraisers can override (with the override audited, §9).

---

## 5. Filtering vs. Ranking Fields

This is the central design distinction the requirements ask us to make explicit.

- **Filter = hard constraint (binary include/exclude).** Defines *which* comps are eligible. A comp failing a filter does not appear. (FR28.1, FR28.2, FR28.3, FR28.7.1)
- **Rank = soft relevance (continuous).** Orders *eligible* comps by similarity to the subject. (FR28.GAP4)

| Field | Filter? | Rank input? | Role |
|---|---|---|---|
| Property type / subtype | ✅ | ✅ | Filter to selected types; rank by subtype closeness. **Dual-role.** |
| Location – radius / polygon / state / market | ✅ | — | Hard geographic bound. |
| Location – exact distance | — | ✅ (Proximity) | Distance *within* the bound drives proximity sub-score. **Dual-role with above.** |
| Submarket | ✅ (optional) | ✅ | Can constrain *and* rank. |
| Size range | ✅ | — | Hard min/max bound. |
| Size closeness to subject | — | ✅ (Size) | Closeness *within* the range drives the sub-score. **Dual-role.** |
| Date range | ✅ | — | Hard recency bound. |
| Recency (time decay) | — | ✅ (Recency) | Closeness in time drives sub-score. **Dual-role with date range.** |
| Year built range | ✅ | (✅ via vintage) | Primarily filter; vintage can inform quality/recency context. |
| Building class (A/B/C) | ✅ (optional) | ✅ (Quality) | Either constrain or rank. |
| Sale/lease status, property rights | ✅ | — | Eligibility constraints (e.g., closed sales only, fee simple only). |
| Cap rate / $-per-unit / $/SF / occupancy ranges | ✅ | — | Eligibility constraints; *not* relevance (they're outcomes, not similarity). |
| Amenities | (optional filter) | ✅ | Usually a rank input. |
| Data completeness | ✅ (optional floor) | ✅ (secondary) | Optional eligibility floor + tie-breaker. |
| Prior usage | — | ✅ (optional) | Rank-only, optional. |

**Design rules of thumb:**
1. **Eligibility facts** (status, rights, hard geography, hard size/date bounds) → **filters**.
2. **Closeness-to-subject facts** (distance, size delta, time delta, type/subtype, quality, amenities) → **rank inputs**.
3. A field can be **both** (location, size, type, date) — the *range* filters, the *closeness within range* ranks. The UI must make this dual role obvious (§10).

---

## 6. Property-Type Considerations

The score must adapt per property type — both the **size metric** and the **dominant inputs** differ. Default weight profiles should reflect this (illustrative emphases below; exact defaults are an open question for appraiser SMEs, §13).

| Property type | Primary size metric | Inputs that dominate | Type-specific signals (from FR27.1 "Dynamic Physical attributes") |
|---|---|---|---|
| **Multi-Family** | # units | Proximity, Submarket, Size (units), **Unit mix**, Amenities | Avg unit size, avg rent/unit/mo, project & unit amenity rating, GIM |
| **Office** | Building SF | **Class (A/B/C)**, Proximity (CBD vs suburban), Size, Tenant credit | Parking, tenant name/type, tenant credit rating |
| **Industrial** | Building SF | **Clear height**, **Dock doors**, FAR, Size | Functional utility dominates; location less so |
| **Retail** | Building SF (GLA) | Tenant/anchor type, Demographics, Proximity | Tenant name/type, parking, median HH income, population density |
| **Hospitality / Lodging** | # keys/rooms | Competitive set, Service tier/flag, ADR/RevPAR | Occupancy, ADR, RevPAR, rooms-revenue multiplier (proximity less central) |
| **Self-Storage** | NRSF | % climate-controlled, Occupancy, Proximity | Ground vs upper, interior/exterior, CC/non-CC |
| **Seniors Housing** | # units/beds | Care level, % private pay, Occupancy | Private vs public pay, care levels & fees, entrance fees |
| **Manufactured Housing (MHC)** | # sites/pads | % community-owned homes, Size (sites), Proximity | COH vs resident-owned, single/double-wide, avg rent/site |
| **Land** | Acres / Land SF | **Zoning/density**, Size, Topography, Utilities, Access | Mirrors the **Land Valuation** adjustment grid exactly |

**Cross-type ranking** (e.g., comparing MF against Senior Housing) should generally be *prevented by the type filter*; if allowed, the Property-Type sub-score (§4 #3) downweights adjacent types. Whether adjacency is permitted at all is an open question (§13).

---

## 7. Comp-Type Considerations

The three comp types in the requirements (FR27.1 / FR27.2.1 / FR27.2.2) need different sub-score emphases and a few type-specific normalizations.

### 7.1 Sale comps (FR27.1)
- **Emphasize:** Recency (≈ market conditions), Proximity, Size, Property rights, Conditions of sale (arm's length).
- **Normalize:** Compare on the **price-per-unit-of-comparison** appropriate to the type (the workbook's "Subject Unit of Comparison": Unit/SF/Room/Bed/Key). Cap-rate proximity may be an *eligibility filter* rather than a relevance input (it's an outcome).
- **Watch:** Exclude or down-rank non-arm's-length / distressed unless explicitly sought (status filter).

### 7.2 Commercial lease comps (FR27.2.1)
- **Emphasize:** Tenant credit, Space SF, Lease date (recency), Submarket, Class.
- **Normalize:** **Lease structure matters** — NNN vs Gross vs Modified Gross must be normalized to a comparable **effective rent** before size/rent closeness is meaningful (the FR flags this gap explicitly). Concessions (free rent, TI, LCs) feed the effective-rent normalization, not the relevance score directly.
- **Watch:** First-generation vs second-generation space; lease vs sublease.

### 7.3 Unit-rent comps (FR27.2.2)
- **Emphasize:** **Unit-type-level matching** (Studio / 1BR / 2BR / 3BR…), Submarket, Amenities, Occupancy, Size (# units / # floors).
- **Normalize:** Analyze rent **per unit type** and conclude premiums per floor plan, then **blend** to market/gross-potential rent (per FR27.2.2 AC). Affordability (% AMI) is a strong eligibility filter for affordable deals.
- **Watch:** Self-storage / seniors / MHC have their own unit taxonomies (CC vs non-CC; care level; COH vs resident-owned) — the unit-type match sub-score must use the type's taxonomy.

---

## 8. Similarity Calculation Approach (worked example)

**Subject (S):** 20800 Homestead Road, Cupertino CA — Multi-Family, 248 units, built 2019. *(workbook sample subject, v46.02.9)*
**Comp (C):** 1234 Main St — Multi-Family, 210 units, built 2017, sold 5 months ago, 0.4 mi away, same submarket, Class B (subject Class B), strong amenity overlap, 92% fields populated.
**Weight profile (W):** MF sale-comp defaults from §4.

| Input | Raw inputs | subScore | weight | weight × subScore |
|---|---|---|---|---|
| Proximity | 0.4 mi (d_max 5 mi) | 0.95 | 0.25 | 0.2375 |
| Size | 210 vs 248 units | 0.88 | 0.20 | 0.1760 |
| Recency | 5 months | 0.90 | 0.15 | 0.1350 |
| Property type | exact MF subtype | 1.00 | 0.15 | 0.1500 |
| Submarket | exact match | 1.00 | 0.10 | 0.1000 |
| Quality/Class | Class B vs B | 1.00 | 0.05 | 0.0500 |
| Amenities | high overlap | 0.85 | 0.05 | 0.0425 |
| Completeness | 92% populated | 0.92 | 0.03 | 0.0276 |
| Prior usage | used 1× similar | 0.20 | 0.02 | 0.0040 |
| **Σ** | | | **1.00** | **0.9226** |

`RelevanceScore = 100 × 0.9226 / 1.00 = ` **92 / 100 → ★ 92**

If, say, **submarket were missing**, criterion #2 drops out; the denominator becomes `0.90`, and the score is recomputed over the remaining eight criteria (re-normalized), with the **completeness sub-score** signalling the thinner evidence in the UI.

This worked example is exactly what the **POC** renders (§11) and what the "**explain this score**" panel shows the appraiser — every term, fully decomposed.

---

## 9. Storage & Auditability

**Core principle:** a relevance score is **not an attribute of a property** — it is **relative to `(subject, candidate, weight-profile, point-in-time, algorithm-version)`**. Storing it as a single column on a comp record would be wrong (it would be meaningless without its subject + weights). Recommended storage shape:

```
comp_relevance_score
├─ id
├─ project_id            (FK)            -- scopes to the appraisal
├─ subject_property_id   (FK)            -- the "relative to" anchor
├─ comp_event_id         (FK)            -- the candidate (sale/lease/unit-rent EVENT, not just property)
├─ weight_profile_id     (FK)            -- which profile (default vs user-overridden)
├─ composite_score       (0–100)
├─ sub_scores            (JSON)          -- {proximity:0.95, size:0.88, ...} for "explain this score"
├─ sub_score_inputs      (JSON)          -- raw inputs used (distance, deltas) for full audit
├─ algorithm_version     (string)        -- e.g. "relscore-v1.0" for reproducibility
├─ manual_rank_override   (int, nullable) -- drag-and-drop reorder position
├─ override_reason        (text, nullable)
├─ computed_at           (timestamp)
└─ computed_by           (user)
```

**What to persist and why:**
- **Subject-context snapshot + weight profile used** → the score is reproducible and explainable later (USPAP workfile defensibility).
- **Per-criterion sub-scores + raw inputs** → powers the "explain this score" UI and audit.
- **`algorithm_version`** → if the scoring functions change, historical scores remain interpretable; old appraisals don't silently shift.
- **Manual reorder + reason** → FR28.GAP4 requires drag-and-drop reorder; the override and its rationale must be auditable (an appraiser overriding the machine is a defensible, recorded act).
- **Recompute triggers** → score is recomputed when the **subject context changes** (FR28.GAP4 AC) or the weight profile changes; cache results to meet the **<3s** target (FR27.8).
- **Event-centric, not property-centric scoring** → consistent with the kickoff "property is the entity, sales/leases/valuations are events" model — we score the **event** (a specific sale/lease) against the subject.
- **Field-level source attribution preserved** → the kickoff requires every field to carry its source; sub-score inputs should reference that provenance.
- **Keep distinct from FR32.4** → the *quality* score lives in its own structure; relevance and quality are different columns/tables with different purposes (see Appendix).

**Persistence scope:** ranking + manual reorder persist **per project/session** (FR28.GAP4 AC), so an appraiser returning to a project sees the same order they left.

---

## 10. UI Presentation

### 10.1 Principles
1. **Default sort = relevance, descending** (FR28.GAP4, FR28.8.2).
2. **Score is always visible** — a ★ 0–100 badge per comp in **all three result views** (List / Map+Summary / Adjustment Grid).
3. **Explainable on demand** — "explain this score" expands the per-criterion `Σ wᵢ × subScoreᵢ` breakdown (the §8 table) so the appraiser sees *why*.
4. **Re-sortable & overridable** — re-sort by any single criterion, cascade multi-sort ("first by price, then size" — FR28.8.2), and **drag-and-drop / up-down reorder** (FR28.GAP4); overrides are flagged + audited.
5. **Weights are adjustable in-context** — a weight-profile control (sliders or preset picker by property type) that **re-ranks live**, with a "reset to default" affordance.
6. **Context comparison** — show selected-vs-non-selected-vs-overall metric averages (FR28.8.1/8.2 AC).

### 10.2 ASCII wireframe (List + Map split view; see POC for interactive version)

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ SUBJECT: 20800 Homestead Road, Cupertino CA   ·  Multi-Family · 248 units · built 2019      │
│ Weight profile: [ MF · Sale Comps ▼ ]   Prox .25  Size .20  Recency .15  Type .15  …  [Reset]│
│ [ List ] [ Map+Summary ] [ Adjustment Grid ]            347 eligible · ranked by Relevance ▼ │
├───────────────────────────────────────┬───────────────────────────────────────────────────┤
│  RESULTS (sorted by ★ Relevance)       │  MAP                                              │
│ ┌───────────────────────────────────┐ │     · ·    (1)        rank-styled pins             │
│ │ #1  ★92  1234 Main St   0.4 mi  ☐ │ │   (3)   (1)                                        │
│ │     MF · 210 u · 2019 · $42.5M    │ │       (2)        ·  ·                               │
│ │     [Prox 95][Size 88][Rec 90]    │ │   ·        (4)          ·                           │
│ │     [Type 100][Submkt 100]  ▸expl │ │             ·     ·                                 │
│ ├───────────────────────────────────┤ │                                                   │
│ │ #2  ★87  88 Oak Ave     1.1 mi  ☐ │ │  ── "explain this score" (expanded) ──────────    │
│ │     MF · 230 u · 2017 · $36.0M    │ │   Relevance = Σ wᵢ × subScoreᵢ                     │
│ │     [Prox 82][Size 95][Rec 88] ▸  │ │   proximity   0.25 × 0.95 = 0.2375                 │
│ ├───────────────────────────────────┤ │   size        0.20 × 0.88 = 0.1760                 │
│ │ #3  ★81  …                        │ │   recency     0.15 × 0.90 = 0.1350                 │
│ │ #4  ★78  …  (drag ⇅ to reorder)   │ │   …                       = … → ★92                 │
│ └───────────────────────────────────┘ │                                                   │
│  Selected avg $/u $176k · non-sel $171k · overall $173k                                     │
└───────────────────────────────────────┴───────────────────────────────────────────────────┘
        [POC / illustrative — not production scoring]
```

### 10.3 View-specific notes
- **List view (FR28.8.1):** Relevance is a sortable column; per-criterion mini-badges inline; drag-handle for reorder.
- **Map+Summary (FR28.8.2):** Pins styled/numbered by rank; "most similar in rank order" in the summary rail.
- **Adjustment Grid (FR28.8.3):** Comps as columns ordered left→right by relevance (or sale date); the score shown in the header row; appraiser can hide it when it shouldn't appear in the deliverable.

---

## 11. POC

A standalone, dependency-free **interactive HTML mockup** accompanies this document:

> **`comp-similarity-spike/poc/similarity-results-mockup.html`** — open in any browser.

It demonstrates how final similarity results display to end users, using the Cupertino MF sample subject:
- Ranked results list with **★ composite score badges** and per-criterion mini-badges.
- **"Explain this score"** expandable panel showing the full `Σ wᵢ × subScoreᵢ` decomposition (the §8 table).
- **Weight-profile sliders** that **visibly re-rank** the list as you drag them (client-side, illustrative).
- A **map placeholder** with rank-styled pins and **List / Map / Adjustment-Grid** view toggles.
- Prominent **"POC / illustrative — not production scoring"** labelling.

The ASCII wireframe in §10.2 mirrors the same layout for readers without a browser.

---

## 12. Assumptions, Risks & Mitigations

### 12.1 Assumptions
- The **property-centric data model** (property = entity; sale/lease/valuation = events) is the storage substrate (kickoff Day 1–2).
- Comps carry **geocoded lat/long** (FR28.2 radius search requires it).
- **Field-level source attribution** exists and is queryable (kickoff).
- A **"Subject Unit of Comparison"** is set per file (workbook Settings: Unit/SF/Room/Bed/Key) and drives the size metric.

### 12.2 Risks & mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| **Opaque scoring undermines USPAP defensibility** | Appraiser can't justify comp choice | Transparent weighted-additive + "explain this score" + audited overrides (§3, §9, §10). |
| **Feedback-loop bias** from Prior-Usage input | Entrenches past habits, hides novel comps | Keep Prior-Usage weight tiny & optional; off by default in regulated work (§4 #9). |
| **Missing/uneven data** scores good comps poorly | Quality comps buried | Re-normalize over available criteria + surface completeness (§3.3). |
| **Bad geocoding / submarket data** | Two of the strongest signals degrade | Validate geocoding; treat submarket as optional until source is defined (§13). |
| **Weight defaults wrong for a property type** | Poor default ranking, low trust | Defaults owned by appraiser SMEs per type; easy override + reset (§6, §13). |
| **Confusion between relevance score & FR32.4 quality score** | Mis-trust, double-counting | Keep separate stores, separate UI semantics; document the distinction (Appendix). |
| **Score leaks into client deliverables unintentionally** | Disclosure / liability | Make inclusion in reports an explicit, off-by-default choice (§13, FR28.14). |

---

## 13. Open Questions for PVA Validation

These need answers from PVA stakeholders / appraiser SMEs before build:

1. **Default weight profiles** — Who owns the canonical defaults per *property-type × comp-type*? What are the starting values? (Appraiser SME workshop.)
2. **Submarket definition source** — CoStar? RealPage? Internal polygons? LightBox? The Submarket sub-score depends on it.
3. **Recency decay** — Curve shape and horizon (e.g., 0 at 24 vs 36 months)? Should it flex by market conditions / property type?
4. **Prior-Usage input** — Include it at all in regulated work, given circularity risk? Default on or off?
5. **FR28.GAP4 ↔ FR32.4 governance** — Combined display? Should a minimum *quality* score gate whether a comp is *rankable*? Two scores side-by-side or one blended?
6. **Minimum completeness threshold** — Is there a floor below which a comp is "insufficient to rank / not actively usable" (kickoff note)? What is it per type?
7. **Weight-profile scope & permissions** — Per-user vs per-company profiles? Who may override? Is an override a recorded USPAP workfile element?
8. **Cross-/adjacent-type ranking** — Allowed at all (e.g., MF vs Seniors)? If so, what adjacency map?
9. **Portfolio subjects** — When a project has multiple subjects, rank relative to which subject (per-subject, blended, or user-chosen)? (FR28.GAP4 "rank relative to currently selected subject(s)".)
10. **Geocoding** — Source & accuracy SLA; how to handle comps lacking lat/long (exclude from proximity? neutral sub-score?).
11. **Performance/scale** — DB size, concurrency, and caching strategy to hold the **<3s** target (FR27.8) as the comp corpus grows.
12. **Deliverable disclosure** — Should the relevance score ever appear in client-facing Quick Reports (FR28.14)? Default behavior?

---

## 14. High-Level Estimation

> Spike output is a *definition*; the numbers below size the **follow-on implementation** so the team can plan. T-shirt sizing + indicative story-point ranges (team-relative). Not commitments.

| Epic / work item | Depends on | Size | Pts (range) |
|---|---|---|---|
| Comps DB fields to support scoring inputs (per-type dynamic attrs, geocode, completeness meta) | FR27.1/2.x | M | 8–13 |
| Geocoding pipeline + distance/proximity computation | FR28.2 | M | 8–13 |
| Submarket data integration & mapping | Q#2 resolved | M–L | 13–21 |
| Relevance scoring engine (sub-score functions + weighted-additive + missing-data normalization, versioned) | inputs ready | L | 13–21 |
| Weight-profile config (defaults per type, user override, persistence) | engine | M | 8–13 |
| Storage & audit model (`comp_relevance_score`, recompute triggers, caching) | engine | M | 8–13 |
| Results UI: score badges, default rank, re-sort/cascade/drag-reorder across List/Map/Grid | engine + FR28.8.x | L | 13–21 |
| "Explain this score" breakdown panel | engine | S–M | 5–8 |
| POC → production hardening of the mockup | this spike | M | 8–13 |
| **Remaining spike effort** (this doc done; SME validation workshop + finalize defaults) | — | S | 3–5 |

**Suggested sequencing:** DB fields → geocoding → scoring engine → weight config + storage → UI → explainability. Submarket integration can run in parallel and plug in when ready (its sub-score is independently weightable).

---

## 15. Appendix

### 15.1 Relevance score (FR28.GAP4) vs. Quality score (FR32.4)
| | **FR28.GAP4 — Relevance** | **FR32.4 — Quality (P2)** |
|---|---|---|
| Question answered | "How *similar* is this comp to **this subject**?" | "How *good/complete/verified* is this comp record?" |
| Relative to | A specific subject + weight profile | The comp itself (absolute) |
| Changes when | Subject or weights change | Underlying data quality changes |
| P0? | ✅ Yes (this spike) | ❌ P2 |
| Recommendation | System of record for ranking | Optional eligibility floor + secondary signal; **do not blend** without explicit stakeholder decision (Q#5). |

### 15.2 LightBox reference note
The reference link provided (`lightbox.vc`) is a venture-capital firm; the property-data company is **LightBox (lightboxre.com)**. LightBox is used here only as a *directional* reference for how commercial-property platforms surface ranked/scored comps. This recommendation is grounded in the **PVA requirements themselves** (FR28.GAP4, FR27.x) and the workbench's existing adjustment-grid model — the workbench already integrates a **LightBox API** (config/enumerations/dictionary tabs) plus a **Comp Prompt (AI)** tab and **tblFuzzyMatch**, which are natural touch-points for sourcing/deduping the comps the score ranks.

### 15.3 Glossary
- **Comp / comparable** — a property *event* (sale, lease, or unit-rent) used as evidence of value.
- **Relevance / similarity score** — 0–100 measure of how similar a comp is to the subject, for ranking.
- **Weight profile** — the set of per-criterion weights, defaulted per property-type × comp-type, appraiser-adjustable.
- **Sub-score** — a single criterion's normalized [0,1] similarity (proximity, size, recency, …).
- **Subject** — the property being appraised; the anchor all relevance is measured against.
- **USPAP** — Uniform Standards of Professional Appraisal Practice; the reason explainability/auditability are non-negotiable.

---

*End of spike document. Companion files: `poc/similarity-results-mockup.html` (interactive POC) · `Requirements-Traceability-Matrix.md` (Jira → FR mapping).*
