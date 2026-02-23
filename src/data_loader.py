import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "nfl", "spreadspoke.csv")

def load_nfl_data():
    df = pd.read_csv(DATA_PATH)
    
    # Keep only completed games
    df = df[df["score_home"].notna()]
    
    df["schedule_date"] = pd.to_datetime(df["schedule_date"])
    
    return df