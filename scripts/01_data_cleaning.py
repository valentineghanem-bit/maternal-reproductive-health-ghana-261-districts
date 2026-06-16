"""
Project 14: Ghana Maternal & Reproductive Health -- 261 Districts
Script 01: Data Cleaning & Integration
Author: Valentine Golden Ghanem
Date: 2026-06-09 (Phase 1 -- real data integration)

Inputs (relative to ROOT/data/raw/):
  - access-to-health-care_subnational_gha.csv
  - fp2020_subnational_gha.csv
  - fertility-rates_subnational_gha.csv
  - anemia_subnational_gha.csv
  - select-gender-indicators_subnational_gha.csv
  - health-insurance_subnational_gha.csv
  - select-education-indicators_subnational_gha.csv
  - Master Sheet.xlsx  (GSS Census 2021, 261 districts)
  - Ghana_New_260_District.geojson  (260 district polygons)

Outputs:
  - data/processed/maternal_ghana_261districts_clean.csv
  - outputs/tables/table1_descriptive.csv
  - outputs/data/district_crosswalk.csv
  - outputs/data/data_quality_report.csv

COMP-002: DHS 2022 subnational files are REGIONAL level (16 regions).
Regional values are assigned to all constituent districts (ecological design;
acknowledged per STROBE s7 and manuscript Limitations).

COMP-006: composite_maternal_index audit fix (2026-06-10). Using ONLY the 4 DHS
regional service-coverage variables (anc_skilled, sba, facility_delivery,
pnc_coverage) produced an index with exactly 16 unique values (one per region) --
i.e. zero within-region district-level variation. This would make Phase 2-3
spatial analysis (Moran's I / LISA) and Phase 4 ML risk stratification trivially
collinear with region membership (ecological fallacy made literal). FIX: composite
now blends the 4 DHS regional service-coverage indicators (supply-side, ecologically
assigned) with 3 district-level census-derived access-barrier indicators -- inverted
poverty_rate, illiteracy_rate, uninsured_rate (demand-side, genuinely vary by
district). This restores meaningful within-region district variation while
preserving the maternal-health DHS focus. Documented in Methods/Limitations.
"""

import os
import json
import warnings
import pandas as pd
import numpy as np
from scipy import stats

warnings.filterwarnings("ignore")

# ── Relative paths (EX-026) ───────────────────────────────────────────────────
BASE         = os.path.dirname(os.path.abspath(__file__))
ROOT         = os.path.dirname(BASE)
RAW          = os.path.join(ROOT, "data", "raw")
PROC         = os.path.join(ROOT, "data", "processed")
OUT_DATA     = os.path.join(ROOT, "outputs", "data")
OUT_TABLES   = os.path.join(ROOT, "outputs", "tables")
GEOJSON_PATH = os.path.join(RAW, "Ghana_New_260_District.geojson")
MASTER_SHEET = os.path.join(RAW, "Master Sheet.xlsx")

for _d in [PROC, OUT_DATA, OUT_TABLES]:
    os.makedirs(_d, exist_ok=True)

# ── DHS file paths ────────────────────────────────────────────────────────────
DHS_FILES = {
    "access":    os.path.join(RAW, "access-to-health-care_subnational_gha.csv"),
    "fp2020":    os.path.join(RAW, "fp2020_subnational_gha.csv"),
    "fertility": os.path.join(RAW, "fertility-rates_subnational_gha.csv"),
    "anemia":    os.path.join(RAW, "anemia_subnational_gha.csv"),
    "gender":    os.path.join(RAW, "select-gender-indicators_subnational_gha.csv"),
    "insurance": os.path.join(RAW, "health-insurance_subnational_gha.csv"),
    "education": os.path.join(RAW, "select-education-indicators_subnational_gha.csv"),
}

