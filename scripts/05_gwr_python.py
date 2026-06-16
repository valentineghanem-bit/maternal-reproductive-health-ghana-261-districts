"""
Project 14: Ghana Maternal & Reproductive Health — 261 Districts
Script 05: Spatial Regression Analysis (Python — R/GWmodel unavailable in sandbox)
  - Global OLS (numpy + scipy; SE, t-stat, p-value)
  - VIF via auxiliary regressions
  - Residual Moran's I (KDTree KNN k=4 from GeoJSON centroids — exact match with Phase 2)
  - Geographically Weighted Regression (bisquare adaptive kernel, AICc; haversine distance)
    NOTE (post-COMP-006/COMP-008): composite_maternal_index now has 261 unique values
    (4 DHS regional service-coverage components + 3 inverted census district-level
    access-barrier components). Predictors poverty_rate/illiteracy_rate/uninsured_rate are
    EXCLUDED as they are components of the outcome itself. OLS is the primary model;
    GWR local coefficients are retained for spatial heterogeneity inspection only.
Author: Valentine Golden Ghanem
Date: 2026-06-09
Inputs:
  - data/processed/maternal_ghana_261districts_clean.csv
  - data/raw/Ghana_New_260_District.geojson
  - outputs/data/district_crosswalk.csv
Outputs:
  - outputs/data/global_ols_results.csv
  - outputs/data/ols_vif.csv
  - outputs/data/morans_i_r_verification.csv
  - outputs/data/gwr_local_r2.csv
  - outputs/data/gwr_local_coefficients.csv
  - outputs/data/spatial_regression_comparison.csv
# END
"""

import os, sys, json, warnings
import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial import KDTree

warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
PROC = os.path.join(ROOT, "data", "processed")
RAW  = os.path.join(ROOT, "data", "raw")
OUT  = os.path.join(ROOT, "outputs", "data")
os.makedirs(OUT, exist_ok=True)

OUTCOME_COL = "composite_maternal_index"
# poverty_rate, illiteracy_rate, uninsured_rate EXCLUDED post-COMP-006/COMP-008:
# these 3 vars are now components of composite_maternal_index itself —
# including them as predictors of the composite would be circular/leakage.
PREDICTOR_COLS = [
    "working_age_prop", "female_pop_prop",
    "women_edu_secondary", "women_literacy", "no_insurance_women", "women_anemia",
    "wife_beating_justified", "decision_autonomy", "ipv_12months",
]


# =============================================================================
# SPATIAL WEIGHT MATRIX — Phase 2 exact replication
# KDTree Euclidean KNN k=4 on GeoJSON polygon centroids (EX-008)
# =============================================================================

def load_geojson_centroids(geojson_path, crosswalk_path):
    """
    Extract polygon centroids from GeoJSON in [lon, lat] order.
    Apply district_crosswalk (ALL CAPS → Master Sheet names).
    Returns dict: ms_district_name -> np.array([lon, lat])
    """
    with open(geojson_path) as f:
        gj = json.load(f)

    cw = pd.read_csv(crosswalk_path)
    geojson_to_ms = dict(zip(cw["district_geojson"].str.strip(),
                             cw["district_ms"].str.strip()))

    centroids = {}
    for feat in gj["features"]:
        props = feat["properties"]
        raw_name = (props.get("DISTRICT", "") or props.get("NAME_2", "") or "").strip()
        ms_name = geojson_to_ms.get(raw_name)
        if ms_name is None:
            continue
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            coords = np.array(geom["coordinates"][0])
            centroids[ms_name] = coords.mean(axis=0)
        elif geom["type"] == "MultiPolygon":
            all_coords = np.vstack([np.array(p[0]) for p in geom["coordinates"]])
            centroids[ms_name] = all_coords.mean(axis=0)
    return centroids


def build_knn_weights(coord_arr, k=4):
    """
    Row-standardised KNN (k=4) via KDTree Euclidean — exact Phase 2 replication.
    coord_arr: (n, 2) array of [lon, lat] coordinates.
    """
    n = len(coord_arr)
    tree = KDTree(coord_arr)
    _, idx = tree.query(coord_arr, k=k + 1)   # first result is self
    W = np.zeros((n, n))
    for i, neighbours in enumerate(idx):
        for j in neighbours[1:]:               # skip self
            W[i, j] = 1.0
    row_sums = W.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return W / row_sums


