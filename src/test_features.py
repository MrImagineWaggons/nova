import pandas as pd
from feature_builder import build_features

df = pd.read_csv(r"C:\Users\kovaa\OneDrive\Desktop\Nova - bot\data\nfl\spreadspoke.csv", encoding="utf-8-sig")
df_features = build_features(df)

print(df_features[["schedule_date", "team_home", "team_away", "home_last5_pts", "away_last5_pts", "home_elo", "away_elo", "home_win"]].head(10))
