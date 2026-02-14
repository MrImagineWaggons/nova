import joblib
import pandas as pd

# Load model
model = joblib.load(r"C:\Users\kovaa\OneDrive\Desktop\Nova - bot\models\nfl_model.pkl")

def predict_game(home_last5_pts, away_last5_pts, home_elo, away_elo):
    df = pd.DataFrame([[home_last5_pts, away_last5_pts, home_elo, away_elo]],
                      columns=["home_last5_pts", "away_last5_pts", "home_elo", "away_elo"])
    prob = model.predict_proba(df)[0][1]  # probability home team wins
    return prob

# Example test
if __name__ == "__main__":
    prob = predict_game(24, 21, 1600, 1550)
    print(f"Home Win Probability: {prob*100:.1f}%")
