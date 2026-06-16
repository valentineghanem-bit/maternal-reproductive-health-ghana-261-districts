"""
Project 14: Ghana Maternal & Reproductive Health — 261 Districts
test_canonical_values.py — Pytest canonical assertions (EX-016)
Author: Valentine Golden Ghanem
Date: 2026-06-09

Usage: pytest tests/test_canonical_values.py -v
All assertions are populated at QA-0 from the Canonical Values Register.
Run after Phase 8 (analysis complete) and again after every manuscript revision.
# END
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_CSV = os.path.join(BASE, 'master_maternal_ghana_261districts_v1.csv')
OUT_DATA = os.path.join(BASE, 'outputs', 'data')
MORANS_CSV = os.path.join(OUT_DATA, 'morans_i_results.csv')
LISA_CSV = os.path.join(OUT_DATA, 'lisa_results.csv')
ML_CSV = os.path.join(OUT_DATA, 'ml_metrics_lorocv.csv')


# ── [CANONICAL VALUES — populated at QA-0] ───────────────────────────────────
# Extracted from the Master CSV and analysis outputs after Phase 6 completion.

CANONICAL_N_DISTRICTS    = 261       # 261 districts (Guan/Oti included; descriptive/ML/composite N)
CANONICAL_MORANS_I       = 0.8437    # Global Moran's I, composite_maternal_index, KNN k=4
CANONICAL_MORANS_P       = 0.001     # permutation p-value (p < 0.001)
CANONICAL_LISA_HH        = 10        # significant HH clusters (Rook contiguity, p<0.05)
CANONICAL_LISA_LL        = 38        # significant LL clusters (Rook contiguity, p<0.05)
CANONICAL_GI_HOTSPOTS    = 37        # Getis-Ord Gi* significant hotspots (p<0.05, hotspot_class=='Hotspot')
CANONICAL_XGB_MACROF1    = 0.488444950861589   # GradientBoostingClassifier LOROCV mean macro-F1 (ML-NAMING-001)
CANONICAL_XGB_ACCURACY   = 0.6015109241978729  # GradientBoostingClassifier LOROCV mean accuracy
CANONICAL_COMPOSITE_MEAN = 65.63294024655217   # composite_maternal_index mean
CANONICAL_COMPOSITE_SD   = 17.81075592156025   # composite_maternal_index sd


@pytest.fixture(scope='module')
def master():
    if not os.path.exists(MASTER_CSV):
        pytest.skip("Master CSV not yet built — run build_final_dataset.py")
    return pd.read_csv(MASTER_CSV)


@pytest.fixture(scope='module')
def morans():
    if not os.path.exists(MORANS_CSV):
        pytest.skip("Moran's I results not yet built")
    return pd.read_csv(MORANS_CSV)


@pytest.fixture(scope='module')
def lisa():
    if not os.path.exists(LISA_CSV):
        pytest.skip("LISA results not yet built")
    return pd.read_csv(LISA_CSV)


@pytest.fixture(scope='module')
def ml_metrics():
    if not os.path.exists(ML_CSV):
        pytest.skip("ML metrics not yet built")
    return pd.read_csv(ML_CSV)


# ── District count assertions ────────────────────────────────────────────────

def test_district_count(master):
    """Master CSV must contain 261 rows (261 districts)."""
    assert len(master) == 261, f"Expected 261 districts, got {len(master)}"


def test_district_uniqueness(master):
    """All district names must be unique."""
    assert master['district'].nunique() == len(master), \
        "Duplicate district names detected"


def test_region_count(master):
    """Must have exactly 16 regions."""
    assert master['region'].nunique() == 16, \
        f"Expected 16 regions, got {master['region'].nunique()}"


# ── Outcome variable range checks ────────────────────────────────────────────

def test_sba_range(master):
    """SBA rate must be 0–100%."""
    if 'sba_rate' in master.columns and master['sba_rate'].notna().any():
        assert master['sba_rate'].between(0, 100).all(), \
            "SBA rate out of 0–100% range"


def test_anc4_range(master):
    """ANC4+ coverage must be 0–100%."""
    if 'anc4_coverage' in master.columns and master['anc4_coverage'].notna().any():
        assert master['anc4_coverage'].between(0, 100).all(), \
            "ANC4+ coverage out of 0–100% range"


def test_composite_range(master):
    """Composite index must be 0–100."""
    if 'composite_maternal_index' in master.columns and master['composite_maternal_index'].notna().any():
        assert master['composite_maternal_index'].between(0, 100, inclusive='both').all(), \
            "Composite index outside 0–100 range"


# ── Canonical value assertions (populated at QA-0) ───────────────────────────

def test_morans_i_canonical(morans):
    """Global Moran's I must match canonical value."""
    if CANONICAL_MORANS_I is None:
        pytest.skip("Canonical Moran's I not yet set — populate after Phase 2")
    row = morans[morans['variable'] == 'composite_maternal_index']
    assert not row.empty, "composite_maternal_index not in Moran's I results"
    I_obs = row['morans_I'].values[0]
    assert abs(I_obs - CANONICAL_MORANS_I) < 0.001, \
        f"Moran's I mismatch: expected {CANONICAL_MORANS_I}, got {I_obs}"


