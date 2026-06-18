const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageBreak,
} = require("docx");
const fs = require("fs");

// ── Style helpers ────────────────────────────────────────────────────────────
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const HEAD_FILL = "1B3A5C";
const SUB_FILL  = "DDEBF7";
const ALT_FILL  = "F5F9FC";

const cellMargins = { top: 60, bottom: 60, left: 100, right: 100 };

function cell(text, { bold = false, fill = null, color = null, width, align = AlignmentType.LEFT, size = 19 } = {}) {
  return new TableCell({
    borders,
    width: width ? { size: width, type: WidthType.DXA } : undefined,
    shading: fill ? { fill, type: ShadingType.CLEAR } : undefined,
    margins: cellMargins,
    children: [new Paragraph({
      alignment: align,
      children: [new TextRun({ text, bold, color: color || (fill === HEAD_FILL ? "FFFFFF" : "1A1A1A"), size })],
    })],
  });
}

function headerRow(cells, widths) {
  return new TableRow({
    children: cells.map((t, i) => cell(t, { bold: true, fill: HEAD_FILL, width: widths[i] })),
  });
}

function dataRow(cells, widths, shade = false) {
  return new TableRow({
    children: cells.map((t, i) => cell(t, { width: widths[i], fill: shade ? ALT_FILL : null })),
  });
}

function table(widths, rows) {
  const total = widths.reduce((a, b) => a + b, 0);
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths, rows });
}

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
}
function h3(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(text)] });
}
function p(text, opts = {}) {
  return new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text, ...opts })] });
}
function bullet(text, opts = {}) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 40 },
    children: [new TextRun({ text, ...opts })],
  });
}
function note(text) {
  return new Paragraph({
    spacing: { after: 160, before: 80 },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: "1B3A5C", space: 8 } },
    indent: { left: 200 },
    children: [new TextRun({ text, italics: true, color: "44546A", size: 19 })],
  });
}
function caption(text) {
  return new Paragraph({ spacing: { before: 40, after: 160 }, children: [new TextRun({ text, italics: true, size: 18, color: "666666" })] });
}
function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}
function mono(text) {
  return new Paragraph({
    spacing: { after: 160 },
    shading: { fill: "F4F4F4", type: ShadingType.CLEAR },
    indent: { left: 200 },
    children: [new TextRun({ text, font: "Consolas", size: 18 })],
  });
}

// Standard col widths (content width 9360)
const W3 = [3120, 3120, 3120];
const W4 = [2200, 1600, 2280, 3280];
const W5 = [2600, 1300, 1300, 2080, 2080];

// ════════════════════════════════════════════════════════════════════════════
const children = [];

// ── TITLE ─────────────────────────────────────────────────────────────────────
children.push(
  new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "PVA Platform — Comp Search Architecture &", bold: true, size: 36 })] }),
  new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: "Similarity Scoring / Weighting Framework", bold: true, size: 36 })] }),
  new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "Spike Reference Doc — FR27.1, FR27.2.1, FR27.2.2, FR28.GAP4", italics: true, color: "666666", size: 20 })] }),
  new Paragraph({ spacing: { after: 320 }, children: [new TextRun({ text: "Companion to: Comparable Selection and Attribute Weighting (subdocument)", italics: true, color: "666666", size: 20 })] }),
);

// ── REVIEW NOTES ON SUBDOCUMENT ──────────────────────────────────────────────
children.push(h1("0. Review of Submitted Subdocument"));
p("");
children.push(p("The subdocument is strong and production-ready. It already nails the highest-risk decisions: hybrid search UX, mandatory pre-search filters, the two-tier universal/bonus weight architecture, and null-handling rules. The content below is folded in as-is. Suggested refinements before finalizing:"));
children.push(
  bullet("Clean up the Multi-Family weight table — the \u201CWhat you measure\u201D cell for Proximity reads \u201CGBA? No — use unit count\u201D, which looks like an internal editing note. Replace with \u201CDistance from subject; unit count is the relevant size metric for MF (see Size row)\u201D."),
  bullet("The Office table mixes the \u201CType\u201D and rationale columns inconsistently (e.g. \u201CSlight reduction \u2014 office investors look market-wide\u201D sits in the Type column). Recommend splitting into a dedicated \u201CP1 Adjustment Note\u201D column so the Type column stays consistent (\u201CFixed \u2014 universal\u201D / \u201CBonus\u201D) across all property-type tables."),
  bullet("Add explicit normalization formulas for Proximity and Recency (done in Section 3 below) \u2014 the subdoc defines Size (pct_delta) but not the other two universal dimensions, which a developer will need."),
  bullet("Extend weight tables to the remaining PVA property types (Industrial, Hotel, Self-Storage, Senior Housing, MHC, Land) using the same two-tier pattern \u2014 added in Section 6."),
  bullet("Add a short \u201Cwhy WAM and not ML\u201D justification for the appraiser/compliance audience \u2014 added in Section 2, since FR-level docs will be read by non-engineers."),
);
note("Everything else in the subdocument \u2014 the hybrid search recommendation, mandatory pre-search filters, universal core table, null-handling table, and Step 1\u20134 example flow \u2014 is adopted unchanged and reproduced in Sections 1, 4, 5 and Appendix A.");

