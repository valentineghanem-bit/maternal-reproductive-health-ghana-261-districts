# Methodology — Project 14: Spatial Inequities in Maternal and Reproductive Health, Ghana

**Author:** Valentine Golden Ghanem  
**Version:** 1.0 (scaffold) | Updated progressively through Phases 1–12  
**Reporting guidelines:** STROBE · RECORD-Spatial · TRIPOD+AI

**See also:** `docs/data_dictionary.md` for a full column-by-column dictionary of the
89-column master CSV, including the 11 renamed raw Census 2021 provenance columns
(NAMING-001) and the ML-NAMING-001 disclosure for `xgb_predicted_risk` (§7.2 below).

---

## 1. Study Design

**Design:** Ecological cross-sectional study.  
**Unit of analysis:** Health district (N=261, Ghana 2022).  
**Time period:** 2022 (primary); 2021 for census denominators.  
**Outcome:** Composite maternal health index (primary); MMR, ABR, mCPR, unmet need (secondary).

---

## 2. Setting

Ghana is divided into 261 health districts across 16 regions (as of 2022). The 261st district — Guan — is located in Oti Region and was formally gazetted in 2019. Legacy GeoJSON boundary files that omit Guan are corrected using the `MANUAL_CORRECTIONS` dict in `01_data_cleaning.py` (SPAT-006).

---

## 3. Data Sources

| Source | Variable set | Year | Unit | Access |
|--------|-------------|------|------|--------|
| Ghana DHIMS2 | SBA rate, ANC4+ coverage, facility delivery, PNC, maternal deaths | 2022 | District | GHS-ERC |
| Ghana DHS 2022 (FR387) | mCPR, ABR, unmet need for FP, wealth index | 2022 | Region (16) | DHS Programme |
| GSS Census 2021 | Population, poverty rate, education, urban proportion | 2021 | District | statsghana.gov.gh |
| NHIA Annual Report 2022 | NHIS active enrolment rate | 2022 | District | nhia.gov.gh |
| GHSF 2023 | Facility density, health workforce density | 2023 | District | GHS |

**DHS regional-to-district assignment:** Ghana DHS 2022 reports at regional level. District values are imputed using the `POST_TO_PRE` and `DHS_TO_MS16` region harmonisation dictionaries (EX-033). Districts receive the value of their parent DHS region.

**Note (Phases 1–6 scope):** the NHIA and GHSF 2023 sources are listed for completeness but were **not** used as analytic variables in the composite index (§4), OLS/GWR predictors (§6), or ML features (§7) for Phases 1–6 — `no_insurance_women` (NHIS non-enrolment among women) is sourced from DHS 2022, not the NHIA Annual Report. Facility/workforce density (GHSF 2023) are not currently in any model and are flagged as potential future-phase covariates.

---

## 4. Outcome Variable: Composite Maternal Health Index

The composite index (0–100) aggregates **seven** indicators using min-max normalisation followed by equal-weight averaging (COMP-006):

| Component | Source | Direction | Treatment |
|-----------|--------|-----------|-----------|
| ANC with skilled provider (`anc_skilled`) | DHS 2022 (regional) | Higher = better | norm(x) |
| Skilled birth attendance rate (`sba`) | DHS 2022 (regional) | Higher = better | norm(x) |
| Institutional delivery rate (`facility_delivery`) | DHS 2022 (regional) | Higher = better | norm(x) |
| Postnatal care coverage (`pnc_coverage`) | DHS 2022 (regional) | Higher = better | norm(x) |
| Poverty rate (`poverty_rate`) | Census 2021 (district) | Higher = worse | 1 − norm(x) |
| Illiteracy rate (`illiteracy_rate`) | Census 2021 (district) | Higher = worse | 1 − norm(x) |
| Uninsured rate (`uninsured_rate`) | Census 2021 (district) | Higher = worse | 1 − norm(x) |

The first four components are DHS 2022 regional service-coverage indicators (assigned to constituent districts via the region-harmonisation dictionaries, EX-033) and by themselves contribute variation only at the regional level. The three Census 2021 components are measured at district level and were added (COMP-006) specifically so the composite carries genuine within-region district-level variation — without them, all districts within a region would receive an identical index value.

Formula: `Index_i = mean(norm(anc_skilled_i), norm(sba_i), norm(facility_delivery_i), norm(pnc_coverage_i), 1−norm(poverty_rate_i), 1−norm(illiteracy_rate_i), 1−norm(uninsured_rate_i)) × 100`

Where `norm(x_i) = (x_i − min(x)) / (max(x) − min(x))`

PCA sensitivity analysis is computed across all seven components and sign-aligned with the equal-weight composite via correlation.

**Note:** because `poverty_rate`, `illiteracy_rate`, and `uninsured_rate` are components of the outcome itself, they are excluded from all OLS/GWR predictor sets (§6) and ML feature sets (§7) to avoid circularity (post-COMP-006/COMP-008).

---

## 5. Spatial Analysis