# ── Region crosswalk: DHS Location --> Master Sheet Region ───────────────────
DHS_TO_MS16 = {
    "Ahafo":                 "Ahafo",
    "Ashanti":               "Ashanti",
    "Bono":                  "Bono",
    "Bono East":             "Bono East",
    "Central":               "Central",
    "Eastern":               "Eastern",
    "Greater Accra":         "Greater Accra",
    "..Northeast":           "North East",
    "..Northern(post 2022)": "Northern",
    "Oti":                   "Oti",
    "..Savannah":            "Savannah",
    "Upper East":            "Upper East",
    "Upper West":            "Upper West",
    "Volta (post 2022)":     "Volta",
    "Western (post 2022)":   "Western",
    "Western North":         "Western North",
}

# ── GeoJSON DISTRICT (ALL CAPS) --> Master Sheet MMDA name (SPAT-006) ────────
MANUAL_CORRECTIONS = {
    "ABUAKWA NORTH":                         "Abuakwa North Municipal",
    "ABUAKWA SOUTH":                         "Abuakwa South Municipal",
    "ABURA-ASEBU-KWAMANKESE":                "Abura Asebu Kwamankese",
    "ACCRA METROPOLIS":                      "Accra Metropolitan Area (AMA)-Ablekuma South, Ashiedu Keteke & Okaikoi South",
    "ADANSI AKROFUOM":                       "Akrofuom",
    "ADENTA MUNICIPAL":                      "Adentan Municipal",
    "AGOTIME ZIOPE":                         "Agortime-Ziope",
    "AHAFO ANO NORTH":                       "Ahafo Ano North Municipal",
    "AJUMAKO-ENYAN-ESSIAM":                  "Ajumako Enyan Essiam",
    "AKATSI SOUTH":                          "Akatsi South Municipal",
    "AKWAPEM NORTH":                         "Akwapim North Municipal",
    "AKWAPEM SOUTH":                         "Akwapim South Municipal",
    "AKYEM MANSA":                           "Akyemansa",
    "AOWIN":                                 "Aowin Municipal",
    "ASANTE AKIM NORTH":                     "Asante Akim North Municipal",
    "ASANTE AKIM SOUTH":                     "Asante Akim South Municipal",
    "ASENE AKROSO MANSO":                    "Asene Manso Akroso",
    "ASIKUMA-ODOBEN-BRAKWA":                 "Asikuma Odoben Brakwa",
    "ASOKWA  MUNICIPAL":                     "Asokwa Municipal",
    "ASSIN FOSU":                            "Assin Central Municipal",
    "ATEBUBU AMANTIN":                       "Atebubu Amantin Municipal",
    "ATWIMA NWABIAGYA SOUTH":                "Atwima Nwabiagya South Municipal",
    "AWUTU SENYA":                           "Awutu Senya West",
    "AWUTU SENYA EAST":                      "Awutu Senya East Municipal",
    "AYAWASO WEST":                          "Ayawaso West Municipal",
    "BIBIANI-ANHWIASO-BEKWAI MUNICIPAL":     "Bibiani Anhwiaso Bekwai Municipal",
    "BOLGA  EAST":                           "Bolgatanga East",
    "BOSOMTWE":                              "Bosomtwi",
    "BUILSA NORTH":                          "Builsa North Municipal",
    "CAPE COAST METROPOLITAN":               "Cape Coast Metropolitan Area (CCMA)-Cape Coast South & Cape Coast North",
    "DENKYEMBOUR":                           "Denkyembuor",
    "DORMAA MUNICIPAL":                      "Dormaa Central Municipal",
    "EAST MAMPRUSI":                         "East Mamprusi Municipal",
    "EJURA-SEKYEDUMASE":                     "Ejura Sekyedumase Municipal",
    "GA EAST":                               "Ga East Municipal",
    "GUSHEGU":                               "Gushegu Municipal",
    "JAMAN SOUTH MUNICIPAL":                 "Jaman South",
    "JASIKAN":                               "Jasikan Municipal",
    "JIRAPA":                                "Jirapa Municipal",
    "JOMORO":                                "Jomoro Municipal",
    "KASENA NANKANA EAST":                   "Kasena Nankana Municipal",
    "KETU NORTH":                            "Ketu North Municipal",
    "KETU SOUTH":                            "Ketu South Municipal",
    "KOMENDA-EDINA-EGUAFO-ABIREM MUNICIPAL": "Komenda Edina Eguafo Abirem Municipal",
    "KPONE KATAMANSO":                       "Kpone Katamanso Municipal",
    "KRACHI WEST":                           "Krachi West Municipal",
    "KUMASI METROPOLITAN":                   "Kumasi Metropolitan Area (KMA)-Bantama, Manhyia North, Manhyia South, Nhyiaeso, & Subin",
    "KWAEBIBIREM":                           "Kwaebibirem Municipal",
    "KWAHU SOUTH":                           "Kwahu South Municipal",
    "KWAHU WEST":                            "Kwahu West Municipal",
    "LA DADE-KOTOPON":                       "La Dade-Kotopon Municipal",
    "LA-NKWANTANANG-MADINA":                 "La Nkwantanang Madina Municipal",
    "LAMBUSSIE-KARNI":                       "Lambussie Karni",
    "LAWRA":                                 "Lawra Municipal",
    "LOWER MANYA":                           "Lower Manya Krobo Municipal",
    "MFANTSEMAN MUNICIPAL":                  "Mfantsiman Municipal",
    "NADOWLI-KALEO":                         "Nadowli Kaleo",
    "NANUMBA NORTH":                         "Nanumba North Municipal",
    "NINGO/PRAMPRAM":                        "Ningo-Prampram",
    "NKORANZA SOUTH":                        "Nkoranza South Municipal",
    "NKWANTA NORTH":                         "Nkwanta North (Kpassa)",
    "NSAWAM ADOAGYIRI":                      "Nsawam Adoagyiri Municipal",
    "NZEMA EAST":                            "Nzema East Municipal",
    "OKAIKWEI NORTH MUNICIPAL":              "Okaikoi North Municipal",
    "PRESTEA/HUNI VALLEY":                   "Prestea/Huni Valley Municipal",
    "SAGNERIGU":                             "Sagnarigu Municipal",
    "SAVELUGU":                              "Savelugu Municipal",
    "SAWLA-TUNA-KALBA":                      "Sawla Tuna Kalba",
    "SEFWI-WIAWSO":                          "Sefwi Wiawso Municipal",
    "SEKONDI TAKORADI METROPOLIS":           "Sekondi Takoradi Metropolitan Area (STMA)-Takoradi, Sekondi & Essikado-Ketan",
    "SEKYERE AFRAM PLAINS NORTH":            "Sekyere Afram Plains",
    "SHAI OSUDOKU":                          "Shai-Osudoku",
    "SISSALA EAST":                          "Sissala East Municipal",
    "SUNYANI WEST":                          "Sunyani West Municipal",
    "TAMALE METROPOLITAN":                   "Tamale Metropolitan Area (TMA)-Tamale Central & Tamale South",
    "TARKWA NSUAEM":                         "Tarkwa-Nsuaem Municipal",
    "TEMA METROPOLITAN":                     "Tema Metropolitan Area (TMA)-Tema Central & Tema East",
    "TWIFO ATTI-MORKWA":                     "Twifo Ati Morkwa",
    "TWIFO HEMANG LOWER DENKYIRA":           "Twifo Heman Lower Denkyira",
    "UPPER MANYA":                           "Upper Manya Krobo",
    "WASSA AMENFI EAST":                     "Wassa Amenfi East Municipal",
    "WASSA AMENFI WEST":                     "Wassa Amenfi West Municipal",
    "WEST AKIM":                             "West Akim Municipal",
    "YILO KROBO":                            "Yilo Krobo Municipal",
    "YUNYOO-NASUAN":                         "Yunyoo Nasuan",
}