// ── EXECUTIVE SUMMARY ─────────────────────────────────────────────────────────
children.push(h1("1. Executive Summary & Final Recommendation"));
children.push(p("For a platform supporting 10\u201320 property types with thousands\u2013millions of historical transactions and a hard requirement for appraiser/regulator explainability, the recommended approach is:"));
children.push(
  bullet("Algorithm: Weighted Additive Model (WAM) with distance decay \u2014 a transparent weighted-sum model, not a black-box ML model, for v1 production scoring.", { bold: false }),
  bullet("Search UX: Hybrid \u2014 Approach 1 (instant ranked results from address + property type) as default, Approach 2 (filter panel) as collapsible refinement."),
  bullet("Attribute architecture: Two-tier \u2014 6 universal dimensions (100% base) + property-type bonus signals (additive, capped at +20)."),
  bullet("Weight source: Expert-defined starting weights (Section 6 tables), validated by appraisers during this spike, with a roadmap to statistical calibration (regression / SHAP) once \u2265 6\u201312 months of selection-outcome data exists (Section 8)."),
  bullet("Storage: Snapshot composite score + full per-dimension breakdown + scoring_version at comp-selection time (already defined in the prior spike output)."),
);
note("This combination is what CoStar, CBRE, JLL, Cushman & Wakefield, RealPage and Fannie Mae's Collateral Underwriter all converge on for production comp-ranking: an explainable weighted model as the scoring engine, wrapped in a hybrid search-then-filter UX. Pure ML scoring (XGBoost/LightGBM) is used by large AVM providers for automated value estimates (the dollar number), not for comp ranking/selection \u2014 because USPAP requires the appraiser to see and reason about why a comp was suggested.");

// ════════════════════════════════════════════════════════════════════════════
children.push(pageBreak());
children.push(h1("2. Similarity Scoring Algorithm Comparison"));
p("");
children.push(p("Eight approaches are commonly discussed for comp similarity / valuation modelling. The table below compares them on production fit for a comp-ranking use case (not full AVM price estimation)."));
children.push(table([1500, 2360, 2360, 1620, 1520], [
  headerRow(["Algorithm","How it works","Pros","Cons","Used in production by"], [1500,2360,2360,1620,1520]),
  dataRow(["Weighted Linear Combination (WLC)","Score = \u03A3(weight\u1D62 \u00D7 normalized_attr\u1D62). Simple sum of weighted, 0\u20131 normalized attributes.","Fully transparent; trivial to audit; easy to tune per property type","Assumes attributes are independent and linearly additive \u2014 ignores interactions","Most enterprise CMA tools (baseline form)"], [1500,2360,2360,1620,1520], false),
  dataRow(["Gower's Coefficient","Generalized similarity index that natively mixes numeric, categorical, binary and ordinal types in one distance metric (0\u20131 per pair, then averaged)","Handles mixed data types elegantly without manual normalization rules","Less intuitive to explain to appraisers; weighting per-type still needed; less common in real-estate tooling","Mostly academic / data-science AVM research, some niche proptech"], [1500,2360,2360,1620,1520], true),
  dataRow(["Weighted Euclidean Distance (WED)","Distance = \u221A\u03A3(weight\u1D62 \u00D7 (attr_subject \u2212 attr_comp)\u00B2). Lower distance = more similar.","Good for k-NN style \u201Cfind nearest comps\u201D; works well with continuous variables","Categorical variables need awkward encoding; squared term over-penalizes large gaps in one attribute","Zillow/Redfin-style \u201Csimilar homes\u201D (residential AVMs)"], [1500,2360,2360,1620,1520], false),
  dataRow(["Weighted Average","Simple average of per-attribute scores using weights as %, no decay/curve shaping","Easiest possible implementation","Treats all relationships as linear; no decay curve for distance/time \u2014 unrealistic for proximity & recency","Legacy/manual spreadsheet CMA tools"], [1500,2360,2360,1620,1520], true),
  dataRow(["WAM + Distance Decay (recommended)","WLC, but proximity & recency use non-linear decay curves (exponential/step) instead of raw linear difference","Transparent AND realistic \u2014 a comp 0.5mi away should score much closer to a comp at 1mi than the linear gap implies; same for a 2-month-old sale vs 24-month-old","Decay curve parameters need calibration per market/property type","CoStar Suggested Comps, RealPage rent comps, Fannie Mae CU proximity scoring"], [1500,2360,2360,1620,1520], false),
  dataRow(["Hedonic Regression","Statistical model: Price = \u03B2\u2080 + \u03B2\u2081(size) + \u03B2\u2082(age) + \u03B2\u2083(location)... estimates each attribute's $ contribution to value","Produces $ adjustments directly (not just similarity) \u2014 useful for sales-comparison grid adjustments; well-established, regulator-familiar","Requires substantial clean transaction history per market/property type; coefficients can be unstable with sparse data; doesn't rank comps by itself","Fannie Mae/Freddie Mac AVMs, county assessor mass-appraisal systems"], [1500,2360,2360,1620,1520], true),
  dataRow(["Gradient Boosting (XGBoost / LightGBM / CatBoost)","ML ensemble trained on historical transactions to predict price or a similarity/relevance label; feature importances derived post-hoc","Highest raw accuracy when data volume is large; captures non-linear interactions automatically (e.g. \u201Csize matters more for industrial than office\u201D)","Black-box without SHAP; needs large, clean, labeled training sets per property type; harder to explain to appraisers/auditors in real time; weight drift over time needs monitoring","Zillow Zestimate, large bank AVMs (value estimation, not comp ranking)"], [1500,2360,2360,1620,1520], false),
  dataRow(["Hybrid (WAM core + ML-informed weight tuning)","WAM/WLC remains the scoring formula shown to users; ML (regression/GBM + SHAP) is run offline periodically to suggest updated weights, which a human approves","Best of both \u2014 explainable real-time scoring, data-driven weight evolution, full audit trail of weight changes","Requires building both systems; ML pipeline is \u201Cadvisory\u201D only initially, adds engineering overhead","CoStar/CBRE-class platforms; recommended end-state for PVA"], [1500,2360,2360,1620,1520], true),
]));
caption("Table 2.1 \u2014 Algorithm comparison for comp similarity scoring.");