def global_morans_i_w(x, W, n_perm=999, seed=42):
    """
    Global Moran's I — exact Phase 2 formula.
    Returns (I, E_I, Var_I, z_score, p_value)
    """
    np.random.seed(seed)
    n   = len(x)
    xz  = x - x.mean()
    S0  = W.sum()
    I   = (n / S0) * float(xz @ W @ xz) / float(xz @ xz)
    E_I = -1.0 / (n - 1)

    perm_I = []
    for _ in range(n_perm):
        xp  = np.random.permutation(x)
        zp  = xp - xp.mean()
        perm_I.append((n / S0) * float(zp @ W @ zp) / float(zp @ zp))
    perm_I = np.array(perm_I)
    Var_I  = float(np.var(perm_I))
    z      = (I - E_I) / np.sqrt(Var_I + 1e-12)
    p      = (np.sum(np.abs(perm_I) >= abs(I)) + 1) / (n_perm + 1)
    return float(I), float(E_I), float(Var_I), float(z), float(p)


# =============================================================================
# OLS UTILITIES
# =============================================================================

def ols_with_stats(X_df, y):
    """Global OLS — returns coefficient table + residuals."""
    Xa  = np.column_stack([np.ones(len(y)), X_df.values])
    n, p = Xa.shape
    beta, _, _, _ = np.linalg.lstsq(Xa, y, rcond=None)
    y_hat  = Xa @ beta
    resid  = y - y_hat
    rss    = float(resid @ resid)
    sigma2 = rss / (n - p)
    XtX_inv = np.linalg.pinv(Xa.T @ Xa)
    se       = np.sqrt(sigma2 * np.diag(XtX_inv))
    t_stat   = beta / (se + 1e-12)
    p_val    = 2 * stats.t.sf(np.abs(t_stat), df=n - p)
    ss_tot   = float(((y - y.mean()) ** 2).sum())
    r2       = 1.0 - rss / ss_tot
    adj_r2   = 1.0 - (1.0 - r2) * (n - 1) / (n - p)
    labels   = ["(Intercept)"] + list(X_df.columns)
    return pd.DataFrame({
        "variable":      labels,
        "Estimate":      beta,
        "Std. Error":    se,
        "t value":       t_stat,
        "Pr(>|t|)":      p_val,
        "r_squared":     r2,
        "adj_r_squared": adj_r2,
    }), resid


def compute_vif(X_df):
    """VIF via auxiliary regressions: VIF_j = 1 / (1 - R²_j)."""
    cols = list(X_df.columns)
    rows = []
    for col in cols:
        X_o  = np.column_stack([np.ones(len(X_df)),
                                 X_df[[c for c in cols if c != col]].values])
        y_j  = X_df[col].values
        b, _, _, _ = np.linalg.lstsq(X_o, y_j, rcond=None)
        res  = y_j - X_o @ b
        r2_j = max(0.0, 1.0 - float(res @ res) / (float(((y_j - y_j.mean()) ** 2).sum()) + 1e-12))
        rows.append({"variable": col, "VIF": round(1.0 / (1.0 - r2_j + 1e-12), 3)})
    return pd.DataFrame(rows)


# =============================================================================
# GWR UTILITIES — haversine distances for kernel
# =============================================================================

def haversine_matrix(lat, lon):
    """N×N Haversine distance matrix in km."""
    R  = 6371.0
    lr  = np.radians(lat);  lor = np.radians(lon)
    dlat = lr[:, None] - lr[None, :]
    dlon = lor[:, None] - lor[None, :]
    a = (np.sin(dlat / 2) ** 2 +
         np.cos(lr[:, None]) * np.cos(lr[None, :]) * np.sin(dlon / 2) ** 2)
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def bisquare_weights(d_row, bw_n):
    """Adaptive bisquare kernel. bw_n = number of nearest neighbours."""
    sorted_d = np.sort(d_row)
    h  = sorted_d[min(bw_n, len(sorted_d) - 1)]
    u  = d_row / (h + 1e-12)
    w  = np.where(u < 1.0, (1.0 - u ** 2) ** 2, 0.0)
    w[np.argmin(d_row)] = 1.0     # focal point always gets full weight
    return w