# ── DHS Indicator string --> column name ──────────────────────────────────────
DHS_INDICATOR_MAP = {
    "Assistance during delivery from a skilled provider":              "sba",
    "Place of delivery: Health facility":                              "facility_delivery",
    "Antenatal care from a skilled provider":                          "anc_skilled",
    "No postnatal checkup for mother within first two days of birth":  "no_postnatal_checkup",
    "Current use of any modern method of contraception (all women)":   "modern_cpr",
    "Unmet need for family planning, total (all women)":               "unmet_need_fp",
    "Demand for family planning satisfied by modern methods (all women)": "demand_fp_satisfied",
    "Total fertility rate 15-49":                                      "tfr",
    "Age specific fertility rate: 15-19":                              "abr",
    "Women with any anemia":                                           "women_anemia",
    "Wife beating justified for at least one specific reason [Women]": "wife_beating_justified",
    "Final say in all of the decisions [Women]":                       "decision_autonomy",
    "Physical or sexual or emotional violence committed by husband/partner in last 12 months": "ipv_12months",
    "No health insurance [Women]":                                     "no_insurance_women",
    "Women with secondary or higher education":                        "women_edu_secondary",
    "Women who are literate":                                          "women_literacy",
}

COMPOSITE_COLS = ["anc_skilled", "sba", "facility_delivery", "pnc_coverage"]
# COMP-006: district-level access-barrier indicators (inverted: higher = worse)
# blended in to give composite_maternal_index genuine within-region district variation
COMPOSITE_DISTRICT_COLS = ["poverty_rate", "illiteracy_rate", "uninsured_rate"]