children.push(h2("2.1 Recommendation: WAM + Distance Decay, with a Hybrid Roadmap"));
children.push(p("Build the v1 scoring engine as WAM + distance decay (row 5 above) \u2014 it is the direct evolution of the subdocument's universal/bonus model and requires no historical transaction corpus to launch. Plan the Hybrid model (row 8) as the v2 enhancement once 6\u201312 months of appraiser comp-selection data accumulates (Section 8 explains exactly how that calibration works)."));
children.push(p("Why not ML for v1, in one sentence for non-engineering stakeholders: \u201Cthe score has to be something an appraiser can defend in a USPAP report and a regulator can re-derive by hand \u2014 a weighted sum with visible inputs does that; a trained model does not, until it's been running long enough to validate.\u201D"));

// ════════════════════════════════════════════════════════════════════════════
children.push(pageBreak());
children.push(h1("3. Similarity Score Calculation \u2014 Formulas by Data Type"));
p("");
children.push(p("Each of the six universal dimensions (Section 5) and every bonus signal (Section 6) is normalized to a 0\u2013100 (or 0\u20131) sub-score before weighting. The normalization function depends on the attribute's data type."));

children.push(h2("3.1 Geographic attributes (Proximity)"));
children.push(p("Use great-circle (haversine) distance between subject and comp lat/long, then apply exponential decay \u2014 not a linear ratio, because the marginal difference between 0.5mi and 1mi matters far more than between 9mi and 9.5mi:"));
children.push(mono("Proximity_Score = 100 \u00D7 e^(\u2212\u03BB \u00D7 distance_miles)\n\u03BB tuned per property type, e.g.:\n  Multi-Family / Retail (tight trade area): \u03BB = 0.5  \u2192  1mi\u224861, 3mi\u224822, 5mi\u22488\n  Industrial / Land (wider draw):          \u03BB = 0.15 \u2192 1mi\u224886, 5mi\u224847, 10mi\u224822"));
children.push(p("This is a non-linear decay curve, as recommended in Q2 \u2014 linear distance scoring would treat a 9mi gap and a 9.5mi gap as nearly identical to a 0.5mi vs 1mi gap, which does not match how appraisers actually weigh proximity."));

children.push(h2("3.2 Temporal attributes (Recency)"));
children.push(p("Step-decay (band-based) rather than continuous \u2014 matches how appraisers think in \u201Cwithin 6 months / within 12 months / stale\u201D buckets, and is easier to explain in an audit:"));
children.push(mono("Recency_Score = 100   if months_since_sale \u2264 6\n              =  85   if 6  < months_since_sale \u2264 12\n              =  65   if 12 < months_since_sale \u2264 24\n              =  40   if 24 < months_since_sale \u2264 36\n              =  15   if months_since_sale > 36"));

children.push(h2("3.3 Numerical attributes (Size, Cap Rate, Clear Height, etc.)"));
children.push(p("Percent-delta, floored at zero \u2014 as already defined in the subdocument for size, this generalizes to any continuous numeric attribute:"));
children.push(mono("Attr_Score = max(0, 100 \u00D7 (1 \u2212 |Subject_Val \u2212 Comp_Val| / Subject_Val))\n\nExample (cap rate): Subject 4.8%, Comp 5.1% \u2192 100 \u00D7 (1 \u2212 0.3/4.8) = 93.75"));
children.push(p("For attributes where the relationship is non-linear in practice (e.g. clear height \u2014 a 2ft difference matters a lot below 28ft but barely above 32ft), apply a property-type-specific cap on the denominator rather than raw percent, documented per bonus signal in Section 6."));

children.push(h2("3.4 Categorical attributes (Property Subtype, Quality Class, Rent Type)"));
children.push(p("Hierarchy/tier match \u2014 not a simple 0/1 \u2014 because \u201CClass A vs Class B\u201D should score higher than \u201CClass A vs Class C\u201D:"));
children.push(mono("Exact match            \u2192 100\n1 tier apart (A vs B)  \u2192  60\n2+ tiers apart (A vs C)\u2192  20\nHard-filter mismatch   \u2192   0  (e.g. NNN vs Gross lease type \u2014 see penalty rule, Section 4)"));

children.push(h2("3.5 Linear vs non-linear \u2014 summary"));
children.push(table(W4, [
  headerRow(["Attribute","Function used","Linear or non-linear","Why"], W4),
  dataRow(["Proximity","Exponential decay","Non-linear","Near comps disproportionately more relevant; matches appraiser intuition and CoStar/RealPage behaviour"], W4, false),
  dataRow(["Recency","Step/band decay","Non-linear (discrete)","Matches appraisal report language (\u201Cwithin 6 months\u201D); easy to audit"], W4, true),
  dataRow(["Size, cap rate, numeric bonuses","Percent-delta, floored at 0","Linear (with floor)","Simple, explainable; floor prevents negative scores from extreme outliers"], W4, false),
  dataRow(["Categorical / class / type","Tiered hierarchy match","Non-linear (stepped)","Captures \u201Cclose but not exact\u201D matches (A vs B) vs \u201Cfar apart\u201D (A vs C)"], W4, true),
]));
caption("Table 3.1 \u2014 Function choice per data type.");

