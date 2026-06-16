# Spatial Inequities in Maternal and Reproductive Health Outcomes and ML Risk Stratification Across 261 Districts of Ghana

[![CI](https://github.com/valentineghanem-bit/maternal-reproductive-health-ghana-261-districts/actions/workflows/ci.yml/badge.svg)](https://github.com/valentineghanem-bit/maternal-reproductive-health-ghana-261-districts/actions) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/) [![ORCID](https://img.shields.io/badge/ORCID-0009--0002--8332--0220-green.svg)](https://orcid.org/0009-0002-8332-0220)

**Author:** Valentine Golden Ghanem | Ghana COCOBOD Cocoa Clinic, Accra, Ghana
**ORCID:** [0009-0002-8332-0220](https://orcid.org/0009-0002-8332-0220)
**Affiliation:** Ghana COCOBOD Cocoa Clinic, Accra, Ghana
**Reporting standard:** STROBE · RECORD-Spatial · TRIPOD+AI
**Date:** 2026
**Status:** Manuscript in preparation

---

## 1. Abstract

This ecological, cross-sectional study quantifies spatial inequities in maternal and reproductive health service coverage across all 261 health districts of Ghana (2022 administrative boundaries). A 7-component composite maternal health index (DHS 2022 ANC4+, skilled birth attendance, facility delivery, and postnatal care, combined with inverted Census 2021 poverty, illiteracy, and uninsured rates) averaged 65.6 (SD 17.8) and was strongly spatially clustered (Global Moran's I = 0.8437, z = 21.36, p = 0.001; 999 permutations, KNN k = 4). Univariate and bivariate LISA and Getis-Ord Gi* localise a persistent northern disadvantage. A geographically weighted regression (GWR, pure-Python bisquare adaptive kernel, AICc bandwidth) substantially outperformed Global OLS (R² 0.9774 vs 0.898), evidencing spatially varying determinant effects. Gradient-boosting risk stratification with permutation importance and region-stratified leave-one-region-out cross-validation (LOROCV) identifies working-age population proportion, female population share, and the proportion of women without health insurance as the dominant district-level predictors of HIGH-risk classification.

---

## 2. Research Question & Aims

- **Primary:** Quantify and map spatial inequities in a composite maternal and reproductive health service-coverage index across Ghana's 261 districts, and identify their district-level determinants.
- **Secondary:** (a) Characterise spatial clustering of the composite index using Global/Local Moran's I, bivariate LISA, and Getis-Ord Gi*; (b) test whether determinant effects vary geographically via GWR versus Global OLS; (c) stratify districts into maternal-health risk tiers and rank predictors using gradient boosting with permutation importance; (d) assess generalisability under honest spatial leave-one-region-out cross-validation.

---

## 3. Methods Summary

| Method | Tool | Purpose |
|--------|------|---------|
| Composite maternal health index (7-component) | Custom / pandas | Service-coverage outcome construction |
| Global Moran's I (KNN k=4, 999 perms) | esda / libpysal | Spatial autocorrelation of the composite index |
| Univariate LISA | esda | High-High / Low-Low cluster detection |
| Bivariate LISA | esda | Determinant × outcome co-clustering |
| Getis-Ord Gi* | esda | Hotspot / coldspot identification |
| Global OLS + VIF + residual Moran's I | numpy / statsmodels-free | Baseline regression & spatial-residual diagnostics |
| Geographically Weighted Regression (GWR) | Pure Python (`05_gwr_python.py`) | Bisquare adaptive kernel, AICc bandwidth — spatially varying coefficients |
| Gradient Boosting (XGBoost if available) + permutation importance | scikit-learn | Risk stratification & predictor ranking |
| Region-stratified LOROCV + SMOTE | scikit-learn / imbalanced-learn | Honest spatial cross-validation, class balancing |

---

## 4. Data Sources

| Source | Variables | Year | Access |
|--------|-----------|------|--------|
| Ghana DHS 2022 | ANC4+, skilled birth attendance, facility delivery, PNC, mCPR, unmet need, ABR, TFR | 2022 | [dhsprogram.com](https://dhsprogram.com) (registration) |
| Ghana Population & Housing Census 2021 | District poverty, illiteracy, insurance coverage, demographic structure | 2021 | [statsghana.gov.gh](https://statsghana.gov.gh) |
| National Health Insurance Authority | District NHIS enrolment / uninsured rates | 2022 | NHIA Annual Report 2022 |
| Ghana 260-district boundary GeoJSON | Polygon geometries (Guan district tabular-only) | 2021 | [statsghana.gov.gh](https://statsghana.gov.gh) |

> DHS data accessed under the standard DHS Programme Data Use Agreement. No individual participant data redistributed.

---

## 5. Key Findings

| Metric | Value |
|--------|-------|
| Composite index, national mean (SD) | 65.6 (17.8) |
| Risk tertiles | 87 High- · 87 Moderate- · 87 Low-risk |
| Highest-coverage region | Bono (79.1) |
| Lowest-coverage region | Northern (24.8) |
| Equity gap (best ÷ worst region) | 3.2× |
| HIGH-risk districts (index < 50) | 43 |
| Composite index Global Moran's I | 0.8437 (z = 21.36, p = 0.001) |
| GWR R² (vs Global OLS R² 0.898) | 0.9774 |
| Top predictors (permutation importance) | Working-age proportion · female population share · uninsured women |
| Districts analysed | 261 (Guan tabular-only; 260 polygon geometries) |

---

## 6. Repository Structure

```
maternal-reproductive-health-ghana-261-districts/
├── scripts/
│   ├── 01_data_cleaning.py          # Ingestion, cleaning, composite index construction
│   ├── 02_spatial_analysis.py       # Moran's I, LISA, bivariate LISA, Getis-Ord Gi*
│   ├── 03_ml_pipeline.py            # Gradient Boosting + permutation importance + LOROCV
│   ├── 04_visualisations.py         # Choropleth, LISA, Gi* maps, figures
│   ├── 05_gwr_python.py             # GWR — pure Python (bisquare kernel, AICc), Global OLS, VIF
│   ├── 05_gwr_analysis.R            # R/GWmodel alternative — NOT executed (not a source of any reported value)
│   ├── 06_fix_figures.py            # Figure regeneration / formatting
│   └── build_final_dataset.py       # Master CSV assembly
├── master_maternal_ghana_261districts_v1.csv   # Master analytical dataset (261 districts)
├── dashboard/
│   └── Maternal_Reproductive_Health_Ghana_Dashboard.html   # HI-EI interactive dashboard (self-contained, offline)
├── poster/
│   └── Maternal_Reproductive_Health_Ghana_Poster.html      # Bespoke A0 conference poster (self-contained, print-ready)
├── data/
│   ├── raw/                         # Original subnational source files + boundary GeoJSON
│   └── processed/                   # Cleaned, analysis-ready CSV
├── outputs/
│   ├── data/                        # LISA / Gi* / GWR / ML intermediate outputs (CSV)
│   ├── figures/                     # Publication figures (PNG, 300 DPI)
│   └── tables/                      # Summary tables (CSV)
├── docs/                            # Data dictionary, methodology
├── tests/
│   └── test_canonical_values.py
├── requirements.txt
├── CITATION.cff
└── README.md
```

> The manuscript is maintained locally and is **not** committed to this repository (policy: source code and reproducible outputs only).

---

## 7. Reproducibility

### 7.1 Requirements

- Python 3.11 (pinned in `requirements.txt`)
- Key packages: numpy, pandas, geopandas, scikit-learn, xgboost, shap, matplotlib, plotly
- Random seed: 42 throughout; permutations: 999
- Estimated runtime: ~10–15 minutes on a standard laptop
- Tested on: Ubuntu 22.04 / Windows 11 (CI: GitHub Actions)

### 7.2 Clone & install

```bash
git clone https://github.com/valentineghanem-bit/maternal-reproductive-health-ghana-261-districts.git
cd maternal-reproductive-health-ghana-261-districts
pip install -r requirements.txt
```

### 7.3 Run the analytical pipeline

```bash
python scripts/01_data_cleaning.py
python scripts/02_spatial_analysis.py
python scripts/03_ml_pipeline.py
python scripts/05_gwr_python.py
python scripts/04_visualisations.py
python scripts/build_final_dataset.py
```

### 7.4 Run the test suite

```bash
pytest tests/ -v
```

### 7.5 Launch the interactive dashboard application

```bash
# The interactive Streamlit application (optional):
streamlit run app.py
# Visit the URL printed in the terminal (default http://localhost:8501)
```

### 7.6 Open the static HTML dashboard

```bash
# macOS
open dashboard/Maternal_Reproductive_Health_Ghana_Dashboard.html
# Windows
start dashboard/Maternal_Reproductive_Health_Ghana_Dashboard.html
# Linux
xdg-open dashboard/Maternal_Reproductive_Health_Ghana_Dashboard.html
```

---

## 8. Outputs

| Output | Description |
|--------|-------------|
| `outputs/data/` | Master analytical outputs: LISA / Gi* results, GWR coefficients, ML predictions |
| `outputs/figures/` | Publication-quality PNG figures (300 DPI) |
| `outputs/tables/` | Summary tables (Table 1, spatial summary) |
| `dashboard/` | Self-contained interactive HTML dashboard (HI-EI) |
| `poster/` | A0 conference poster (HTML, print-ready) |

## 8a. Downloadable Artefacts (HTML)

Both the interactive dashboard and the conference poster are committed as self-contained HTML files — no server, no build step required.

| Artefact | View on GitHub | Live preview | Direct download (raw HTML) |
|----------|---------------|--------------|---------------------------|
| Interactive dashboard | [View](https://github.com/valentineghanem-bit/maternal-reproductive-health-ghana-261-districts/blob/main/dashboard/Maternal_Reproductive_Health_Ghana_Dashboard.html) | [Preview](https://htmlpreview.github.io/?https://github.com/valentineghanem-bit/maternal-reproductive-health-ghana-261-districts/blob/main/dashboard/Maternal_Reproductive_Health_Ghana_Dashboard.html) | [Download](https://raw.githubusercontent.com/valentineghanem-bit/maternal-reproductive-health-ghana-261-districts/main/dashboard/Maternal_Reproductive_Health_Ghana_Dashboard.html) |
| Conference poster | [View](https://github.com/valentineghanem-bit/maternal-reproductive-health-ghana-261-districts/blob/main/poster/Maternal_Reproductive_Health_Ghana_Poster.html) | [Preview](https://htmlpreview.github.io/?https://github.com/valentineghanem-bit/maternal-reproductive-health-ghana-261-districts/blob/main/poster/Maternal_Reproductive_Health_Ghana_Poster.html) | [Download](https://raw.githubusercontent.com/valentineghanem-bit/maternal-reproductive-health-ghana-261-districts/main/poster/Maternal_Reproductive_Health_Ghana_Poster.html) |

> **Tip:** The dashboard works fully offline once downloaded. The poster is print-ready at A0 (841 × 1189 mm).

---

## 9. Reporting Standard

This study follows the **STROBE** (Strengthening the Reporting of Observational Studies in Epidemiology) reporting guideline for observational ecological studies. Machine learning components follow **TRIPOD+AI**; spatial statistical components follow **RECORD-Spatial**.

---

## 10. Ethical Statement

This study analyses publicly released aggregate data from the Ghana Demographic and Health Survey 2022 (ICF International), the Ghana Statistical Service 2021 Population and Housing Census, and National Health Insurance Authority district summaries. No individual participant data were accessed. All inputs are de-identified district and regional summary statistics aggregated to a level that precludes spatial re-identification. Ethical review was not required for analysis of publicly available aggregate statistics; DHS data were accessed under the standard DHS Programme Data Use Agreement.

---

## 11. Citation

**APA:**
Ghanem, V. G. (2026). *Spatial Inequities in Maternal and Reproductive Health Outcomes and ML Risk Stratification Across 261 Districts of Ghana.* GitHub. https://github.com/valentineghanem-bit/maternal-reproductive-health-ghana-261-districts

**BibTeX:**
```bibtex
@misc{ghanem2026maternal,
  author = {Ghanem, Valentine Golden},
  title  = {Spatial Inequities in Maternal and Reproductive Health Outcomes and ML Risk Stratification Across 261 Districts of Ghana},
  year   = {2026},
  url    = {https://github.com/valentineghanem-bit/maternal-reproductive-health-ghana-261-districts}
}
```

A machine-readable citation is provided in `CITATION.cff`.

---

## 12. License

Code is released under the **MIT License** — see [LICENSE](LICENSE) for details.
Outputs and figures: **CC BY 4.0**.

---

## 13. Author & Contact

**Valentine Golden Ghanem**
Ghana COCOBOD Cocoa Clinic, Accra, Ghana
Email: valentineghanem@gmail.com
ORCID: [0009-0002-8332-0220](https://orcid.org/0009-0002-8332-0220)

---

## 14. Acknowledgements

The author thanks the DHS Programme and ICF International for the Ghana DHS 2022, the Ghana Statistical Service for the 2021 Census district files and boundary GeoJSON, and the National Health Insurance Authority for district enrolment summaries. Spatial analysis relied on esda and libpysal; the GWR implementation is pure Python (bisquare adaptive kernel, AICc bandwidth). Machine learning used scikit-learn and XGBoost with permutation importance and region-stratified cross-validation.
