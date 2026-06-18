# Spike Report — Define Similarity Score Approach for Comp Search

## Background

| Field | Detail |
|---|---|
| **Spike Name** | Define Similarity Score Approach for Comp Search — how a comparable-property *relevance / similarity score* should be calculated, stored, and presented across all P0 property types and comp types. |
| **Conducted by** | _<your name>_ (mitul.s@shaip.com) |
| **Backlog Ticket** | _<link to JIRA spike ticket>_ |
| **Sprint & Date** | _<sprint>_ · _<date>_ |
| **Primary requirement** | **FR28.GAP4 — Comp Ranking** |
| **Related P0 requirements** | FR27.1, FR27.2.1, FR27.2.2 (+ supporting FR27.8, FR28.1–FR28.14) |
| **Status** | Discovery / design spike — **no production scoring logic**. POC display only. |

**One-line summary:** P0 requires the platform to rank comparable records by their relevance to a subject property. This spike recommends a **hybrid comp search** (hard filters → transparent weighted score → appraiser selection) built on a **Universal Core + Property-Type Bonus Layer** scoring model, and defines how that score is calculated, stored, and shown to appraisers — plus the open questions that need PVA/appraiser validation before build.

---

## Spike Details

### Spike Goals / Objectives

This spike answers, for **all P0-supported property types and comp types**:

1. *How should the similarity / relevance score be calculated?* (the algorithm + formulas)
2. *Which fields filter results vs. rank results?*
3. *What are the candidate scoring inputs, and which differ by property type / comp type?*
4. *How should the score be stored for audit/debugging?*
5. *How should the score be presented to appraisers?*
6. *What open questions need PVA/appraiser validation?*

> The goal is **not** to implement production scoring logic. It is to define the approach and surface the open questions.

**Mapping the report to the JIRA ticket** (every Expected Output / Acceptance Criterion is covered):

| JIRA Expected Output / AC | Where answered |
|---|---|
| P0 similarity/ranking requirements reviewed | §1 Requirements & traceability |
| Recommended similarity scoring approach | §2–§3, §6 |
| Candidate scoring inputs documented | §7 |
| Filtering vs ranking fields identified | §5 |
| Initial calculation approach recommended | §6 (algorithm), §7 (formulas), §11 (worked example) |
| Property-type & comp-type specific considerations | §9, §10 |
| How the score is stored (audit/debugging) | §12 |
| How the score is displayed to users | §13 + POC wireframe |
| POC: how final results display to the user | §13 (Evidence: wireframe) |
| Open questions for PVA validation | Next Steps |

### Method

1. **Requirements review** — read the P0 comp requirements (FR27.x, FR28.x) and built a traceability matrix to the four Jira-named requirements.
2. **Production benchmarking** — surveyed how production CRE/AVM systems score comps (Fannie Mae Collateral Underwriter, CoreLogic, CoStar, RealPage, Zillow; patents US6115694, US12254030) to choose a defensible algorithm.
3. **Synthesis** — consolidated four internal research drafts into one model, resolving conflicts (notably two competing score formulas) into a single recommendation.
4. **Worked calculation** — validated the chosen formula end-to-end on a sample Multi-Family subject so the math is reproducible.
5. **POC** — produced a results-screen wireframe showing how the final score displays to an appraiser (no live calculation, per the ticket).

---

## Conclusions / Recommendations

### 1. Executive summary & requirements reviewed

**Recommendation (one line):** Adopt a **transparent, configurable, weighted similarity score** built as a **Universal Core (6 dimensions) + Property-Type Bonus Layer**, normalized to **0–100**, computed *after* a hard-filter step and *before* appraiser selection.

Four design principles drive everything below:

- **Filter first, then rank.** Hard filters decide *which* comps are eligible; the score decides *what order* eligible comps appear in.
- **Transparent & explainable.** Comp selection is a regulated, defensible act (USPAP). Every score must decompose into readable, auditable parts — never a black box. This is why a weighted model is chosen over opaque distance metrics or (for P0) machine learning.
- **Relevance ≠ completeness.** "How *similar* is this comp to this subject?" is a different question from "how *well documented* is this comp record?" The two are scored and stored separately.
- **The score orders; the appraiser decides.** The score never replaces judgment — it ranks the candidate set the appraiser then curates.

The workflow:

> **Search → Filter** (hard include/exclude) **→ RANK** (relevance score) **→ Select** (appraiser judgment) **→ Report**

**P0 comp requirements reviewed (traceability matrix).** The bold rows are named directly in the Jira ticket.

| Req ID | Title | Process step | Relevance to this spike |
|---|---|---|---|
| **FR27.1** | **Unified Comps Database – Sales** | Database | Defines the sale-comp fields the score reads (incl. per-type "dynamic physical attributes"); AC asks to *"suggest comps using a basic algorithm and preset weightings that can be altered by the user."* |
| **FR27.2.1** | **Unified Comps Database – Leases** | Database | AC requires *"suggested based on algorithm/similarity indexation including location (distance + submarket), quality (class, amenities), size, tenancy, vintage."* |
| **FR27.2.2** | **Unified Comps Database – Unit Rents** | Database | AC requires per-unit-type similarity (location, quality, size, vintage, **unit mix**) for MF / MHC / self-storage / seniors / student housing. |
| **FR28.GAP4** | **Comp Ranking** | **Rank** | **Core requirement.** Composite relevance score; configurable criteria (proximity, recency, size, type, completeness, prior usage); default rank + re-sort + drag-reorder; persists per project/session; re-ranks on subject change. |
| FR27.8 | Comp Search UI – Basic | Search | Search surface hosting results & ranking; **<3 s** performance target. |
| FR28.1 | Search Filter – Property Type | Filter | Hierarchical multi-select type/subtype — a **filter** *and* a rank input. |
| FR28.2 | Search Filter – Location | Filter | Radius / polygon / state / market — **filter** *and* source of proximity & submarket rank inputs. |
| FR28.3 | Search Filter – Size Range | Filter | Size range — **filter**; size *closeness* is a rank input. |
| FR28.7.1 | Additional Filters | Filter | Year built, class, cap rate, $/SF, status, rights, occupancy — feed both filters and several sub-scores. |
| FR28.8.1 | Results – List View | Results | Sortable list; default sort = relevance; shows score column. |
| FR28.8.2 | Results – Map / Summary View | Results | Split map + summary; *"most similar comps displayed in rank order."* |
| FR28.8.3 | Results – Adjustment Grid View | Results | Comps as columns; default left-to-right ordering relates to rank/recency. |
| FR28.10 | Comp Detail View | Detail | Hosts the per-criterion "explain this score" breakdown. |
| FR28.11 | Select Comps for Project | Select | Selection follows ranking; snapshots comp data; increments "times used" (feeds *Prior Usage*). |
| FR28.12 | Manual Comp Entry | Manual | Manually entered comps must also be scorable. |
| FR28.14 | Quick Report Generation | Report | Whether the relevance score appears in client deliverables is an open question. |