// ════════════════════════════════════════════════════════════════════════════
children.push(pageBreak());
children.push(h1("4. Two-Tier Attribute Architecture (from subdocument, adopted)"));
p("");
children.push(p("To support 10\u201320 property types without maintaining 10\u201320 unrelated weight tables, use a Two-Tier model:"));
children.push(
  bullet("Tier 1 \u2014 Universal Core (6 dimensions, sum to 100%): Proximity, Recency, Size, Property Type Match, Data Completeness, Prior Usage. Always present, always scored, for every property type. The weight stays fixed; only the underlying metric and decay parameters change per type (e.g. Size = unit count for MF, NRA for office, GBA for industrial)."),
  bullet("Tier 2 \u2014 Property-Type Bonus Layer (additive, capped at +20 points): activates only when both subject and comp have the relevant field populated. Never penalizes missing data \u2014 \u201Cnull means unknown, not negative.\u201D"),
);
children.push(mono("Final_Normalized_Score = ((Base_Score + Total_Bonus_Points) / (100 + Max_Possible_Bonus)) \u00D7 100"));

children.push(h2("4.1 Null-handling and penalty rules (adopted from subdocument)"));
children.push(table(W4, [
  headerRow(["Scenario","Rule","Example","Effect"], W4),
  dataRow(["Universal dimension field null on comp","Skip dimension; redistribute its weight proportionally across remaining universal dimensions","GBA missing \u2192 Size dropped; Proximity 30%\u219237.5%, Recency 20%\u219225%, Type 15%\u219218.75%, Completeness 10%\u219212.5%, Usage 5%\u21926.25%","Score remains comparable across comps with different data completeness"], W4, false),
  dataRow(["Bonus field null on either side","Skip bonus entirely \u2014 no add, no subtract","Cap rate missing on comp \u2192 no cap-rate bonus applied to anyone","Composite unaffected; never penalize for unknown"], W4, true),
  dataRow(["All bonuses populated","Apply every qualifying bonus; cap total at 100","MF comp: +5 unit mix, +5 class, +5 submarket, +3 occupancy = +17 \u2192 76 base \u2192 93 final","Reflects a genuinely excellent comp"], W4, false),
  dataRow(["Near-hard-filter mismatch","Severe penalty multiplier on the affected dimension (\u2192 near 0), comp stays visible but ranks low","NNN subject vs Gross-lease comp \u2192 Type Match \u2192 0.1 \u2192 final score < 50 regardless of other dimensions","Comp isn't hidden (appraiser can still see/justify it) but is clearly de-prioritized"], W4, true),
]));
caption("Table 4.1 \u2014 Null and penalty handling, unchanged from subdocument.");

// ════════════════════════════════════════════════════════════════════════════
children.push(pageBreak());
children.push(h1("5. Universal Core Attribute Weight Table"));
p("");
children.push(p("These six dimensions apply to every property type. The weight (%) is fixed; only the measurement metric and decay parameters vary by property type (Section 6)."));
children.push(table([1700,1100,2360,4200], [
  headerRow(["Attribute","Weight","Formula (Section 3)","Why it's universal"], [1700,1100,2360,4200]),
  dataRow(["Proximity","30%","Haversine + exponential decay","#1 adjustment in every appraisal grid, every property type"], [1700,1100,2360,4200], false),
  dataRow(["Recency","20%","Step/band decay","Market conditions affect every property type; stale comps need larger adjustments"], [1700,1100,2360,4200], true),
  dataRow(["Size similarity","20%","Percent-delta (metric varies by type)","Every property has a primary size metric \u2014 importance constant, the ruler changes"], [1700,1100,2360,4200], false),
  dataRow(["Property type match","15%","Tiered hierarchy match","Subtype granularity matters even after hard-filtering on major type"], [1700,1100,2360,4200], true),
  dataRow(["Data completeness","10%","% of FR27.1-required fields populated","Data quality is a universal concern regardless of property type"], [1700,1100,2360,4200], false),
  dataRow(["Prior usage","5%","Log-scaled times_used, filtered by type + MSA","Tiebreaker \u2014 comps validated by many appraisers rank slightly higher"], [1700,1100,2360,4200], true),
]));
caption("Table 5.1 \u2014 Universal core (sums to 100% base score).");

// ════════════════════════════════════════════════════════════════════════════
children.push(pageBreak());
children.push(h1("6. Property-Type Weight Tables"));
p("");
children.push(note("The original research prompt referenced generic property categories (residential apartments, villas, plots, agricultural land). PVA's actual supported property set is commercial/multifamily-oriented (10 types from Settings \u2192 Property Major Type). The tables below use PVA's real property types so they map directly to existing fields. If residential land/villas enter scope later, they slot into the same two-tier framework using the Land/Industrial pattern as a starting template."));

children.push(h2("6.1 Multi-Family (adopted from subdocument)"));
children.push(table(W5, [
  headerRow(["Attribute","Weight","Type","Metric","Why"], W5),
  dataRow(["Proximity","30%","Universal","Distance from subject; \u03BB=0.5 decay","#1 adjustment in MF sales grids"], W5, false),
  dataRow(["Recency","20%","Universal","Sale/lease date vs effective date","MF market reprices fast"], W5, true),
  dataRow(["Size similarity","20%","Universal (metric varies)","Unit count delta (not GBA)","Unit count is the MF size comparator"], W5, false),
  dataRow(["Property type match","15%","Universal","MF subtype: Garden / Mid-Rise / High-Rise / SRO","Garden vs High-Rise = different buyer pool"], W5, true),
  dataRow(["Data completeness","10%","Universal","FR27.1 MF minimum fields","Standard"], W5, false),
  dataRow(["Prior usage","5%","Universal","times_used, filtered MF + MSA","Tiebreaker"], W5, true),
  dataRow(["Unit mix similarity","+5 bonus","MF-specific","Cosine similarity of BR/BA mix vector","Most important MF-specific signal"], W5, false),
  dataRow(["Quality class match","+5 bonus","MF, Office, Retail, Industrial","Class A/B/C tiered match","Strong appraiser-entered signal"], W5, true),
  dataRow(["Submarket match","+5 bonus","MF, Office, Retail","CoStar submarket tag","Major metros only"], W5, false),
  dataRow(["Occupancy at sale","+3 bonus","MF, MHC, Self-Storage, Senior","Occupancy % delta","Indicates stabilization comparability"], W5, true),
]));
caption("Table 6.1 \u2014 Multi-Family (max bonus = +18, normalized against +20 cap).");

