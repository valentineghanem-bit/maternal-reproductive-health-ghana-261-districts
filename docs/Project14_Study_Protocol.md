# Project 14 — Study Protocol
## Spatial Inequities in Maternal and Reproductive Health Outcomes and ML Risk Stratification in Ghana's 261 Health Districts
## AIPOCH v6.5 | Valentine Golden Ghanem | 2026-06-09

---

## 1. Background and Rationale

Ghana's maternal mortality ratio (MMR) of approximately 310 per 100,000 live births
(WHO 2020 estimate) remains above the SDG 3.1 target of <70 per 100,000. Substantial
within-country disparities exist, with Northern, Savannah, and North East regions recording
disproportionately poor outcomes relative to Greater Accra and Ashanti. Despite progress in
antenatal care coverage, skilled birth attendance, and facility delivery rates at the national
level, district-level heterogeneity and its spatial structure remain poorly characterised.

### 1.1 Research Gaps

Six-dimensional gap analysis:

1. **Knowledge gap:** National-level trends documented, but district-level spatial clustering
   of composite maternal health burden not quantified at 261-district resolution.

2. **Empirical gap:** DHIMS2 data available at district level for SBA, ANC4+, facility
   delivery, and PNC, but rarely analysed in a spatially explicit framework with ML.

3. **Methodological gap:** Existing studies rely on logistic regression; no ML risk
   stratification with SHAP interpretability or GWR local heterogeneity analysis for
   maternal health at district level in Ghana.

4. **Theoretical gap:** No formal causal DAG linking structural determinants (poverty,
   education, NHIS enrolment, workforce) to maternal health outcomes in Ghana
   at district level.

5. **Population gap:** Adolescent reproductive health (ABR, unmet need) rarely
   integrated with maternal health indicators in spatial analyses.

6. **Translational gap:** Evidence not mapped to Ghana's legal obligations under the
   Maputo Protocol (Art. 14) and Public Health Act (Act 851).

---

## 2. Study Objectives

**Primary:** Characterise the spatial distribution and clustering of maternal and
reproductive health outcomes across Ghana's 261 districts (2021–2022).

**Secondary objectives:**
1. Identify spatial hotspots (Gi*) and LISA cluster types for composite maternal health burden.
2. Quantify district-level correlates via GWR and XGBoost+SHAP.
3. Develop an ML risk-stratification model (High/Moderate/Low) for policy targeting.
4. Map findings to the Maputo Protocol + Ghana Act 851 policy framework.

---

## 3. Study Design

- **Design:** Ecological cross-sectional study with spatial epidemiology and ML components.
- **Period:** Cross-sectional 2021–2022 (DHIMS2 2022, DHS FR387, Census 2021).
- **Unit of analysis:** Ghana health district (N = 261).
- **Reporting:** STROBE + RECORD-Spatial + TRIPOD+AI.

---

## 4. Data Sources

| Dataset | Variables | Period |
|---------|-----------|--------|
| DHIMS2 2022 | SBA, ANC4+, facility delivery, PNC, MMR | 2022 |
| Ghana DHS 2022 (FR387) | ABR, mCPR, unmet need, skilled ANC | 2022 |
| GSS Census 2021 | Poverty, education, population denominators | 2021 |
| GHSF 2023 | Facility density, workforce | 2023 |
| NHIA 2022 | NHIS enrolment rate | 2022 |
| OSM / GHS GeoJSON | District boundaries (261 districts) | 2023 |

---

## 5. Outcome Variables

**Primary outcome:**
Composite maternal health index (0–100): PCA-derived standardised score from
SBA rate, ANC4+ coverage, facility delivery rate, and PNC rate.

**Secondary outcomes:**
- MMR (continuous; Poisson BYM model for small-area estimation)
- High-risk district classification (binary; XGBoost + SMOTE)

---

## 6. Analytical Plan

### 6.1 Descriptive Phase (Phase 1)
- Table 1: All indicators by region (mean ± SD for continuous; n(%) for categorical).
- DHIMS2 completeness audit: flag districts <80%.
- Outlier detection: IQR + z-score.

