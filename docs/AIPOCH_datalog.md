# Project 14 — Data Log (UPDATED Phase 0 — 2026-06-09)
## /datalog — Mandatory at every analytical session start
## AIPOCH v6.5 | Principal Scientist: Valentine Golden Ghanem

---

## DATASET REGISTER

### DS-01: Ghana DHS 2022 — Subnational Estimates (7 files)

| Field | Value |
|-------|-------|
| Dataset name | Ghana Demographic and Health Survey 2022 (FR387) — Subnational Data Portal |
| Version | Subnational DHS export (2025) |
| Extraction date | 2026-06-09 |
| Files | access-to-health-care_subnational_gha.csv · fp2020_subnational_gha.csv · fertility-rates_subnational_gha.csv · anemia_subnational_gha.csv · select-gender-indicators_subnational_gha.csv · health-insurance_subnational_gha.csv · select-education-indicators_subnational_gha.csv |
| Geographic level | **Regional (16 current post-2022 regions) — NOT district level** |
| Filter used | `SurveyYear == 2022` AND `IsPreferred == 1.0` AND `Location IN DHS_TO_MS16.keys()` |
| Row structure | 2 rows per region per indicator; IsPreferred=0 and IsPreferred=1 — always use IsPreferred=1 |
| Header anomaly | Row 1 in each file is a repeat header (ISO3 = '#country+code') — skip on load |
| IRB reference | Ghana Health Service Ethics Review Board [REF PENDING] |

**DHS_TO_MS16 Region Crosswalk (DHS Location → Master Sheet Region):**
```python
DHS_TO_MS16 = {
    'Ahafo':                   'Ahafo',
    'Ashanti':                 'Ashanti',
    'Bono':                    'Bono',
    'Bono East':               'Bono East',
    'Central':                 'Central',
    'Eastern':                 'Eastern',
    'Greater Accra':           'Greater Accra',
    '..Northeast':             'North East',
    '..Northern(post 2022)':   'Northern',
    'Oti':                     'Oti',
    '..Savannah':              'Savannah',
    'Upper East':              'Upper East',
    'Upper West':              'Upper West',
    'Volta (post 2022)':       'Volta',
    'Western (post 2022)':     'Western',
    'Western North':           'Western North',
}
```
> EXCLUDED: 'Western (pre 2022)', 'Volta (pre 2022)', 'Brong-Ahafo',
> 'Northern (pre 2022)', 'Northern, Upper West, Upper East' — old composite rows

**Variables extracted from DS-01 (exact DHS Indicator strings + confirmed value ranges):**

| Variable | Exact DHS Indicator string | File | Range |
|---------|--------------------------|------|-------|
| `sba` | Assistance during delivery from a skilled provider | access | 70.3–98.0% |
| `facility_delivery` | Place of delivery: Health facility | access | 67.1–97.4% |
| `anc_skilled` | Antenatal care from a skilled provider | access | 92.9–100.0% |
| `no_postnatal_checkup` | No postnatal checkup for mother within first two days of birth | access | 3.3–27.3% |
| `pnc_coverage` | Derived: 100 – no_postnatal_checkup | — | 72.7–96.7% |
| `modern_cpr` | Current use of any modern method of contraception (all women) | fp2020 | 14.8–29.8% |
| `unmet_need_fp` | Unmet need for family planning, total (all women) | fp2020 | 12.5–21.8% |
| `demand_fp_satisfied` | Demand for family planning satisfied by modern methods (all women) | fp2020 | 37.9–61.7% |
| `tfr` | Total fertility rate 15-49 | fertility | 2.9–6.6 |
| `abr` | Age specific fertility rate: 15-19 | fertility | 36–121/1,000 |
| `women_anemia` | Women with any anemia | anemia | 30.1–51.8% |
| `wife_beating_justified` | Wife beating justified for at least one specific reason [Women] | gender | 5.8–57.8% |
| `decision_autonomy` | Final say in all of the decisions [Women] | gender | 38.1–71.3% |
| `ipv_12months` | Physical or sexual or emotional violence committed by husband/partner in last 12 months | gender | 18.3–46.9% |
| `women_edu_secondary` | Women with secondary or higher education | education | 31.8–84.6% |
| `women_literacy` | Women who are literate | education | 27.2–79.2% |
| `no_insurance_women` | No health insurance [Women] | insurance | 1.5–16.5% |

---

### DS-02: GSS Census 2021 — District-Level Socioeconomic Data

| Field | Value |
|-------|-------|
| Dataset name | Ghana Statistical Service 2021 Population and Housing Census |
| File | Master Sheet.xlsx |
| Extraction date | 2026-06-09 |
| Shape | 261 rows × 18 columns |
| Geographic level | **District (N=261 including Guan)** |
| Key identifier | "Metropolitan, Municipal, and District Assemblies (MMDA's)" |
| Coordinate columns | Latitude, Longitude (district polygon centroids) |

**Variables derived from DS-02:**