children.push(h2("6.2 Office (adopted from subdocument, refined per Review Note)"));
children.push(table([2300,1100,1500,2800,1660], [
  headerRow(["Attribute","Weight","Type","Metric","P1 Note"], [2300,1100,1500,2800,1660]),
  dataRow(["Proximity","30%","Universal","Distance; \u03BB=0.3","Consider 25% for office in P1 \u2014 submarket bonus compensates"], [2300,1100,1500,2800,1660], false),
  dataRow(["Recency","20%","Universal","Sale/lease date","Standard"], [2300,1100,1500,2800,1660], true),
  dataRow(["Size similarity (NRA)","20%","Universal (metric varies)","NRA delta, not GBA","NRA is the office size metric"], [2300,1100,1500,2800,1660], false),
  dataRow(["Property type match","15%","Universal","Subtype: CBD / Suburban / Medical / Co-Working","Medical vs standard office = different market"], [2300,1100,1500,2800,1660], true),
  dataRow(["Data completeness","10%","Universal","FR27.1 Office fields","Standard"], [2300,1100,1500,2800,1660], false),
  dataRow(["Prior usage","5%","Universal","times_used, Office + MSA","Standard"], [2300,1100,1500,2800,1660], true),
  dataRow(["Quality class (A/B/C)","+5 bonus","Office, Retail, Industrial","Tiered class match","Most important office-specific signal after proximity"], [2300,1100,1500,2800,1660], false),
  dataRow(["Submarket match","+4 bonus","Office, MF, Retail","CoStar submarket","Office submarkets well-defined and material"], [2300,1100,1500,2800,1660], true),
  dataRow(["Parking ratio","+4 bonus","Office, Retail","Spaces / 1,000 SF, pct-delta","Suburban office buyers care deeply"], [2300,1100,1500,2800,1660], false),
  dataRow(["Tenant credit rating","+4 bonus","Office, Retail","Credit tier of primary tenant","Credit tenant NNN = premium"], [2300,1100,1500,2800,1660], true),
  dataRow(["Cap rate proximity","+3 bonus","All income properties","<50bps delta","Sparse \u2014 bonus only"], [2300,1100,1500,2800,1660], false),
]));
caption("Table 6.2 \u2014 Office (max bonus = +20).");

children.push(h2("6.3 Retail (adopted from subdocument)"));
children.push(table(W5, [
  headerRow(["Attribute","Weight","Type","Metric","Why"], W5),
  dataRow(["Proximity (trade area)","30%","Universal","Distance; \u03BB=0.5 (tighter trade area)","Trade area is smaller than most property types"], W5, false),
  dataRow(["Recency","20%","Universal","Sale/lease date","Standard"], W5, true),
  dataRow(["Size (GBA/NRA)","20%","Universal (metric varies)","NRA for lease comps, GBA for sales","Standard"], W5, false),
  dataRow(["Property type match","15%","Universal","Subtype: strip / neighborhood / power / single-tenant","Single-tenant NNN vs multi-tenant very different"], W5, true),
  dataRow(["Data completeness","10%","Universal","FR27.1 Retail fields","Standard"], W5, false),
  dataRow(["Prior usage","5%","Universal","times_used, Retail + MSA","Standard"], W5, true),
  dataRow(["Tenant type / credit rating","+5 bonus","Retail, Office","National credit vs local tenant","Credit tenant \u2192 lower cap rate"], W5, false),
  dataRow(["Anchor tenant presence","+4 bonus","Retail (Shopping Center)","Anchored vs unanchored strip","Major value driver"], W5, true),
  dataRow(["Parking ratio","+4 bonus","Retail, Office","Spaces / 1,000 SF","Critical for suburban retail"], W5, false),
  dataRow(["Submarket match","+4 bonus","Retail, MF, Office","CoStar submarket","Urban vs suburban distinctions"], W5, true),
  dataRow(["Cap rate proximity","+3 bonus","All income properties","<50bps delta","Sparse \u2014 bonus only"], W5, false),
]));
caption("Table 6.3 \u2014 Retail (max bonus = +20).");