**In scope:** scoring model, candidate inputs, filter-vs-rank split, per-property-type & per-comp-type considerations, calculation method, storage/audit model, UI presentation, a worked POC, open questions.

**Out of scope (explicit):** production scoring engine, real geocoding/submarket integration, live DB migration, ML training, wiring the POC to real data. These are named as follow-on epics in Next Steps.

### 2. Recommended workflow — hybrid search (filter → rank)

Two search philosophies exist in production CRE tools:

| | **Approach 1 — AI-first** (subject → instant ranked results → refine) | **Approach 2 — Filter-first** (set all filters → search) |
|---|---|---|
| How it works | Enter subject address + type; system returns top-ranked comps immediately; refine with filters after. | Build a filter set (date, size, radius, class…) first, then search; results sorted by chosen criteria. |
| Used by | CoStar Suggested Comps, Fannie Mae CU, RealPage, Zillow Similar Homes | Traditional LightBox Comp Starter, legacy MLS, ARGUS comp input |
| Strength | Fast first result; surfaces comps the appraiser wouldn't find; progressive. | Full control; explicit, auditable filter trail; deterministic. |
| Weakness | Algorithm-trust gap; cold-start; black-box risk if no breakdown. | Slow to first result; filter paralysis; may exclude good comps. |

**Recommendation — Hybrid (enterprise standard, used by CoStar, CBRE Valuations, JLL):** build **Approach 1 as the default** (subject address → instant ranked results in **<3 s**, score visible on every comp from first render) and surface **Approach 2 filters as a refinement panel**, collapsed by default. **Filters narrow the pool; they never replace the score-based ranking** within that pool. Record each search-expansion step (e.g. 0.5 mi → 1 mi → 2 mi) for the USPAP workfile.

### 3. Search approach & hard filters (what is required before scoring)

Before the similarity algorithm runs, the database is narrowed by **hard filters**. A comp that fails a hard filter never appears.

**Required before any search can run (the search anchors):**

| # | Required input | Why |
|---|---|---|
| 1 | **Subject location anchor** — address, APN/parcel ID, lat/long, or map pin | Gives the proximity anchor. Proximity is the single largest weight (30%); without a location anchor the Haversine distance — and therefore a valid score — cannot be computed. |
| 2 | **Property type** | Gates which comp pool is searched. You cannot compare a 10,000 SF office to a 10,000 SF industrial warehouse — the economics differ entirely. Every production system (CoStar, Fannie Mae CU, LightBox) requires a property type before returning comps. |
| 3 | **Comp type** — Sale / Lease / Unit-Rent | *(Gap fill.)* The three comp types (FR27.1 / FR27.2.1 / FR27.2.2) draw from different record sets with different fields and different pricing units. A sale-comp search and a lease-comp search are not interchangeable, so comp type is a **hard filter**, set alongside property type and location. |

**Hard filters (mandatory, binary include/exclude — applied before scoring):**

- **Property type / major class** (FR28.1)
- **Location boundary** — radius / polygon / state / MSA (FR28.2)
- **Comp type** — Sale / Lease / Unit-Rent
- **Hard exclusion rules** — e.g. non-arm's-length / distressed sales excluded unless explicitly sought; fee-simple-only; closed sales only.
- **Optional per-type near-hard filters** — a small number of structural attributes are so decisive they can act as near-hard filters for specific types (e.g. **clear height** for Industrial, **% climate-controlled** for Self-Storage, **care level** for Senior Housing). See §10. These can be implemented either as true hard filters at the search layer or as a severe penalty on the type-match dimension (§6).

**Soft filters (optional, refine the pool after results appear; re-rank but never reset ranking):** date range, search radius, size range, building class, submarket, occupancy, cap-rate range, $/SF range, year-built range.

### 4. Filtering vs. ranking fields

This is the central distinction the requirements ask us to make explicit.

- **Filter = hard constraint (binary).** Defines *which* comps are eligible. (FR28.1, FR28.2, FR28.3, FR28.7.1)
- **Rank = soft relevance (continuous).** Orders *eligible* comps by similarity. (FR28.GAP4)

| Field | Filter? | Rank input? | Role |
|---|---|---|---|
| Property type / subtype | ✅ | ✅ | Filter to selected types; rank by subtype closeness. **Dual-role.** |
| Comp type (Sale/Lease/Unit-Rent) | ✅ | — | Hard pool selector. |
| Location – radius / polygon / state / market | ✅ | — | Hard geographic bound. |
| Location – exact distance | — | ✅ (Proximity) | Distance *within* the bound drives the proximity sub-score. **Dual-role.** |
| Submarket | ✅ (optional) | ✅ (bonus) | Can constrain *and* rank. |
| Size range | ✅ | — | Hard min/max bound. |
| Size closeness to subject | — | ✅ (Size) | Closeness *within* the range drives the sub-score. **Dual-role.** |
| Date range | ✅ | — | Hard recency bound. |
| Recency (time decay) | — | ✅ (Recency) | Closeness in time drives the sub-score. **Dual-role.** |
| Year-built range | ✅ | (✅ via vintage) | Primarily filter; vintage informs quality/recency context. |
| Building class (A/B/C) | ✅ (optional) | ✅ (bonus) | Either constrain or rank. |
| Sale/lease status, property rights | ✅ | — | Eligibility constraints. |
| Cap rate / $-per-unit / $/SF / occupancy ranges | ✅ | — | Eligibility constraints — *outcomes*, not similarity. |
| Amenities / unit mix | (optional filter) | ✅ (bonus) | Usually a rank input. |
| Data completeness | ✅ (optional floor) | ✅ (universal dim) | Optional eligibility floor + ranking dimension. |
| Prior usage | — | ✅ (tie-breaker) | Rank-only. |