| Variable | Source column | Derivation |
|---------|--------------|-----------|
| `region` | Region | Direct |
| `district_ms` | MMDA's column | Direct (harmonised name) |
| `latitude` | Latitude | Direct |
| `longitude` | Longitude | Direct |
| `poverty_rate` | Incidence of Poverty | Direct (%) |
| `intensity_poverty` | Intensity of Poverty | Direct (%) |
| `uninsured_rate` | Uninsured Population / Total Population × 100 | Derived |
| `illiteracy_rate` | Illiterate Population / Total Population × 100 | Derived |
| `female_pop_prop` | (Female 0-14 + 15-64 + 65+) / Total × 100 | Derived |
| `working_age_prop` | (Male 15-64 + Female 15-64) / Total × 100 | Derived |
| `total_population` | Total Population | Direct |

**District name harmonisation (SPAT-006):**
- ~85 of 260 GeoJSON DISTRICT names differ from Master Sheet MMDA names
- Pattern: GeoJSON omits "MUNICIPAL"/"METROPOLITAN" suffixes; some spellings differ
- Resolution: `MANUAL_CORRECTIONS` dict built in Phase 1 via systematic fuzzy-match + manual review
- Guan (Oti, 261st district): in Master Sheet but absent from GeoJSON — excluded from spatial (N=260) but included in descriptive (N=261)

---

### DS-03: Ghana GeoJSON District Boundaries

| Field | Value |
|-------|-------|
| File | Ghana_New_260_District.geojson |
| Features | 260 polygons |
| DISTRICT field | ALL CAPS (e.g., "ASHANTI AKIM NORTH") |
| REGION field | ALL CAPS (16 values; "NORTHERN EAST" = North East Region) |
| CRS | WGS84 |
| Missing district | Guan (Oti) — no polygon |
| Oti count | GeoJSON: 8 districts; Master Sheet: 9 (Guan is the 9th) |

---

### DS-04: WHO GHO — National Indicators (background context only)

| Field | Value |
|-------|-------|
| Files | maternal_and_reproductive_health_indicators_gha.csv · health_workforce_indicators_gha.csv · nutrition_indicators_gha.csv |
| Geographic level | **National only — NOT subnational** |
| Use | Introduction + Methods contextual statistics ONLY; not in spatial/ML models |

Key national 2022 figures for manuscript context:
- Nursing & midwifery per 10,000: **44.7** (WHO GHO 2022)
- ANC ≥4 visits: **87.8%** (WHO GHO 2022) — national only
- Births with skilled attendance: **86.2%** (WHO GHO 2022) — national only
- Facility births: **86.2%** (WHO GHO 2022) — national only

---

## DATA QUALITY FLAGS

| Flag | Condition | Action |
|------|-----------|--------|
| COMP-001 | Guan has no GeoJSON polygon | Exclude from spatial (N=260); include in descriptive (N=261) |
| COMP-002 | All DHS indicators are regional level, not district | Assign regional values to constituent districts; acknowledge per STROBE §7 |
| COMP-003 | ANC4+ visits NOT available at regional level in DHS files | Composite uses ANC skilled provider (anc_skilled) instead; document in Methods |
| COMP-004 | WHO GHO files are national level | Use for background statistics in Introduction only; not in analytical models |
| COMP-005 | ~85 GeoJSON/Master Sheet district name mismatches | MANUAL_CORRECTIONS dict built in Phase 1 cleaning |
| COMP-006 | composite_maternal_index built from 4 DHS regional vars alone had only 16 unique values (= region count); zero within-region district variation -> would make Moran's I/LISA (Phase 2-3) and ML risk stratification (Phase 4) trivially collinear with region membership | Composite redefined to blend 4 DHS regional service-coverage vars (supply-side) with 3 inverted district-level census access-barrier vars: poverty_rate, illiteracy_rate, uninsured_rate (demand-side). Now 261 unique values; risk_label tertiles exactly 87/87/87. Audit fix applied 2026-06-10. |
| COMP-007 | 2 Master Sheet district names contained typos ("Cape Cape Metropolitan Area..." and "Sekondi Takoradi Metropolitan Area (STMA)- Takoradi..." with stray space) that did not match the corrected spellings used in MANUAL_CORRECTIONS, breaking the GeoJSON<->Master Sheet crosswalk join for Cape Coast Metro and Sekondi-Takoradi Metro | Fixed at source in `load_master_sheet()` via MS_NAME_FIXES dict. Reverse crosswalk check now confirms exactly 1 unmatched MS district (Guan, per COMP-001) and 0 unmatched crosswalk rows. Audit fix applied 2026-06-10. |
| COMP-008 | poverty_rate, illiteracy_rate, and uninsured_rate are inverted components of composite_maternal_index (post-COMP-006); including them as predictors of risk_label (Phase 4 ML) or composite_maternal_index (Phase 5 GWR/OLS) would be circular regression / data leakage | Excluded from FEATURE_COLS in `03_ml_pipeline.py` (14 features remain) and from PREDICTOR_COLS in `05_gwr_python.py` (9 predictors remain). Inline code comments document rationale in both scripts. Audit fix applied 2026-06-10. |

