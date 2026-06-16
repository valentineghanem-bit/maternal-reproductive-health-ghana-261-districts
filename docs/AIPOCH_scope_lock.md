# Project 14 — Scope Lock
## Spatial Inequities in Maternal and Reproductive Health Outcomes and ML Risk Stratification
## 261-District Ghana Analysis | AIPOCH v6.5 | /scope-lock ENGAGED

---

## CENTRAL THESIS

This study addresses the **empirical, methodological, and translational** research gaps in
maternal and reproductive health surveillance in sub-Saharan Africa by applying
district-level spatial epidemiology and machine learning risk stratification to Ghana's
261 health districts, advancing evidence for targeted policy intervention under
Articles 12 & 14 of the ICESCR and the Maputo Protocol.

**Anchor statement:**
"This study characterises the spatial distribution of maternal and reproductive health
outcomes across Ghana's 261 districts using Global Moran's I, bivariate LISA, and Gi*
hotspot analysis; identifies district-level correlates via GWR and XGBoost+SHAP; and
produces an ML risk-stratification model to guide resource allocation toward districts
at highest risk of poor maternal outcomes."

---

## RESEARCH OBJECTIVES

1. Quantify the spatial autocorrelation and clustering of maternal and reproductive health
   indicators across Ghana's 261 districts.
2. Identify spatial hotspots and coldspots for composite maternal health burden.
3. Determine district-level correlates of poor maternal health outcomes using GWR and
   XGBoost + SHAP interpretability.
4. Develop an ML risk-stratification model classifying districts as High / Moderate / Low
   risk for targeted intervention.
5. Map spatial findings to Ghana's legal and policy framework (Maputo Protocol, Act 851,
   SDG 3.1, 3.7).

---

## PRIMARY OUTCOMES (dependent variables)

> REVISED 2026-06-09 (Phase 0): Data confirmed from uploaded real datasets. ANC4+ visits
> not available at regional level in DHS subnational files; replaced with ANC skilled provider.
> All DHS variables are at REGIONAL level (16 regions), assigned to constituent districts.

| Indicator | Exact DHS/Source variable | Level | Range |
|-----------|--------------------------|-------|-------|
| Skilled birth attendance (SBA %) | "Assistance during delivery from a skilled provider" | Regional (DHS 2022) | 70.3–98.0% |
| Institutional delivery (%) | "Place of delivery: Health facility" | Regional (DHS 2022) | 67.1–97.4% |
| ANC skilled coverage (%) | "Antenatal care from a skilled provider" | Regional (DHS 2022) | 92.9–100.0% |
| Postnatal care ≤48h (%) | 100 – "No postnatal checkup for mother within first two days of birth" | Regional (DHS 2022) | 72.7–96.7% |
| Modern CPR (%) | "Current use of any modern method of contraception (all women)" | Regional (DHS 2022) | 14.8–29.8% |
| TFR (births per woman) | "Total fertility rate 15-49" | Regional (DHS 2022) | 2.9–6.6 |
| ABR (per 1,000 women 15–19) | "Age specific fertility rate: 15-19" | Regional (DHS 2022) | 36–121 |
| Unmet need for FP (%) | "Unmet need for family planning, total (all women)" | Regional (DHS 2022) | 12.5–21.8% |
| FP demand satisfied (%) | "Demand for family planning satisfied by modern methods (all women)" | Regional (DHS 2022) | 37.9–61.7% |

**Composite outcome (primary):** Equal-weight min-max index (0–100, higher = better):
`mean([norm(anc_skilled), norm(sba), norm(facility_delivery), norm(pnc_coverage)]) × 100`

---

## PREDICTOR VARIABLES (covariates)

> CONFIRMED 2026-06-09 from real data. Variables listed with exact source column names.

| Variable | Exact source variable | Source | Level | Range |
|---------|----------------------|--------|-------|-------|
| `poverty_rate` | Incidence of Poverty | Master Sheet (Census 2021) | District | Varies |
| `uninsured_rate` | Uninsured Population / Total Population × 100 | Master Sheet (Census 2021) | District | Derived |
| `illiteracy_rate` | Illiterate Population / Total Population × 100 | Master Sheet (Census 2021) | District | Derived |
| `working_age_prop` | (Male+Female Pop 15-64) / Total × 100 | Master Sheet (Census 2021) | District | Derived |
| `women_edu_secondary` | "Women with secondary or higher education" | DHS 2022 | Regional | 31.8–84.6% |
| `women_literacy` | "Women who are literate" | DHS 2022 | Regional | 27.2–79.2% |
| `no_insurance_women` | "No health insurance [Women]" | DHS 2022 | Regional | 1.5–16.5% |
| `women_anemia` | "Women with any anemia" | DHS 2022 | Regional | 30.1–51.8% |
| `wife_beating_justified` | "Wife beating justified for at least one specific reason [Women]" | DHS 2022 | Regional | 5.8–57.8% |
| `decision_autonomy` | "Final say in all of the decisions [Women]" | DHS 2022 | Regional | 38.1–71.3% |
| `ipv_12months` | "Physical or sexual or emotional violence committed by husband/partner in last 12 months" | DHS 2022 | Regional | 18.3–46.9% |

