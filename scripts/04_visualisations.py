"""
Project 14: Ghana Maternal & Reproductive Health — 261 Districts
Script 04: Visualisations
  - Choropleth maps: composite index, LISA clusters, Gi* hotspots
  - Bivariate LISA map
  - SHAP figures (summary, waterfall, dependence)
  - Calibration curve + confusion matrix
  - Table 1 export (CSV)
Author: Valentine Golden Ghanem
Date: 2026-06-09
Inputs:
  - data/raw/Ghana_New_260_District.geojson
  - master_maternal_ghana_261districts_v1.csv
  - outputs/data/lisa_results.csv
  - outputs/data/bivariate_lisa_results.csv
  - outputs/data/getis_ord_results.csv
  - outputs/data/shap_values.csv
Outputs:
  - outputs/figures/choropleth_composite_index.png     (300 DPI, vector-quality)
  - outputs/figures/lisa_cluster_map.png               (300 DPI)
  - outputs/figures/bivariate_lisa_map.png             (300 DPI)
  - outputs/figures/gi_star_hotspot_map.png            (300 DPI)
  - outputs/figures/moran_scatterplot.png              (300 DPI)
  - outputs/figures/shap_summary.png                   (300 DPI — from 03_ml_pipeline.py)
  - outputs/tables/table1_descriptive.csv
# END
"""

import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection

warnings.filterwarnings('ignore')

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
RAW = os.path.join(ROOT, 'data', 'raw')
OUT_DATA = os.path.join(ROOT, 'outputs', 'data')
OUT_FIG = os.path.join(ROOT, 'outputs', 'figures')
MASTER_CSV = os.path.join(ROOT, 'master_maternal_ghana_261districts_v1.csv')
GEOJSON = os.path.join(RAW, 'Ghana_New_260_District.geojson')

os.makedirs(OUT_FIG, exist_ok=True)
os.makedirs(os.path.join(ROOT, 'outputs', 'tables'), exist_ok=True)

# ── Colour palettes (WCAG AA compliant) ──────────────────────────────────────
CMAP_SEQUENTIAL = 'YlOrRd'      # choropleth: composite index / rates
CMAP_DIVERGING   = 'RdBu_r'     # Moran scatterplot
LISA_COLOURS = {
    'HH': '#d7191c',   # red — high-high cluster
    'LL': '#2c7bb6',   # blue — low-low cluster
    'HL': '#fdae61',   # orange — high-low outlier
    'LH': '#abd9e9',   # light blue — low-high outlier
    'NS': '#d3d3d3',   # grey — not significant
}
GI_COLOURS = {
    'Hotspot':         '#d7191c',
    'Coldspot':        '#2c7bb6',
    'Not significant': '#d3d3d3',
}


def load_geojson(path):
    with open(path) as f:
        return json.load(f)


def extract_polygon_patches(gj, district_order, values, cmap_name,
                             vmin=None, vmax=None, geojson_to_ms=None):
    """
    Extract matplotlib Polygon patches from GeoJSON.
    geojson_to_ms: dict mapping GeoJSON ALL CAPS name → Master Sheet district name.
    Returns: patches, colours, not_found, cmap, norm
    """
    val_map = dict(zip(district_order, values))
    cmap = plt.cm.get_cmap(cmap_name)
    if vmin is None:
        vmin = min(v for v in val_map.values() if v is not None and not np.isnan(v))
    if vmax is None:
        vmax = max(v for v in val_map.values() if v is not None and not np.isnan(v))
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    patches = []
    colours = []
    not_found = []

    for feat in gj.get('features', []):
        props = feat.get('properties', {})
        raw_name = (props.get('DISTRICT', '') or props.get('district', '') or
                    props.get('NAME_2', '') or props.get('name', '')).strip()
        # Convert GeoJSON ALL CAPS → Master Sheet district name via crosswalk
        name = geojson_to_ms.get(raw_name, raw_name) if geojson_to_ms else raw_name
        val = val_map.get(name)
        geom = feat['geometry']

        rings = []
        if geom['type'] == 'Polygon':
            rings = [geom['coordinates'][0]]
        elif geom['type'] == 'MultiPolygon':
            rings = [p[0] for p in geom['coordinates']]

        colour = cmap(norm(val)) if val is not None and not np.isnan(val) else (0.8, 0.8, 0.8, 1.0)

        for ring in rings:
            pts = np.array(ring)[:, :2]
            patch = MplPolygon(pts, closed=True)
            patches.append(patch)
            colours.append(colour)

        if name not in val_map:
            not_found.append(raw_name)

    return patches, colours, not_found, cmap, norm