### 6.2 Spatial Analysis (Phases 2–5)

```
Step 1: Global Moran's I (KNN k=4, centroids) per indicator + composite
Step 2: Univariate LISA (Rook contiguity) — composite index
Step 3: Bivariate LISA (composite × poverty; composite × SBA; composite × NHIS enrolment)
Step 4: Getis-Ord Gi* — hotspot/coldspot districts
Step 5: SLM vs SEM (Lagrange multiplier test; select dominant model)
Step 6: Residual Moran's I after regression — confirm autocorrelation removed
```

### 6.3 Bayesian Disease Mapping (Phase 6 — MMR)

BYM/INLA: Poisson likelihood; E_i = expected cases from indirect standardisation.
Report: posterior mean RR per district + 95% CrI + P(RR>1|data) + spatial fraction φ.
Hotspot threshold: P(RR>1) > 0.95.

### 6.4 GWR (Phase 7)

GWR via GWmodel (R) or Python mgwr:
- AICc bandwidth selection
- Local R² map (choropleth)
- Local coefficient maps for top predictors

### 6.5 ML Risk Stratification (Phase 8)

```
Model:          XGBoost classifier (primary)
Outcome:        3-class risk label (High / Moderate / Low) from composite index tertiles
Features:       All predictor variables (Section 4 of scope lock)
Validation:     LOROCV (leave-one-region-out) — 16 regions
Class balance:  SMOTE (k_neighbors = min(5, n_pos - 1)) if any class < 10%
Metrics:        Macro-F1, AUC-OvR, sensitivity, specificity per class
Interpretability: SHAP summary + waterfall + dependence plots (top 5 features)
Benchmark:      Logistic regression (multinomial)
```

---

## 7. Causal Framework (DAG — to be formalised in Phase 4)

Key confounders to represent:
- Poverty → (SBA, ANC4+, facility delivery) ← NHIS enrolment ← employment
- Education (female) → (ANC4+, contraceptive use) → unmet need
- Urban/rural → distance to facility → SBA, facility delivery
- Workforce density → SBA, ANC quality

DAG will be sketched in tldraw → formalised in Mermaid → embedded as Figure S1.

---

## 8. Deliverables (Five Mandatory — Tenet 11)

| # | Deliverable | Target filename |
|---|-------------|-----------------|
| 1 | Manuscript | Project14_Manuscript_Maternal_Ghana_261Districts.docx |
| 2 | Conference Poster | Project14_Poster_Maternal_Ghana_261Districts.html |
| 3 | Interactive Dashboard | Maternal_Health_Ghana_Dashboard.html + app.py |
| 4 | Master CSV | master_maternal_ghana_261districts_v1.csv |
| 5 | GitHub Repository | maternal-reproductive-health-ghana-261-districts/ |

---

## 9. Policy Bridge

Per Tenet 12, confirmed spatial hotspots trigger /policy-bridge:
- **Maputo Protocol Art. 14:** State obligation to ensure reproductive health services
- **ICESCR Art. 12 (AAAQ):** Availability + Accessibility + Acceptability + Quality
- **African Charter Art. 16:** Right to health; non-discrimination (Art. 2)
- **Ghana Public Health Act 2012 (Act 851):** §14 notification; maternal death audit
- **NHIA Act 2012 (Act 852):** Equity in coverage for reproductive care

---

## 10. Timeline

| Phase | Activity | Target |
|-------|----------|--------|
| 0–1 | Data extraction + cleaning + Table 1 | Session 1 |
| 2–5 | Spatial analysis (Moran, LISA, Gi*, regression) | Session 2 |
| 6–7 | BYM/INLA + GWR | Session 2–3 |
| 8 | XGBoost + SHAP | Session 3 |
| 9 | Manuscript draft + STROBE | Session 4 |
| 10 | GitHub repo scaffold | Session 4 |
| 11 | QA Protocol (QA-0 through QA-8) | Session 4–5 |
| 12 | /github-publish | Session 5 |

---

*Protocol version: 1.0 | AIPOCH v6.5 | /scope-lock ENGAGED*
# END