def local_wls(X, y, w):
    """WLS at one focal point. Returns (beta, local_r2_weighted, h_ii)."""
    sw   = np.sqrt(w)
    Xw   = X * sw[:, None];  yw = y * sw
    XtX  = Xw.T @ Xw
    try:
        XtX_inv = np.linalg.inv(XtX + 1e-8 * np.eye(XtX.shape[0]))
    except np.linalg.LinAlgError:
        XtX_inv = np.linalg.pinv(XtX)
    beta    = XtX_inv @ Xw.T @ yw
    y_hat   = X @ beta
    y_bar_w = np.average(y, weights=w + 1e-12)
    ss_tot  = float(np.sum(w * (y - y_bar_w) ** 2))
    ss_res  = float(np.sum(w * (y - y_hat) ** 2))
    lr2     = max(0.0, 1.0 - ss_res / (ss_tot + 1e-12))
    focal   = int(np.argmax(w))
    h_ii    = float(X[focal] @ XtX_inv @ X[focal])
    return beta, lr2, h_ii


def gwr_aicc_score(X, y, D, bw_n):
    """AICc + OOF predictions for one bandwidth candidate."""
    n   = len(y)
    yh  = np.zeros(n);  tr_H = 0.0
    for i in range(n):
        w       = bisquare_weights(D[i], bw_n)
        beta, _, h_ii = local_wls(X, y, w)
        yh[i]   = X[i] @ beta
        tr_H   += h_ii
    rss    = float(np.sum((y - yh) ** 2))
    sigma2 = rss / n
    denom  = max(n - 2.0 - tr_H, 1.0)
    aicc   = (2.0 * n * np.log(np.sqrt(sigma2 + 1e-12)) +
              n * np.log(2.0 * np.pi) +
              n * (n + tr_H) / denom)
    return aicc, yh, tr_H