children.push(h2("6.4 Industrial (new)"));
children.push(table(W5, [
  headerRow(["Attribute","Weight","Type","Metric","Why"], W5),
  dataRow(["Proximity","22%","Universal (reduced)","Distance; \u03BB=0.15 (wide draw radius)","Industrial users draw from a wider geography \u2014 reduce vs default 30%, redistribute +8 to clear height/dock bonuses"], W5, false),
  dataRow(["Recency","16%","Universal (reduced)","Sale/lease date","Industrial pricing moves more slowly than MF"], W5, true),
  dataRow(["Size (GBA)","20%","Universal","GBA delta","Standard size comparator for industrial"], W5, false),
  dataRow(["Property type match","15%","Universal","Subtype: Warehouse/Distribution, Flex/R&D, Manufacturing, Cold Storage","Cold storage vs dry warehouse = very different buyer pool"], W5, true),
  dataRow(["Data completeness","10%","Universal","FR27.1 Industrial fields","Standard"], W5, false),
  dataRow(["Prior usage","5%","Universal","times_used, Industrial + MSA","Standard"], W5, true),
  dataRow(["Clear height similarity","+6 bonus","Industrial-specific","Absolute ft delta, capped at \u00B18ft","Below 28ft a 2ft gap matters a lot; above 32ft it barely matters"], W5, false),
  dataRow(["Dock door ratio","+5 bonus","Industrial-specific","Doors per 10,000 SF, pct-delta","Functional fit for distribution use"], W5, true),
  dataRow(["Quality class match","+3 bonus","Industrial, Office, Retail","Tiered class match","Standard quality signal"], W5, false),
  dataRow(["Cap rate proximity","+3 bonus","All income properties","<50bps delta","Sparse \u2014 bonus only"], W5, true),
]));
caption("Table 6.4 \u2014 Industrial (universal redistributed to 88% + 17 bonus, normalized to 100/+20 cap).");

children.push(h2("6.5 Hotel / Hospitality (new)"));
children.push(table(W5, [
  headerRow(["Attribute","Weight","Type","Metric","Why"], W5),
  dataRow(["Proximity","26%","Universal (reduced)","Distance; \u03BB=0.3","Hotel demand draws from a metro/corridor, slightly wider than retail"], W5, false),
  dataRow(["Recency","18%","Universal (reduced)","Sale date","Hotel values track RevPAR cycles \u2014 redistribute 6% combined to RevPAR/ADR bonuses"], W5, true),
  dataRow(["Size (room count)","20%","Universal (metric varies)","Room count delta","Primary hotel size comparator"], W5, false),
  dataRow(["Property type match","15%","Universal","Chain scale tier: Luxury \u2192 Economy","Chain scale defines comp pool more than physical similarity"], W5, true),
  dataRow(["Data completeness","10%","Universal","FR27.1 Hotel fields","Standard"], W5, false),
  dataRow(["Prior usage","5%","Universal","times_used, Hotel + MSA","Standard"], W5, true),
  dataRow(["RevPAR proximity","+6 bonus","Hotel-specific","Percent-delta, capped at \u00B125%","Strongest operating-performance comparator"], W5, false),
  dataRow(["ADR proximity","+5 bonus","Hotel-specific","Percent-delta","Complements RevPAR"], W5, true),
  dataRow(["Brand/flag match","+3 bonus","Hotel-specific","Exact / same-parent-company tiered match","Franchise agreements affect cash flow"], W5, false),
  dataRow(["Occupancy at sale","+2 bonus","Hotel, MF, MHC, Self-Storage, Senior","Occupancy % delta","Stabilization comparability"], W5, true),
]));
caption("Table 6.5 \u2014 Hotel (universal redistributed to 94% + 16 bonus).");

children.push(h2("6.6 Self-Storage, Senior Housing, MHC, Land \u2014 condensed"));
children.push(p("These four types follow the identical universal-core pattern (Proximity / Recency / Size / Type Match / Completeness / Prior Usage at the standard 30/20/20/15/10/5 split unless noted). Only the bonus layer and size metric differ:"));
children.push(table([1700,1500,2660,3500], [
  headerRow(["Property Type","Size metric","Bonus signals (additive, max +20)","Notes"], [1700,1500,2660,3500]),
  dataRow(["Self-Storage","Net rentable SF","+6 % climate-controlled match (pct-delta) \u00B7 +5 occupancy at sale \u00B7 +5 unit-mix cosine similarity \u00B7 +4 cap rate proximity","Climate-control mix is the single biggest driver of value/SF differences within self-storage"], [1700,1500,2660,3500], false),
  dataRow(["Senior Housing","Bed/unit count","+6 % private-pay mix (pct-delta) \u00B7 +5 care level tiered match (IL/AL/Memory/SNF) \u00B7 +5 occupancy at sale \u00B7 +4 cap rate proximity","Care level acts almost like a hard filter \u2014 IL vs SNF should rarely co-rank highly even before bonuses"], [1700,1500,2660,3500], true),
  dataRow(["Manufactured Housing Community (MHC)","Pad/site count","+6 utility structure match (direct-bill vs submeter, tiered) \u00B7 +5 occupancy at sale \u00B7 +5 home-ownership mix (tenant-owned vs park-owned, pct-delta) \u00B7 +4 cap rate proximity","Utility billing structure materially changes NOI \u2014 must match for a comp to be truly comparable"], [1700,1500,2660,3500], false),
  dataRow(["Land (any subtype)","Acreage / lot SF","+6 zoning designation tiered match (exact \u2192 same category \u2192 different) \u00B7 +5 entitlement status match (raw/entitled/permitted) \u00B7 +5 topography/utility-access similarity \u00B7 +4 highest-and-best-use alignment","Zoning is close to a hard filter \u2014 raw agricultural land vs entitled commercial pad should score near zero even at 0.1mi"], [1700,1500,2660,3500], true),
]));
caption("Table 6.6 \u2014 Self-Storage, Senior Housing, MHC, and Land condensed bonus layers.");