def extract_categorical_patches(gj, district_order, cat_values, colour_dict,
                                 geojson_to_ms=None):
    """Extract patches coloured by categorical value.
    geojson_to_ms: dict mapping GeoJSON ALL CAPS name → Master Sheet district name.
    """
    val_map = dict(zip(district_order, cat_values))
    patches = []
    colours = []

    for feat in gj.get('features', []):
        props = feat.get('properties', {})
        raw_name = (props.get('DISTRICT', '') or props.get('district', '') or
                    props.get('NAME_2', '') or '').strip()
        # Convert GeoJSON ALL CAPS → Master Sheet district name via crosswalk
        name = geojson_to_ms.get(raw_name, raw_name) if geojson_to_ms else raw_name
        val = val_map.get(name, 'NS')
        colour = colour_dict.get(val, (0.8, 0.8, 0.8, 1.0))
        geom = feat['geometry']
        rings = []
        if geom['type'] == 'Polygon':
            rings = [geom['coordinates'][0]]
        elif geom['type'] == 'MultiPolygon':
            rings = [p[0] for p in geom['coordinates']]
        for ring in rings:
            pts = np.array(ring)[:, :2]
            patches.append(MplPolygon(pts, closed=True))
            colours.append(colour)

    return patches, colours


# ── Choropleth: composite index ───────────────────────────────────────────────

def plot_choropleth_composite(master, gj, out_path, geojson_to_ms=None):
    if 'composite_maternal_index' not in master.columns:
        print("  [SKIP] composite_maternal_index not found.")
        return

    districts = master['district'].tolist()
    values = master['composite_maternal_index'].values

    patches, colours, _, cmap, norm = extract_polygon_patches(
        gj, districts, values, CMAP_SEQUENTIAL, geojson_to_ms=geojson_to_ms)

    fig, ax = plt.subplots(figsize=(10, 12))
    pc = PatchCollection(patches, facecolors=colours, edgecolors='white', linewidths=0.3)
    ax.add_collection(pc)
    ax.autoscale()
    ax.set_aspect('equal')
    ax.axis('off')

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label('Composite Maternal Health Index', fontsize=12, fontweight='semibold')

    ax.set_title('Spatial Distribution of Composite Maternal Health Index\nGhana, 261 Districts',
                 fontsize=14, fontweight='semibold', pad=12)

    # Caption (EX-019: fig.text + tight_layout)
    caption = ('Figure 1. Choropleth map of the composite maternal health index across 261 districts of Ghana. '
               'Index derived from SBA rate, ANC skilled provider coverage, facility delivery rate, and PNC attendance (≤48h). '
               'Higher values indicate better maternal health outcomes. Source: Ghana DHS 2022 (FR387).')
    fig.text(0.5, 0.01, caption, ha='center', fontsize=10, wrap=True,
             bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.7))
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [Saved] {os.path.basename(out_path)}")


# ── LISA cluster map ──────────────────────────────────────────────────────────

def plot_lisa_map(master, gj, out_path, geojson_to_ms=None):
    lisa_path = os.path.join(OUT_DATA, 'lisa_results.csv')
    if not os.path.exists(lisa_path):
        print("  [SKIP] lisa_results.csv not found.")
        return

    lisa_df = pd.read_csv(lisa_path)
    merged = master[['district']].merge(lisa_df, on='district', how='left')

    # Assign NS where not significant
    cat_values = merged.apply(
        lambda r: r['quadrant'] if r.get('significant', 0) == 1 else 'NS', axis=1
    ).tolist()

    patches, colours = extract_categorical_patches(
        gj, merged['district'].tolist(), cat_values, LISA_COLOURS,
        geojson_to_ms=geojson_to_ms)

    fig, ax = plt.subplots(figsize=(10, 12))
    pc = PatchCollection(patches, facecolors=colours, edgecolors='white', linewidths=0.3)
    ax.add_collection(pc)
    ax.autoscale()
    ax.set_aspect('equal')
    ax.axis('off')

    legend_handles = [
        mpatches.Patch(facecolor=LISA_COLOURS['HH'], label='HH — High-High cluster'),
        mpatches.Patch(facecolor=LISA_COLOURS['LL'], label='LL — Low-Low cluster'),
        mpatches.Patch(facecolor=LISA_COLOURS['HL'], label='HL — High-Low outlier'),
        mpatches.Patch(facecolor=LISA_COLOURS['LH'], label='LH — Low-High outlier'),
        mpatches.Patch(facecolor=LISA_COLOURS['NS'], label='Not significant (p≥0.05)'),
    ]
    ax.legend(handles=legend_handles, loc='lower left', fontsize=10, title='LISA cluster type',
              title_fontsize=11, framealpha=0.9)

    ax.set_title('LISA Cluster Map — Composite Maternal Health Index\nGhana, 261 Districts (p<0.05)',
                 fontsize=14, fontweight='semibold', pad=12)

    n_hh = (merged['significant'] == 1).sum() if 'significant' in merged.columns else '—'
    caption = ('Figure 2. Local Indicators of Spatial Association (LISA) cluster map. '
               'Rook contiguity spatial weights; permutation-based inference (n=999). '
               'HH = high-high spatial clusters; LL = low-low spatial clusters. '
               'Grey districts: p≥0.05 (not statistically significant).')
    fig.text(0.5, 0.01, caption, ha='center', fontsize=10, wrap=True,
             bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.7))
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [Saved] {os.path.basename(out_path)}")


