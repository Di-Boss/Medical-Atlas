# src/train_model_final_v9_ultra.py
import os
import psycopg2
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from catboost import CatBoostClassifier, Pool
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import accuracy_score, f1_score

load_dotenv()
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_NAME = os.getenv("POSTGRES_DB", "atlas_db")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

print("Connecting to database...")
conn = psycopg2.connect(
    host=DB_HOST,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    port=DB_PORT
)

query = """
SELECT 
    t.resistant,
    p.age,
    p.weight_kg,
    p.gender,
    p.cancer_type,
    p.region,
    t.pathogen_id,
    t.antibiotic_id,
    t.duration_days,
    t.admission_date
FROM treatments t
JOIN patients p ON t.patient_id = p.patient_id
WHERE t.resistant IS NOT NULL
LIMIT 1500000;
"""

print("Loading data...")
df = pd.read_sql_query(query, conn)
conn.close()
print(f"Loaded {len(df):,} records")

df.dropna(subset=["age", "weight_kg", "duration_days"], inplace=True)
numeric_cols = ["age", "weight_kg", "duration_days"]
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

df["admission_date"] = pd.to_datetime(df["admission_date"], errors="coerce")
for col in numeric_cols:
    q01, q99 = df[col].quantile([0.01, 0.99])
    df[col] = df[col].clip(q01, q99)

categorical_cols = ["gender", "cancer_type", "region"]
df[categorical_cols] = df[categorical_cols].fillna("missing").astype(str)

df["admission_year"] = df["admission_date"].dt.year.fillna(0).astype(int)
df["admission_month"] = df["admission_date"].dt.month.fillna(0).astype(int)

def month_to_season(m):
    if m in (12, 1, 2): return 0
    if m in (3, 4, 5): return 1
    if m in (6, 7, 8): return 2
    if m in (9, 10, 11): return 3
    return -1

df["season"] = df["admission_month"].apply(month_to_season).astype(int)

df["region_pathogen"] = df["region"] + "_" + df["pathogen_id"].astype(str)
df["region_antibiotic"] = df["region"] + "_" + df["antibiotic_id"].astype(str)
df["antibiotic_cancer"] = df["antibiotic_id"].astype(str) + "_" + df["cancer_type"].astype(str)

interaction_cols = ["region_pathogen", "region_antibiotic", "antibiotic_cancer"]

for col in interaction_cols:
    top = df[col].value_counts().nlargest(5000).index
    df[col] = df[col].where(df[col].isin(top), "other")

freq_cols = []
for col in categorical_cols + interaction_cols:
    freq_col = f"{col}_freq"
    vc = df[col].value_counts()
    df[freq_col] = df[col].map(vc).astype(float) / vc.max()
    freq_cols.append(freq_col)

# -----------------------------------------------------
# 🚀 ULTRA-FAST KFold TARGET ENCODING (MILLION-ROW SAFE)
# -----------------------------------------------------
y_array = df["resistant"].values
kf = KFold(n_splits=5, shuffle=True, random_state=42)
te_cols = []

for col in categorical_cols + interaction_cols:
    te_col = f"{col}_target_enc"
    te_cols.append(te_col)

    values = df[col].values
    te_result = np.zeros(len(df), dtype=float)
    global_mean = y_array.mean()

    for train_idx, valid_idx in kf.split(values):
        # Compute means on train fold (fast)
        train_values = values[train_idx]
        train_targets = y_array[train_idx]

        means = pd.DataFrame({
            "col": train_values,
            "target": train_targets
        }).groupby("col")["target"].mean()

        # Map and fill NaN with global mean
        te_result[valid_idx] = np.array(
            pd.Series(values[valid_idx]).map(means).fillna(global_mean)
        )

    df[te_col] = te_result

# -----------------------------------------------------

df["weight_age_ratio"] = df["weight_kg"] / (df["age"] + 1)
df["duration_log"] = np.log1p(df["duration_days"])
df["weight_log"] = np.log1p(df["weight_kg"])
df["age_log"] = np.log1p(df["age"])
df["weight_sq"] = df["weight_kg"] ** 2
df["age_sq"] = df["age"] ** 2
df["duration_sq"] = df["duration_days"] ** 2
df["age_duration"] = df["age"] * df["duration_days"]
df["weight_duration"] = df["weight_kg"] * df["duration_days"]
df["age_bin"] = pd.cut(df["age"], bins=[0,20,40,60,80,120], labels=False).astype(str)

features = []
features += numeric_cols
features += ["admission_year", "admission_month", "season"]
features += categorical_cols
features += interaction_cols
features += freq_cols
features += te_cols
features += [
    "weight_age_ratio", "duration_log", "weight_log", "age_log",
    "weight_sq", "age_sq", "duration_sq", "age_duration",
    "weight_duration", "age_bin"
]

features = [f for f in features if f in df.columns]

X = df[features]
y = df["resistant"].astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

median_values = X_train.median(numeric_only=True)
X_train = X_train.fillna(median_values)
X_test = X_test.fillna(median_values)

cat_features_for_cb = [
    c for c in (categorical_cols + interaction_cols + ["age_bin", "season"])
    if c in X_train.columns
]

train_pool = Pool(X_train, y_train, cat_features=cat_features_for_cb)
test_pool = Pool(X_test, y_test, cat_features=cat_features_for_cb)

model = CatBoostClassifier(
    iterations=4000,
    depth=10,
    learning_rate=0.03,
    loss_function="Logloss",
    eval_metric="F1",
    random_seed=42,
    thread_count=-1,
    task_type="GPU",
    devices='0',
    auto_class_weights="Balanced",
    l2_leaf_reg=4,
    border_count=254,
    random_strength=1.0,
    min_data_in_leaf=20,
    verbose=100
)

print("Training model...")
model.fit(train_pool, eval_set=test_pool, use_best_model=True)

y_pred = model.predict(test_pool)
acc = accuracy_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)

print("\n✅ Model trained successfully!")
print(f"Accuracy: {acc:.4f}")
print(f"F1 Score: {f1:.4f}")

model.save_model("training_final_v9_ultra.cbm")
print("\n📦 Saved model: training_final_v9_ultra.cbm")