// ════════════════════════════════════════════════════════════════════════════
children.push(pageBreak());
children.push(h1("7. Worked Examples"));
p("");
children.push(h2("7.1 Example similarity score calculation (Multi-Family)"));
children.push(p("Subject: 245-unit Garden/Low-Rise, Class B+, Cupertino CA. Comp: Sunnyvale Gardens, 230 units, Garden/Low-Rise, Class B+, 0.4mi away, sold 4 months ago, 92% occupied at sale, BR/BA mix nearly identical to subject."));
children.push(table([3400,1400,1400,3160], [
  headerRow(["Dimension","Weight","Sub-score","Contribution"], [3400,1400,1400,3160]),
  dataRow(["Proximity (0.4mi, \u03BB=0.5)","30%","100\u00D7e^(\u22120.5\u00D70.4)=82","24.6"], [3400,1400,1400,3160], false),
  dataRow(["Recency (4 months)","20%","100 (\u22646mo band)","20.0"], [3400,1400,1400,3160], true),
  dataRow(["Size \u2014 unit count (245 vs 230)","20%","100\u00D7(1\u221215/245)=93.9","18.8"], [3400,1400,1400,3160], false),
  dataRow(["Property type match (Garden vs Garden)","15%","100 (exact)","15.0"], [3400,1400,1400,3160], true),
  dataRow(["Data completeness (18/20 fields)","10%","90","9.0"], [3400,1400,1400,3160], false),
  dataRow(["Prior usage (used 3x in MSA)","5%","60 (log-scaled)","3.0"], [3400,1400,1400,3160], true),
  dataRow(["Base Score (sum)","100%","\u2014","90.4"], [3400,1400,1400,3160], false),
  dataRow(["Bonus: Unit mix cosine sim. (0.97)","+5 max","97% of 5","+4.85"], [3400,1400,1400,3160], true),
  dataRow(["Bonus: Quality class match (B+ = B+)","+5 max","exact","+5.00"], [3400,1400,1400,3160], false),
  dataRow(["Bonus: Submarket match (same)","+5 max","exact","+5.00"], [3400,1400,1400,3160], true),
  dataRow(["Bonus: Occupancy at sale (92% vs 94% subj.)","+3 max","98% of 3","+2.94"], [3400,1400,1400,3160], false),
  dataRow(["Total Bonus","\u2014","\u2014","17.79"], [3400,1400,1400,3160], true),
  dataRow(["Final Normalized Score","((90.4+17.79)/(100+20))\u00D7100","\u2014","90.2"], [3400,1400,1400,3160], false),
]));
caption("Table 7.1 \u2014 Worked similarity score: result \u2248 90 / 100, a top-tier comp.");

children.push(h2("7.2 Example valuation calculation using ranked comps (sales comparison)"));
children.push(p("With comps ranked by similarity score, the appraiser typically weights adjusted comp indications by their similarity score when reconciling to a value/unit \u2014 a defensible, transparent reconciliation method:"));
children.push(table([2800,1500,1800,1700,1560], [
  headerRow(["Comp","Similarity Score","Adj. Price/Unit","Weight (score/\u03A3scores)","Weighted Contribution"], [2800,1500,1800,1700,1560]),
  dataRow(["Sunnyvale Gardens","90.2","$268,500","90.2/301.0 = 30.0%","$80,610"], [2800,1500,1800,1700,1560], false),
  dataRow(["Cupertino Village","81.4","$251,000","81.4/301.0 = 27.0%","$67,800"], [2800,1500,1800,1700,1560], true),
  dataRow(["The Meadows, Santa Clara","68.3","$274,000","68.3/301.0 = 22.7%","$62,182"], [2800,1500,1800,1700,1560], false),
  dataRow(["Saratoga Oaks, San Jose","61.1","$259,500","61.1/301.0 = 20.3%","$52,679"], [2800,1500,1800,1700,1560], true),
  dataRow(["\u03A3 / Indicated Value per Unit","301.0","\u2014","100%","$263,271 \u2192 ~$264,000/unit"], [2800,1500,1800,1700,1560], false),
]));
caption("Table 7.2 \u2014 Similarity-weighted reconciliation: indicated value \u2248 $264,000/unit \u00D7 245 units \u2248 $64.7M. The similarity score informs reconciliation weight, but final value remains an appraiser judgment, not an automated output (per Executive Summary).");

