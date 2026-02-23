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

def american_to_implied_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def calculate_ev(prob, american_odds):
    if american_odds > 0:
        decimal = 1 + (american_odds / 100)
    else:
        decimal = 1 + (100 / abs(american_odds))

    return (prob * decimal) - 1