KEY_VARS = [
    "composite_maternal_index", "sba", "facility_delivery", "anc_skilled",
    "pnc_coverage", "modern_cpr", "unmet_need_fp", "demand_fp_satisfied",
    "tfr", "abr", "women_anemia", "wife_beating_justified",
    "decision_autonomy", "ipv_12months", "no_insurance_women",
    "women_edu_secondary", "women_literacy",
    "poverty_rate", "uninsured_rate", "illiteracy_rate",
    "working_age_prop", "female_pop_prop",
]


# =============================================================================
def load_dhs_subnational():
    frames = []
    for key, fpath in DHS_FILES.items():
        if not os.path.exists(fpath):
            print(f"  [WARN] missing: {os.path.basename(fpath)}")
            continue
        df = pd.read_csv(fpath, dtype=str)
        df = df[df["ISO3"] != "#country+code"].copy()
        for col in ["SurveyYear", "IsPreferred", "Value"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df[
            (df["SurveyYear"] == 2022) &
            (df["IsPreferred"] == 1.0) &
            (df["Location"].isin(DHS_TO_MS16.keys()))
        ].copy()
        df = df[df["Indicator"].isin(DHS_INDICATOR_MAP)].copy()
        df["var_name"] = df["Indicator"].map(DHS_INDICATOR_MAP)
        df["Value_num"] = pd.to_numeric(df["Value"], errors="coerce")
        frames.append(df[["Location", "var_name", "Value_num"]])

    long = pd.concat(frames, ignore_index=True)
    long = long.drop_duplicates(subset=["Location", "var_name"], keep="last")
    wide = long.pivot(index="Location", columns="var_name", values="Value_num").reset_index()
    wide.columns.name = None
    if "no_postnatal_checkup" in wide.columns:
        wide["pnc_coverage"] = 100.0 - wide["no_postnatal_checkup"]
    wide["region"] = wide["Location"].map(DHS_TO_MS16)
    wide = wide.drop(columns=["Location"])
    print(f"  DHS: {len(wide)} regions | cols={sorted(wide.columns.tolist())}")
    return wide


def load_master_sheet():
    ms = pd.read_excel(MASTER_SHEET, dtype=str)
    mmda_col = next((c for c in ms.columns if "MMDA" in str(c) or "Metropolitan" in str(c)), ms.columns[0])
    ms = ms.rename(columns={mmda_col: "district_ms"})
    ms["district_ms"] = ms["district_ms"].astype(str).str.strip()

    # COMP-007: Master Sheet has 2 raw typos that break the GeoJSON crosswalk join
    # (MANUAL_CORRECTIONS targets the corrected spellings below). Fix at source.
    MS_NAME_FIXES = {
        "Cape Cape Metropolitan Area (CCMA)-Cape Coast South & Cape Coast North":
            "Cape Coast Metropolitan Area (CCMA)-Cape Coast South & Cape Coast North",
        "Sekondi Takoradi Metropolitan Area (STMA)- Takoradi, Sekondi & Essikado-Ketan":
            "Sekondi Takoradi Metropolitan Area (STMA)-Takoradi, Sekondi & Essikado-Ketan",
    }
    ms["district_ms"] = ms["district_ms"].replace(MS_NAME_FIXES)

    region_col = next((c for c in ms.columns if str(c).strip().lower() == "region"), None)
    if region_col:
        ms = ms.rename(columns={region_col: "region"})
        ms["region"] = ms["region"].astype(str).str.strip()

    def get_num(df, *keys):
        for k in keys:
            for c in df.columns:
                if k.lower() in str(c).lower():
                    return pd.to_numeric(df[c], errors="coerce")
        return pd.Series(np.nan, index=df.index)

    ms["latitude"]         = get_num(ms, "latitude", "lat")
    ms["longitude"]        = get_num(ms, "longitude", "lon", "long")
    ms["total_population"] = get_num(ms, "total population", "totalpop")
    ms["poverty_rate"]     = get_num(ms, "incidence of poverty", "poverty rate")
    ms["intensity_poverty"]= get_num(ms, "intensity of poverty")

    uninsured  = get_num(ms, "uninsured population", "uninsured")
    illiterate = get_num(ms, "illiterate population", "illiterate")
    female_tot = get_num(ms, "female population 0-14") + \
                 get_num(ms, "female population 15-64") + \
                 get_num(ms, "female population 65")
    male_1564  = get_num(ms, "male population 15-64")
    fem_1564   = get_num(ms, "female population 15-64")

    ms["uninsured_rate"]   = uninsured  / ms["total_population"] * 100
    ms["illiteracy_rate"]  = illiterate / ms["total_population"] * 100
    ms["female_pop_prop"]  = female_tot / ms["total_population"] * 100
    ms["working_age_prop"] = (male_1564 + fem_1564) / ms["total_population"] * 100

    print(f"  Master Sheet: {len(ms)} districts | working_age missing={ms['working_age_prop'].isna().sum()}")
    return ms


def load_geojson():
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        gj = json.load(f)
    rows = [{"district_geojson": str(feat["properties"].get("DISTRICT","")).strip(),
             "region_geojson":   str(feat["properties"].get("REGION","")).strip()}
            for feat in gj["features"]]
    gdf = pd.DataFrame(rows)
    print(f"  GeoJSON: {len(gdf)} polygons")
    return gdf


def build_district_crosswalk(ms_df, geojson_df):
    ms_upper = {n.upper().strip(): n for n in ms_df["district_ms"].tolist()}
    rows, unmatched = [], []
    for geo_d in geojson_df["district_geojson"].unique():
        key = geo_d.upper().strip()
        key_clean = " ".join(key.split())
        if key in MANUAL_CORRECTIONS:
            ms_m, meth = MANUAL_CORRECTIONS[key], "manual"
        elif key in ms_upper:
            ms_m, meth = ms_upper[key], "title_case"
        elif key_clean in ms_upper:
            ms_m, meth = ms_upper[key_clean], "cleaned"
        else:
            ms_m, meth = None, "unmatched"
            unmatched.append(geo_d)
        rows.append({"district_geojson": geo_d, "district_ms": ms_m, "match_method": meth})
    cw = pd.DataFrame(rows)
    print(f"  Crosswalk: {len(cw)} polygons | unmatched={len(unmatched)}")
    if unmatched:
        print(f"    Unmatched: {unmatched}")
    return cw


def merge_dhs_to_districts(ms_df, dhs_wide):
    merged = ms_df.merge(dhs_wide, on="region", how="left")
    print(f"  Merged: {len(merged)} districts | sba missing={merged['sba'].isna().sum()}")
    return merged


def compute_composite_index(df):
    # Supply-side: DHS regional service-coverage (higher = better; ecological)
    avail = [c for c in COMPOSITE_COLS if c in df.columns]
    # Demand-side: district-level access barriers (higher = worse; inverted)
    avail_inv = [c for c in COMPOSITE_DISTRICT_COLS if c in df.columns]

    normed = pd.DataFrame(index=df.index)
    for col in avail:
        cmin, cmax = df[col].min(), df[col].max()
        normed[col] = (df[col] - cmin) / (cmax - cmin) if cmax > cmin else 0.5
    for col in avail_inv:
        cmin, cmax = df[col].min(), df[col].max()
        normed[col] = 1 - ((df[col] - cmin) / (cmax - cmin)) if cmax > cmin else 0.5

    all_cols = avail + avail_inv
    df["composite_maternal_index"] = normed[all_cols].mean(axis=1) * 100

    # PCA sensitivity (across all 7 blended components -- COMP-006)
    try:
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler
        X = normed[all_cols].dropna()
        if len(X) >= 4:
            Xs = StandardScaler().fit_transform(X)
            pc1 = PCA(n_components=1, random_state=42).fit_transform(Xs).flatten()
            # Sign-align PC1 with composite_maternal_index (higher = better)
            corr = np.corrcoef(pc1, df.loc[X.index, "composite_maternal_index"])[0, 1]
            if corr < 0:
                pc1 = -pc1
            df.loc[X.index, "composite_pca"] = (pc1 - pc1.min()) / (pc1.max() - pc1.min()) * 100
        else:
            df["composite_pca"] = np.nan
    except ImportError:
        df["composite_pca"] = np.nan

    ci = df["composite_maternal_index"]
    print(f"  Composite [COMP-006]: components={all_cols}")
    print(f"  Composite: mean={ci.mean():.1f} SD={ci.std():.1f} range=[{ci.min():.1f},{ci.max():.1f}] unique={ci.nunique()}")
    return df


def derive_risk_label(df):
    p33 = df["composite_maternal_index"].quantile(0.333)
    p67 = df["composite_maternal_index"].quantile(0.667)
    df["risk_label"] = df["composite_maternal_index"].apply(
        lambda x: "HIGH" if x <= p33 else ("MODERATE" if x <= p67 else "LOW")
    )
    print(f"  Risk labels: {df['risk_label'].value_counts().to_dict()} | p33={p33:.1f} p67={p67:.1f}")
    return df


def detect_outliers(df, cols):
    rows = []
    for col in cols:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) < 4:
            continue
        Q1, Q3 = s.quantile(0.25), s.quantile(0.75)
        IQR = Q3 - Q1
        iqr_n = int(((s < Q1 - 1.5*IQR) | (s > Q3 + 1.5*IQR)).sum())
        z_n   = int((np.abs(stats.zscore(s)) > 3).sum())
        rows.append({"variable": col, "iqr_outlier_n": iqr_n, "zscore_outlier_n": z_n,
                     "note": "review" if iqr_n > 0 else "ok"})
    return pd.DataFrame(rows)