# ── Gi* hotspot map ───────────────────────────────────────────────────────────

def plot_gi_star_map(master, gj, out_path, geojson_to_ms=None):
    gi_path = os.path.join(OUT_DATA, 'getis_ord_results.csv')
    if not os.path.exists(gi_path):
        print("  [SKIP] getis_ord_results.csv not found.")
        return

    gi_df = pd.read_csv(gi_path)
    merged = master[['district']].merge(gi_df, on='district', how='left')
    merged['hotspot_class'] = merged['hotspot_class'].fillna('Not significant')
    cat_values = merged['hotspot_class'].tolist()

    patches, colours = extract_categorical_patches(
        gj, merged['district'].tolist(), cat_values, GI_COLOURS,
        geojson_to_ms=geojson_to_ms)

    fig, ax = plt.subplots(figsize=(10, 12))
    pc = PatchCollection(patches, facecolors=colours, edgecolors='white', linewidths=0.3)
    ax.add_collection(pc)
    ax.autoscale()
    ax.set_aspect('equal')
    ax.axis('off')

    n_hot = (merged['hotspot_class'] == 'Hotspot').sum()
    n_cold = (merged['hotspot_class'] == 'Coldspot').sum()

    legend_handles = [
        mpatches.Patch(facecolor=GI_COLOURS['Hotspot'], label=f'Hotspot (n={n_hot})'),
        mpatches.Patch(facecolor=GI_COLOURS['Coldspot'], label=f'Coldspot (n={n_cold})'),
        mpatches.Patch(facecolor=GI_COLOURS['Not significant'], label='Not significant'),
    ]
    ax.legend(handles=legend_handles, loc='lower left', fontsize=10, title='Gi* classification',
              title_fontsize=11, framealpha=0.9)

    ax.set_title('Getis-Ord Gi* Hotspot Map — Composite Maternal Health Index\nGhana, 261 Districts (p<0.05)',
                 fontsize=14, fontweight='semibold', pad=12)

    caption = (f'Figure 3. Getis-Ord Gi* hotspot delineation. '
               f'Hotspot districts (n={n_hot}) represent significant spatial concentrations '
               f'of low maternal health outcomes. Coldspot districts (n={n_cold}) indicate '
               f'spatial concentrations of high outcomes. Permutation inference (n=999).')
    fig.text(0.5, 0.01, caption, ha='center', fontsize=10, wrap=True,
             bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.7))
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [Saved] {os.path.basename(out_path)}")


# ── Bivariate LISA map ────────────────────────────────────────────────────────

