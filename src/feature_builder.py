import pandas as pd

BASE_ELO = 1500
K_FACTOR = 20

def update_elo(home_elo, away_elo, home_score, away_score):
    expected_home = 1 / (1 + 10 ** ((away_elo - home_elo) / 400))
    result_home = 1 if home_score > away_score else 0

    new_home = home_elo + K_FACTOR * (result_home - expected_home)
    new_away = away_elo + K_FACTOR * ((1 - result_home) - (1 - expected_home))

    return new_home, new_away


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("schedule_date").copy()

    # Rolling offensive averages
    df["home_last5_pts"] = (
        df.groupby("team_home")["score_home"]
        .rolling(5, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )

    df["away_last5_pts"] = (
        df.groupby("team_away")["score_away"]
        .rolling(5, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )

    # Rolling defensive averages
    df["home_last5_allowed"] = (
        df.groupby("team_home")["score_away"]
        .rolling(5, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )

    df["away_last5_allowed"] = (
        df.groupby("team_away")["score_home"]
        .rolling(5, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )

    # Target
    df["home_win"] = (df["score_home"] > df["score_away"]).astype(int)

    # Proper Elo without leakage
    elo_ratings = {}
    home_elos = []
    away_elos = []

    for _, row in df.iterrows():
        home = row["team_home"]
        away = row["team_away"]

        home_elo = elo_ratings.get(home, BASE_ELO)
        away_elo = elo_ratings.get(away, BASE_ELO)

        # Store BEFORE update
        home_elos.append(home_elo)
        away_elos.append(away_elo)

        # Update after storing
        new_home, new_away = update_elo(
            home_elo, away_elo, row["score_home"], row["score_away"]
        )

        elo_ratings[home] = new_home
        elo_ratings[away] = new_away

    df["home_elo"] = home_elos
    df["away_elo"] = away_elos
    df["elo_diff"] = df["home_elo"] - df["away_elo"]

    return df.dropna()
