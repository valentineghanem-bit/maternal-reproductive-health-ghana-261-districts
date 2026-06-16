# Spatial Inequities in Maternal and Reproductive Health Outcomes and ML Risk Stratification Across 261 Districts of Ghana

**Authors:** Valentine Golden Ghanem  
**Institution:** Ghana COCOBOD Cocoa Clinic, Accra, Ghana  
**Date initiated:** June 2026  
**Status:** Phases 1–7 complete (data cleaning, spatial analysis, ML risk stratification, visualisations, GWR, master dataset assembly, manuscript drafting). Manuscript (with embedded figures), interactive HI-EI dashboard, and bespoke A0 poster finalised (2026-06-16).

---

## Overview

This repository contains the full reproducible analytical pipeline for a 261-district ecological cross-sectional study examining spatial inequities in maternal and reproductive health outcomes across Ghana.

**Central thesis:** Maternal health outcomes in Ghana exhibit significant spatial autocorrelation, with high-risk clusters concentrated in northern and rural districts, driven by poverty, NHIS enrolment deficits, and facility access barriers — all addressable through geographically targeted policy under the Maputo Protocol, Ghana Public Health Act 851, and the National Health Insurance Act 852.

**Five mandatory deliverables:**
- Manuscript (STROBE + RECORD-Spatial + TRIPOD+AI)
- Conference poster — bespoke A0 HTML (self-contained, colourblind-safe, print-ready)
- Interactive HTML dashboard — HI-EI (Health Information / Epidemiology Intelligence Dashboard); self-contained, offline-capable, zoomable district maps with full LISA legend
- Master CSV: `master_maternal_ghana_261districts_v1.csv`
- This repository

---

## Study Design

| Feature | Detail |
|---------|--------|
| Study type | Ecological cross-sectional |
| Geographic unit | Health district (N=261) |
| Period | 2022 (DHIMS2, DHS, Census, NHIA) |
| Primary outcome | Composite maternal health index — 7-component (DHS 2022 ANC4+/SBA/facility delivery/PNC + inverted Census 2021 poverty/illiteracy/uninsured rates), COMP-006 |
| Secondary outcomes | MMR, ABR, mCPR, unmet need for family planning |
| Spatial analysis | Global Moran's I · Univariate LISA · Bivariate LISA · Getis-Ord Gi* |
| Regression | Global OLS (R²=0.898) · GWR — pure Python (`05_gwr_python.py`), bisquare adaptive kernel, AICc bandwidth selection (R²=0.9774) |
| ML | Gradient Boosting (sklearn; XGBoost preferred if available) + permutation feature importance (SHAP-analogous) · LOROCV · SMOTE |
| Bayesian | BYM/iCAR (R-INLA) for MMR small-area estimation — **planned, not yet executed** |

---

## Repository Structure