// ════════════════════════════════════════════════════════════════════════════
children.push(pageBreak());
children.push(h1("8. Weight Determination Methodology"));
p("");
children.push(h2("8.1 Phase 1 (launch): Expert-defined weights"));
children.push(p("The weights in Section 6 are expert-defined starting points based on appraisal-grid adjustment conventions (proximity and recency dominate every grid; size and type match are the next-most-common adjustments). This is the same starting point CoStar and CBRE used historically \u2014 production weights are rarely \u201Clearned from scratch\u201D; they start as expert priors and are then refined."));
children.push(p("During this spike's PVA/appraiser validation step, run the worked example (Section 7.1) past 2\u20133 senior appraisers per major property type and ask: \u201Cdoes a 90/100 score for this comp pair match your gut feel of how comparable these are?\u201D Adjust the six universal weights (not the bonus weights) based on consensus \u2014 bonus weights can be tuned per-property-type more freely since they're additive and capped.");

children.push(h2("8.2 Phase 2 (6\u201312+ months of data): Statistical calibration"));
children.push(p("Once the platform has accumulated comp-selection history (which comps appraisers actually chose vs skipped, for a given subject), three complementary techniques can refine weights:"));
children.push(
  bullet("Regression-based: Treat \u201Cwas this comp selected?\u201D as a binary outcome and run logistic regression with the six universal sub-scores + bonus sub-scores as predictors. The resulting coefficients suggest revised weights \u2014 e.g. if \u201Crecency sub-score\u201D has a much larger coefficient than 20% implies, appraisers are valuing recency more than the current weight reflects."),
  bullet("Feature importance extraction: Train a gradient-boosted classifier (same selected/skipped label) and extract feature importances (gain-based or permutation importance). This captures non-linear interactions the regression misses \u2014 e.g. \u201Cproximity matters much more when recency is poor.\u201D"),
  bullet("SHAP values: For the GBM model above, SHAP (SHapley Additive exPlanations) decomposes each prediction into per-feature contributions \u2014 directly comparable to the \u201Ccontribution\u201D column in Table 7.1. SHAP is the bridge between an opaque GBM and the explainable WAM format: SHAP values can be averaged across many predictions to produce updated universal/bonus weights that are still presented to users as a weighted-sum breakdown."),
  bullet("Model calibration technique: Run the above quarterly per property type + MSA cohort (need \u2265 ~200 selection events per cohort for stability). Present suggested weight deltas to a product/appraisal review board \u2014 never auto-deploy weight changes. Log every weight change with scoring_version bump (already defined in the storage spec) so historical scores remain reproducible."),
);
note("This is the \u201CHybrid\u201D row from Table 2.1 in practice: ML runs offline as an advisory weight-tuning process; the live scoring formula stays a transparent WAM. Appraisers and auditors only ever see and interact with the weighted-sum model \u2014 the ML layer is invisible infrastructure that keeps the weights current.");

// ════════════════════════════════════════════════════════════════════════════
children.push(pageBreak());
children.push(h1("9. Recommended Production Architecture"));
p("");
children.push(table([1800,3300,4260], [
  headerRow(["Layer","Component","Responsibility"], [1800,3300,4260]),
  dataRow(["1. Search","Hybrid search service (Section 1 / Appendix A)","Hard-filter on Property Type + geo-radius \u2192 returns candidate pool to scoring layer"], [1800,3300,4260], false),
  dataRow(["2. Scoring engine","WAM + decay calculator (Sections 3\u20136)","Computes 6 universal sub-scores + applicable bonus sub-scores per candidate; produces composite + breakdown JSON"], [1800,3300,4260], true),
  dataRow(["3. Config store","Weight tables per property type (versioned)","Section 6 tables as versioned config (DB-backed, not hardcoded) \u2014 enables scoring_version bumps without redeploy"], [1800,3300,4260], false),
  dataRow(["4. Presentation","Comp results UI (relevance bar, reason codes, breakdown panel \u2014 POC from prior spike)","Renders composite score, top reason codes, expandable breakdown; supports sort/filter/override per FR28.8.x"], [1800,3300,4260], true),
  dataRow(["5. Audit/storage","comp_similarity_score table (prior spike schema)","Snapshots composite_score, score_breakdown JSON, scoring_version, user_override at selection time"], [1800,3300,4260], false),
  dataRow(["6. Calibration (Phase 2)","Offline batch job: regression + GBM + SHAP (Section 8.2)","Quarterly weight-delta suggestions \u2192 human review \u2192 versioned config update (Layer 3)"], [1800,3300,4260], true),
]));
caption("Table 9.1 \u2014 Six-layer architecture: layers 1\u20135 ship in v1 (this spike's scope); layer 6 is the v2 roadmap item.");

// ════════════════════════════════════════════════════════════════════════════
children.push(pageBreak());
children.push(h1("Appendix A \u2014 End-to-End Search Flow Example (from subdocument)"));
p("");
children.push(p("Reproduced from the subdocument for completeness \u2014 this is the reference UX flow the architecture in Section 9 must support."));
children.push(h3("Step 1 \u2014 Required inputs (2 fields)"));
children.push(mono("Subject address:  20800 Homestead Road, Cupertino, CA\nProperty type:    Multi-Family\nSubject specs (optional): 50,000 SqFt, Built 2015\n\u2192 System auto-populates lat/long, GBA, unit count from parcel data\n\u2192 Search runs immediately against MF comp pool within default 1mi radius"));
children.push(h3("Step 2 \u2014 Instant results (no filters needed)"));
children.push(mono("Rank  Address                          Score  Prox  Rec  Size  Type  Data\n#1    18950 Vallco Pkwy, Cupertino    91    high  high high  high  high\n#2    10110 Bandley Dr, Cupertino     78    high  high med   high  high\n#3    3133 De Anza Blvd, San Jose      61    med   med  med   med   med\n#4    1161 Cadillac Ct, Milpitas       42    low   low  low   med   low"));
children.push(h3("Step 3 \u2014 Optional refinement (collapsed filter panel)"));
children.push(bullet("Date range \u2192 re-ranks within window"));
children.push(bullet("Size range (\u00B1%) \u2192 removes outliers, re-ranks remainder"));
children.push(bullet("Radius \u2192 expand/contract search boundary"));
children.push(bullet("Quality class \u2192 A/B/C filter"));
children.push(bullet("Submarket \u2192 same CoStar submarket only"));
children.push(p("Each filter re-ranks using the same score formula; the score pill remains visible throughout."));
children.push(h3("Step 4 \u2014 Select comps"));
children.push(bullet("Appraiser selects 3\u201310 comps \u2192 pulled into PVA adjustment grid"));
children.push(bullet("Score snapshot frozen at selection time (scoring_version + all dimension scores)"));
children.push(bullet("Search/expansion trail logged for the USPAP workfile"));

// ════════════════════════════════════════════════════════════════════════════
// Build & save
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: "Arial", color: "1B3A5C" },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, font: "Arial", color: "1B3A5C" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: "2E5A8C" },
        paragraph: { spacing: { before: 140, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 480, hanging: 240 } } } }] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, right: 1440, bottom: 1080, left: 1440 } } },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("/mnt/user-data/outputs/PVA_Similarity_Scoring_Weighting_Framework.docx", buf);
  console.log("done");
});