**National context (WHO GHO — Introduction only, not in models):**
- Nursing & midwifery per 10,000: 44.7 (2022)
- Health workforce data is NATIONAL level only — not available subnationally from provided files

---

## ANALYTICAL PIPELINE (Chain B + Chain D)

```
Phase 0   /datalog — provenance, IRB reference
Phase 1   /explore-data — Table 1, data quality audit, DHIMS2 completeness flags
Phase 2   Spatial autocorrelation (KNN k=4): Global Moran's I per indicator
Phase 3   Univariate LISA (Rook contiguity) → Bivariate LISA (composite × poverty)
Phase 4   Getis-Ord Gi* hotspot delineation
Phase 5   Spatial regression: SLM vs SEM (Lagrange multiplier test)
Phase 6   BYM/INLA for district-level MMR (Poisson; φ + exceedance P(RR>1))
Phase 7   GWR (AICc bandwidth; local R² map)
Phase 8   XGBoost + SHAP (composite risk index outcome; SMOTE if class < 10%)
Phase 9   Manuscript (STROBE + RECORD-Spatial + TRIPOD+AI)
Phase 10  GitHub repo scaffold
Phase 11  QA Protocol (QA-0 through QA-8)
Phase 12  /github-publish
```

---

## DATA LOG (CONFIRMED Phase 0 — 2026-06-09)

```
/datalog
  DS-01: Ghana DHS 2022 Subnational (7 files)
  Level:     Regional (16 post-2022 regions)
  Filter:    SurveyYear==2022, IsPreferred==1.0, Location IN DHS_TO_MS16.keys()
  Extracted: 2026-06-09
  IRB:       Ghana Health Service Ethics Review Board [REF TBC]

  DS-02: GSS Census 2021 (Master Sheet.xlsx)
  Level:     District (N=261)
  Extracted: 2026-06-09
  Columns:   MMDA names, Region, Lat/Lon, Poverty, Uninsured, Illiteracy, Population

  DS-03: Ghana_New_260_District.geojson
  Level:     District polygons (N=260; Guan absent)
  Extracted: 2026-06-09
  Note:      DISTRICT field ALL CAPS; ~85 name mismatches with DS-02 → MANUAL_CORRECTIONS

  DS-04: WHO GHO national files (3 files)
  Level:     NATIONAL ONLY — not for spatial analysis
  Use:       Background statistics in Introduction + Methods only
```

---

## SCOPE BOUNDARIES (non-negotiable)

- Geographic unit: Ghana 261 health districts (261st = Guan, Oti; island district, no polygon)
- Time period: Cross-sectional 2021–2022 (DHIMS2 2022 + DHS 2022 + Census 2021)
- Study design: Ecological cross-sectional with ML risk stratification
- Population: All women of reproductive age (15–49) in Ghana
- Outcomes are district-level aggregates — NO individual-level inference (ecological fallacy caveat mandatory)

---

## TARGET JOURNAL (ranked by fit + APC waiver)

| Priority | Journal | IF | Q | APC waiver |
|----------|---------|-----|---|-----------|
| 1 | Reproductive Health | 4.1 | Q1 | Hinari Group B ✓ |
| 2 | BMC Pregnancy and Childbirth | 3.1 | Q2 | Hinari Group B ✓ |
| 3 | BMJ Global Health | 6.1 | Q1 | APC waiver Ghana ✓ |
| 4 | PLOS ONE | 3.7 | Q1 | DOAJ Gold ✓ |
| 5 | International Journal of Gynaecology & Obstetrics | 2.6 | Q2 | Hinari Group B ✓ |

*All APC waivers to be verified at session start per --ghana-apc-lock.*

---

## REPORTING GUIDELINE

STROBE (primary) + RECORD-Spatial (geographic extension) + TRIPOD+AI (ML component)

---

## POLICY BRIDGE TRIGGERS

- /policy-bridge fires if confirmed spatial hotspots identified (Tenet 12)
- Legal hierarchy: Maputo Protocol Art. 14 (women's reproductive health) → ICESCR Art. 12
  → African Charter Art. 16 → Ghana Public Health Act 2012 (Act 851) → NHIA Act 2012 (Act 852)

---

/scope-lock ENGAGED 2026-06-09 | Valentine Golden Ghanem | AIPOCH v6.5
New directions require explicit /scope-unlock with justification.
# END