```
maternal-reproductive-health-ghana-261-districts/
│
├── data/                          # Data directory (see Data Access below)
│   ├── raw/                       # Original source files (not committed if >50 MB)
│   └── processed/                 # Cleaned, analysis-ready CSV
│
├── scripts/
│   ├── 01_data_cleaning.py        # Data ingestion, cleaning, composite index
│   ├── 02_spatial_analysis.py     # Pure-numpy spatial analysis (Moran's I, LISA, Gi*)
│   ├── 03_ml_pipeline.py          # Gradient Boosting (XGBoost if available) + permutation importance + LOROCV
│   ├── 04_visualisations.py       # Choropleth maps, LISA maps, figures
│   ├── 05_gwr_python.py           # GWR — pure Python (bisquare kernel, AICc bandwidth, haversine), Global OLS, VIF, residual Moran's I
│   ├── 05_gwr_analysis.R          # Drafted R/GWmodel alternative GWR + Moran's I verification — NOT executed (R unavailable in sandbox); not the source of any reported value
│   └── build_final_dataset.py     # Master CSV assembly
│
├── dashboard/
│   └── Maternal_Reproductive_Health_Ghana_Dashboard.html   # HI-EI interactive dashboard (self-contained, offline)
│
├── poster/
│   └── Maternal_Reproductive_Health_Ghana_Poster.html      # Bespoke A0 conference poster (self-contained, print-ready)
│
├── figures/                       # Reserved for manuscript/journal-final figure selections
│                                   #   (currently empty — .gitkeep; all 9 generated figures
│                                   #   live in outputs/figures/, see below)
├── outputs/
│   ├── data/                      # Intermediate analytical outputs (CSV)
│   ├── figures/                   # All 9 script-generated figures (300 DPI PNG):
│   │                               #   choropleth_composite_index.png, lisa_cluster_map.png,
│   │                               #   bivariate_lisa_map.png, gi_star_hotspot_map.png,
│   │                               #   moran_scatterplot.png, shap_summary.png,
│   │                               #   shap_dependence_1/2/3_*.png
│   └── tables/                    # Table 1 and supplementary tables
│
├── tests/
│   └── test_canonical_values.py   # Pytest canonical assertions (populated at QA-0)
│
├── docs/
│   ├── methodology.md             # Full analytical methods documentation
│   └── data_dictionary.md         # Column-by-column dictionary for the master CSV (89 cols)
│
├── master_maternal_ghana_261districts_v1.csv    # Master dataset (261 rows)
├── requirements.txt               # Pinned Python dependencies
├── CITATION.cff                   # Machine-readable citation
├── LICENSE                        # MIT
├── Dockerfile                     # Reproducible environment
├── .gitattributes                 # Git LFS for large binary files
└── .github/workflows/ci.yml       # CI: lint + test on push/PR
```

---

## Installation & Reproducibility

### Python environment

```bash
git clone https://github.com/valentineghanem-bit/maternal-reproductive-health-ghana-261-districts.git
cd maternal-reproductive-health-ghana-261-districts
pip install -r requirements.txt
```

### Docker (recommended for exact reproducibility)

```bash
docker build -t maternal-ghana .
docker run -v $(pwd):/workspace maternal-ghana
```

### R packages (optional — not required for any reported result)

GWR, OLS/VIF, and Moran's I verification are all implemented in pure Python (`scripts/05_gwr_python.py`, `scripts/02_spatial_analysis.py`) and require no R installation. `scripts/05_gwr_analysis.R` is a drafted alternative R/GWmodel + spdep implementation that was never executed (R unavailable in the analysis sandbox). It is retained for users who wish to independently verify results in R, but is not part of the reproducibility chain:

```r
install.packages(c("tidyverse", "sf", "spdep", "GWmodel", "car"))
```

---

## Analysis Workflow

Run scripts in order:

```bash
python scripts/01_data_cleaning.py      # Phase 1: data preparation, composite index
python scripts/02_spatial_analysis.py   # Phase 2: Moran's I, LISA, Gi*
python scripts/03_ml_pipeline.py        # Phase 3: ML risk stratification (Gradient Boosting/XGBoost + permutation importance + LOROCV)
python scripts/04_visualisations.py     # Phase 4: figures and maps
python scripts/05_gwr_python.py         # Phase 5: Global OLS, VIF, GWR (pure Python, no R required)
python scripts/build_final_dataset.py   # Phase 6: master CSV assembly
pytest tests/ -v                        # Validate canonical values
```

**Note:** `scripts/05_gwr_analysis.R` is a drafted, unexecuted alternative implementation (requires R + GWmodel + spdep) and is not part of this workflow — see `docs/methodology.md` §5.5/§6.2.

**Important:** Place the 261-district GeoJSON file (`ghana_districts_261.geojson`) in `data/raw/` before running.  
Download from: https://data.humdata.org/dataset/ghana-administrative-boundaries

---

## Data Access