**Rules of thumb:** (1) *Eligibility facts* (status, rights, hard geography, hard size/date bounds, comp type) → **filters**. (2) *Closeness-to-subject facts* (distance, size delta, time delta, subtype, quality, amenities) → **rank inputs**. (3) A field can be **both** — the *range* filters, the *closeness within the range* ranks.

### 5. The scoring model / algorithm

**Model: Universal Core + Property-Type Bonus Layer**, evaluated with a Weighted-similarity (Weighted Euclidean Distance–style) approach. Six universal dimensions form a stable **0–100 base score**; a property-type-specific **bonus layer** adds asset-class intelligence on top; the result is normalized back to a 0–100 index.

#### 5.1 Universal core (same 6 dimensions, same weights, for every property type)

| # | Dimension | Default weight | What it measures | Notes |
|---|---|---|---|---|
| 1 | **Proximity** | **30%** | Distance from subject (Haversine) with decay | Location is the #1 adjustment in every appraisal grid. |
| 2 | **Recency** | **20%** | Time between comp event and effective date | Stale comps need the largest market-conditions adjustment. |
| 3 | **Size similarity** | **20%** | % delta on the type-appropriate size metric | *Weight is fixed; the metric changes by type* (§8). |
| 4 | **Property-type match** | **15%** | Subtype closeness within the filtered type | Garden vs High-Rise MF = different buyer. |
| 5 | **Data completeness** | **10%** | % of the type's required fields populated | Keeps relevance honest; distinct from a quality score. |
| 6 | **Prior usage** | **5%** | How often the comp was used in similar work | Tie-breaker only; small by design (bias risk). |

> **Key insight:** the *weight* stays constant across property types, but the *measurement* changes. Size is always 20% — but it measures unit-count delta for Multi-Family, GBA delta for Industrial, and room-count delta for Hotels. *Same importance, different ruler.*

**Base-score formula** (each `subScoreᵢ` is normalized 0–100; each `weightᵢ` is the % above):

```
BaseScore = Σ ( subScoreᵢ × weightᵢ )      for i in the 6 universal dimensions
          = 0–100
```

#### 5.2 Property-type bonus layer (additive, per-type, never penalizes nulls)

Each property type defines a small set of **bonus signals** (e.g. unit mix, quality class, submarket, occupancy for Multi-Family) with point caps (e.g. +5, +5, +5, +3). A bonus contributes `cap × matchQuality` (matchQuality ∈ [0,1]); a perfect match earns the full cap. Bonuses are **additive only** — a missing bonus field adds nothing and subtracts nothing (null = unknown, not bad).

#### 5.3 Final normalization (scales base + bonus back to a clean 0–100 index)

```
FinalScore = ( (BaseScore + TotalBonusPoints) / (100 + MaxPossibleBonus) ) × 100
```

- `TotalBonusPoints` = sum of the earned bonuses.
- `MaxPossibleBonus` = sum of the caps of the **active** bonus signals for this search (a signal is "active" only when the **subject** has the field populated, so it could be earned).
- Normalizing by `100 + MaxPossibleBonus` lets the bonus act as a true index — it scales results elegantly to 0–100 without everything clustering near 100.

#### 5.4 Missing-data handling (critical — a missing field must not bury a good comp)

| Situation | Rule |
|---|---|
| **A universal dimension field is null on the comp** | Drop that dimension and **re-normalize** the remaining universal weights to sum to 100% (the base-score denominator covers active dimensions only). |
| **A bonus field is null on the comp** | Skip that bonus — add/subtract nothing. |
| **A bonus field is null on the *subject*** | Disable that bonus for the *entire search session* (and exclude its cap from `MaxPossibleBonus`). |
| **Near-hard-filter mismatch** (e.g. CC vs non-CC self-storage; NNN vs Gross lease) | Apply a severe penalty to the type-match dimension (sub-score → ~0–10). The comp stays visible but ranks very low: `PenalizedScore = FinalScore × penaltyMultiplier`. |

Data completeness is *also* surfaced separately so the appraiser knows when a high score was computed on thinner evidence.

### 6. Sub-score formulas (with worked micro-examples)

Different data types (distance, dates, square footage, categories) cannot be compared with the same math. Each formula converts a real-world attribute into a normalized **0–100** sub-score. *(Examples use a Multi-Family subject of 142 units, search radius 6 mi.)*

| Sub-score | Formula | Micro-example |
|---|---|---|
| **Proximity** (Haversine + linear decay) | Haversine gives great-circle distance `d` (mi) between two lat/long points. `Prox = max(0, 100 × (1 − d / searchRadius))`. *(Exponential decay `100 × e^(−d/h)` is an alternative for dense urban markets.)* | Comp 0.3 mi away, radius 6 mi → `100 × (1 − 0.3/6) = 95`. |
| **Size** (% delta) | `Size = max(0, 100 × (1 − |Subject − Comp| / Subject))`. Metric switches by type (§8). | Comp 120 units vs subject 142 → `100 × (1 − 22/142) = 84.5 ≈ 85`. |
| **Recency** (month-band step) | Months since the comp event, bucketed: `0–6 = 100, 6–12 = 85, 12–24 = 65, 24–36 = 40, 36+ = 15`. *(Exponential decay is an alternative.)* | Sold 3 months ago → band 0–6 → `100`. |
| **Property-type match** (hierarchy) | `exact subtype = 100, same type/other subtype = 75, same major group = 40, adjacent type = 20, different = 0`. | Garden MF vs Garden MF → `100`. |
| **Data completeness** | `100 × (required fields populated / required fields expected)` for the type. | 22 of 25 required MF fields → `88`. |
| **Prior usage** (log/step scale) | `0 uses = 30 (not penalized), 1–3 = 55, 4–9 = 70, 10+ = 100`; filtered by same type + MSA. | Used 4× in similar MF work → `70`. |
| **Amenities** (Jaccard, bonus) | `Jaccard = |A ∩ B| / |A ∪ B|`, ×100 over the two amenity sets. | 8 shared of 10 total amenities → `0.80 → 80`. |
| **Unit mix** (cosine, bonus) | Cosine similarity of the BR/BA unit-mix vectors, ×100. | Near-identical mix → `0.96 → 96`. |

