import requests

API_KEY = "cc591fede2083b9d6a4016df58683077"

def get_moneyline_odds(home_team, away_team):
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
    
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american"
    }

    response = requests.get(url, params=params)
    data = response.json()

    for game in data:
        teams = game.get("teams", [])
        if home_team in teams and away_team in teams:
            bookmakers = game.get("bookmakers", [])
            if bookmakers:
                markets = bookmakers[0]["markets"][0]["outcomes"]
                odds = {}
                for outcome in markets:
                    odds[outcome["name"]] = outcome["price"]
                return odds

    return None
