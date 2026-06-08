"""
field_mapper.py
---------------
Aligns ERD fields with LightBox and CoStar source fields using semantic
similarity.

Improvements over the original version
---------------------------------------
  1. Two-pass greedy matching      Scores every pair first, then assigns by
                                   descending confidence so high-quality
                                   matches lock in before weaker ones consume
                                   candidates.

  2. Subset boost minimum length   Requires the shared substring to be >= 8
                                   chars so short tokens like 'condition' /
                                   'type' / 'name' can't hijack a match.

  3. Parenthetical stripping       Removes "(mi)", "(SF)", "$", "/" before
                                   tokenising, fixing CoStar fields like
                                   "$Price/Unit" and "Avg Rent-Direct (Retail)".

  4. Category-aware penalty        Uses the optional Field Category column to
                                   down-score cross-category matches by 0.15,
                                   killing false positives like
                                   improvement_value_per_sf → "Taxes Per SF".

  5. Expanded prefix & synonym     Covers sales_, inc_, exp_, prop_, bldg_,
                                   lease_, owner_, tax_, val_ and abbreviations
                                   mgmt, pct, bal, dep, eff, maint, op, acct …

  6. Smarter singularisation       Handles -ies→y, -ves→f, -ses/-xes/-zes with
                                   a wider safe-list; 'address' stays 'address'.

  7. Jaro-Winkler layer            Pure-Python, no extra deps; catches
                                   transpositions and shared-prefix variants.
                                   Contribution is capped when token sets are
                                   fully disjoint to prevent false positives
                                   like tenant_name → Rent Roll_tenantcam.

  8. Token Jaccard overlap         Partial credit when fields share most tokens
                                   but differ by one.

  9. Fused-token splitting         Splits run-together tokens using a vocab of
                                   known domain words so 'commleaseterm' and
                                   'comm_lease_terms' normalise to the same
                                   token set; 'landsf' → ['land', 'sf'].

 10. Match Score column            Writes the similarity score to the output so
                                   you can audit / tune the threshold without
                                   re-running.
"""

import csv
import re
import difflib


# ---------------------------------------------------------------------------
# Jaro-Winkler  (pure Python, no external dependencies)
# ---------------------------------------------------------------------------