def run_gwr(X, y, lat, lon):
    """Full GWR pipeline with AICc bandwidth selection."""
    n   = len(y)
    D   = haversine_matrix(lat, lon)
    candidates = list(range(20, min(141, n - 5), 15))
    print(f"  AICc bandwidth search over {len(candidates)} values: {candidates}")

    best_bw, best_aicc = None, np.inf
    for bw in candidates:
        aicc, _, tr_H = gwr_aicc_score(X, y, D, bw)
        print(f"    bw={bw:3d}  AICc={aicc:10.3f}  tr(H)={tr_H:.2f}")
        if aicc < best_aicc:
            best_aicc, best_bw = aicc, bw

    print(f"  -> Optimal bandwidth: {best_bw} nearest neighbours  (AICc={best_aicc:.3f})")
    p = X.shape[1]
    local_coeffs = np.zeros((n, p))
    local_r2     = np.zeros(n)
    y_hat_final  = np.zeros(n)
    for i in range(n):
        w = bisquare_weights(D[i], best_bw)
        beta, lr2, _ = local_wls(X, y, w)
        local_coeffs[i] = beta
        local_r2[i]     = lr2
        y_hat_final[i]  = X[i] @ beta

    ss_tot    = float(np.sum((y - y.mean()) ** 2))
    ss_res    = float(np.sum((y - y_hat_final) ** 2))
    global_r2 = max(0.0, 1.0 - ss_res / (ss_tot + 1e-12))
    return local_coeffs, local_r2, best_bw, best_aicc, global_r2


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=== Project 14: Spatial Regression Analysis (Python fallback) ===\n")

    csv_path = os.path.join(PROC, "maternal_ghana_261districts_clean.csv")
    if not os.path.exists(csv_path):
        print("[ERROR] Run 01_data_cleaning.py first."); sys.exit(1)

    df = pd.read_csv(csv_path)
    print(f"  Loaded: {df.shape[0]} districts x {df.shape[1]} columns")

    avail_preds = [c for c in PREDICTOR_COLS
                   if c in df.columns and df[c].notna().any()]
    mask  = df[[OUTCOME_COL] + avail_preds + ["latitude", "longitude"]].notna().all(axis=1)
    df_m  = df[mask].copy().reset_index(drop=True)
    print(f"  Complete-case rows: {len(df_m)}")

    y     = df_m[OUTCOME_COL].values.astype(float)
    X_raw = df_m[avail_preds].copy()
    # Standardise predictors for OLS + GWR stability
    X_std = (X_raw - X_raw.mean()) / (X_raw.std() + 1e-12)
    lat   = df_m["latitude"].values
    lon   = df_m["longitude"].values

    # ── Build Phase 2 KNN weights from GeoJSON centroids ─────────────────────
    geojson_path   = os.path.join(RAW, "Ghana_New_260_District.geojson")
    crosswalk_path = os.path.join(OUT, "district_crosswalk.csv")
    W_knn = None
    if os.path.exists(geojson_path) and os.path.exists(crosswalk_path):
        print("\n  Building KNN k=4 weights (GeoJSON centroids, KDTree Euclidean — Phase 2 method)...")
        centroids = load_geojson_centroids(geojson_path, crosswalk_path)
        coord_arr = np.array([centroids.get(d, [0.0, 0.0])
                              for d in df_m["district"].values])
        W_knn = build_knn_weights(coord_arr, k=4)
        print(f"  KNN weights built: {W_knn.shape[0]} x {W_knn.shape[1]}")
    else:
        print("  [WARNING] GeoJSON or crosswalk not found; Moran's I verification will be skipped.")

    # ── STEP 1: Global OLS ────────────────────────────────────────────────────
    print("\n[STEP 1] Global OLS...")
    ols_tbl, ols_resid = ols_with_stats(X_std, y)
    ols_tbl.to_csv(os.path.join(OUT, "global_ols_results.csv"), index=False)
    r2     = ols_tbl["r_squared"].iloc[0]
    adj_r2 = ols_tbl["adj_r_squared"].iloc[0]
    print(f"  Global OLS  R^2={r2:.4f}  Adj-R^2={adj_r2:.4f}")
    print("  [Saved] global_ols_results.csv")

    # ── STEP 2: VIF ───────────────────────────────────────────────────────────
    print("\n[STEP 2] VIF check...")
    vif_df = compute_vif(X_std)
    vif_df.to_csv(os.path.join(OUT, "ols_vif.csv"), index=False)
    high = vif_df[vif_df["VIF"] > 5]
    if len(high):
        print(f"  WARNING High VIF (>5): {', '.join(high['variable'].tolist())}")
    else:
        print("  VIF: all predictors < 5")
    print("  [Saved] ols_vif.csv")

    # ── STEP 3: Moran's I verification + residual Moran's I ──────────────────
    print("\n[STEP 3] Moran's I verification (Phase 2 method) + residual Moran's I...")
    morans_rows = []

    # Load Phase 2 canonical outcome Moran's I
    ph2_mi_path = os.path.join(OUT, "morans_i_results.csv")
    if os.path.exists(ph2_mi_path):
        ph2 = pd.read_csv(ph2_mi_path).iloc[0]
        print(f"  Phase 2 canonical: I={ph2['morans_I']:.4f}  z={ph2['z_score']:.4f}  p={ph2['p_value']:.4f}")
        morans_rows.append({
            "variable":    OUTCOME_COL,
            "morans_I":    round(float(ph2["morans_I"]), 4),
            "E_I":         round(float(ph2.get("E_I", -0.004)), 4),
            "z_score":     round(float(ph2["z_score"]), 4),
            "p_value":     round(float(ph2["p_value"]), 4),
            "weight_type": "KNN_k4_KDTree_Euclidean",
            "note":        "Phase 2 canonical value (GeoJSON polygon centroids)",
        })

    # Residual Moran's I using same W
    if W_knn is not None:
        I_r, E_r, V_r, z_r, p_r = global_morans_i_w(ols_resid, W_knn, n_perm=999)
        print(f"  Residual Moran's I = {I_r:.4f}  z = {z_r:.4f}  p = {p_r:.4f}")
        if p_r < 0.05:
            print("  WARNING Significant residual autocorrelation -> spatial model required (STAT-003)")
        morans_rows.append({
            "variable":    f"{OUTCOME_COL}_OLS_residuals",
            "morans_I":    round(I_r, 4),
            "E_I":         round(E_r, 4),
            "z_score":     round(z_r, 4),
            "p_value":     round(p_r, 4),
            "weight_type": "KNN_k4_KDTree_Euclidean",
            "note":        "Residual autocorrelation post-OLS (STAT-003)",
        })
    else:
        I_r, z_r, p_r = None, None, None
        print("  [SKIP] Residual Moran's I — W not available")

    if morans_rows:
        pd.DataFrame(morans_rows).to_csv(os.path.join(OUT, "morans_i_r_verification.csv"), index=False)
        print("  [Saved] morans_i_r_verification.csv")

    # ── STEP 4: GWR ───────────────────────────────────────────────────────────
    print("\n[STEP 4] Geographically Weighted Regression (bisquare adaptive, AICc)...")
    print("  NOTE (post-COMP-006/008): composite has 261 unique values; index-component")
    print("        predictors (poverty/illiteracy/uninsured) excluded to avoid leakage.")
    print("        OLS is the primary regression model; GWR documents spatial heterogeneity.")

    X_gwr = np.column_stack([np.ones(len(y)), X_std.values])
    col_names_gwr = ["intercept"] + avail_preds
    local_coeffs, local_r2, best_bw, best_aicc, gwr_global_r2 = run_gwr(X_gwr, y, lat, lon)

    print(f"  GWR global R^2 = {gwr_global_r2:.4f}")
    print(f"  Local R^2: mean={local_r2.mean():.4f}  min={local_r2.min():.4f}  max={local_r2.max():.4f}")
    n_unique_y = len(np.unique(np.round(y, 4)))
    print(f"  Unique outcome values: {n_unique_y} (expected 261 post-COMP-006)")

    lr2_df = pd.DataFrame({
        "district": df_m["district"].values,
        "region":   df_m["region"].values,
        "Local_R2": local_r2,
        "latitude": lat,
        "longitude": lon,
    })
    lr2_df.to_csv(os.path.join(OUT, "gwr_local_r2.csv"), index=False)
    print("  [Saved] gwr_local_r2.csv")

    coef_df = pd.DataFrame(local_coeffs, columns=col_names_gwr)
    coef_df.insert(0, "district", df_m["district"].values)
    coef_df.insert(1, "region",   df_m["region"].values)
    coef_df["Local_R2"]  = local_r2
    coef_df["latitude"]  = lat
    coef_df["longitude"] = lon
    coef_df.to_csv(os.path.join(OUT, "gwr_local_coefficients.csv"), index=False)
    print("  [Saved] gwr_local_coefficients.csv")

    # ── Comparison table ──────────────────────────────────────────────────────
    resid_note = (f"Residual MI={I_r:.4f} p={p_r:.4f} -> spatial model required"
                  if I_r is not None else "Residual MI: W unavailable")
    gwr_note   = (f"Local R^2 mean={local_r2.mean():.4f}; index-component predictors excluded"
                  f" (post-COMP-008); bw={best_bw} neighbours")
    comp = pd.DataFrame([{
        "model":         "Global OLS",
        "r_squared":     round(r2, 4),
        "adj_r_squared": round(adj_r2, 4),
        "bandwidth":     None,
        "AICc":          None,
        "note":          resid_note,
    }, {
        "model":         "GWR (bisquare adaptive, Python)",
        "r_squared":     round(gwr_global_r2, 4),
        "adj_r_squared": None,
        "bandwidth":     best_bw,
        "AICc":          round(best_aicc, 3),
        "note":          gwr_note,
    }])
    comp.to_csv(os.path.join(OUT, "spatial_regression_comparison.csv"), index=False)
    print("  [Saved] spatial_regression_comparison.csv")

    print("\n=== Spatial regression complete. ===")


if __name__ == "__main__":
    main()
    # END
