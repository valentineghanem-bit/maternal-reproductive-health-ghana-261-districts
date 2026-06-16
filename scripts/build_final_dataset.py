"""
Project 14: Ghana Maternal & Reproductive Health — 261 Districts
build_final_dataset.py — Assemble master CSV (EX-003)
Author: Valentine Golden Ghanem
Date: 2026-06-09

Merges:
  - data/processed/maternal_ghana_261districts_clean.csv   (cleaned indicators)
  - outputs/data/lisa_results.csv                          (LISA quadrant + significance)
  - outputs/data/bivariate_lisa_results.csv               (BV LISA)
  - outputs/data/getis_ord_results.csv                     (Gi* hotspot class)
  - outputs/data/morans_i_results.csv                      (global I — appended as scalar)
  - outputs/data/ml_predictions.csv                        (risk_label, XGBoost prediction)
  - outputs/data/shap_values.csv                           (mean |SHAP| per feature)

Output:
  - master_maternal_ghana_261districts_v1.csv
  - data_source attribution columns included per project standard (EX-003)
# END
"""

import os
import sys
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
PROC = os.path.join(ROOT, 'data', 'processed')
OUT_DATA = os.path.join(ROOT, 'outputs', 'data')
WORKSPACE = ROOT  # final CSV saved to project root

MASTER_CSV = os.path.join(WORKSPACE, 'master_maternal_ghana_261districts_v1.csv')

def load_if_exists(path, label):
    if os.path.exists(path):
        df = pd.read_csv(path)
        print(f"  [OK] Loaded {label}: {df.shape}")
        return df
    else:
        print(f"  [MISSING] Not found: {label} -- will be empty columns in master")
        return None