| Source | Variable set | Year | Access |
|--------|-------------|------|--------|
| Ghana DHIMS2 | SBA, ANC4+, facility delivery, PNC, MMR | 2022 | GHS approved researchers |
| Ghana DHS 2022 (FR387) | mCPR, ABR, unmet need (regional) | 2022 | https://dhsprogram.com |
| GSS Population Census | Population denominators, poverty, education | 2021 | https://statsghana.gov.gh |
| NHIA Annual Report | NHIS enrolment rates | 2022 | https://nhia.gov.gh |
| GHSF 2023 | Facility density, workforce density | 2023 | GHS |

**Note on DHS data:** Ghana DHS 2022 is published at regional level (16 regions). Regional values are assigned to constituent districts using the POST_TO_PRE and DHS_TO_MS16 harmonisation dictionaries documented in `scripts/01_data_cleaning.py`.

---

## Key Methods Notes

- **261 districts**: Guan district (Oti Region), gazetted 2019, is included. Legacy GeoJSON files that omit Guan are supplemented with manual corrections.
- **Spatial weights**: Global Moran's I uses KNN k=4 from district centroids; LISA uses Rook contiguity (≥2 shared GeoJSON vertices). Consistent with Projects 8–13 (EX-008).
- **LOROCV**: All ML performance statistics are from leave-one-region-out cross-validation (16 folds), not random splits, to prevent ecological artifact inflation (ML-005).
- **SMOTE guard**: k_neighbors = min(5, min_class_n − 1) to prevent errors with small folds (EX-028).
- **Random seed**: 42, fixed throughout (ML-002).
- **No libpysal dependency**: Spatial analysis is implemented in pure NumPy + SciPy (EX-031).
- **GWR also pure Python**: `05_gwr_python.py` implements Global OLS, VIF, and GWR (bisquare adaptive kernel, AICc bandwidth selection, haversine distance) without any R dependency; `05_gwr_analysis.R` is a drafted, unexecuted alternative (GWR-004/GWR-005).
- **Permutation importance, not SHAP**: Tenet-13 interpretability is provided via `sklearn.inspection.permutation_importance` (model-agnostic, Breiman 2001), saved to `shap_values.csv` (filename retained for pipeline compatibility) and `permutation_importance.csv`. No SHAP library is used and no waterfall plot exists (ML-DOC-003/004).

---

## Reporting Guidelines

This study adheres to:
- **STROBE** — STrengthening the Reporting of OBservational studies in Epidemiology
- **RECORD-Spatial** — RECORD extension for spatial analyses of routinely collected data
- **TRIPOD+AI** — Transparent Reporting of a multivariable prediction model for Individual Prognosis Or Diagnosis (AI extension)

---

## Policy Bridge

Confirmed spatial hotspots trigger automatic policy mapping across:
- Maputo Protocol (Article 14) — women's reproductive health rights
- ICESCR Article 12 (AAAQ Framework) — right to health
- African Charter on Human and Peoples' Rights (Articles 2, 16)
- Ghana Public Health Act, 2012 (Act 851) — mandatory notification
- National Health Insurance Act, 2012 (Act 852) — geographic equity mandate

---

## Target Journal

1. **Reproductive Health** (Q1, IF 4.1) — APC waiver via Hinari Group B
2. **BMC Pregnancy and Childbirth** (Q1) — APC waiver via Hinari Group B  
3. **BMJ Global Health** (Q1, IF 7.1) — APC waiver for LMIC authors

---

## Citation

If you use this code or data, please cite:

```
Ghanem VG. Spatial inequities in maternal and reproductive health outcomes and ML risk
stratification across 261 districts of Ghana. [Preprint] 2026.
```

See `CITATION.cff` for machine-readable citation format.

---

## Ethics

Ethical approval: Ghana Health Service Ethics Review Board (GHS-ERC).  
This study uses aggregate district-level data. No individual-level data are included.  
Data availability: GHS data available to approved researchers upon application.

---

## Licence

MIT © 2026 Valentine Golden Ghanem

---

## AIPOCH Framework

This repository was produced using the AIPOCH v6.5 Public Health & Epidemiology Research System.  
QA badge will be issued at project completion: `QA_PASSED_[Date].txt`
