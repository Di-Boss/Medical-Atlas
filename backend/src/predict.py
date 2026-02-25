# src/predict.py
import os
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from dotenv import load_dotenv

load_dotenv()
MODEL_PATH = os.path.join(os.path.dirname(__file__), "training_final_v9_ultra.cbm")

# Load CatBoost model
model = CatBoostClassifier()
model.load_model(MODEL_PATH)
print("Model loaded successfully!")

# Precomputed numeric medians from training (used as fallbacks)
MEDIANS = {
    "age": 50.0,
    "weight_kg": 70.0,
    "duration_days": 7.0,
    "weight_age_ratio": 70.0 / 51.0,
    "duration_log": float(np.log1p(7.0)),
    "weight_duration": 70.0 * 7.0,
    "age_duration": 50.0 * 7.0,
    "age_sq": 50.0 ** 2,
    "weight_sq": 70.0 ** 2,
    "duration_sq": 7.0 ** 2,
    "weight_log": float(np.log1p(70.0)),
    "age_log": float(np.log1p(50.0)),
    "admission_year": 0,
    "admission_month": 0,
    "season": 0
}

# Safe defaults for frequency and target-encoding features (you can replace with real values from training)
FREQ_DEFAULT = 0.0        # values were normalized by max (0..1) during training
TE_DEFAULT = 0.5          # fallback target-encoding mean (class prior-ish)

# Helper functions
def _clamp_age_for_bins(age: float) -> float:
    return max(0.0, min(age, 119.0))

def _map_interaction(val: str, top_set: set) -> str:
    # If you populate top_set with top values from training, this will map unseen -> 'other'
    return val if val in top_set else "other"

def month_to_season(m: int) -> int:
    if m in (12, 1, 2): return 0
    if m in (3, 4, 5): return 1
    if m in (6, 7, 8): return 2
    if m in (9, 10, 11): return 3
    return -1

# Top interactions (empty sets here; ideally fill with training top values to preserve interaction buckets)
TOP_REGION_PATHOGEN = set()
TOP_REGION_ANTIBIOTIC = set()
TOP_ANTIBIOTIC_CANCER = set()

# Feature order exactly like training (34 features)
FEATURE_ORDER = [
    "age",
    "weight_kg",
    "duration_days",

    "admission_year",
    "admission_month",
    "season",

    "gender",
    "cancer_type",
    "region",

    "region_pathogen",
    "region_antibiotic",
    "antibiotic_cancer",

    "gender_freq",
    "cancer_type_freq",
    "region_freq",
    "region_pathogen_freq",
    "region_antibiotic_freq",
    "antibiotic_cancer_freq",

    "gender_target_enc",
    "cancer_type_target_enc",
    "region_target_enc",
    "region_pathogen_target_enc",
    "region_antibiotic_target_enc",
    "antibiotic_cancer_target_enc",

    "weight_age_ratio",
    "duration_log",
    "weight_log",
    "age_log",
    "weight_sq",
    "age_sq",
    "duration_sq",
    "age_duration",
    "weight_duration",
    "age_bin"
]