> These are the proposed P0 formulas; exact curve shapes (decay horizon, recency bands) are configurable and flagged for SME validation (Next Steps).

### 7. Candidate scoring inputs (consolidated)

| Input | Source field(s) | Sub-score function | Default weight / role | Notes |
|---|---|---|---|---|
| **Proximity** | lat/long (geocoded) | Haversine + decay | 30% (universal) | `d_max`/`h` configurable per market density. |
| **Recency** | sale/lease date vs effective date | month-band step | 20% (universal) | Horizon market-sensitive; configurable. |
| **Size** | type-appropriate metric (§8) | % delta | 20% (universal) | Metric switches by property type. |
| **Property-type match** | property_type, subtype, tags | hierarchy match | 15% (universal) | Also a filter; sub-score handles subtype closeness. |
| **Data completeness** | meta: % required fields populated | populated/expected | 10% (universal) | Kept distinct from FR32.4 quality score. |
| **Prior usage** | times_used, usage history (FR28.11) | log/step scale | 5% (universal, tie-breaker) | Bias risk — small & optionally off in regulated work. |
| **Submarket** | submarket / MSA tag (source TBD) | categorical match | bonus | Complements proximity; source is an open question. |
| **Quality / class** | quality (A/B/C), condition | ordinal/exact match | bonus | Highly material for office/industrial. |
| **Amenities / functional features** | amenity set, ratings | Jaccard / rating proximity | bonus | Parking, anchor, clear height, unit mix, etc. |
| **Occupancy / income profile** | occupancy, cap rate, NOI | proximity of values | bonus / filter | Income properties & lease comps. |

### 8. Size metric by property type (the most important per-type configuration)

Use the wrong size metric and the 20% size dimension scores incorrectly for *every* comp.

| Property type | Size metric | Why |
|---|---|---|
| Multi-Family, Student, BTR | **Unit count** | $/unit is the MF pricing metric, not SF. |
| Office | **NRA** (Net Rentable Area, SF) | Tenants pay on NRA; GBA overstates usable area. |
| Retail / Shopping Center | **NRA** (lease) / **GBA** (sale) | Matches the comp type's pricing basis. |
| Industrial / Warehouse / Flex | **GBA** (Gross Building Area, SF) | Standard for industrial; clear height/dock modify utility. |
| Hotels / Lodging | **Room / key count** | RevPAR/ADR per room is the income metric; SF irrelevant. |
| Manufactured Housing (MHC) | **Site / pad count** | Revenue is rent per site; building SF irrelevant. |
| Self-Storage | **Net rentable SF** | $/SF is the storage pricing unit. |
| Senior Housing / Health Care | **Unit or bed count** | Care/revenue is per resident/bed. |
| Land / Agricultural | **Acres or land SF** | No improvements — land area is the only size metric. |

### 9. Comp-type considerations

The three comp types share one engine but need different emphases and normalizations.

- **Sale comps (FR27.1).** *Emphasize:* recency (≈ market conditions), proximity, size, property rights, arm's-length conditions. *Normalize:* compare on the price-per-unit-of-comparison for the type (Unit / SF / Room / Bed / Key). Cap-rate proximity is an *eligibility filter* (an outcome), not a relevance input. *Watch:* exclude/down-rank distressed or non-arm's-length unless explicitly sought.
- **Lease comps (FR27.2.1).** *Emphasize:* tenant credit, space SF, lease date, submarket, class. *Normalize:* **lease structure matters** — NNN vs Gross vs Modified Gross must be normalized to a comparable **effective rent** (after concessions: free rent, TI, LCs) before size/rent closeness is meaningful. *Watch:* first- vs second-generation space; lease vs sublease.
- **Unit-rent comps (FR27.2.2).** *Emphasize:* **unit-type-level matching** (Studio / 1BR / 2BR / 3BR…), submarket, amenities, occupancy, size. *Normalize:* analyze rent **per unit type**, conclude premiums per floor plan, then blend to market/gross-potential rent. Affordability (% AMI) is a strong eligibility filter for affordable deals. *Watch:* self-storage / seniors / MHC have their own unit taxonomies (CC vs non-CC; care level; community-owned vs resident-owned) — the unit-match sub-score must use that type's taxonomy.

### 10. Property-type considerations + weight tables (all P0 types)

Every table below shares the **same universal base (the 6 rows)**. Only the **bonus layer** and the noted near-hard filters change. Bonuses apply only when both subject and comp populate the field.

**10.1 Multi-Family** — *unit mix is the strongest MF-specific signal.*

| Attribute | Weight / cap | What you measure |
|---|---|---|
| Proximity / Recency / Size (unit count) / Type / Completeness / Prior usage | 30 / 20 / 20 / 15 / 10 / 5% | Universal base |
| Unit mix (BR/BA cosine) | bonus +5 | Cosine of unit-mix vectors |
| Quality class (A/B/C) | bonus +5 | Class match |
| Submarket | bonus +5 | Same CoStar/RealPage submarket |
| Occupancy at sale | bonus +3 | Stabilised vs lease-up |

**10.2 Office** — *submarket can matter as much as raw distance; class is the top office signal.*

