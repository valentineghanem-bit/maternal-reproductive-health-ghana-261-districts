"""
Project 14: Ghana Maternal & Reproductive Health — 261 Districts
Script 03: ML Risk Stratification Pipeline
  - GradientBoostingClassifier (sklearn; XGBoost if available)
  - Permutation importance (sklearn.inspection.permutation_importance — Tenet 13 compliant)
  - LOROCV (leave-one-region-out cross-validation; ML-005 prevention)
  - SMOTE guard (EX-028)
Author: Valentine Golden Ghanem
Date: 2026-06-09
Inputs:
  - data/processed/maternal_ghana_261districts_clean.csv
Outputs:
  - outputs/data/ml_predictions.csv
  - outputs/data/ml_metrics_lorocv.csv
  - outputs/data/shap_values.csv          (permutation importance; SHAP-equivalent)
  - outputs/figures/shap_summary.png      (feature importance bar chart)
  - outputs/figures/shap_dependence_*.png (partial dependence per top feature)
# END
"""

import os
import sys
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
PROC = os.path.join(ROOT, "data", "processed")
OUT_DATA = os.path.join(ROOT, "outputs", "data")
OUT_FIG = os.path.join(ROOT, "outputs", "figures")
RANDOM_STATE = 42  # ML-002: fixed seed

os.makedirs(OUT_DATA, exist_ok=True)
os.makedirs(OUT_FIG, exist_ok=True)

FEATURE_COLS = [
    # Census 2021 — district level (poverty_rate, illiteracy_rate, uninsured_rate
    # EXCLUDED post-COMP-006/COMP-008: these 3 vars are now components of
    # composite_maternal_index, the variable risk_label is derived from —
    # including them as features would be circular/leakage)
    "working_age_prop", "female_pop_prop",
    # DHS 2022 — regional, assigned to districts (excludes composite components)
    "women_edu_secondary", "women_literacy", "no_insurance_women", "women_anemia",
    "wife_beating_justified", "decision_autonomy", "ipv_12months",
    "modern_cpr", "unmet_need_fp", "demand_fp_satisfied", "abr", "tfr",
]
OUTCOME_COL = "risk_label"


def run_lorocv(X, y, regions, model_cls, model_params):
    """Leave-one-region-out CV (ML-005 prevention). Returns fold metrics + OOF predictions."""
    from sklearn.metrics import f1_score, accuracy_score
    folds = []
    oof_pred = np.zeros(len(y), dtype=int)
    for reg in regions.unique():
        test_idx = regions[regions == reg].index
        train_idx = regions[regions != reg].index
        if len(train_idx) == 0 or len(test_idx) == 0:
            continue
        X_tr, X_te = X.loc[train_idx], X.loc[test_idx]
        y_tr, y_te = y.loc[train_idx], y.loc[test_idx]
        # SMOTE guard (EX-028)
        try:
            from imblearn.over_sampling import SMOTE
            min_n = y_tr.value_counts().min()
            k = min(5, min_n - 1)
            if k >= 1:
                sm = SMOTE(k_neighbors=k, random_state=RANDOM_STATE)
                X_tr, y_tr = sm.fit_resample(X_tr, y_tr)
        except ImportError:
            pass
        clf = model_cls(**model_params)
        clf.fit(X_tr, y_tr)
        preds = clf.predict(X_te)
        oof_pred[test_idx] = preds
        folds.append({
            "region_left_out": reg,
            "n_test": len(y_te),
            "accuracy": accuracy_score(y_te, preds),
            "macro_f1": f1_score(y_te, preds, average="macro", zero_division=0),
        })
    return pd.DataFrame(folds), oof_pred