def build_table1(df):
    rows = []
    for var in KEY_VARS:
        if var not in df.columns:
            continue
        s = pd.to_numeric(df[var], errors="coerce").dropna()
        n = len(s)
        if n < 3:
            rows.append({"variable": var, "statistic": "insufficient data", "n_valid": n, "note": ""})
            continue
        _, p_sw = stats.shapiro(s) if n <= 5000 else (None, 0.0)
        if p_sw < 0.05:
            stat = f"{s.median():.1f} [{s.quantile(0.25):.1f}-{s.quantile(0.75):.1f}]"
            note = "median [IQR]"
        else:
            stat = f"{s.mean():.1f} ({s.std():.1f})"
            note = "mean (SD)"
        rows.append({"variable": var, "statistic": stat, "n_valid": n, "note": note})
    for lvl in ["HIGH", "MODERATE", "LOW"]:
        if "risk_label" in df.columns:
            n_l = int((df["risk_label"] == lvl).sum())
            rows.append({"variable": f"risk_label: {lvl}", "statistic": f"{n_l} ({n_l/len(df)*100:.1f}%)",
                         "n_valid": n_l, "note": "n (%)"})
    return pd.DataFrame(rows)


# =============================================================================
def main():
    print("=" * 70)
    print("Project 14: Ghana Maternal & Reproductive Health -- Data Cleaning")
    print("=" * 70)

    print("\nStep 1 -- Loading DHS subnational files...")
    dhs_wide = load_dhs_subnational()

    print("\nStep 2 -- Loading Master Sheet (261 districts)...")
    ms_df = load_master_sheet()

    print("\nStep 3 -- Loading GeoJSON...")
    geo_df = load_geojson()

    print("\nStep 4 -- Building district crosswalk...")
    crosswalk = build_district_crosswalk(ms_df, geo_df)

    print("\nStep 5 -- Merging DHS regional values to districts...")
    merged = merge_dhs_to_districts(ms_df, dhs_wide)
    # EX-026/SPAT-006: create unified 'district' column for all downstream scripts
    merged["district"] = merged["district_ms"]

    print("\nStep 6 -- Computing composite index and risk labels...")
    merged = compute_composite_index(merged)
    merged = derive_risk_label(merged)

    print("\nStep 7 -- Detecting outliers...")
    outlier_cols = ["composite_maternal_index","sba","facility_delivery","anc_skilled",
                    "pnc_coverage","tfr","abr","poverty_rate","uninsured_rate"]
    outlier_rpt = detect_outliers(merged, outlier_cols)

    print("\nStep 8 -- Building Table 1...")
    table1 = build_table1(merged)

    # Data source attribution (EX-003)
    merged["data_source_dhs"]     = "Ghana DHS 2022 Subnational"
    merged["data_source_census"]  = "Ghana GSS Census 2021"
    merged["data_source_geojson"] = "Ghana_New_260_District.geojson"

    print("\nStep 9 -- Saving outputs...")
    clean_path = os.path.join(PROC, "maternal_ghana_261districts_clean.csv")
    merged.to_csv(clean_path, index=False)
    print(f"  Clean CSV: {clean_path}  ({len(merged)} rows x {merged.shape[1]} cols)")

    table1.to_csv(os.path.join(OUT_TABLES, "table1_descriptive.csv"), index=False)
    print(f"  Table 1:   {os.path.join(OUT_TABLES, 'table1_descriptive.csv')}")

    crosswalk.to_csv(os.path.join(OUT_DATA, "district_crosswalk.csv"), index=False)
    print(f"  Crosswalk: {os.path.join(OUT_DATA, 'district_crosswalk.csv')}")

    outlier_rpt.to_csv(os.path.join(OUT_DATA, "data_quality_report.csv"), index=False)
    print(f"  DQ report: {os.path.join(OUT_DATA, 'data_quality_report.csv')}")

    print("\n" + "=" * 70)
    print("COMPLETE")
    print(f"  N districts:          {len(merged)}")
    print(f"  N with DHS data:      {merged['sba'].notna().sum()}")
    print(f"  Composite mean (SD):  {merged['composite_maternal_index'].mean():.2f} ({merged['composite_maternal_index'].std():.2f})")
    print(f"  Risk HIGH:            {(merged['risk_label']=='HIGH').sum()}")
    print(f"  Risk MODERATE:        {(merged['risk_label']=='MODERATE').sum()}")
    print(f"  Risk LOW:             {(merged['risk_label']=='LOW').sum()}")
    wa_miss = merged['working_age_prop'].isna().sum()
    print(f"  working_age missing:  {wa_miss}")
    print("=" * 70)
    return merged


if __name__ == "__main__":
    main()