| Attribute | Weight / cap | What you measure |
|---|---|---|
| Universal base (size = **NRA**) | 30 / 20 / 20 / 15 / 10 / 5% | Subtype: CBD / Suburban / Medical / Co-Working |
| Quality class (A/B/C) | bonus +5 | Most important office signal |
| Submarket | bonus +4 | Office submarkets are well-defined |
| Parking ratio | bonus +4 | Spaces / 1,000 SF — critical suburban |
| Tenant credit rating | bonus +4 | Credit tenant = cap-rate premium |

> *P1 note:* validate whether proximity should drop to ~25% for office (submarket carries more) via hedonic regression.

**10.3 Industrial / Warehouse** — *clear height is a near-hard filter.*

| Attribute | Weight / cap | What you measure |
|---|---|---|
| Universal base (size = **GBA**, weighted slightly higher) | 25 / 20 / 25 / 15 / 10 / 5% | Subtype: Warehouse / Flex / Manufacturing / R&D |
| Clear height (ft) | bonus +5 / **near-hard filter** | <2 ft delta = +5, >6 ft = penalty |
| Dock doors / ratio | bonus +4 | Loading-access comparability |
| Quality class | bonus +3 | Class match |
| Cap rate | bonus +3 | <50 bps delta |

**10.4 Retail / Shopping Center** — *trade-area overlap defines proximity; use a steeper decay curve.*

| Attribute | Weight / cap | What you measure |
|---|---|---|
| Universal base (size = NRA lease / GBA sale; **steeper proximity decay**) | 30 / 20 / 20 / 15 / 10 / 5% | Subtype: Strip / Neighborhood / Power / Single-Tenant NNN |
| Tenant type / credit | bonus +5 | National credit vs local |
| Anchor presence | bonus +4 | Anchored vs unanchored; anchor type |
| Parking ratio | bonus +4 | Spaces / 1,000 SF |
| Cap rate | bonus +3 | <50 bps delta |

**10.5 Hotels / Lodging** — *RevPAR predicts value better than physical size.*

| Attribute | Weight / cap | What you measure |
|---|---|---|
| Universal base (size = **room count**, reduced; type & completeness raised) | 20 / 20 / 15 / 20 / 15 / 5% | Segment: Full-Service / Limited / Extended-Stay / Boutique |
| RevPAR match | bonus +6 | Revenue per available room delta |
| ADR match | bonus +5 | Average daily rate delta |
| Brand flag / tier | bonus +3 | Flagged vs independent |
| Occupancy | bonus +2 | Occupancy at sale |

**10.6 Manufactured Housing (MHC)** — *% community-owned homes is the key differentiator.*

| Attribute | Weight / cap | What you measure |
|---|---|---|
| Universal base (size = **site/pad count**) | 30 / 20 / 20 / 15 / 10 / 5% | Subtype: All-Age vs 55+ |
| % Community-owned homes | bonus +5 | COH% delta — income profile |
| Avg rent / site / month | bonus +5 | Primary MHC income metric |
| Occupancy | bonus +5 | Occupancy delta |
| Utility structure | bonus +3 | Owner- vs tenant-paid water/sewer |

**10.7 Self-Storage** — *% climate-controlled is a near-hard filter.*

| Attribute | Weight / cap | What you measure |
|---|---|---|
| Universal base (size = **net rentable SF**) | 30 / 20 / 20 / 15 / 10 / 5% | % CC is a near-hard filter |
| % Climate-controlled | bonus +6 / **near-hard filter** | CC vs non-CC = different product |
| Occupancy | bonus +5 | SS stabilises ~85% |
| Unit mix | bonus +5 | 5×5, 5×10, 10×10, 10×20 distribution |
| Cap rate | bonus +4 | <50 bps delta |

**10.8 Senior Housing / Health Care** — *care level is a near-hard filter; % private pay drives NOI.*

| Attribute | Weight / cap | What you measure |
|---|---|---|
| Universal base (size = **unit/bed count**; proximity reduced, type/completeness raised) | 20 / 20 / 20 / 20 / 15 / 5% | IL / AL / Memory Care / SNF |
| % Private pay | bonus +6 | Private vs Medicare/Medicaid mix |
| Care-level match | bonus +5 / **near-hard filter** | Cross-care-level comps rarely credible |
| Occupancy | bonus +5 | Occupancy delta |
| Quality | bonus +4 | Physical quality rating |

**10.9 Land / Agricultural** — *mirrors the Land Valuation adjustment grid; no improvements.*

| Attribute | Weight / cap | What you measure |
|---|---|---|
| Universal base (size = **acres / land SF**) | 30 / 20 / 20 / 15 / 10 / 5% | Subtype by use designation |
| Zoning / density | bonus +6 | Allowable use & FAR/units-per-acre |
| Topography / shape | bonus +4 | Usable-area comparability |
| Utilities / access | bonus +4 | Served vs unserved; road frontage |
| Entitlements | bonus +3 | Entitled vs raw |

> **Cross-type ranking** (e.g. MF vs Senior Housing) is normally prevented by the property-type hard filter. If ever allowed, the property-type sub-score down-weights adjacent types. Whether adjacency is permitted at all is an open question (Next Steps).

### 11. End-to-end worked calculation (how the score is computed)

**Subject (S):** 20800 Homestead Road, Cupertino CA — Multi-Family (Garden), **142 units**, Class A, built 2019, Submarket X.
**Comp #1 (C):** 18950 Vallco Pkwy, Cupertino CA — Multi-Family (Garden), **120 units**, Class A, **sold 3 months ago**, **0.3 mi** away, Submarket X, **88%** of required fields populated, used **4×** in similar MF work.
**Settings:** search radius 6 mi; effective date = today; MF weight profile.

**Step 1 — Universal sub-scores (using the §6 formulas):**

