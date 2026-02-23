import os
import joblib
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import log_loss, roc_auc_score
from data_loader import load_nfl_data
from feature_builder import build_features

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "nfl_model.pkl")

def train():
    df = load_nfl_data()
    df = build_features(df)

    features = [
        "home_last5_pts",
        "away_last5_pts",
        "home_last5_allowed",
        "away_last5_allowed",
        "elo_diff"
    ]

    X = df[features]
    y = df["home_win"]

    # Time-based split
    split_index = int(len(df) * 0.8)
    X_train, X_test = X[:split_index], X[split_index:]
    y_train, y_test = y[:split_index], y[split_index:]

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss"
    )

    model.fit(X_train, y_train)

    preds = model.predict_proba(X_test)[:, 1]

    print("Log Loss:", log_loss(y_test, preds))
    print("AUC:", roc_auc_score(y_test, preds))

    joblib.dump(model, MODEL_PATH)
    print("Model saved.")

if __name__ == "__main__":
    train()