---

## COMPOSITE MATERNAL HEALTH INDEX — CONFIRMED DEFINITION (REVISED — COMP-006)

**Components:**

| Component | Variable | Source / Level | Direction | Range |
|-----------|---------|-----------------|-----------|-------|
| Skilled ANC coverage | `anc_skilled` | DHS 2022, regional (ecological) | Higher = better | 92.9–100.0% |
| Skilled birth attendance | `sba` | DHS 2022, regional (ecological) | Higher = better | 70.3–98.0% |
| Institutional delivery | `facility_delivery` | DHS 2022, regional (ecological) | Higher = better | 67.1–97.4% |
| PNC ≤48h | `pnc_coverage` | DHS 2022, regional (ecological) | Higher = better | 72.7–96.7% |
| Poverty rate | `poverty_rate` | GSS Census 2021, district | Higher = worse (inverted) | 6.3–68.6% |
| Illiteracy rate | `illiteracy_rate` | GSS Census 2021, district | Higher = worse (inverted) | 5.4–60.8% |
| Uninsured rate (population) | `uninsured_rate` | GSS Census 2021, district | Higher = worse (inverted) | 5.2–73.2% |

**Formula:**
```
norm(x_i)     = (x_i − min(x)) / (max(x) − min(x))                 # 4 DHS service-coverage vars
norm_inv(x_i) = 1 − [(x_i − min(x)) / (max(x) − min(x))]            # 3 census access-barrier vars (inverted)
composite_i   = mean([norm(anc_skilled_i), norm(sba_i), norm(facility_delivery_i), norm(pnc_coverage_i),
                       norm_inv(poverty_rate_i), norm_inv(illiteracy_rate_i), norm_inv(uninsured_rate_i)]) × 100
```

**composite_pca:** PCA(n_components=1) over the same 7 standardised components, sign-aligned with composite_maternal_index, rescaled 0–100.

**Result (post COMP-006 fix):** mean=65.63, SD=17.81, range=[16.1, 88.2], unique=261 (full district-level variation).

**Risk label:** Tertile of composite_i — bottom 33rd %ile = HIGH; middle = MODERATE; top = LOW. p33=64.1, p67=76.0 -> HIGH=87, MODERATE=87, LOW=87 (exact thirds).

**Methods/Limitations note (mandatory):** The 4 DHS-derived components are assigned ecologically at the regional level (COMP-002); the 3 census-derived components vary genuinely at district level. The composite is therefore a multi-level (region x district) index — within-region ranking reflects district socioeconomic deprivation, while between-region ranking additionally reflects regional maternal health service coverage.

---

## CANONICAL VALUES REGISTER

*Populated at QA-0 after analysis completes. Leave blank until Phase 8.*

| Statistic | Value | Source |
|-----------|-------|--------|
| N districts (spatial) | 260 | GeoJSON |
| N districts (tabular) | 261 | Master CSV |
| N regions | 16 | Master Sheet |
| Composite index mean ± SD | 65.63 ± 17.81 | Phase 1 (post-COMP-006) |
| Global Moran's I (composite) | 0.8437 (z=21.3639, p=0.0010) | Phase 2 |
| LISA HH count | 10 | Phase 3 |
| LISA LL count | 38 | Phase 3 |
| Gi* hotspot districts | 37 | Phase 3 |
| XGBoost macro-F1 LOROCV | 0.4884 ± 0.3684 (GBC fallback; mean accuracy 0.6015 ± 0.3515) | Phase 4 |
| Top SHAP feature 1 | working_age_prop (0.3202 ± 0.0260) | Phase 4 |
| Top SHAP feature 2 | female_pop_prop (0.1533 ± 0.0138) | Phase 4 |
| Top SHAP feature 3 | no_insurance_women (0.0568 ± 0.0086) | Phase 4 |
| Global OLS R² / Adj-R² | 0.8980 / 0.8943 | Phase 5 |
| Residual Moran's I (OLS) | 0.4623 (z=11.7142, p=0.0010) — significant; spatial model required (STAT-003) | Phase 5 |
| GWR optimal bandwidth | 50 nearest neighbours (AICc=1399.043) | Phase 5 |
| GWR global R² | 0.9774 | Phase 5 |
| GWR local R² range | mean=0.8752, min=0.5759, max=0.9826 | Phase 5 |

---

## IRB DECLARATION

Study uses secondary aggregated district-level data from Ghana DHS 2022 and GSS Census 2021.
No individual-level data or patient identifiers are processed.
Ethics waiver pending: Ghana Health Service Ethics Review Board (GHS-ERC) [REF TBC].

---

*Phase 0 COMPLETE — 2026-06-09 | All datasets profiled; variable names confirmed from real data*
# END