| Dimension | Raw input | Sub-score (0–100) | Weight | Weighted |
|---|---|---|---|---|
| Proximity | 0.3 mi (radius 6) → `100×(1−0.3/6)` | **95** | 0.30 | 28.5 |
| Recency | 3 months → band 0–6 | **100** | 0.20 | 20.0 |
| Size | 120 vs 142 units → `100×(1−22/142)` | **85** | 0.20 | 17.0 |
| Property-type match | Garden MF vs Garden MF (exact subtype) | **100** | 0.15 | 15.0 |
| Data completeness | 88% required fields | **88** | 0.10 | 8.8 |
| Prior usage | used 4× → band 4–9 | **70** | 0.05 | 3.5 |
| **BaseScore** | | | **1.00** | **92.8** |

**Step 2 — MF bonus layer** (active signals → `MaxPossibleBonus = 5+5+5+3 = 18`):

| Bonus | matchQuality × cap | Earned |
|---|---|---|
| Unit mix (cosine 0.96) | 0.96 × 5 | 4.8 |
| Quality class (A vs A, exact) | 1.00 × 5 | 5.0 |
| Submarket (X vs X, exact) | 1.00 × 5 | 5.0 |
| Occupancy (close) | 0.90 × 3 | 2.7 |
| **TotalBonusPoints** | | **17.5** |

**Step 3 — Final normalization:**

```
FinalScore = ((BaseScore + TotalBonusPoints) / (100 + MaxPossibleBonus)) × 100
           = ((92.8 + 17.5) / (100 + 18)) × 100
           = (110.3 / 118) × 100
           = 93.5  →  ★ 93 / 100
```

**Missing-field variant — what if the comp's unit count (Size) is null?** Drop Size (weight 0.20) and re-normalize the remaining five universal weights over their sum (0.80):

| Dimension | Re-normalized weight | Sub-score | Weighted |
|---|---|---|---|
| Proximity | 0.30/0.80 = 0.375 | 95 | 35.6 |
| Recency | 0.25 | 100 | 25.0 |
| Property-type match | 0.1875 | 100 | 18.75 |
| Data completeness | 0.125 | 88* | 11.0 |
| Prior usage | 0.0625 | 70 | 4.4 |
| **BaseScore** | **1.00** | | **94.75** |

```
FinalScore = ((94.75 + 17.5) / 118) × 100 = 95.1  →  ★ 95 / 100
```

\*In practice the *completeness* sub-score also drops when a field is missing, signalling the thinner evidence in the UI; we hold it here to isolate the weight-re-normalization mechanic. The point: a missing field is treated as **unknown**, never as a zero that buries an otherwise strong comp.

### 12. Storage & auditability

**Core principle:** a relevance score is **not an attribute of a property** — it is relative to `(subject, candidate event, weight profile, point in time, algorithm version)`. Storing it as a single column on a comp record would be meaningless without its subject and weights.

**Two scores, never merged:**

| | **Relevance score (FR28.GAP4)** | **Completeness score** |
|---|---|---|
| Question | "How *similar* is this comp to **this subject**?" | "How *well documented* is this comp record?" |
| Nature | Dynamic — recomputed per subject at search time | Static — computed when the comp record is created/updated |
| Stored in | `comp_relevance_score` (search-time snapshot) | a field on the comp record |

**Recommended `comp_relevance_score` shape (event-centric):**

```
comp_relevance_score
├─ id
├─ project_id            (FK)   -- scopes to the appraisal
├─ subject_property_id   (FK)   -- the "relative to" anchor
├─ comp_event_id         (FK)   -- the candidate sale/lease/unit-rent EVENT (not just a property)
├─ weight_profile_id     (FK)   -- default vs user-overridden profile
├─ composite_score       (0–100)
├─ sub_scores            (JSON) -- {proximity:95, size:85, ...} for "explain this score"
├─ bonuses_applied       (JSON) -- earned bonus points per signal
├─ sub_score_inputs      (JSON) -- raw inputs (distance, deltas) for full audit
├─ scoring_version       (string) -- e.g. "relscore-v1.0" for reproducibility
├─ manual_rank_override  (int, nullable)  -- drag-and-drop position
├─ override_reason       (text, nullable)
├─ search_radius, effective_date
├─ computed_at           (timestamp)
└─ computed_by           (user)
```

**What to persist and why:**
- **Subject context + weight profile + per-criterion sub-scores + raw inputs** → the score is reproducible and explainable later (USPAP workfile defensibility; powers "explain this score").
- **`scoring_version`** → if scoring functions change, historical scores stay interpretable and old appraisals don't silently shift. Never rewrite historical snapshots.
- **Selection snapshot (FR28.11)** → freeze the composite score (immutable) at the moment of selection; record `selected=true`, `selected_at`.
- **Deselection reason** → captured as future ML training signal (rows where `selected=false` but `score>75` are appraiser overrides).
- **Manual reorder + reason** → FR28.GAP4 requires drag-and-drop reorder; the override and its rationale are auditable.
- **Recompute triggers** → recompute when the subject context or weight profile changes (FR28.GAP4 AC); cache to hold the **<3 s** target (FR27.8).
- **Search trail** → store each expansion step for the workfile ("0.5 mi → 1 mi → 2 mi").
- **Persistence scope** → ranking + manual reorder persist **per project/session**, so an appraiser returning sees the same order they left.

### 13. UI presentation + POC

**Principles:** (1) default sort = relevance, descending; (2) the score is **always visible** as a 0–100 pill (green/amber/red) on every comp in all three result views (List / Map+Summary / Adjustment Grid); (3) **"explain this score"** expands the per-dimension `Σ subScoreᵢ × weightᵢ` breakdown + reason codes; (4) re-sortable, multi-sort, and drag-reorder (overrides flagged + audited; badge shows "Custom order — score sorting paused"); (5) weight profile adjustable in-context (sliders / preset picker) that **re-ranks live**, with reset-to-default; (6) context comparison of selected-vs-non-selected metric averages.