### 5.1 Global Moran's I
- **Weight matrix:** KNN k=4, constructed from district polygon centroids
- **Inference:** Permutation-based (n=999, seed=42)
- **Reported:** I, E(I), Var(I), z-score, p-value
- **Threshold:** p<0.05 (two-tailed) triggers spatial modelling

### 5.2 Univariate LISA
- **Weight matrix:** Rook contiguity (≥2 shared GeoJSON vertices, row-standardised)
- **Inference:** Permutation-based (n=999, seed=42)
- **Output:** HH / LL / HL / LH quadrant classification; p<0.05 significance flag

### 5.3 Bivariate LISA
- **Variates:** Composite maternal index (x) × poverty rate (y)
- **Interpretation:** HH = high poverty co-localised with low composite index

### 5.4 Getis-Ord Gi*
- **Statistic:** Includes self-weight (Gi* variant)
- **Classification:** Hotspot (z>0, p<0.05) / Coldspot (z<0, p<0.05)

### 5.5 Implementation note
All spatial analysis (Moran's I, LISA, Gi*) is implemented in pure NumPy + SciPy without libpysal dependency (EX-031), using KNN k=4 weights from district polygon centroids (KDTree, Euclidean distance).

`outputs/data/morans_i_r_verification.csv` is a Python-generated cross-check (same KNN k=4 / KDTree / Euclidean method as §5.1) that (i) restates the Phase 2 canonical global Moran's I for `composite_maternal_index` (I=0.8437, z=21.3639, p=0.001) and (ii) additionally reports the residual Moran's I after the Global OLS model in §6.1 (I=0.4623, z=11.7142, p=0.001; STAT-003) — confirming significant residual spatial autocorrelation and motivating the GWR model in §6.2.

An alternative R script, `scripts/05_gwr_analysis.R`, was drafted to provide an independent Queen-contiguity verification of global Moran's I via `spdep`, but **R/spdep was unavailable in the execution sandbox and this script was never run**. It is retained in the repository for users with an R environment but is not the source of any value reported in this methodology, the manuscript, or `morans_i_r_verification.csv`.

---

## 6. Regression Analysis

### 6.1 Global OLS
Predictors (9; DHS 2022 regional women's-health/empowerment indicators assigned to districts via the region-harmonisation dictionaries, §3): `working_age_prop`, `female_pop_prop`, `women_edu_secondary`, `women_literacy`, `no_insurance_women`, `women_anemia`, `wife_beating_justified`, `decision_autonomy`, `ipv_12months`.

The three Census 2021 access-barrier variables (`poverty_rate`, `illiteracy_rate`, `uninsured_rate`) are deliberately **excluded** as predictors because they are components of the outcome `composite_maternal_index` itself (§4, COMP-006/COMP-008); including them would be circular.

Model fit (n=261): R² = 0.898, adjusted R² = 0.894.

- VIF checked for all predictors (threshold: VIF>5 triggers co-linearity discussion). Two predictors exceed the threshold — `women_edu_secondary` (VIF=15.13) and `women_literacy` (VIF=9.06) — reflecting the expected strong correlation between female secondary education and female literacy. Both are retained as substantively important determinants; the collinearity is acknowledged in the manuscript Discussion/Limitations rather than resolved by dropping either variable. The GWR model in §6.2 is reported as the primary spatial-inferential model partly because it relaxes the assumption of a single global coefficient for these correlated predictors.
- Residual Moran's I computed after OLS (STAT-003): I=0.4623, p=0.001 — significant residual spatial autocorrelation, motivating GWR.

### 6.2 Geographically Weighted Regression (GWR)
Implementation: pure Python (`scripts/05_gwr_python.py`; R/GWmodel unavailable in the execution sandbox).

- **Kernel:** bisquare adaptive
- **Distance metric:** haversine (great-circle distance between district centroids)
- **Bandwidth:** AICc-based selection, bw = 50 neighbours, AICc = 1399.043
- **Outputs:** Local R² per district (mean = 0.8752, see `outputs/data/gwr_local_r2.csv`) and local coefficients for each of the 9 OLS predictors (`outputs/data/gwr_local_coefficients.csv`)
- **Model comparison:** GWR overall R² = 0.9774 vs Global OLS R² = 0.898 (`outputs/data/spatial_regression_comparison.csv`) — the substantial improvement indicates spatial non-stationarity in predictor–outcome relationships
- Predictors are identical to §6.1 (the three composite-component variables remain excluded)

An alternative R/GWmodel implementation (`scripts/05_gwr_analysis.R`, including a Monte Carlo non-stationarity test via `bw.gwr()`) was drafted but **was not executed** (R/GWmodel unavailable in sandbox); it is retained for users with an R environment but is not the source of any reported GWR result.

---

## 7. Machine Learning Risk Stratification

### 7.1 Risk label derivation
Tertile-based classification of the composite maternal index:
- High risk: bottom tertile (index ≤ 33rd percentile)
- Moderate risk: middle tertile
- Low risk: top tertile

### 7.2 Model
- Primary: GradientBoostingClassifier (scikit-learn; n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8, random_state=42). XGBoost (identical hyperparameters) is the preferred implementation and is used automatically if available; the execution environment for this analysis did not have XGBoost installed, so the script's documented sklearn fallback (GradientBoostingClassifier — same gradient-boosted-tree algorithm family) was used. All reported figures/tables are labelled "Gradient Boosting".
- No separate logistic-regression benchmark model was fitted.

### 7.3 Validation
- LOROCV: 16 folds (one region held out per fold)
- Performance: mean accuracy and mean macro-F1 (± SD across folds)
- **Label-homogeneity caveat:** 4 of 16 folds (North East, Northern, Oti, Savannah) consist entirely of districts with `risk_label = HIGH`, producing trivially perfect fold metrics (accuracy = 1.0, macro-F1 = 1.0) for those folds. This inflates mean LOROCV performance and is reported as a Limitation / stress-test finding (Tenet 6 — uncertainty before interpretation).
- No calibration curve or Brier score was computed (out of scope for this multiclass risk-stratification analysis).

### 7.4 Interpretability (Tenet 13 — Permutation Feature Importance, SHAP-analogous)
- Permutation importance (`sklearn.inspection.permutation_importance`; Breiman 2001; n_repeats=30, random_state=42, scoring=accuracy) — a model-agnostic, multicollinearity-robust substitute for SHAP. Saved to `outputs/data/shap_values.csv` (column name retained for `build_final_dataset.py` compatibility) and `outputs/data/permutation_importance.csv`.
- Summary bar chart (figsize=(14,10)) — `outputs/figures/shap_summary.png`
- Partial-dependence plots, top 3 features — `outputs/figures/shap_dependence_*.png`
- Plain-language translation of top 3 features in manuscript §3.3
- **Note:** no per-district SHAP waterfall plot is produced, as waterfall decomposition is SHAP-specific and unavailable from permutation importance. This is documented as a Limitation. Manuscript prose must refer to "permutation feature importance," never "SHAP values."

### 7.5 SMOTE guard (EX-028)
`k_neighbors = min(5, min_class_n − 1)` to prevent errors when any class has <6 training samples in a LOROCV fold.

---

## 8. Bayesian Disease Mapping (MMR)

**Status: planned — not executed in Phases 1–6.** The following specification documents the intended approach should MMR small-area estimation be added in a later phase; no BYM/iCAR/INLA output currently exists in `outputs/`.

MMR is estimated for districts with sparse data using the BYM/iCAR model:

`η_i = α + u_i + v_i`

- **u_i:** Intrinsic CAR prior (structured spatial effect via Queen contiguity)
- **v_i:** Gaussian exchangeable prior (unstructured heterogeneity)
- **Priors:** Penalised complexity (PC) priors for σ_u and σ_v
- **Software:** R-INLA
- **Outputs:** Posterior mean RR, 95% CrI, exceedance probability P(RR>1|data), spatial fraction φ
- **Hotspot criterion:** P(RR>1|data) > 0.95

---

## 9. Bias Assessment

| Bias type | Assessment method |
|-----------|------------------|
| Selection | DHIMS2 completeness check (flag <80% per district) |
| Information | DHIMS2 vs DHS 2022 triangulation for shared indicators |
| Confounding | DAG with listed confounders; GWR (§6.2) used in place of a single global coefficient to assess spatial non-stationarity in predictor effects |
| Ecological fallacy | Explicitly acknowledged; inference bounded to district level |
| MAUP | Sensitivity analysis: region-level aggregation comparison |

---

## 10. Ethical Approval

Ethical approval: Ghana Health Service Ethics Review Board (GHS-ERC).  
IRB reference: [To be completed upon application submission]  
Data classification: Aggregate district-level data — no individual-level data.

---

## 11. Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11 | Data cleaning, spatial analysis, ML, GWR |
| NumPy | 1.26.4 | Spatial weight matrices, Moran's I, GWR |
| SciPy | 1.13.x | OLS, VIF, GWR kernel weighting |
| pandas | 2.2.2 | Data manipulation |
| XGBoost | 2.0.3 (used if available) | Risk stratification — preferred implementation; not installed in execution environment, see §7.2 |
| scikit-learn | 1.5.0 | GradientBoostingClassifier (ML fallback), permutation importance, LOROCV metrics |
| matplotlib | 3.9.0 | Figures (300 DPI) |
| R | not used | `scripts/05_gwr_analysis.R` drafted but not executed (unavailable in sandbox); see §5.5, §6.2 |
| GWmodel | not used | Drafted alternative GWR implementation only; not the source of reported GWR results |
| R-INLA | not used | §8 (Bayesian disease mapping) is planned, not yet executed |
| spdep | not used | Drafted alternative Moran's I verification only; not the source of `morans_i_r_verification.csv` |

---

*This methodology document is updated progressively as each analysis phase completes. Last updated: 2026-06-10 (Phases 2–6 documentation audit and correction — GWR-001 through GWR-005, COMP-009, ML-DOC-001 through ML-DOC-004, SOFTWARE-001).*
