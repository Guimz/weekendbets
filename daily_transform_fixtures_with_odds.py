import requests
import pandas as pd
import json
import os
from pandas import json_normalize
from constants import odds_url, fixtures_url
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Get today's date and the date 20 days from now
today = datetime.now().date()
start_day = today - timedelta(days=8)
end_date = today + timedelta(days=8)

odds_start_date = datetime.combine(today, datetime.min.time())
odds_end_date = datetime.combine(end_date, datetime.min.time())

fixtures_start_date = datetime.combine(start_day, datetime.min.time())
fixtures_end_date = datetime.combine(end_date, datetime.min.time())

load_dotenv()

season = "2024"
bookmaker = "8"
bet = "1"

headers = {
	"x-rapidapi-key": os.getenv("x-rapidapi-key"),
	"x-rapidapi-host": os.getenv("x-rapidapi-host")
}

odds_date_range = [odds_start_date + timedelta(days=x) for x in range((odds_end_date-odds_start_date).days + 1)]
fixtures_date_range = [fixtures_start_date + timedelta(days=x) for x in range((fixtures_end_date-fixtures_start_date).days + 1)]


def extract_odds_from_api(season, bookmaker, bet):
    for date in odds_date_range:
        try:
            date = date.strftime("%Y-%m-%d")
            print(f"Date extracting odds for: {date}")
            final_df = pd.DataFrame()  # Initialize final_df before the loop
            page = 1
            while True:
                querystring = {"date":f"{date}","season":f"{season}","bookmaker":f"{bookmaker}","bet":f"{bet}","page":f"{page}"}
                response = requests.get(odds_url, headers=headers, params=querystring)
                data = response.json()
                if not data['response']:
                    break
                df = json_normalize(data['response'])
                if page == 1:
                    final_df = df
                else:
                    final_df = pd.concat([final_df, df])
                page += 1
            df = final_df.copy()
            df = df[['update', 'bookmakers', 'league.id', 'league.season', 'fixture.id']]
            df['home_odd'] = df['bookmakers'].apply(lambda x: x[0]['bets'][0]['values'][0]['odd'])
            df['draw_odd'] = df['bookmakers'].apply(lambda x: x[0]['bets'][0]['values'][1]['odd'])
            df['away_odd'] = df['bookmakers'].apply(lambda x: x[0]['bets'][0]['values'][2]['odd'])
            df = df[['league.id', 'league.season', 'fixture.id', 'home_odd', 'draw_odd', 'away_odd']]
            print(f"odds_{date}_{season}_{bookmaker}_{bet} to be stored")
            print(df)
            df.to_json(f'json/transformed/odds/odds_{date}_{season}_{bookmaker}_{bet}.json', orient='records', lines=False)
        except Exception as e:
            print(f"An error occurred while extracting odds for date {date}: {str(e)}")



def get_fixtures_with_odds():
    for date in fixtures_date_range:
        date = date.strftime("%Y-%m-%d")
        print(f"Extracting fixtures for: {date}")
        querystring = {"date":f"{date}"}
        response = requests.get(fixtures_url, headers=headers, params=querystring)
        data = response.json()
        with open(f'json/fixtures/fixtures_{date}.json', 'w') as f:
            json.dump(data, f)
        df = json_normalize(data['response'])
        df = df[['fixture.id', 'fixture.date', 'league.id', 'league.season', 'teams.home.id', 'teams.away.id', 'goals.home', 'goals.away']]
        with open('json/teams/all_teams.json', 'r') as f:
            team_data = json.load(f)
        team_df = pd.DataFrame(team_data)
        team_df = team_df[['team_id', 'team_name']]
        team_df = team_df.rename(columns={'team_id': 'teams.home.id', 'team_name': 'teams.home.name'})
        df = df.merge(team_df, on='teams.home.id', how='left')
        team_df = team_df.rename(columns={'teams.home.id': 'teams.away.id', 'teams.home.name': 'teams.away.name'})
        df = df.merge(team_df, on='teams.away.id', how='left')

        leagues_df = pd.read_csv('leagues.csv')
        leagues_df = leagues_df[['league.id', 'league.name']]
        df = df.merge(leagues_df, on='league.id', how='left')
        # Load transformed odds data for the current date
        try:
            print(f"trying to open odds file")
            with open(f'json/transformed/odds/odds_{date}_{season}_{bookmaker}_{bet}.json', 'r') as f:
                odds_data = json.load(f)
            odds_df = pd.DataFrame(odds_data)
        except FileNotFoundError:
            print(f"No odds data found for date: {date}")
            odds_df = pd.DataFrame(columns=['fixture.id', 'home_odd', 'draw_odd', 'away_odd', 'league.id', 'league.season'])

        # odds_df = load_odds_from_json_per_day(date, season, bookmaker, bet)
        odds_df = odds_df.drop(columns=['league.id', 'league.season'])

        df = df.merge(odds_df, on='fixture.id', how='left')
        df = df.dropna(subset=['draw_odd'])

        df.rename(columns={"fixture.id": "Fixture", "fixture.date": "Date", "league.id": "League id", "league.season": "Season", "teams.home.id": "Home id", "teams.away.id": "Away id", 
                           "goals.home": "Home goals", "goals.away": "Away goals", "teams.home.name": "Home team", "teams.away.name": "Away team", "league.name": "League", "home_odd": "Home odd",
                           "draw_odd": "Draw odd", "away_odd": "Away odd"}, inplace=True)
        print(f"final df: {df}")
        df.to_json(f'json/transformed/fixtures_with_odds/fixture_with_odds_{date}.json', orient='records', lines=False)


if __name__ == '__main__':
    extract_odds_from_api(season, bookmaker, bet)
    get_fixtures_with_odds()
    # print(odds_df)
    # odds_df.to_csv(f'odds_{league}_{season}_{bookmaker}_{bet}.csv', index=False)