**POC — results-screen wireframe** (illustrative; no live calculation, per the ticket):

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ SUBJECT: 20800 Homestead Road, Cupertino CA  ·  Multi-Family · 142 units · Class A · 2019  │
│ Comp type: [ Sales ▼ ]   Weight profile: [ MF · Sales ▼ ]                                  │
│ Prox .30  Recency .20  Size .20  Type .15  Complete .10  Prior .05            [ Reset ]     │
│ [ List ] [ Map+Summary ] [ Adjustment Grid ]              347 eligible · ranked by ★ ▼      │
├───────────────────────────────────────────┬────────────────────────────────────────────────┤
│  RESULTS (sorted by ★ Relevance)          │  MAP                                            │
│ ┌───────────────────────────────────────┐ │     ·  (1)        rank-styled pins              │
│ │ #1  ★93  18950 Vallco Pkwy   0.3 mi  ☐│ │   (3)  (1)                                      │
│ │     MF · 120 u · Class A · sold 3 mo   │ │       (2)     ·  ·                              │
│ │     [Prox 95][Rec 100][Size 85]        │ │   ·       (4)        ·                          │
│ │     [Type 100][Submkt ✓][Unit-mix ✓] ▸ │ │                                                 │
│ ├───────────────────────────────────────┤ │ ── "explain this score" (expanded) ───────────  │
│ │ #2  ★82  10110 Bandley Dr    0.7 mi  ☐│ │   FinalScore = ((Base + Bonus)/(100+18))×100    │
│ │     MF · 96 u · Class A · sold 10 mo   │ │   proximity   95 × 0.30 = 28.5                  │
│ │     [Prox 88][Rec 85][Size 68] ▸       │ │   recency    100 × 0.20 = 20.0                  │
│ ├───────────────────────────────────────┤ │   size        85 × 0.20 = 17.0                  │
│ │ #3  ★67  3133 De Anza Blvd   2.1 mi  ☐│ │   type       100 × 0.15 = 15.0                  │
│ │ #4  ★42  1161 Cadillac Ct    5.4 mi  ☐│ │   complete    88 × 0.10 =  8.8                  │
│ │        (drag ⇅ to reorder)             │ │   prior       70 × 0.05 =  3.5  → base 92.8     │
│ └───────────────────────────────────────┘ │   + bonus 17.5  →  ★ 93                          │
│  Selected avg $/u $176k · non-sel $171k · overall $173k                                     │
└───────────────────────────────────────────┴────────────────────────────────────────────────┘
                          [ POC / illustrative — not production scoring ]