def main():
    print("=== build_final_dataset.py -- Assembling Master CSV ===\n")

    # Load base
    base_path = os.path.join(PROC, 'maternal_ghana_261districts_clean.csv')
    if not os.path.exists(base_path):
        print("[ERROR] Base dataset not found. Run 01_data_cleaning.py first.")
        sys.exit(1)

    master = pd.read_csv(base_path)
    print(f"  Base: {master.shape}")

    # Merge LISA
    lisa = load_if_exists(os.path.join(OUT_DATA, 'lisa_results.csv'), 'LISA')
    if lisa is not None and 'district' in lisa.columns:
        lisa = lisa.rename(columns={
            'local_I': 'lisa_local_I',
            'p_perm': 'lisa_p_perm',
            'quadrant': 'lisa_quadrant',
            'significant': 'lisa_significant',
        })
        master = master.merge(lisa[['district', 'lisa_local_I', 'lisa_p_perm',
                                     'lisa_quadrant', 'lisa_significant']],
                               on='district', how='left')

    # Merge Bivariate LISA
    bv = load_if_exists(os.path.join(OUT_DATA, 'bivariate_lisa_results.csv'), 'BV-LISA')
    if bv is not None and 'district' in bv.columns:
        bv = bv.rename(columns={
            'bv_I': 'bv_lisa_I',
            'p_perm': 'bv_lisa_p_perm',
            'bv_quadrant': 'bv_lisa_quadrant',
            'significant': 'bv_lisa_significant',
        })
        master = master.merge(bv[['district', 'bv_lisa_I', 'bv_lisa_p_perm',
                                    'bv_lisa_quadrant', 'bv_lisa_significant']],
                               on='district', how='left')

    # Merge Gi*
    gi = load_if_exists(os.path.join(OUT_DATA, 'getis_ord_results.csv'), 'Gi*')
    if gi is not None and 'district' in gi.columns:
        gi = gi.rename(columns={
            'Gi_star': 'gi_star',
            'p_perm': 'gi_p_perm',
            'hotspot_class': 'gi_hotspot_class',
        })
        master = master.merge(gi[['district', 'gi_star', 'gi_p_perm', 'gi_hotspot_class']],
                               on='district', how='left')

    # Merge ML predictions
    ml = load_if_exists(os.path.join(OUT_DATA, 'ml_predictions.csv'), 'ML predictions')
    if ml is not None and 'district' in ml.columns:
        master = master.merge(ml, on='district', how='left')

    # Merge GWR local R2 (Phase 5)
    gwr_r2 = load_if_exists(os.path.join(OUT_DATA, 'gwr_local_r2.csv'), 'GWR local R2')
    if gwr_r2 is not None and 'district' in gwr_r2.columns:
        gwr_r2 = gwr_r2.rename(columns={'Local_R2': 'gwr_local_r2'})
        master = master.merge(gwr_r2[['district', 'gwr_local_r2']], on='district', how='left')

    # Data source attribution columns (EX-003)
    # DHS 2022 subnational: all regional-level indicators assigned to districts
    dhs_cols = [
        'sba', 'anc_skilled', 'facility_delivery', 'pnc_coverage', 'no_postnatal_checkup',
        'modern_cpr', 'unmet_need_fp', 'demand_fp_satisfied', 'tfr', 'abr',
        'women_anemia', 'wife_beating_justified', 'decision_autonomy', 'ipv_12months',
        'no_insurance_women', 'women_edu_secondary', 'women_literacy',
    ]
    for col in dhs_cols:
        if col in master.columns:
            master[f'data_source_{col}'] = 'Ghana DHS 2022 (FR387)'

    # GSS Census 2021: district-level socioeconomic variables
    census_cols = [
        'poverty_rate', 'intensity_poverty', 'uninsured_rate', 'illiteracy_rate',
        'working_age_prop', 'female_pop_prop', 'total_population', 'latitude', 'longitude',
    ]
    for col in census_cols:
        if col in master.columns:
            master[f'data_source_{col}'] = 'GSS Census 2021'

    # Derived composite (COMP-006: 7-component, see methodology.md S4)
    if 'composite_maternal_index' in master.columns:
        master['data_source_composite_maternal_index'] = (
            'Derived (COMP-006): equal-weight mean of min-max normalised anc_skilled, sba, '
            'facility_delivery, pnc_coverage (Ghana DHS 2022, FR387, regional) and 1-minus-min-max-normalised '
            'poverty_rate, illiteracy_rate, uninsured_rate (GSS Census 2021, district)'
        )
    master['data_source_spatial_weights'] = 'Ghana_New_260_District.geojson; KNN k=4 (Moran); Rook (LISA)'
    if 'gwr_local_r2' in master.columns:
        master['data_source_gwr_local_r2'] = 'Derived: GWR (adaptive bisquare, AICc-optimised bandwidth) on composite_maternal_index ~ predictor_cols'
    master['dataset_version'] = 'v1.0'
    master['extraction_year'] = 2022

    # Drop exact-duplicate columns (DATA-001)
    # These Title-Case / alt-named columns are exact duplicates of an existing
    # snake_case column already retained above and add no information.
    duplicate_cols = [
        'Latitude',              # dup of latitude
        'Longitude',             # dup of longitude
        'Total Population',      # dup of total_population
        'Intensity of Poverty',  # dup of intensity_poverty
        'true_risk',             # dup of risk_label
        'district_ms',           # dup of district
        'Incidence of Poverty',  # dup of poverty_rate
    ]
    master = master.drop(columns=[c for c in duplicate_cols if c in master.columns])

    # Rename raw-provenance columns to snake_case (NAMING-001)
    # Retained (not dropped) -- these are raw Census 2021 counts/classification
    # from which several rate/proportion columns are derived; kept for
    # transparency and derivation verification (see methodology.md data dictionary).
    rename_map = {
        'Class': 'district_class',
        'Employed Population': 'employed_population',
        'Unemployed Population': 'unemployed_population',
        'Illiterate Population': 'illiterate_population',
        'Uninsured Population': 'uninsured_population',
        'Male Population 0-14': 'male_pop_0_14',
        'Female Population 0-14': 'female_pop_0_14',
        'Male Population 15-64': 'male_pop_15_64',
        'Female Population 15-64': 'female_pop_15_64',
        'Male Population 65+': 'male_pop_65plus',
        'Female Population 65+': 'female_pop_65plus',
    }
    master = master.rename(columns={k: v for k, v in rename_map.items() if k in master.columns})

    # Column ordering
    id_cols = ['district', 'region']
    # Correct column names matching 01_data_cleaning.py output exactly
    outcome_cols = [
        'composite_maternal_index', 'risk_label',
        'sba', 'anc_skilled', 'facility_delivery', 'pnc_coverage',
        'modern_cpr', 'unmet_need_fp', 'demand_fp_satisfied', 'abr', 'tfr',
    ]
    predictor_cols = [
        # Census 2021 -- district level
        'poverty_rate', 'uninsured_rate', 'illiteracy_rate', 'working_age_prop', 'female_pop_prop',
        # DHS 2022 -- regional predictors (non-composite)
        'women_edu_secondary', 'women_literacy', 'no_insurance_women', 'women_anemia',
        'wife_beating_justified', 'decision_autonomy', 'ipv_12months',
    ]
    spatial_cols = ['lisa_local_I', 'lisa_p_perm', 'lisa_quadrant', 'lisa_significant',
                    'bv_lisa_I', 'bv_lisa_p_perm', 'bv_lisa_quadrant', 'bv_lisa_significant',
                    'gi_star', 'gi_p_perm', 'gi_hotspot_class', 'gwr_local_r2']
    ml_cols = ['xgb_predicted_risk', 'xgb_prob_high', 'xgb_prob_moderate', 'xgb_prob_low']
    flag_cols = ['low_completeness_flag']

    ordered = (id_cols +
               [c for c in outcome_cols if c in master.columns] +
               [c for c in predictor_cols if c in master.columns] +
               [c for c in spatial_cols if c in master.columns] +
               [c for c in ml_cols if c in master.columns] +
               [c for c in flag_cols if c in master.columns] +
               [c for c in master.columns if c not in id_cols + outcome_cols + predictor_cols +
                spatial_cols + ml_cols + flag_cols])

    master = master[[c for c in ordered if c in master.columns]]

    # Save
    master.to_csv(MASTER_CSV, index=False)
    print(f"\n  [Saved] {MASTER_CSV}")
    print(f"  Shape: {master.shape}")
    print(f"  Districts: {master['district'].nunique()}")

    # Sentinel check (TECH-006)
    rows, cols = master.shape
    print(f"\n  [Sentinel] {rows} rows | Expected: 261")
    print(f"  [Sentinel] {cols} columns | Expected: 89 (post DATA-001/NAMING-001)")

    return master

if __name__ == '__main__':
    main()
    # END
