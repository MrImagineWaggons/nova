import os
import pandas as pd
import joblib
from xgboost import XGBClassifier
from feature_builder import build_features

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "nfl", "spreadspoke.csv")
MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "nfl_model.pkl")

print("Loading dataset...")
df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

print("Building features...")
df = build_features(df)

# Time-based split (last season as test)
last_season = df["schedule_season"].max()
train = df[df["schedule_season"] < last_season]
test = df[df["schedule_season"] == last_season]

features = [
    "home_last5_pts",
    "away_last5_pts",
    "home_last5_allowed",
    "away_last5_allowed",
    "elo_diff"
]

X_train, y_train = train[features], train["home_win"]
X_test, y_test = test[features], test["home_win"]

print("Training model...")

model = XGBClassifier(
    n_estimators=600,
    learning_rate=0.03,
    max_depth=5,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric="logloss",
    random_state=42
)

model.fit(
    X_train,
    y_train,
    eval_set=[(X_test, y_test)],
    verbose=False
)

if len(X_test) > 0:
    accuracy = model.score(X_test, y_test)
    print(f"Test Accuracy ({last_season}): {accuracy:.3f}")

os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
joblib.dump(model, MODEL_PATH)

print(f"Model saved to {MODEL_PATH}")