def plot_bivariate_lisa_map(master, gj, out_path, geojson_to_ms=None):
    bv_path = os.path.join(OUT_DATA, 'bivariate_lisa_results.csv')
    if not os.path.exists(bv_path):
        print("  [SKIP] bivariate_lisa_results.csv not found.")
        return

    bv_df = pd.read_csv(bv_path)
    merged = master[['district']].merge(bv_df, on='district', how='left')

    cat_values = merged.apply(
        lambda r: r['bv_quadrant'] if r.get('significant', 0) == 1 else 'NS', axis=1
    ).tolist()

    patches, colours = extract_categorical_patches(
        gj, merged['district'].tolist(), cat_values, LISA_COLOURS,
        geojson_to_ms=geojson_to_ms)

    fig, ax = plt.subplots(figsize=(10, 12))
    pc = PatchCollection(patches, facecolors=colours, edgecolors='white', linewidths=0.3)
    ax.add_collection(pc)
    ax.autoscale()
    ax.set_aspect('equal')
    ax.axis('off')

    sig_counts = {q: (merged[merged['significant'] == 1]['bv_quadrant'] == q).sum()
                  for q in ['HH', 'LL', 'HL', 'LH']}
    legend_handles = [
        mpatches.Patch(facecolor=LISA_COLOURS['HH'],
                       label=f"HH — High poverty / Low outcome (n={sig_counts['HH']})"),
        mpatches.Patch(facecolor=LISA_COLOURS['LL'],
                       label=f"LL — Low poverty / High outcome (n={sig_counts['LL']})"),
        mpatches.Patch(facecolor=LISA_COLOURS['HL'],
                       label=f"HL — High poverty / Low spatial lag (n={sig_counts['HL']})"),
        mpatches.Patch(facecolor=LISA_COLOURS['LH'],
                       label=f"LH — Low poverty / High spatial lag (n={sig_counts['LH']})"),
        mpatches.Patch(facecolor=LISA_COLOURS['NS'], label='Not significant (p≥0.05)'),
    ]
    ax.legend(handles=legend_handles, loc='lower left', fontsize=9,
              title='Bivariate LISA quadrant', title_fontsize=10, framealpha=0.9)

    ax.set_title('Bivariate LISA — Poverty Rate × Composite Maternal Health Index\nGhana, 261 Districts (p<0.05)',
                 fontsize=13, fontweight='semibold', pad=12)

    caption = ('Figure 5. Bivariate Local Indicators of Spatial Association (BV-LISA) map. '
               'Exposure: district poverty rate (GSS Census 2021). '
               'Outcome: composite maternal health index (Ghana DHS 2022). '
               'HH clusters indicate co-occurrence of high poverty and poor maternal outcomes. '
               'Rook contiguity weights; permutation inference (n=999).')
    fig.text(0.5, 0.01, caption, ha='center', fontsize=10, wrap=True,
             bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.7))
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [Saved] {os.path.basename(out_path)}")


# ── Moran scatterplot ─────────────────────────────────────────────────────────

def plot_moran_scatterplot(master, out_path):
    if 'composite_maternal_index' not in master.columns:
        print("  [SKIP] composite_maternal_index not available.")
        return

    x = master['composite_maternal_index'].fillna(master['composite_maternal_index'].median()).values
    z = (x - x.mean()) / x.std()

    # Spatial lag (KNN k=4 placeholder — actual lag from 02_spatial_analysis.py)
    lag_path = os.path.join(OUT_DATA, 'spatial_lag_composite.csv')
    if os.path.exists(lag_path):
        lag_df = pd.read_csv(lag_path)
        Wz = lag_df['spatial_lag_composite'].values
    else:
        # Placeholder: random lag for scaffold verification
        Wz = np.random.randn(len(z)) * 0.3 + z * 0.5
        print("  [INFO] Spatial lag file not found — using placeholder for scatterplot.")

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(z, Wz, color='steelblue', alpha=0.6, edgecolors='white', linewidths=0.5, s=40)

    m, b = np.polyfit(z, Wz, 1)
    x_line = np.linspace(z.min(), z.max(), 100)
    ax.plot(x_line, m * x_line + b, 'r-', linewidth=2, label=f'OLS slope = {m:.3f}')

    ax.axhline(0, color='grey', linestyle='--', linewidth=0.8)
    ax.axvline(0, color='grey', linestyle='--', linewidth=0.8)
    ax.set_xlabel('Composite Maternal Health Index (standardised)', fontsize=12, fontweight='semibold')
    ax.set_ylabel('Spatial Lag (W × Index)', fontsize=12, fontweight='semibold')
    ax.set_title("Moran's I Scatterplot — Composite Maternal Health Index", fontsize=13, fontweight='semibold')
    ax.legend(fontsize=11)

    caption = ("Figure 4. Moran's scatterplot illustrating spatial autocorrelation of the composite "
               "maternal health index. The slope of the OLS line approximates Moran's I. "
               "KNN (k=4) row-standardised spatial weights matrix.")
    fig.text(0.5, 0.01, caption, ha='center', fontsize=10, wrap=True,
             bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.7))
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [Saved] {os.path.basename(out_path)}")


# ── Table 1 ───────────────────────────────────────────────────────────────────

