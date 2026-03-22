#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Voter Enrichment and Analysis Script
------------------------------------
First runs the enrichment pipeline (adds religion, caste, propagation),
then runs a detailed analysis on the enriched CSV and saves a summary report.
"""

import pandas as pd
import numpy as np
import re
import sys
import csv
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from rapidfuzz import fuzz, process
from pranaam import pranaam

# ============================================================================
# ENRICHMENT CONFIGURATION
# ============================================================================
MASTER_CSV = "/Users/iqbaltaha3/Documents/Meja_electoral_roll/master_final.csv"
LOOKUP_CSV = "/Users/iqbaltaha3/Documents/voter_extractor_tool/caste_lookup.csv"
OUTPUT_CSV = "/Users/iqbaltaha3/Documents/voter_extractor_tool/master_enriched.csv"
MAX_WORKERS = os.cpu_count()          # number of parallel processes; set to 1 to disable
FUZZY_THRESHOLD = 80                  # lower = more matches, higher = stricter
NEIGHBOR_WINDOW = 5                   # rows to look left/right for propagation
NEIGHBOR_PASSES = 3                   # number of propagation passes

# ============================================================================
# ANALYSIS CONFIGURATION
# ============================================================================
ANALYSIS_OUTPUT_TXT = "summary_stats.txt"   # output file for analysis report
# ============================================================================

# ============================================================================
# ENRICHMENT FUNCTIONS (from caste_enrichment.py)
# ============================================================================

def load_lookup(lookup_path):
    """Load the surname lookup CSV and build a mapping."""
    try:
        df = pd.read_csv(lookup_path)
        required = ['surname', 'caste', 'category']
        if not all(col in df.columns for col in required):
            raise ValueError(f"Lookup CSV must have columns: {required}")
    except Exception as e:
        print(f"ERROR loading lookup CSV: {e}")
        sys.exit(1)

    mapping = {}
    for _, row in df.iterrows():
        surname = str(row['surname']).strip().lower()
        caste = row['caste']
        category = row['category']
        mapping[surname] = (caste, category)
    print(f"Loaded {len(mapping)} unique surname variants from lookup.")
    return mapping

def clean_surname(s):
    if pd.isna(s):
        return ""
    s = str(s).strip().lower()
    s = re.sub(r'[^\w\s]', '', s)          # remove punctuation
    if len(s) > 3 and s.endswith('a'):
        s = s[:-1]
    return s

def get_surname_from_name(name):
    if pd.isna(name):
        return None
    parts = str(name).strip().split()
    if len(parts) >= 2:
        return parts[-1]
    return None

def fuzzy_match(surname, mapping, threshold):
    if not surname:
        return None, None
    if surname in mapping:
        return mapping[surname]
    choices = list(mapping.keys())
    if not choices:
        return None, None
    result = process.extractOne(surname, choices, scorer=fuzz.ratio)
    if result and result[1] >= threshold:
        best = result[0]
        return mapping[best]
    return None, None

def process_chunk(chunk, mapping, threshold):
    """
    Process a chunk of dataframe (as list of dicts) and return the results
    for the rows in that chunk.
    """
    results = []
    for _, row in chunk.iterrows():
        # Extract surname
        own = get_surname_from_name(row['Name'])
        raw = own if own is not None else get_surname_from_name(row.get('Father_Husband', None))
        no_surname = raw is None
        if no_surname:
            results.append(('SC', 'SC'))
        else:
            cleaned = clean_surname(raw)
            caste, cat = fuzzy_match(cleaned, mapping, threshold)
            results.append((caste if caste else 'Unknown', cat if cat else 'Unknown'))
    return results

def assign_initial_caste_parallel(df, mapping, threshold, workers):
    """
    Assign initial caste using parallel processing.
    Splits dataframe into chunks and processes each chunk in a separate process.
    """
    n_rows = len(df)
    if workers <= 1 or n_rows < 1000:
        print("   Using sequential processing (workers <=1 or small dataset).")
        return assign_initial_caste_sequential(df, mapping, threshold)

    chunk_size = max(1, n_rows // workers)
    chunks = [df.iloc[i:i+chunk_size] for i in range(0, n_rows, chunk_size)]
    print(f"   Splitting {n_rows} rows into {len(chunks)} chunks, {workers} workers.")

    results = [None] * n_rows
    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_chunk = {executor.submit(process_chunk, chunk, mapping, threshold): i for i, chunk in enumerate(chunks)}
        for future in as_completed(future_to_chunk):
            chunk_idx = future_to_chunk[future]
            try:
                chunk_res = future.result()
                start = chunk_idx * chunk_size
                for j, res in enumerate(chunk_res):
                    results[start + j] = res
            except Exception as e:
                print(f"   Error in chunk {chunk_idx}: {e}")
                print("   Falling back to sequential processing.")
                return assign_initial_caste_sequential(df, mapping, threshold)
    return results

def assign_initial_caste_sequential(df, mapping, threshold):
    """Sequential version (fallback)."""
    results = []
    for _, row in df.iterrows():
        own = get_surname_from_name(row['Name'])
        raw = own if own is not None else get_surname_from_name(row.get('Father_Husband', None))
        no_surname = raw is None
        if no_surname:
            results.append(('SC', 'SC'))
        else:
            cleaned = clean_surname(raw)
            caste, cat = fuzzy_match(cleaned, mapping, threshold)
            results.append((caste if caste else 'Unknown', cat if cat else 'Unknown'))
    return results

def propagate_within_house(df, booth_col, house_col, caste_col, cat_col):
    """For each house, assign the most common caste to all members."""
    df['_house_key'] = df[booth_col] + '|' + df[house_col].astype(str)
    for _, group in df.groupby('_house_key'):
        known = group[~group[caste_col].isin(['Unknown', 'SC'])]
        if len(known) == 0:
            continue
        most_common = known[caste_col].mode()[0]
        most_cat = known[known[caste_col] == most_common].iloc[0][cat_col]
        df.loc[group.index, caste_col] = most_common
        df.loc[group.index, cat_col] = most_cat
    return df

def propagate_by_neighborhood(df, booth_col, house_col, caste_col, cat_col, window):
    """Propagate caste to neighbours within a window in the same booth."""
    df['_house_num'] = df[house_col].astype(str).str.extract(r'(\d+)').fillna(0).astype(int)
    df.sort_values([booth_col, '_house_num', 'Name'], inplace=True)
    df.reset_index(drop=True, inplace=True)

    for booth, group in df.groupby(booth_col):
        indices = group.index.tolist()
        for idx in indices:
            if df.loc[idx, caste_col] in ('Unknown', 'SC'):
                pos = group.index.get_loc(idx)
                start = max(0, pos - window)
                end = min(len(group), pos + window + 1)
                neighbors = group.iloc[start:end]
                known_neighbors = neighbors[~neighbors[caste_col].isin(['Unknown', 'SC'])]
                if not known_neighbors.empty:
                    mode_caste = known_neighbors[caste_col].mode()[0]
                    mode_cat = known_neighbors[known_neighbors[caste_col] == mode_caste].iloc[0][cat_col]
                    df.loc[idx, caste_col] = mode_caste
                    df.loc[idx, cat_col] = mode_cat
    return df

def propagate_by_booth(df, booth_col, caste_col, cat_col):
    """Assign the most common caste of the whole booth to any remaining Unknown/SC rows."""
    for booth, group in df.groupby(booth_col):
        known = group[~group[caste_col].isin(['Unknown', 'SC'])]
        if len(known) == 0:
            continue
        most_common = known[caste_col].mode()[0]
        most_cat = known[known[caste_col] == most_common].iloc[0][cat_col]
        mask = (df[booth_col] == booth) & (df[caste_col].isin(['Unknown', 'SC']))
        df.loc[mask, caste_col] = most_common
        df.loc[mask, cat_col] = most_cat
    return df

def final_cleanup(df, caste_col, cat_col):
    """Replace any remaining 'Unknown' with 'Other'."""
    df[caste_col] = df[caste_col].replace(['Unknown'], 'Other')
    df[cat_col] = df[cat_col].replace(['Unknown'], 'Other')
    return df

def run_enrichment():
    """Run the full enrichment pipeline."""
    print("=" * 60)
    print("VOTER ENRICHMENT SCRIPT (Advanced Consensus Method)")
    print("=" * 60)

    # 1. Load master CSV with robust error handling
    print(f"\n1. Loading master CSV: {MASTER_CSV}")
    try:
        df = pd.read_csv(MASTER_CSV, on_bad_lines='skip', engine='python')
        print(f"   Loaded {len(df)} rows (skipped malformed rows).")
    except Exception as e:
        print(f"   ERROR: {e}")
        print("   Attempting fallback: reading line by line with csv module...")
        rows = []
        with open(MASTER_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            for i, row in enumerate(reader, start=2):
                if len(row) != len(header):
                    print(f"   Skipping line {i}: expected {len(header)} fields, got {len(row)}")
                    continue
                rows.append(row)
        if not rows:
            print("   No valid rows found. Exiting.")
            sys.exit(1)
        df = pd.DataFrame(rows, columns=header[:len(rows[0])])
        print(f"   Loaded {len(df)} rows from fallback.")

    # Ensure required columns exist
    required_cols = ['Name', 'Father_Husband', 'Booth', 'House']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"ERROR: Missing columns: {missing}. Available columns: {df.columns.tolist()}")
        sys.exit(1)

    # 2. Add religion with Pranaam
    print("\n2. Adding religion using Pranaam...")
    try:
        result = pranaam.pred_rel(df['Name'].tolist())
        df['religion'] = result['pred_label'].map({'muslim': 'Muslim', 'not-muslim': 'Hindu'})
        df['religion_prob'] = result['pred_prob_muslim']
        print("   Religion added.")
    except Exception as e:
        print(f"   ERROR during Pranaam: {e}")
        print("   Skipping religion step.")
        df['religion'] = 'Unknown'
        df['religion_prob'] = np.nan

    # 3. Load caste lookup
    print("\n3. Loading caste lookup...")
    mapping = load_lookup(LOOKUP_CSV)

    # 4. Initial caste assignment via surname lookup (parallel)
    print("4. Initial caste assignment via surname lookup...")
    if MAX_WORKERS > 1:
        print(f"   Using {MAX_WORKERS} workers.")
        init_results = assign_initial_caste_parallel(df, mapping, FUZZY_THRESHOLD, MAX_WORKERS)
    else:
        init_results = assign_initial_caste_sequential(df, mapping, FUZZY_THRESHOLD)
    df['caste'] = [r[0] for r in init_results]
    df['category'] = [r[1] for r in init_results]

    # 5. Propagate within house
    print("5. Propagating within houses...")
    df = propagate_within_house(df, 'Booth', 'House', 'caste', 'category')

    # 6. Propagate by neighborhood (multiple passes)
    print(f"6. Propagating by neighborhood ({NEIGHBOR_PASSES} passes, window={NEIGHBOR_WINDOW})...")
    for i in range(NEIGHBOR_PASSES):
        print(f"   Pass {i+1}/{NEIGHBOR_PASSES}...")
        df = propagate_by_neighborhood(df, 'Booth', 'House', 'caste', 'category', NEIGHBOR_WINDOW)

    # 7. Propagate by booth (last resort)
    print("7. Propagating by booth (last resort)...")
    df = propagate_by_booth(df, 'Booth', 'caste', 'category')

    # 8. Final cleanup: replace any remaining 'Unknown' with 'Other'
    print("8. Final cleanup...")
    df = final_cleanup(df, 'caste', 'category')

    # 9. Drop temporary columns
    temp_cols = ['_house_key', '_house_num']
    df.drop(columns=[c for c in temp_cols if c in df.columns], inplace=True, errors='ignore')

    # 10. Save final output
    print(f"\n9. Saving enriched CSV to: {OUTPUT_CSV}")
    try:
        df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
        print("   Success.")
    except Exception as e:
        print(f"   ERROR: {e}")
        sys.exit(1)

    # 11. Summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total rows: {len(df):,}")
    print("\nReligion distribution:")
    print(df['religion'].value_counts(dropna=False))
    print("\nCaste distribution (final):")
    print(df['caste'].value_counts(dropna=False))
    print("\nCategory distribution:")
    print(df['category'].value_counts(dropna=False))

    print("\n✅ Enrichment DONE.")
    return df

# ============================================================================
# ANALYSIS FUNCTIONS (from summary_stats.py)
# ============================================================================

def get_surname(name):
    if pd.isna(name):
        return None
    parts = str(name).split()
    if len(parts) >= 2:
        return parts[-1].lower()
    return None

def run_analysis():
    """Run the analysis on the enriched CSV."""
    print("\n" + "=" * 60)
    print("VOTER DATA ANALYSIS")
    print("=" * 60)
    print(f"Loading enriched CSV: {OUTPUT_CSV}")

    try:
        df = pd.read_csv(OUTPUT_CSV)
        total = len(df)
        print(f"Loaded {total} rows.\n")
    except Exception as e:
        print(f"ERROR loading enriched CSV: {e}")
        print("Skipping analysis.")
        return

    # Redirect output to a file
    f = open(ANALYSIS_OUTPUT_TXT, 'w', encoding='utf-8')
    original_stdout = sys.stdout
    sys.stdout = f

    print("=" * 80)
    print("VOTER DATA ANALYSIS")
    print("=" * 80)
    print(f"Analysis date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total voters: {total:,}\n")

    # 1. Category distribution
    print("\n--- CATEGORY DISTRIBUTION (final) ---")
    cat_counts = df['category'].value_counts()
    cat_pct = df['category'].value_counts(normalize=True) * 100
    for cat, cnt in cat_counts.items():
        print(f"{cat:12} {cnt:8,}  ({cat_pct[cat]:5.1f}%)")
    print(f"\nCategory 'Other' count: {cat_counts.get('Other', 0)}")

    # 2. Religion distribution
    print("\n--- RELIGION DISTRIBUTION ---")
    rel_counts = df['religion'].value_counts()
    rel_pct = df['religion'].value_counts(normalize=True) * 100
    for rel, cnt in rel_counts.items():
        print(f"{rel:12} {cnt:8,}  ({rel_pct[rel]:5.1f}%)")
    print()

    # 3. Cross‑tabulation: Category vs Religion
    print("\n--- CATEGORY vs RELIGION (cross‑tabulation) ---")
    cross = pd.crosstab(df['category'], df['religion'], margins=True)
    print(cross.to_string())

    # 4. Gender distribution
    if 'Gender' in df.columns:
        print("\n--- GENDER DISTRIBUTION ---")
        gen_counts = df['Gender'].value_counts()
        gen_pct = df['Gender'].value_counts(normalize=True) * 100
        for gen, cnt in gen_counts.items():
            print(f"{gen:12} {cnt:8,}  ({gen_pct[gen]:5.1f}%)")
    else:
        print("\n--- Gender column not found ---")

    # 5. Age group analysis
    if 'Age' in df.columns:
        print("\n--- AGE GROUP DISTRIBUTION ---")
        age = pd.to_numeric(df['Age'], errors='coerce')
        age_clean = age.dropna()
        if len(age_clean) > 0:
            bins = [0, 18, 25, 35, 50, 65, 120]
            labels = ['<18', '18-25', '26-35', '36-50', '51-65', '65+']
            age_group = pd.cut(age_clean, bins=bins, labels=labels, right=False)
            age_counts = age_group.value_counts()
            age_pct = age_group.value_counts(normalize=True) * 100
            for grp, cnt in age_counts.items():
                print(f"{grp:8} {cnt:8,}  ({age_pct[grp]:5.1f}%)")
            print(f"\nAge statistics: mean = {age_clean.mean():.1f}, median = {age_clean.median():.0f}")
        else:
            print("No valid age data.")
    else:
        print("\n--- Age column not found ---")

    # 6. Household analysis
    if 'House' in df.columns and 'Booth' in df.columns:
        print("\n--- HOUSEHOLD ANALYSIS ---")
        df['_household_id'] = df['Booth'].astype(str) + '_' + df['House'].astype(str)
        household_sizes = df.groupby('_household_id').size()
        print(f"Total households: {len(household_sizes):,}")
        print(f"Average household size: {household_sizes.mean():.2f}")
        print(f"Median household size: {household_sizes.median():.0f}")
        print(f"Max household size: {household_sizes.max()}")
        print("\nHousehold size distribution:")
        size_counts = household_sizes.value_counts().sort_index()
        for sz, cnt in size_counts.items():
            print(f"   {sz:2} members: {cnt:6,} households ({cnt/len(household_sizes)*100:.1f}%)")
        df.drop(columns=['_household_id'], inplace=True)
    else:
        print("\n--- Household analysis requires 'House' and 'Booth' columns ---")

    # 7. Top surnames by category
    print("\n--- TOP 10 SURNAMES BY CATEGORY ---")
    df['surname'] = df['Name'].apply(get_surname)
    categories = df['category'].unique()
    for cat in categories:
        cat_df = df[df['category'] == cat]
        if len(cat_df) == 0:
            continue
        top_surnames = cat_df['surname'].value_counts().head(10)
        print(f"\n{cat} (total {len(cat_df)} voters):")
        for sur, cnt in top_surnames.items():
            if sur:
                print(f"   {sur}: {cnt}")

    # 8. Numeric summary
    print("\n--- NUMERIC SUMMARY STATISTICS ---")
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        for col in numeric_cols:
            print(f"\n{col}:")
            print(df[col].describe())
    else:
        print("No numeric columns found.")

    # 9. Correlation matrix
    if len(numeric_cols) > 1:
        print("\n--- CORRELATION MATRIX (numeric columns) ---")
        corr = df[numeric_cols].corr()
        print(corr.to_string())
    else:
        print("\n--- Insufficient numeric columns for correlation matrix ---")

    # 10. EPIC quality
    if 'EPIC' in df.columns:
        print("\n--- EPIC DATA QUALITY ---")
        epic_missing = df['EPIC'].isna().sum()
        epic_unique = df['EPIC'].nunique()
        print(f"EPIC missing: {epic_missing} ({epic_missing/total*100:.1f}%)")
        print(f"Unique EPIC numbers: {epic_unique}")
        print(f"Duplicate EPIC counts: {df['EPIC'].duplicated().sum()}")
    else:
        print("\n--- EPIC column not found ---")

    # Clean up temporary column
    if 'surname' in df.columns:
        df.drop(columns=['surname'], inplace=True)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE.")
    print(f"Output saved to {ANALYSIS_OUTPUT_TXT}")

    sys.stdout.flush()
    f.close()
    sys.stdout = original_stdout
    print(f"\n✅ Analysis written to {ANALYSIS_OUTPUT_TXT}")

# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================
def main():
    """Run enrichment first, then analysis."""
    try:
        run_enrichment()
    except Exception as e:
        print(f"\n❌ Enrichment failed: {e}")
        print("Skipping analysis.")
        sys.exit(1)

    try:
        run_analysis()
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        print("But enrichment succeeded. Check analysis output.")
        sys.exit(1)

    print("\n✅ All done.")

if __name__ == "__main__":
    main()