def predict_resistance(age, weight_kg, gender, cancer_type,
                       pathogen_id, antibiotic_id, duration_days, region,
                       admission_date=None):
    # Basic normalization / casts
    age = _clamp_age_for_bins(float(age))
    weight_kg = float(weight_kg)
    duration_days = float(duration_days)

    # Admission features
    if admission_date is None:
        admission_year, admission_month, season = 0, 0, 0
    else:
        ad = pd.to_datetime(admission_date, errors="coerce")
        admission_year = int(ad.year) if not pd.isna(ad) else 0
        admission_month = int(ad.month) if not pd.isna(ad) else 0
        season = month_to_season(admission_month)

    # Interaction features (map unseen -> "other" using TOP_* sets)
    region_pathogen = _map_interaction(f"{region}_{pathogen_id}", TOP_REGION_PATHOGEN)
    region_antibiotic = _map_interaction(f"{region}_{antibiotic_id}", TOP_REGION_ANTIBIOTIC)
    antibiotic_cancer = _map_interaction(f"{antibiotic_id}_{cancer_type}", TOP_ANTIBIOTIC_CANCER)

    # Engineered numeric features (as in training)
    weight_age_ratio = weight_kg / (age + 1)
    duration_log = float(np.log1p(duration_days))
    weight_duration = weight_kg * duration_days
    age_duration = age * duration_days
    age_bin_val = pd.cut([age], bins=[0,20,40,60,80,120], labels=False)[0]
    age_bin = str(int(age_bin_val)) if not pd.isna(age_bin_val) else "0"
    age_sq = age ** 2
    weight_sq = weight_kg ** 2
    duration_sq = duration_days ** 2
    weight_log = float(np.log1p(weight_kg))
    age_log = float(np.log1p(age))

    # Frequency features fallback (if you have training counts/vc, replace these defaults)
    gender_freq = FREQ_DEFAULT
    cancer_type_freq = FREQ_DEFAULT
    region_freq = FREQ_DEFAULT
    region_pathogen_freq = FREQ_DEFAULT
    region_antibiotic_freq = FREQ_DEFAULT
    antibiotic_cancer_freq = FREQ_DEFAULT

    # Target-encoding fallbacks (if you have training maps, replace these defaults)
    gender_target_enc = TE_DEFAULT
    cancer_type_target_enc = TE_DEFAULT
    region_target_enc = TE_DEFAULT
    region_pathogen_target_enc = TE_DEFAULT
    region_antibiotic_target_enc = TE_DEFAULT
    antibiotic_cancer_target_enc = TE_DEFAULT

    # Build single-row DataFrame containing ALL required features
    row = {
        "age": age,
        "weight_kg": weight_kg,
        "duration_days": duration_days,

        "admission_year": admission_year,
        "admission_month": admission_month,
        "season": season,

        "gender": str(gender),
        "cancer_type": str(cancer_type),
        "region": str(region),

        "region_pathogen": region_pathogen,
        "region_antibiotic": region_antibiotic,
        "antibiotic_cancer": antibiotic_cancer,

        "gender_freq": gender_freq,
        "cancer_type_freq": cancer_type_freq,
        "region_freq": region_freq,
        "region_pathogen_freq": region_pathogen_freq,
        "region_antibiotic_freq": region_antibiotic_freq,
        "antibiotic_cancer_freq": antibiotic_cancer_freq,

        "gender_target_enc": gender_target_enc,
        "cancer_type_target_enc": cancer_type_target_enc,
        "region_target_enc": region_target_enc,
        "region_pathogen_target_enc": region_pathogen_target_enc,
        "region_antibiotic_target_enc": region_antibiotic_target_enc,
        "antibiotic_cancer_target_enc": antibiotic_cancer_target_enc,

        "weight_age_ratio": weight_age_ratio,
        "duration_log": duration_log,
        "weight_log": weight_log,
        "age_log": age_log,
        "weight_sq": weight_sq,
        "age_sq": age_sq,
        "duration_sq": duration_sq,
        "age_duration": age_duration,
        "weight_duration": weight_duration,
        "age_bin": age_bin
    }

    df = pd.DataFrame([row])

    # Categorical columns (same as training cat_features_for_cb)
    cat_cols = [
        "gender", "cancer_type", "region",
        "region_pathogen", "region_antibiotic", "antibiotic_cancer",
        "age_bin", "season"
    ]
    for col in cat_cols:
        df[col] = df[col].astype(str)

    # Fill numeric NaNs with MEDIANS; frequency/te fallbacks already set
    for col in df.columns:
        if pd.isna(df.at[0, col]):
            if col in MEDIANS:
                df.at[0, col] = MEDIANS[col]
            else:
                # For freq/te and any other missing feature, keep the safe defaults:
                if col.endswith("_freq"):
                    df.at[0, col] = FREQ_DEFAULT
                elif col.endswith("_target_enc"):
                    df.at[0, col] = TE_DEFAULT
                else:
                    df.at[0, col] = 0.0

    # Reorder columns to match training exactly
    df = df[FEATURE_ORDER]

    pool = Pool(df, cat_features=cat_cols)
    pred = int(model.predict(pool)[0])
    try:
        prob = float(model.predict_proba(pool)[0][1])
    except Exception:
        prob = 0.0 if pred == 0 else 1.0

    return {"resistant": pred, "probability": prob}

# Example usage
if __name__ == "__main__":
    res = predict_resistance(
        age=35,
        weight_kg=67,
        gender="Male",
        admission_date="2025-11-28",
        cancer_type="Lung",
        pathogen_id=1,
        antibiotic_id=1,
        duration_days=7,
        region="Ohio"
    )
    print(res)
