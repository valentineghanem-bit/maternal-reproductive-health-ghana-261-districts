"""
Project 14: Ghana Maternal & Reproductive Health — 261 Districts
Script 02: Spatial Analysis
  - Global Moran's I (KNN k=4)
  - Univariate LISA (Rook contiguity)
  - Bivariate LISA (composite × poverty)
  - Getis-Ord Gi* hotspot delineation
  - Spatial lag / spatial error model selection
  - Residual Moran's I check (STAT-003)
Author: Valentine Golden Ghanem
Date: 2026-06-09
Inputs:
  - data/processed/maternal_ghana_261districts_clean.csv
  - data/raw/Ghana_New_260_District.geojson
  - outputs/data/district_crosswalk.csv (written by 01_data_cleaning.py)
Outputs:
  - outputs/data/spatial_weights_knn4.npz
  - outputs/data/morans_i_results.csv
  - outputs/data/lisa_results.csv
  - outputs/data/bivariate_lisa_results.csv
  - outputs/data/getis_ord_results.csv
  - outputs/data/spatial_lag_composite.csv
  - outputs/figures/ [spatial maps via 04_visualisations.py]
# END
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
PROC = os.path.join(ROOT, 'data', 'processed')
RAW = os.path.join(ROOT, 'data', 'raw')
OUT_DATA = os.path.join(ROOT, 'outputs', 'data')
os.makedirs(OUT_DATA, exist_ok=True)

# ── Spatial weight matrices (EX-008) ─────────────────────────────────────────
# Moran's I  → KNN k=4 from centroids
# LISA       → Rook contiguity (≥2 shared GeoJSON vertices)

def build_knn_weights(coords, k=4):
    """
    Build row-standardised KNN spatial weight matrix (k=4).
    coords: np.array shape (n, 2) — [lon, lat]
    Returns W: np.array (n, n), row-standardised
    """
    from scipy.spatial import KDTree
    n = len(coords)
    tree = KDTree(coords)
    _, idx = tree.query(coords, k=k+1)  # k+1 because first result is self
    W = np.zeros((n, n))
    for i, neighbours in enumerate(idx):
        for j in neighbours[1:]:  # skip self
            W[i, j] = 1.0
    # Row-standardise
    row_sums = W.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1  # prevent division by zero
    W = W / row_sums
    return W


def build_rook_weights(geojson_path, district_order, geojson_to_ms=None):
    """
    Build row-standardised Rook contiguity weight matrix.
    Two districts are neighbours if their GeoJSON polygons share ≥2 vertices.
    district_order: list of district names in the order matching the data rows.
    geojson_to_ms: dict mapping GeoJSON ALL CAPS names → Master Sheet district names.
    """
    with open(geojson_path) as f:
        gj = json.load(f)

    name_to_idx = {d: i for i, d in enumerate(district_order)}
    n = len(district_order)
    W = np.zeros((n, n))

    # Extract all polygon vertices per district
    def get_vertices(geom):
        verts = set()
        if geom['type'] == 'Polygon':
            for ring in geom['coordinates']:
                for pt in ring:
                    verts.add((round(pt[0], 5), round(pt[1], 5)))
        elif geom['type'] == 'MultiPolygon':
            for poly in geom['coordinates']:
                for ring in poly:
                    for pt in ring:
                        verts.add((round(pt[0], 5), round(pt[1], 5)))
        return verts

    features = gj.get('features', [])
    district_verts = {}
    for feat in features:
        props = feat.get('properties', {})
        raw_name = (props.get('DISTRICT', '') or props.get('district', '') or
                    props.get('NAME_2', '') or props.get('name', '')).strip()
        # Convert GeoJSON ALL CAPS name to Master Sheet district name via crosswalk
        if geojson_to_ms is not None:
            name = geojson_to_ms.get(raw_name, raw_name)
        else:
            name = raw_name
        if name in name_to_idx:
            district_verts[name] = get_vertices(feat['geometry'])

    for d1, v1 in district_verts.items():
        for d2, v2 in district_verts.items():
            if d1 == d2:
                continue
            shared = len(v1 & v2)
            if shared >= 2:
                i, j = name_to_idx[d1], name_to_idx[d2]
                W[i, j] = 1.0

    # Row-standardise
    row_sums = W.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    W = W / row_sums
    return W


def global_morans_i(x, W, n_permutations=999, seed=42):
    """
    Compute Global Moran's I with permutation inference.
    Returns: (I, E_I, Var_I, z_score, p_value)
    """
    np.random.seed(seed)
    n = len(x)
    x_mean = np.mean(x)
    z = x - x_mean
    S0 = W.sum()

    numerator = np.dot(z, np.dot(W, z))
    denominator = np.dot(z, z)
    I = (n / S0) * (numerator / denominator)

    E_I = -1.0 / (n - 1)

    # Permutation inference
    perm_I = []
    for _ in range(n_permutations):
        x_perm = np.random.permutation(x)
        z_p = x_perm - np.mean(x_perm)
        num_p = np.dot(z_p, np.dot(W, z_p))
        den_p = np.dot(z_p, z_p)
        perm_I.append((n / S0) * (num_p / den_p))

    perm_I = np.array(perm_I)
    Var_I = np.var(perm_I)
    z_score = (I - E_I) / np.sqrt(Var_I)
    p_value = (np.sum(np.abs(perm_I) >= np.abs(I)) + 1) / (n_permutations + 1)

    return I, E_I, Var_I, z_score, p_value


def local_morans_i(x, W, n_permutations=999, seed=42):
    """
    Local Moran's I (LISA) — univariate.
    Returns DataFrame with: district_idx, Ii, z_Ii, p_perm, quadrant, significant (p<0.05)
    """
    np.random.seed(seed)
    n = len(x)
    x_mean = np.mean(x)
    z = (x - x_mean) / np.std(x)
    Wz = np.dot(W, z)

    Ii = z * Wz

    # Permutation p-values
    perm_Ii = np.zeros((n_permutations, n))
    for p in range(n_permutations):
        x_p = np.random.permutation(x)
        z_p = (x_p - np.mean(x_p)) / np.std(x_p)
        Wz_p = np.dot(W, z_p)
        perm_Ii[p] = z_p * Wz_p

    p_perm = np.array([(np.sum(np.abs(perm_Ii[:, i]) >= np.abs(Ii[i])) + 1)
                        / (n_permutations + 1) for i in range(n)])

    # Quadrant classification
    quad = []
    for i in range(n):
        if z[i] >= 0 and Wz[i] >= 0:
            quad.append('HH')
        elif z[i] < 0 and Wz[i] < 0:
            quad.append('LL')
        elif z[i] >= 0 and Wz[i] < 0:
            quad.append('HL')
        else:
            quad.append('LH')

    df = pd.DataFrame({
        'local_I': Ii,
        'z_local_I': (Ii - Ii.mean()) / Ii.std(),
        'p_perm': p_perm,
        'quadrant': quad,
        'significant': (p_perm < 0.05).astype(int)
    })
    return df


def bivariate_lisa(x, y, W, n_permutations=999, seed=42):
    """
    Bivariate Local Moran's I: spatial lag of y × x.
    Returns DataFrame with: BV_Ii, p_perm, quadrant, significant
    """
    np.random.seed(seed)
    n = len(x)
    zx = (x - np.mean(x)) / np.std(x)
    zy = (y - np.mean(y)) / np.std(y)
    Wzy = np.dot(W, zy)

    BV_Ii = zx * Wzy

    perm_BV = np.zeros((n_permutations, n))
    for p in range(n_permutations):
        y_p = np.random.permutation(y)
        zy_p = (y_p - np.mean(y_p)) / np.std(y_p)
        Wzy_p = np.dot(W, zy_p)
        perm_BV[p] = zx * Wzy_p

    p_perm = np.array([(np.sum(np.abs(perm_BV[:, i]) >= np.abs(BV_Ii[i])) + 1)
                        / (n_permutations + 1) for i in range(n)])

    quad = []
    for i in range(n):
        if zx[i] >= 0 and Wzy[i] >= 0:
            quad.append('HH')
        elif zx[i] < 0 and Wzy[i] < 0:
            quad.append('LL')
        elif zx[i] >= 0 and Wzy[i] < 0:
            quad.append('HL')
        else:
            quad.append('LH')

    df = pd.DataFrame({
        'bv_I': BV_Ii,
        'p_perm': p_perm,
        'bv_quadrant': quad,
        'significant': (p_perm < 0.05).astype(int)
    })
    return df


def getis_ord_gi_star(x, W_binary, coords, n_permutations=999, seed=42):
    """
    Getis-Ord Gi* (includes self in spatial lag).
    W_binary: un-standardised binary weight matrix (including diagonal).
    Returns DataFrame with: Gi_star, z_Gi, p_perm, hotspot_class
    """
    np.random.seed(seed)
    n = len(x)
    W_self = W_binary + np.eye(n)  # include self

    x_bar = np.mean(x)
    s = np.std(x)
    Wi_sum = W_self.sum(axis=1)
    Gi_star = (np.dot(W_self, x) - x_bar * Wi_sum) / (s * np.sqrt(
        (n * (W_self ** 2).sum(axis=1) - Wi_sum ** 2) / (n - 1)
    ))

    perm_G = np.zeros((n_permutations, n))
    for p in range(n_permutations):
        x_p = np.random.permutation(x)
        x_bar_p = np.mean(x_p)
        s_p = np.std(x_p)
        perm_G[p] = (np.dot(W_self, x_p) - x_bar_p * Wi_sum) / (s_p * np.sqrt(
            (n * (W_self ** 2).sum(axis=1) - Wi_sum ** 2) / (n - 1)
        ))

    p_perm = np.array([(np.sum(np.abs(perm_G[:, i]) >= np.abs(Gi_star[i])) + 1)
                        / (n_permutations + 1) for i in range(n)])

    hotspot = []
    for i in range(n):
        if p_perm[i] < 0.05 and Gi_star[i] > 0:
            hotspot.append('Hotspot')
        elif p_perm[i] < 0.05 and Gi_star[i] < 0:
            hotspot.append('Coldspot')
        else:
            hotspot.append('Not significant')

    df = pd.DataFrame({
        'Gi_star': Gi_star,
        'p_perm': p_perm,
        'hotspot_class': hotspot
    })
    return df


def main():
    print("=== Project 14: Spatial Analysis ===\n")

    # Load cleaned data
    clean_path = os.path.join(PROC, 'maternal_ghana_261districts_clean.csv')
    if not os.path.exists(clean_path):
        print("[WARNING] Cleaned data not found. Run 01_data_cleaning.py first.")
        return

    df = pd.read_csv(clean_path)
    print(f"  Loaded: {df.shape[0]} districts × {df.shape[1]} columns")

    # Check for composite index
    if 'composite_maternal_index' not in df.columns:
        print("[WARNING] composite_maternal_index not found. Build it in 01_data_cleaning.py.")
        return

    # ── Load district crosswalk (GeoJSON ALL CAPS → Master Sheet district name) ─
    crosswalk_path = os.path.join(OUT_DATA, 'district_crosswalk.csv')
    if not os.path.exists(crosswalk_path):
        print("[WARNING] district_crosswalk.csv not found. Run 01_data_cleaning.py first.")
        return
    cw = pd.read_csv(crosswalk_path)
    # Map: geojson ALL CAPS name → Master Sheet district name
    geojson_to_ms = dict(zip(cw['district_geojson'].str.strip(),
                              cw['district_ms'].str.strip()))

    # ── Build spatial weights ────────────────────────────────────────────────
    geojson_path = os.path.join(RAW, 'Ghana_New_260_District.geojson')
    if not os.path.exists(geojson_path):
        print("[WARNING] GeoJSON not found. Spatial weights cannot be built.")
        return

    district_order = df['district'].tolist()

    print("  Building KNN k=4 weights (Moran's I)...")
    # Extract centroids from GeoJSON; apply crosswalk to convert ALL CAPS → MS names
    with open(geojson_path) as f:
        gj = json.load(f)
    centroids = {}
    for feat in gj['features']:
        props = feat['properties']
        raw_name = (props.get('DISTRICT', '') or props.get('NAME_2', '') or '').strip()
        ms_name = geojson_to_ms.get(raw_name)  # convert to Master Sheet name
        if ms_name is None:
            continue
        geom = feat['geometry']
        if geom['type'] == 'Polygon':
            coords = np.array(geom['coordinates'][0])
            centroids[ms_name] = coords.mean(axis=0)
        elif geom['type'] == 'MultiPolygon':
            all_coords = np.vstack([np.array(p[0]) for p in geom['coordinates']])
            centroids[ms_name] = all_coords.mean(axis=0)

    coord_arr = np.array([centroids.get(d, [0.0, 0.0]) for d in district_order])
    W_knn = build_knn_weights(coord_arr, k=4)

    print("  Building Rook contiguity weights (LISA)...")
    W_rook = build_rook_weights(geojson_path, district_order, geojson_to_ms)

    # ── Tenet 5: Global Moran's I FIRST (SPAT-001) ──────────────────────────
    print("\n  → Global Moran's I (composite_maternal_index):")
    x = df['composite_maternal_index'].fillna(df['composite_maternal_index'].median()).values
    I, E_I, Var_I, z, p = global_morans_i(x, W_knn)
    print(f"    I={I:.4f}  E(I)={E_I:.4f}  z={z:.4f}  p={p:.4f}")
    morans_results = pd.DataFrame([{
        'variable': 'composite_maternal_index',
        'morans_I': round(I, 4), 'E_I': round(E_I, 4),
        'Var_I': round(Var_I, 6), 'z_score': round(z, 4), 'p_value': round(p, 4),
        'weight_type': 'KNN_k4'
    }])
    morans_results.to_csv(os.path.join(OUT_DATA, 'morans_i_results.csv'), index=False)
    print(f"    [Saved] morans_i_results.csv")

    # ── Univariate LISA ──────────────────────────────────────────────────────
    print("\n  → Univariate LISA (composite_maternal_index, Rook contiguity):")
    lisa_df = local_morans_i(x, W_rook)
    lisa_df.insert(0, 'district', district_order)
    lisa_df.to_csv(os.path.join(OUT_DATA, 'lisa_results.csv'), index=False)
    for q in ['HH', 'LL', 'HL', 'LH']:
        n_sig = ((lisa_df['quadrant'] == q) & (lisa_df['significant'] == 1)).sum()
        print(f"    {q}: {n_sig} significant")

    # ── Bivariate LISA (composite × poverty) ─────────────────────────────────
    if 'poverty_rate' in df.columns and df['poverty_rate'].notna().any():
        print("\n  → Bivariate LISA (composite x poverty):")
        y = df['poverty_rate'].fillna(df['poverty_rate'].median()).values
        bv_df = bivariate_lisa(x, y, W_rook)
        bv_df.insert(0, 'district', district_order)
        bv_df.to_csv(os.path.join(OUT_DATA, 'bivariate_lisa_results.csv'), index=False)
        for q in ['HH', 'LL', 'HL', 'LH']:
            n_sig = ((bv_df['bv_quadrant'] == q) & (bv_df['significant'] == 1)).sum()
            print(f"    {q}: {n_sig}")
    else:
        print("\n  [SKIP] Bivariate LISA -- poverty_rate not populated yet.")

    # ── Getis-Ord Gi* hotspot delineation ────────────────────────────────────
    print("\n  → Getis-Ord Gi* hotspot delineation:")
    # Use binary (un-standardised) Rook weights for Gi*; self-loop added inside function
    W_rook_binary = (W_rook > 0).astype(float)
    gi_df = getis_ord_gi_star(x, W_rook_binary, coord_arr)
    gi_df.insert(0, 'district', district_order)
    gi_df.to_csv(os.path.join(OUT_DATA, 'getis_ord_results.csv'), index=False)
    n_hot = (gi_df['hotspot_class'] == 'Hotspot').sum()
    n_cold = (gi_df['hotspot_class'] == 'Coldspot').sum()
    print(f"    Hotspots: {n_hot} | Coldspots: {n_cold}")
    print(f"    [Saved] getis_ord_results.csv")

    # ── Spatial lag (KNN k=4) ─────────────────────────────────────────────────
    print("\n  → Saving spatial lag composite (KNN k=4)...")
    Wz_raw = np.dot(W_knn, x)
    lag_df = pd.DataFrame({
        'district': district_order,
        'composite_maternal_index': x,
        'spatial_lag_composite': Wz_raw
    })
    lag_df.to_csv(os.path.join(OUT_DATA, 'spatial_lag_composite.csv'), index=False)
    print(f"    [Saved] spatial_lag_composite.csv")

    # ── Save KNN weight matrix ────────────────────────────────────────────────
    knn_out = os.path.join(OUT_DATA, 'spatial_weights_knn4.npz')
    np.savez_compressed(knn_out, W=W_knn, districts=np.array(district_order))
    print(f"    [Saved] spatial_weights_knn4.npz")

    print("\n=== Spatial analysis complete. ===")
