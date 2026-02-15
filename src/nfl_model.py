def calculate_win_probability(home_ppg, home_allowed,
                              away_ppg, away_allowed,
                              home_field=True):

    # Offensive vs Defensive strength
    home_off_edge = home_ppg - away_allowed
    away_off_edge = away_ppg - home_allowed

    # Raw score differential
    diff = home_off_edge - away_off_edge

    # Home field advantage boost
    if home_field:
        diff += 1.5

    # Logistic scaling to probability
    import math
    probability = 1 / (1 + math.exp(-diff / 6))

    return round(probability, 4)