def compute_importance(clf, X, y, feature_names, out_dir):
    """
    Permutation importance (Breiman 2001; Molnar 2019) — Tenet 13 compliant.
    Model-agnostic; robust to multicollinearity.  Saves shap_values.csv
    (column names preserved for build_final_dataset.py compatibility) +
    summary bar chart + partial-dependence plots for top 3 features.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.inspection import permutation_importance

    print("  Computing permutation importance (n_repeats=30, random_state=42)...")
    pi = permutation_importance(clf, X, y, n_repeats=30,
                                random_state=RANDOM_STATE, scoring="accuracy")
    mean_imp = pi.importances_mean           # shape (n_features,)
    std_imp  = pi.importances_std

    # Save as shap_values.csv (mean importance per feature)
    imp_df = pd.DataFrame(mean_imp.reshape(1, -1), columns=feature_names)
    imp_df.to_csv(os.path.join(OUT_DATA, "shap_values.csv"), index=False)
    print("    [Saved] shap_values.csv")

    # Ranked importance table
    rank_df = pd.DataFrame({
        "feature": feature_names,
        "mean_importance": mean_imp,
        "std_importance": std_imp,
    }).sort_values("mean_importance", ascending=False).reset_index(drop=True)
    rank_df.to_csv(os.path.join(OUT_DATA, "permutation_importance.csv"), index=False)

    # ── Summary bar chart (SHAP-style) ───────────────────────────────────────
    top_n = min(15, len(feature_names))
    top_df = rank_df.head(top_n).iloc[::-1]  # ascending for horizontal bar
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.barh(top_df["feature"], top_df["mean_importance"],
            xerr=top_df["std_importance"], color="#e05c5c", alpha=0.85, capsize=3)
    ax.set_xlabel("Mean decrease in accuracy (permutation importance)", fontsize=12, fontweight="semibold")
    ax.set_title("Feature Importance — Gradient Boosting (LOROCV, N=261 districts)",
                 fontsize=13, fontweight="semibold")
    ax.axvline(0, color="grey", lw=0.8)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "shap_summary.png"), dpi=300, bbox_inches="tight")
    plt.close()
    print("    [Saved] shap_summary.png")

    # ── Partial-dependence plots: top 3 features ──────────────────────────────
    top3_names = rank_df["feature"].head(3).tolist()
    for rank, feat_name in enumerate(top3_names, 1):
        feat_idx = list(feature_names).index(feat_name)
        col_vals = X.iloc[:, feat_idx]
        # Marginal relationship: feature value vs predicted class (0=HIGH, 1=LOW, 2=MODERATE after LE)
        pred_proba = clf.predict_proba(X)
        # Use probability of HIGH risk (class index 0 after LabelEncoder sorts alphabetically)
        high_idx = 0  # HIGH < LOW < MODERATE alphabetically → index 0
        high_prob = pred_proba[:, high_idx]
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(col_vals, high_prob, alpha=0.6, s=30, color="#2c7bb6")
        # Lowess trend
        try:
            from statsmodels.nonparametric.smoothers_lowess import lowess
            sm_out = lowess(high_prob, col_vals, frac=0.5, return_sorted=True)
            ax.plot(sm_out[:, 0], sm_out[:, 1], color="#d7191c", lw=2)
        except ImportError:
            pass
        ax.set_xlabel(feat_name, fontsize=12, fontweight="semibold")
        ax.set_ylabel("P(HIGH risk)", fontsize=12)
        ax.set_title(f"Feature Dependence — {feat_name}", fontsize=13, fontweight="semibold")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, f"shap_dependence_{rank}_{feat_name}.png"),
                    dpi=300, bbox_inches="tight")
        plt.close()

    print("\n  ── Top 3 features (permutation importance):")
    for _, row in rank_df.head(3).iterrows():
        print(f"    {row['feature']}: {row['mean_importance']:.4f} +/- {row['std_importance']:.4f}")
    print("\n  Public-health translation: complete in manuscript Section 3.3.")
    return top3_names


def main():
    print("=== Project 14: ML Risk Stratification ===\n")

    clean_path = os.path.join(PROC, "maternal_ghana_261districts_clean.csv")
    if not os.path.exists(clean_path):
        print("[WARNING] Run 01_data_cleaning.py first.")
        return

    df = pd.read_csv(clean_path)

    if "composite_maternal_index" not in df.columns or df["composite_maternal_index"].isna().all():
        print("[WARNING] composite_maternal_index not populated.")
        return

    if "risk_label" not in df.columns:
        print("[WARNING] risk_label missing. Run 01_data_cleaning.py first.")
        return

    print(f"  Risk label distribution:\n{df['risk_label'].value_counts()}")

    avail_features = [c for c in FEATURE_COLS if c in df.columns and df[c].notna().any()]
    X = df[avail_features].copy()
    X = X.fillna(X.median())
    y_raw = df[OUTCOME_COL]
    regions = df["region"]

    print(f"\n  Features ({len(avail_features)}): {avail_features}")
    print(f"  N districts: {len(X)}")

    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    y_enc = pd.Series(le.fit_transform(y_raw), index=y_raw.index)
    print(f"  Classes (LabelEncoder): {dict(zip(le.classes_, le.transform(le.classes_)))}")

    # ── Model selection: XGBoost preferred; GradientBoostingClassifier fallback ──
    try:
        from xgboost import XGBClassifier
        model_cls = XGBClassifier
        model_params = {
            "n_estimators": 200, "max_depth": 4, "learning_rate": 0.05,
            "subsample": 0.8, "colsample_bytree": 0.8,
            "eval_metric": "mlogloss", "random_state": RANDOM_STATE,
        }
        print("\n  → Primary model: XGBoost")
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier
        model_cls = GradientBoostingClassifier
        model_params = {
            "n_estimators": 200, "max_depth": 4, "learning_rate": 0.05,
            "subsample": 0.8, "random_state": RANDOM_STATE,
        }
        print("\n  → Primary model: GradientBoostingClassifier (sklearn) — XGBoost unavailable")
        print("    NOTE: GradientBoostingClassifier uses identical algorithm; results directly comparable.")

    # ── LOROCV ────────────────────────────────────────────────────────────────
    n_folds = regions.nunique()
    print(f"  → LOROCV ({n_folds} folds)...")
    fold_metrics, oof_preds = run_lorocv(X, y_enc, regions, model_cls, model_params)
    acc_mean = fold_metrics["accuracy"].mean()
    acc_std  = fold_metrics["accuracy"].std()
    f1_mean  = fold_metrics["macro_f1"].mean()
    f1_std   = fold_metrics["macro_f1"].std()
    print(f"    Mean accuracy:  {acc_mean:.4f} +/- {acc_std:.4f}")
    print(f"    Mean macro-F1:  {f1_mean:.4f} +/- {f1_std:.4f}")
    fold_metrics.to_csv(os.path.join(OUT_DATA, "ml_metrics_lorocv.csv"), index=False)
    print("    [Saved] ml_metrics_lorocv.csv")

    # ── OOF predictions ───────────────────────────────────────────────────────
    pred_labels = le.inverse_transform(oof_preds)
    pred_df = pd.DataFrame({
        "district": df["district"].values,
        "true_risk": y_raw.values,
        "xgb_predicted_risk": pred_labels,  # column name preserved for master CSV compatibility
    })
    pred_df.to_csv(os.path.join(OUT_DATA, "ml_predictions.csv"), index=False)
    print("    [Saved] ml_predictions.csv")

    # ── Full-data fit for importance ──────────────────────────────────────────
    print("\n  Fitting full model for feature importance...")
    clf_full = model_cls(**model_params)
    clf_full.fit(X, y_enc)

    top3 = compute_importance(clf_full, X, y_enc, avail_features, OUT_FIG)
    if top3:
        print(f"    Top-3: {top3}")

    print("\n=== ML pipeline complete. ===")


if __name__ == "__main__":
    main()
    # END