def test_lisa_hh_count(lisa):
    """LISA HH significant cluster count must match canonical value."""
    if CANONICAL_LISA_HH is None:
        pytest.skip("Canonical LISA HH not yet set — populate after Phase 3")
    n_hh = ((lisa['quadrant'] == 'HH') & (lisa['significant'] == 1)).sum()
    assert n_hh == CANONICAL_LISA_HH, \
        f"LISA HH count mismatch: expected {CANONICAL_LISA_HH}, got {n_hh}"


def test_lisa_ll_count(lisa):
    """LISA LL significant cluster count must match canonical value."""
    if CANONICAL_LISA_LL is None:
        pytest.skip("Canonical LISA LL not yet set — populate after Phase 3")
    n_ll = ((lisa['quadrant'] == 'LL') & (lisa['significant'] == 1)).sum()
    assert n_ll == CANONICAL_LISA_LL, \
        f"LISA LL count mismatch: expected {CANONICAL_LISA_LL}, got {n_ll}"


def test_composite_mean(master):
    """Composite index mean must match canonical value."""
    if CANONICAL_COMPOSITE_MEAN is None:
        pytest.skip("Canonical composite mean not yet set — populate after Phase 1")
    if 'composite_maternal_index' not in master.columns or master['composite_maternal_index'].isna().all():
        pytest.skip("composite_maternal_index not populated")
    obs_mean = master['composite_maternal_index'].mean()
    assert abs(obs_mean - CANONICAL_COMPOSITE_MEAN) < 0.5, \
        f"Composite mean mismatch: expected {CANONICAL_COMPOSITE_MEAN}, got {obs_mean:.4f}"


def test_ml_macro_f1(ml_metrics):
    """LOROCV mean macro-F1 must match canonical value."""
    if CANONICAL_XGB_MACROF1 is None:
        pytest.skip("Canonical XGB macro-F1 not yet set — populate after Phase 8")
    obs_f1 = ml_metrics['macro_f1'].mean()
    assert abs(obs_f1 - CANONICAL_XGB_MACROF1) < 0.01, \
        f"Macro-F1 mismatch: expected {CANONICAL_XGB_MACROF1}, got {obs_f1:.4f}"


# ── Data source attribution ───────────────────────────────────────────────────

def test_data_source_columns(master):
    """Master CSV must carry data_source_* attribution columns (EX-003)."""
    ds_cols = [c for c in master.columns if c.startswith('data_source_')]
    assert len(ds_cols) >= 4, \
        f"Expected ≥4 data_source_* columns, found {len(ds_cols)}: {ds_cols}"


def test_no_pii(master):
    """No personal identifier columns present."""
    pii_cols = ['name', 'firstname', 'lastname', 'id_number', 'phone', 'email', 'ssn']
    found = [c for c in master.columns if any(p in c.lower() for p in pii_cols)]
    assert len(found) == 0, f"Potential PII columns: {found}"


# END