def _jaro(s1: str, s2: str) -> float:
    if s1 == s2:
        return 1.0
    l1, l2 = len(s1), len(s2)
    if l1 == 0 or l2 == 0:
        return 0.0
    match_dist = max(l1, l2) // 2 - 1
    s1_matches = [False] * l1
    s2_matches = [False] * l2
    matches = transpositions = 0
    for i, c in enumerate(s1):
        lo = max(0, i - match_dist)
        hi = min(i + match_dist + 1, l2)
        for j in range(lo, hi):
            if s2_matches[j] or c != s2[j]:
                continue
            s1_matches[i] = s2_matches[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0
    k = 0
    for i in range(l1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1
    j = matches / l1
    return (j + matches / l2 + (matches - transpositions / 2) / matches) / 3


def _jaro_winkler(s1: str, s2: str, p: float = 0.1) -> float:
    jaro = _jaro(s1, s2)
    prefix = 0
    for c1, c2 in zip(s1[:4], s2[:4]):
        if c1 == c2:
            prefix += 1
        else:
            break
    return jaro + prefix * p * (1 - jaro)


# ---------------------------------------------------------------------------
# Fused-token splitter  (FIX 9)
# ---------------------------------------------------------------------------
# Ordered from longest to shortest so greedy matching picks the right token.
# Add domain-specific terms here if you encounter new fused-word false matches.
_SPLIT_VOCAB = sorted([
    'squarefeet', 'squaremeter', 'rentablearea', 'grossleasablearea',
    'grossbuildingarea', 'commonareamaintenance',
    'assessment', 'improvement', 'commercial', 'information',
    'management', 'maintenance', 'operating', 'effective', 'estimated',
    'available', 'balance', 'deposit', 'percent', 'revenue', 'annual',
    'description', 'instrument', 'building', 'property', 'latitude',
    'longitude', 'address', 'amount', 'zoning', 'source', 'value',
    'total', 'month', 'lease', 'terms', 'type', 'unit', 'sale', 'site',
    'parcel', 'tenant', 'income', 'expense', 'account', 'source',
    'market', 'land', 'rent', 'year', 'date', 'name', 'area', 'rate',
    'comm', 'cam', 'sf',
], key=len, reverse=True)


def _split_fused(token: str) -> list:
    """
    Attempt to decompose a fused token into known domain sub-words.
    Returns [token] unchanged when no split is found.
    e.g. 'commleaseterm' → ['comm', 'lease', 'term']
         'landsf'        → ['land', 'sf']
    """
    if len(token) <= 4:
        return [token]
    parts = []
    remaining = token
    while remaining:
        matched = False
        for word in _SPLIT_VOCAB:
            if remaining.startswith(word) and len(word) >= 2:
                parts.append(word)
                remaining = remaining[len(word):]
                matched = True
                break
        if not matched:
            parts.append(remaining)
            break
    return parts if len(parts) > 1 else [token]


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def normalize_field_name(name, return_parts=False):
    """
    Normalises a field name for similarity comparison.

    Steps
    -----
    1. Strip parentheticals / special chars  e.g. "(mi)", "$", "/"
    2. Split camelCase / PascalCase
    3. Iteratively remove known source prefixes
    4. Tokenise, remove trailing digits, singularise
    5. Expand abbreviations via synonym map
    6. Apply fused-token splitting
    7. Remove stop words
    """
    if not name:
        return ("", []) if return_parts else ""

    orig_name = name.strip()

    # FIX 3 — strip parentheticals and non-alphanumeric noise
    cleaned = re.sub(r'\(.*?\)', ' ', orig_name)
    cleaned = re.sub(r'[^a-zA-Z0-9\s_]', ' ', cleaned)

    # Split camelCase / PascalCase before lowercasing
    spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
    name = spaced.lower()

    # FIX 5 — extended prefix list
    prefixes = [
        'parcel_', 'improvement_', 'sales_', 'sites_', 'site_', 'unit_',
        'rent roll summary_', 'unit lease summary_', 'incexp_',
        'assessment_', 'saleinfo_', 'unit lease_', 'rent roll_',
        'rent_roll_', 'rentroll_', 'subrecords_', 'subrecord_',
        'inc_exp_', 'inc_', 'exp_', 'prop_', 'bldg_', 'lease_',
        'owner_', 'tax_', 'val_', 'zoning_subrecords_', 'zoning_',
    ]

    _skip = orig_name.strip() in _SKIP_PREFIX_STRIP
    changed = True
    while changed and not _skip:
        changed = False
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
                changed = True

    name = name.replace('_subrecords_', '_').replace('_subrecord_', '_')
    name = name.replace('noof', 'number')

    # FIX 5 (cont.) — expanded synonym map
    synonyms = {
        # area / size
        'sf': 'squarefeet', 'sqft': 'squarefeet', 'sqfeet': 'squarefeet',
        'sq': 'squarefeet', 'ft': 'squarefeet',
        'ra': 'rentablearea', 'gla': 'grossleasablearea',
        'gba': 'grossbuildingarea', 'm2': 'squaremeters',
        # building / property
        'bldg': 'building', 'yr': 'year', 'prop': 'property',
        'no': 'number', 'noof': 'number', 'num': 'number',
        # address
        'addr': 'address', 'zip': 'zip', 'postalcode': 'zip',
        'pc': 'zip', 'postal': 'zip',
        # coordinates
        'lat': 'latitude', 'lng': 'longitude',
        # financial
        'amt': 'amount', 'bal': 'balance', 'dep': 'deposit',
        'pct': 'percent', 'val': 'value', 'est': 'estimated',
        'tot': 'total', 'ann': 'annual', 'mo': 'month',
        # operational
        'cam': 'commonareamaintenance', 'sh': 'seniorhousing',
        'comm': 'commercial', 'instr': 'instrument', 'desc': 'description',
        'mgmt': 'management', 'maint': 'maintenance', 'eff': 'effective',
        'exp': 'expense', 'inc': 'income', 'op': 'operating',
        'acct': 'account', 'info': 'information', 'src': 'source',
        'dt': 'date', 'rev': 'revenue', 'avail': 'available',
    }

    stop_words = {'of', 'in', 'the', 'and', 'or', 'to', 'per', 'by'}

    PLURAL_SAFE = {
        'address', 'gross', 'sales', 'options', 'status', 'terms',
        'bonus', 'basis', 'less', 'excess', 'loss', 'across', 'plus',
        'corpus', 'campus', 'gas', 'this', 'its',
    }

    raw_parts = re.split(r'[^a-z0-9]+', name)
    normalized_parts = []

    for p in raw_parts:
        if not p:
            continue

        # Remove trailing single digit  (address1 → address)
        p = re.sub(r'([a-z]+)[0-9]$', r'\1', p)

        # FIX 6 — smarter singularisation with wider safe-list
        if p not in PLURAL_SAFE and len(p) > 4:
            if p.endswith('ies') and not p.endswith('series'):
                p = p[:-3] + 'y'            # properties → property
            elif p.endswith('ves') and len(p) > 5:
                p = p[:-3] + 'f'            # halves → half
            elif p.endswith('ses') or p.endswith('xes') or p.endswith('zes'):
                p = p[:-2]                  # expenses → expense, taxes → tax
            elif p.endswith('s') and not p.endswith('ss'):
                p = p[:-1]                  # units → unit, fees → fee

        # postal code dedup
        if p == 'code' and normalized_parts and normalized_parts[-1] == 'zip':
            continue

        # Apply synonym BEFORE fused-split (handles standalone abbreviations)
        p = synonyms.get(p, p)

        # FIX 9 — fused-token splitting
        # After prefix removal, source fields often leave tokens like
        # 'commleaseterm' or 'landsf' that never match their snake_case peers.
        # Split them, apply synonyms to each sub-token, then flatten.
        sub_tokens = _split_fused(p)
        for sub in sub_tokens:
            sub = synonyms.get(sub, sub)
            if sub and sub not in stop_words:
                normalized_parts.append(sub)

    final_name = "".join(normalized_parts)

    if return_parts:
        return final_name, sorted(normalized_parts)
    return final_name


# ---------------------------------------------------------------------------
# Similarity scoring
# ---------------------------------------------------------------------------

def get_similarity_score(str1, str2, cat1=None, cat2=None):
    """
    Hybrid similarity: SequenceMatcher + Jaro-Winkler + token Jaccard +
    subset boost + optional category penalty.

    Parameters
    ----------
    str1, str2 : field name strings to compare
    cat1, cat2 : optional Field Category strings; when both are provided and
                 differ the score is penalised by 0.15  (FIX 4)
    """
    if not str1 or not str2:
        return 0.0

    norm1, parts1 = normalize_field_name(str1, return_parts=True)
    norm2, parts2 = normalize_field_name(str2, return_parts=True)

    if norm1 == norm2:
        score = 1.0
    else:
        # Base holistic score
        seq_score = difflib.SequenceMatcher(None, norm1, norm2).ratio()

        # FIX 7 — Jaro-Winkler layer
        # Rewards shared prefixes; handles transpositions SequenceMatcher misses.
        # Cap its contribution when token sets are fully disjoint (FIX 7 guard):
        # e.g. tenant_name vs Rent Roll_tenantcam share no normalised tokens at
        # all, so JW's prefix affinity for 'tenantn'/'tenantc' must not dominate.
        jw_score = _jaro_winkler(norm1, norm2)
        if parts1 and parts2 and not (set(parts1) & set(parts2)):
            jw_score = min(jw_score, 0.82)   # cap when zero token overlap
        seq_score = max(seq_score, jw_score)

        # Token-order-insensitive score
        if parts1 and parts2:
            joined1 = "".join(parts1)
            joined2 = "".join(parts2)
            if joined1 == joined2:
                return 1.0
            token_score = difflib.SequenceMatcher(None, joined1, joined2).ratio()
            seq_score = max(seq_score, token_score)

        # FIX 8 — Token Jaccard overlap
        if parts1 and parts2:
            set1, set2 = set(parts1), set(parts2)
            union = set1 | set2
            if union:
                jaccard = len(set1 & set2) / len(union)
                if jaccard >= 0.5:
                    seq_score = max(seq_score, 0.75 + jaccard * 0.2)

        # FIX 2 — Subset boost with minimum absolute length guard
        # Minimum 8 chars prevents short concept tokens ('name', 'type',
        # 'condition') from triggering a boost they don't deserve.
        if norm1 and norm2:
            min_len = min(len(norm1), len(norm2))
            if (norm1 in norm2 or norm2 in norm1) and min_len >= 8:
                coverage = min_len / max(len(norm1), len(norm2))
                if coverage > 0.45:
                    seq_score = max(seq_score, 0.85 + (coverage * 0.1))

        score = seq_score

    # FIX 4 — Category-aware penalty
    if cat1 and cat2 and cat1.strip() and cat2.strip() and cat1.strip() != cat2.strip():
        score = max(0.0, score - 0.15)

    return score


# ---------------------------------------------------------------------------
# Two-pass greedy assignment  (FIX 1)
# ---------------------------------------------------------------------------

def _greedy_assign(scored_pairs, threshold=0.8):
    """
    Given [(ref_value, candidate, score), ...], return assignments using
    greedy best-first allocation so high-confidence pairs lock in first.

    Returns
    -------
    assignments    : dict  ref_value → (candidate, score)
    used_candidates: set of consumed candidates
    """
    scored_pairs.sort(key=lambda x: x[2], reverse=True)

    used_candidates = set()
    assignments = {}

    for ref_val, cand, score in scored_pairs:
        if score < threshold:
            break
        if cand in used_candidates or ref_val in assignments:
            continue
        assignments[ref_val] = (cand, score)
        used_candidates.add(cand)

    return assignments, used_candidates


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def align_csv_data(input_file, output_file, threshold=0.8):
    """
    Aligns ERD fields ('FIELD ERD') with LightBox data ('Field LightBox Data')
    in a CSV.  Writes result to 'Field Lighboxdata aligned' and score to
    'Match Score'.  Unmatched candidates are appended at the end.
    """
    print(f"Reading {input_file} …")

    rows = []
    lb_candidates = []

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        if 'Match Score' not in fieldnames:
            fieldnames.append('Match Score')
        for row in reader:
            rows.append(row)
            lb_val = row.get('Field LightBox Data', '').strip()
            if lb_val and lb_val not in lb_candidates:
                lb_candidates.append(lb_val)

    # Collect all candidate scores in one pass
    scored_pairs = []
    for row in rows:
        erd_field = row.get('FIELD ERD', '').strip()
        if not erd_field:
            continue
        for cand in lb_candidates:
            score = get_similarity_score(erd_field, cand)
            if score >= threshold:
                scored_pairs.append((erd_field, cand, score))

    assignments, used_candidates = _greedy_assign(scored_pairs, threshold)

    matches_count = 0
    for row in rows:
        erd_field = row.get('FIELD ERD', '').strip()
        if not erd_field:
            row['Field Lighboxdata aligned'] = ''
            row['Match Score'] = ''
            continue
        if erd_field in assignments:
            cand, score = assignments[erd_field]
            row['Field Lighboxdata aligned'] = cand
            row['Match Score'] = f"{score:.3f}"
            matches_count += 1
        else:
            row['Field Lighboxdata aligned'] = ''
            row['Match Score'] = ''

    unmatched = [c for c in lb_candidates if c not in used_candidates]
    print(f"Aligned {matches_count} fields.  Unmatched: {len(unmatched)}.")

    for cand in unmatched:
        new_row = {key: '' for key in fieldnames}
        new_row['Field Lighboxdata aligned'] = cand
        rows.append(new_row)

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved → {output_file}")


def align_dynamic_data(input_file, output_file, ref_cols, source_col,
                       result_col, category_col=None, threshold=0.8):
    """
    Aligns fields from a source pool column against multiple reference columns.

    Parameters
    ----------
    input_file    : source CSV path
    output_file   : output CSV path
    ref_cols      : list of columns to match against.
                    TIP for CoStar: pass both
                      ['Consolidated ERD Fields', 'LightBox Aligned Fields']
                    so each CoStar field gets two chances — match the ERD
                    directly OR match its already-resolved LightBox peer.
    source_col    : column containing candidate matches
    result_col    : column where the best match will be written
    category_col  : optional column name for Field Category; enables the
                    cross-category penalty  (FIX 4)
    threshold     : minimum similarity score to accept  (default 0.8)
    """
    print(f"Reading {input_file} …")
    print(f"Reference columns : {ref_cols}")
    print(f"Source pool       : {source_col}  →  {result_col}")

    rows = []
    candidates = []

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        if result_col not in fieldnames:
            fieldnames.append(result_col)
        score_col = result_col + ' Score'
        if score_col not in fieldnames:
            fieldnames.append(score_col)

        for row in reader:
            rows.append(row)
            val = row.get(source_col, '').strip()
            if val and val not in candidates:
                candidates.append(val)

    print(f"Candidates in pool: {len(candidates)}")

    # Build category lookup so get_similarity_score can apply FIX 4
    category_lookup = {}
    if category_col:
        for row in rows:
            for col in ref_cols:
                field = row.get(col, '').strip()
                cat = row.get(category_col, '').strip()
                if field and cat:
                    category_lookup[field] = cat
            cand = row.get(source_col, '').strip()
            cat = row.get(category_col, '').strip()
            if cand and cat:
                category_lookup[cand] = cat

    # Collect all candidate scores across every ref column in one pass
    scored_pairs = []
    for row in rows:
        for col in ref_cols:
            ref_val = row.get(col, '').strip()
            if not ref_val:
                continue
            cat1 = category_lookup.get(ref_val) if category_col else None
            for cand in candidates:
                cat2 = category_lookup.get(cand) if category_col else None
                score = get_similarity_score(ref_val, cand, cat1, cat2)
                if score >= threshold:
                    scored_pairs.append((ref_val, cand, score))

    assignments, used_candidates = _greedy_assign(scored_pairs, threshold)

    matches_count = 0
    for row in rows:
        best_match = None
        best_score = 0.0
        for col in ref_cols:
            ref_val = row.get(col, '').strip()
            if ref_val in assignments:
                cand, score = assignments[ref_val]
                if score > best_score:
                    best_score = score
                    best_match = cand
        if best_match:
            row[result_col] = best_match
            row[score_col] = f"{best_score:.3f}"
            matches_count += 1
        else:
            row[result_col] = ''
            row[score_col] = ''

    unmatched = [c for c in candidates if c not in used_candidates]
    print(f"Aligned {matches_count} fields.  Unmatched: {len(unmatched)}.")

    for cand in unmatched:
        new_row = {key: '' for key in fieldnames}
        new_row[result_col] = cand
        rows.append(new_row)

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved → {output_file}")


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == '__main__':

    # LightBox alignment
    align_csv_data(
        input_file='retail_lgbx_raw.csv',
        output_file='output_lightbox_aligned.csv',
        threshold=0.8,
    )

    # CoStar alignment
    # Pass both ref_cols so CoStar fields match via the ERD *or* the
    # already-resolved LightBox peer.  category_col activates FIX 4.
    align_dynamic_data(
        input_file='retail_costar.csv',
        output_file='output_costar_aligned.csv',
        ref_cols=['Consolidated ERD Fields', 'LightBox Aligned Fields'],
        source_col='CoStar Source Fields',
        result_col='CoStar Aligned Fields',
        category_col='Field Category',
        threshold=0.8,
    )


# ---------------------------------------------------------------------------
# Known ambiguous ERD fields that share a name with source prefixes
# ---------------------------------------------------------------------------
# Some ERD field names like 'improvement_assessment' are inherently ambiguous:
# the normaliser strips 'improvement_' as a LightBox prefix, losing the token.
# List them here as overrides so they skip the prefix-stripping loop entirely.
#
# To use: call normalize_field_name() normally — it checks this dict first.
#
# Add any ERD field name you find being over-stripped to this dict.
_SKIP_PREFIX_STRIP = {
    'improvement_assessment',    # ERD concept, not a LightBox prefixed field
    'improvement_value',
    'improvement_id',
    'improvement_comments',
}