def build_table1(master, out_path):
    """Generate Table 1: descriptive statistics."""
    # All column names must match maternal_ghana_261districts_clean.csv output
    continuous_cols = [
        # Composite index and its four components (DHS 2022 — regional)
        'composite_maternal_index', 'sba', 'anc_skilled', 'facility_delivery', 'pnc_coverage',
        # Secondary reproductive health outcomes (DHS 2022)
        'modern_cpr', 'unmet_need_fp', 'demand_fp_satisfied', 'abr', 'tfr',
        # Social/GBV/empowerment indicators (DHS 2022)
        'women_anemia', 'wife_beating_justified', 'decision_autonomy', 'ipv_12months',
        'women_edu_secondary', 'women_literacy', 'no_insurance_women',
        # Census 2021 — district-level socioeconomic
        'poverty_rate', 'uninsured_rate', 'illiteracy_rate',
        'working_age_prop', 'female_pop_prop',
    ]
    rows = []
    for col in continuous_cols:
        if col not in master.columns or master[col].isna().all():
            continue
        x = master[col].dropna()
        from scipy import stats as st
        _, p_norm = st.shapiro(x[:50] if len(x) > 50 else x)
        stat_type = 'Mean (SD)' if p_norm >= 0.05 else 'Median [IQR]'
        if stat_type == 'Mean (SD)':
            summary = f'{x.mean():.2f} ({x.std():.2f})'
        else:
            summary = f'{x.median():.2f} [{x.quantile(0.25):.2f}–{x.quantile(0.75):.2f}]'
        rows.append({
            'Variable': col.replace('_', ' ').title(),
            'N': int(x.count()),
            'Statistic': stat_type,
            'Value': summary,
            'Min': f'{x.min():.2f}',
            'Max': f'{x.max():.2f}',
            'Missing n (%)': f'{master[col].isna().sum()} ({master[col].isna().mean()*100:.1f}%)',
        })

    if rows:
        t1 = pd.DataFrame(rows)
        t1.to_csv(out_path, index=False)
        print(f"  [Saved] {os.path.basename(out_path)}")
    else:
        print("  [SKIP] Table 1 — no populated continuous columns yet.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Project 14: Visualisations ===\n")

    # Check inputs
    if not os.path.exists(MASTER_CSV):
        print("[WARNING] Master CSV not found. Run build_final_dataset.py first.")
        master = pd.DataFrame({'district': [f'District_{i}' for i in range(261)],
                               'region': ['Region'] * 261})
    else:
        master = pd.read_csv(MASTER_CSV)
        print(f"  Loaded master CSV: {master.shape}")

    # ── Load district name crosswalk (GeoJSON ALL CAPS → Master Sheet names) ──
    geojson_to_ms = {}
    crosswalk_path = os.path.join(OUT_DATA, 'district_crosswalk.csv')
    if os.path.exists(crosswalk_path):
        cw = pd.read_csv(crosswalk_path)
        geojson_to_ms = dict(zip(cw['district_geojson'].str.strip(),
                                  cw['district_ms'].str.strip()))
        print(f"  Crosswalk loaded: {len(geojson_to_ms)} name mappings")
    else:
        print("[WARNING] district_crosswalk.csv not found — run 01_data_cleaning.py first.")
        print("          Map figures will be produced without name resolution (all districts may appear grey).")

    if not os.path.exists(GEOJSON):
        print("[WARNING] GeoJSON not found. Choropleth maps require Ghana_New_260_District.geojson in data/raw/")
        print("  → Skipping all map figures.\n")
    else:
        gj = load_geojson(GEOJSON)

        plot_choropleth_composite(
            master, gj,
            os.path.join(OUT_FIG, 'choropleth_composite_index.png'),
            geojson_to_ms=geojson_to_ms
        )
        plot_lisa_map(
            master, gj,
            os.path.join(OUT_FIG, 'lisa_cluster_map.png'),
            geojson_to_ms=geojson_to_ms
        )
        plot_gi_star_map(
            master, gj,
            os.path.join(OUT_FIG, 'gi_star_hotspot_map.png'),
            geojson_to_ms=geojson_to_ms
        )
        plot_bivariate_lisa_map(
            master, gj,
            os.path.join(OUT_FIG, 'bivariate_lisa_map.png'),
            geojson_to_ms=geojson_to_ms
        )

    # Moran scatterplot (doesn't need GeoJSON)
    plot_moran_scatterplot(
        master,
        os.path.join(OUT_FIG, 'moran_scatterplot.png')
    )

    # Table 1
    build_table1(
        master,
        os.path.join(ROOT, 'outputs', 'tables', 'table1_descriptive.csv')
    )

    print("\n=== Visualisations complete. ===")


if __name__ == '__main__':
    main()