```

**View-specific notes:** *List (FR28.8.1)* — relevance is a sortable column with per-dimension mini-badges + a drag handle. *Map+Summary (FR28.8.2)* — pins styled/numbered by rank; "most similar in rank order" in the summary rail. *Adjustment Grid (FR28.8.3)* — comps as columns ordered left→right by relevance (or sale date); score in the header row; hideable when it shouldn't appear in the deliverable.

### 14. Future evolution (out of P0 scope)

The transparent score is the system of record. As a corpus of comp-selection decisions accrues, weights can be *calibrated* without changing the model's shape:

| Phase | Approach | When | Explainability |
|---|---|---|---|
| **P0 (now)** | Weighted similarity, fixed expert weights | Ship in 1 sprint; no historical data needed | Full — every dimension visible (USPAP-defensible) |
| **P1 (~6–12 mo)** | Hedonic regression → market-calibrated β weights | After ~500 selections per type per MSA | Full — `ln(Price) = β₀ + β₁(GBA) + …`; β is the weight |
| **P2 (~12–24 mo)** | XGBoost on labelled selections; SHAP for per-comp explanations | After ~5,000 labelled selections | Partial — SHAP values explain each comp |

**Caveat:** ML carries feedback-loop/bias risk (it learns to prefer what was historically chosen) and explainability risk. If pursued, keep the transparent score as the system of record and treat ML as an advisory overlay. The `times_used` / deselection data captured in P0 *is* the training data for P1/P2 — **we build the data flywheel now**.

---

## Evidence

**E1 — Production-systems benchmarking** (why a transparent weighted model for P0):

| Algorithm | Used by | How it works | P0 fit |
|---|---|---|---|
| **Weighted Euclidean Distance (WED)** | Fannie Mae CU, CoreLogic, LightBox, most AVMs | Normalize each attribute 0–1, weight, sum | ✅ **Recommended** — explainable, fast, USPAP-defensible |
| Weighted Additive (appraisal grid) | CBRE, JLL, standard MAI grids | Dollar adjustments per attribute | ✅ Maps to adjustment grid; manual to scale |
| Hedonic regression | CBRE, Cushman, academic AVMs | β weights from historical sales | ⏭ P1 (needs 500+ txns/type/MSA) |
| XGBoost / LightGBM | RealPage (US12254030), Zillow | Learns non-linear patterns from selections | ⏭ P2 (needs 5,000+ labels; black-box) |
| Weighted cosine | RealPage (unit rent), CBRE (unit mix) | Vector angle similarity | Component only (unit-mix bonus) |
| Gower's coefficient | Academic / mixed-type data | Per-attribute similarity for mixed types | Borrowed idea: per-attribute normalization |

> Fannie Mae patent US6115694 documents fixed predetermined weights (living area 0.30, sale date 0.20, distance 0.20, …) — direct precedent for the P0 fixed-weight approach. RealPage US12254030 documents the XGBoost approach — our P2 target, not P0.

**E2 — Illustrative ranked output** (same MF subject; demonstrates ordering; bonuses folded into the score):

| Rank | Address | Units | Dist | Age | Property type | Prox | Rec | Size | TypeM | Data | ★ Score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| #1 | 18950 Vallco Pkwy, Cupertino | 120 | 0.3 mi | 3 mo | Garden MF · A | 95 | 100 | 85 | 100 | 88 | **93** |
| #2 | 10110 Bandley Dr, Cupertino | 96 | 0.7 mi | 10 mo | Garden MF · A | 88 | 85 | 68 | 100 | 74 | **82** |
| #3 | 3133 De Anza Blvd, San Jose | 188 | 2.1 mi | 15 mo | MF · B | 65 | 65 | 68 | 75 | 61 | **67** |
| #4 | 1161 Cadillac Ct, Milpitas | 72 | 5.4 mi | 22 mo | MF · B | 10 | 65 | 51 | 75 | 55 | **42** |

The ordering reads the way an appraiser reasons: the nearest, most recent, most size- and class-comparable comp ranks first; the far, older, off-class comp ranks last — and every number is inspectable.

**E3 — POC wireframe:** see §13 (results screen with score pills + "explain this score" breakdown). This is what the POC renders for the ticket's "show how final results display to the user" requirement.

**E4 — Requirements traceability:** see §1 matrix (17 P0 comp requirements mapped to Search → Filter → Rank → Select → Report, with the four Jira-named requirements bolded).

---

## Next Steps

### Open questions for PVA / appraiser validation

These need stakeholder answers before build:

1. **Default weight profiles** — who owns the canonical defaults per *property-type × comp-type*, and what are the starting values? (SME workshop.)
2. **Submarket definition source** — CoStar? RealPage? LightBox? Internal polygons? The submarket signal depends on it.
3. **Recency decay** — curve shape and horizon (0 at 24 vs 36 months)? Flex by market conditions / type?
4. **Prior-usage input** — include it at all in regulated work, given circularity risk? Default on or off?
5. **Completeness floor** — is there a minimum below which a comp is "insufficient to rank / not actively usable"? What is it per type?
6. **Near-hard filters** — confirm which structural attributes act as near-hard filters (clear height, % climate-controlled, care level) and whether they filter at the search layer or penalize the score.
7. **FR28.GAP4 ↔ FR32.4 governance** — should a minimum quality score gate rankability? Two scores side-by-side or one blended? (Recommendation: do **not** blend without an explicit decision.)
8. **Weight-profile scope & permissions** — per-user vs per-company? Who may override? Is an override a recorded USPAP workfile element?
9. **Cross-/adjacent-type ranking** — allowed at all (e.g. MF vs Seniors)? If so, what adjacency map?
10. **Portfolio subjects** — when a project has multiple subjects, rank relative to which (per-subject, blended, user-chosen)?
11. **Geocoding** — source & accuracy SLA; how to handle comps lacking lat/long.
12. **Performance / scale** — DB size, concurrency, caching to hold the **<3 s** target as the corpus grows.
13. **Deliverable disclosure** — should the relevance score ever appear in client-facing Quick Reports (FR28.14)? Default behavior?
14. **Score presentation** — numeric 0–100 vs qualitative label (High/Med/Low) by default?

### Follow-on implementation (high-level sizing — *not commitments*)

| Epic / work item | Depends on | Size |
|---|---|---|
| Comps DB fields for scoring (per-type dynamic attrs, geocode, completeness meta) | FR27.1/2.x | M |
| Geocoding pipeline + distance/proximity computation | FR28.2 | M |
| Submarket data integration & mapping | Q#2 resolved | M–L |
| Relevance scoring engine (sub-score fns + universal core + bonus + normalization + null handling, versioned) | inputs ready | L |
| Weight-profile config (defaults per type, user override, persistence) | engine | M |
| Storage & audit model (`comp_relevance_score`, recompute triggers, caching) | engine | M |
| Results UI: score pills, default rank, re-sort/cascade/drag-reorder across List/Map/Grid | engine + FR28.8.x | L |
| "Explain this score" breakdown panel | engine | S–M |
| POC → production hardening | this spike | M |

**Suggested sequencing:** DB fields → geocoding → scoring engine → weight config + storage → UI → explainability. Submarket integration runs in parallel and plugs in when ready.

**Immediate next action:** schedule the **SME validation workshop** to lock default weights per property type × comp type and answer the open questions above.

---

## Appendix

**A1 — Relevance (FR28.GAP4) vs. Quality (FR32.4):**

| | Relevance (FR28.GAP4) | Quality (FR32.4, P2) |
|---|---|---|
| Question | "How *similar* to **this subject**?" | "How *good/complete/verified* is this record?" |
| Relative to | a subject + weight profile | the comp itself (absolute) |
| Changes when | subject or weights change | underlying data quality changes |
| P0? | ✅ (this spike) | ❌ P2 |
| Recommendation | system of record for ranking | optional eligibility floor + secondary signal; **do not blend** without an explicit stakeholder decision |

**A2 — Glossary:**
- **Comp / comparable** — a property *event* (sale, lease, or unit-rent) used as evidence of value.
- **Relevance / similarity score** — 0–100 measure of how similar a comp is to the subject, for ranking.
- **Location anchor** — any location reference (address, parcel ID, lat/long, map pin) used to compute proximity.
- **Universal core** — the 6 dimensions scored for every property type (proximity, recency, size, type, completeness, prior usage).
- **Bonus layer** — per-property-type signals added on top of the base score; never penalize nulls.
- **Weight profile** — the set of per-dimension weights + active bonuses, defaulted per property-type × comp-type, appraiser-adjustable.
- **Hard filter** — a mandatory pre-scoring constraint (property type, location boundary, comp type).
- **Soft filter** — an optional post-results refinement (date, radius, size, class, submarket…).
- **USPAP** — Uniform Standards of Professional Appraisal Practice; the reason explainability/auditability are non-negotiable.
- **Workfile** — the documentation record supporting an appraisal; the search trail + score snapshots feed it.

**A3 — Assumptions:** property-centric data model (property = entity; sale/lease/valuation = events); comps carry geocoded lat/long; field-level source attribution exists; a "Subject Unit of Comparison" is set per file and drives the size metric.

**A4 — Reference note:** LightBox (lightboxre.com) is used here as a *directional* reference for how CRE platforms surface ranked/scored comps; the recommendation is grounded in the PVA requirements and the existing adjustment-grid model, not on any single vendor.

**A5 — Alternative considered (not recommended for the headline model):** a *pure weighted-additive* score with a single weight set summing to 1.0 and re-normalization on missing fields — `100 × Σ(wᵢ·sᵢ)/Σwᵢ` (no separate bonus layer). It is simpler but folds asset-class signals into the same flat weight vector, losing the clean universal-vs-type separation. Retained here only as a fallback should stakeholders prefer maximum simplicity over per-type tunability.

---

*End of spike report. To be attached to the corresponding JIRA spike ticket.*
