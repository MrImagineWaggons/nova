import os
import joblib
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "nfl_model.pkl")

model = joblib.load(MODEL_PATH)

def predict_game(home_last5_pts, away_last5_pts, home_elo, away_elo):
    df = pd.DataFrame(
        [[home_last5_pts, away_last5_pts, home_elo, away_elo]],
        columns=[
            "home_last5_pts",
            "away_last5_pts",
            "home_elo",
            "away_elo"
        ]
    )
    prob = model.predict_proba(df)[0][1]
    return prob
