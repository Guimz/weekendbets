import pandas as pd
import numpy as np
import os
import json
from datetime import date
import streamlit as st
from boto3 import client
from datetime import datetime, timezone, timedelta
from streamlit_extras.dataframe_explorer import dataframe_explorer
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.buy_me_a_coffee import button
import plotly.express as px

now_date = datetime.now(timezone.utc)  # Set now_date to UTC

today = datetime.now().date()

start_day = datetime(2018, 1, 1)
end_date = today + timedelta(days=8)

fixtures_start_date = datetime.combine(start_day, datetime.min.time())
fixtures_end_date = datetime.combine(end_date, datetime.min.time())

fixtures_date_range = [fixtures_start_date + timedelta(days=x) for x in range((fixtures_end_date-fixtures_start_date).days + 1)]

BUCKET = 'weekendbets'
FILE_TO_READ_PREFIX = 'json/transformed/fixtures_with_odds/fixture_with_odds_'

client = client('s3',
                aws_access_key_id = st.secrets['AWS_ACCESS_KEY'],
                aws_secret_access_key = st.secrets['AWS_SECRET_ACCESS_KEY']
                )


def result_colour(val):
    color = '#D7EED7' if val == 'H' else '#FFCCCB'
    return f"color: {color}"

@st.cache_data
def import_json_files_as_dataframe(day):
    dataframes = []
    for date in fixtures_date_range:
        file_date = date.strftime('%Y-%m-%d')

        try:
            result = client.get_object(Bucket=BUCKET, Key=FILE_TO_READ_PREFIX+file_date+'.json')
            data = pd.read_json(result['Body'], convert_axes=False)
            dataframes.append(data)
        except Exception as e:
            print(f"Error reading file for date {file_date}: {e}")

    dataframe = pd.concat(dataframes, ignore_index=True)
    leagues = client.get_object(Bucket=BUCKET, Key='leagues.csv')
    leagues_df = pd.read_csv(leagues['Body'])
    leagues_df = leagues_df[['league.id', 'country.name']]
    leagues_df = leagues_df.rename(columns={'league.id': 'League id', 'country.name': 'Country'})
    dataframe = dataframe.merge(leagues_df, on='League id', how='left')
    return dataframe

def upcoming_home_wins_ui():
    st.header("Upcoming Home Wins")

    @st.dialog("Info", width="large")
    def info_dialog():
        st.write("We do the homework for you, so you don't have to. We will show you a table of the home teams that are favourite to win at home along with lots of extra information for that match to make your decision easier. "
                "You can use the 'Home wins history' page to see the %s of wins for each category (Gold, Silver, Bronze).")

        st.write("I know this shows low odds, but adding them to an accumulator really helps. AI recommends 4 teams to get the best return on investments. "
                "If you were to bet the same amount every week through out the year, you should be winning more than losing and that is the whole point of this.")
        
        st.write("It isn't about making lots of money quickly, but rather to make money and not gamble it away. However, do note that any bets are at your own risk and they do go wrong.")
        
        st.write("You can filter the below table by date, league, category and more to find the matches that you are interested in. This list below will only ever show the upcoming favourite home wins for the next 8 days."
                 "If you want to see the history of home wins, you can go to the 'Home wins history' page.")
    
    if info_dialog not in st.session_state:
        st.button("How it works", on_click=info_dialog)

    # with open("json/ai/openai_response.json", "r") as file:
    #     ai_response = json.load(file)

    # @st.dialog("AI Prediction", width="large")
    # def ai_dialog():
    #     st.write(ai_response)

    # if ai_dialog not in st.session_state:
    #     st.button("AI Report and 4 team acca", on_click=ai_dialog)

    st.markdown("---")
    day = date.today()
    dataframe = import_json_files_as_dataframe(day)
    dataframe['Played'] = np.where(dataframe['Home goals'].isnull(), 0, 1)

    dataframe['Date'] = pd.to_datetime(dataframe['Date'])  # Convert 'Date' to datetime
    dataframe = dataframe[dataframe['Date'] > now_date]  # Compare with UTC now_date

    dataframe = dataframe.drop(columns='Fixture')

    dataframe['Home odd'] = pd.to_numeric(dataframe['Home odd'])
    dataframe['Draw odd'] = pd.to_numeric(dataframe['Draw odd'])
    dataframe['Away odd'] = pd.to_numeric(dataframe['Away odd'])


    dataframe['Expected home goals'] = pd.to_numeric(dataframe['Expected home goals']).round(2)
    dataframe['Expected away goals'] = pd.to_numeric(dataframe['Expected away goals']).round(2)

    categories = ['Gold', 'Silver', 'Bronze', 'Higher Odds']
    conditions = [
        ((dataframe['Draw odd'] >= 4) & (dataframe['Home odd'] < 1.4) & (dataframe['Expected home goals'] > 4.06) & (dataframe['Expected away goals'] < 0.72)),
        ((dataframe['Draw odd'] >= 8) & (dataframe['Home odd'] < 1.2) & (dataframe['Away odd'] > 11)),
        ((dataframe['Draw odd'] >= 7) & (dataframe['Home odd'] < 1.24) & (dataframe['Away odd'] > 10)),
        ((dataframe['Draw odd'] >= 4) & (dataframe['Expected home goals'] > 4) & (dataframe['Expected away goals'] < 0.72))]

    dataframe['Category'] = np.select(conditions, categories, default='other')

    dataframe = dataframe[dataframe['Category'] != 'other']

    dataframe = dataframe.rename(columns={'Home rank': 'H Pos', 'Away rank': 'A Pos', 'Home points': 'H Pts', 'Away points': 'A Pts', 'Home team form': 'H Form', 'Away team form': 'A Form'})

    dataframe = dataframe[['Date', 'H Pos', 'Home team', 'Away team', 'A Pos', 'League', 'Country', 'Category', 'Home odd', 'Draw odd', 'Away odd', 'Expected home goals', 
                           'Expected away goals', 'H Pts', 'A Pts', 'H Form', 'A Form']]

    filtered_df = dataframe_explorer(dataframe, case=False)
    st.markdown('##')

    filtered_df.sort_values(by='Date', ascending=True, inplace=True)

    st.dataframe(filtered_df, use_container_width=True, height=600, hide_index=True)

    button(username="brunop", floating=False, width=221)



def home_wins_history_ui():
    st.header("Home wins history")
    
    day = date.today()
    dataframe = import_json_files_as_dataframe(day)
    dataframe['Played'] = np.where(dataframe['Home goals'].isnull(), 0, 1)

    dataframe['Date'] = pd.to_datetime(dataframe['Date'])  # Convert 'Date' to datetime
    dataframe = dataframe[dataframe['Date'] < now_date]  # Compare with UTC now_date

    dataframe = dataframe.drop(columns='Fixture')

    dataframe['Home odd'] = pd.to_numeric(dataframe['Home odd'])
    dataframe['Draw odd'] = pd.to_numeric(dataframe['Draw odd'])
    dataframe['Away odd'] = pd.to_numeric(dataframe['Away odd'])

    dataframe['Expected home goals'] = pd.to_numeric(dataframe['Expected home goals']).round(2)
    dataframe['Expected away goals'] = pd.to_numeric(dataframe['Expected away goals']).round(2)

    categories = ['Gold', 'Silver', 'Bronze', 'Higher Odds']
    conditions = [
        ((dataframe['Draw odd'] >= 4) & (dataframe['Home odd'] < 1.4) & (dataframe['Expected home goals'] > 4.06) & (dataframe['Expected away goals'] < 0.72)),
        ((dataframe['Draw odd'] >= 8) & (dataframe['Home odd'] < 1.2) & (dataframe['Away odd'] > 11)),
        ((dataframe['Draw odd'] >= 7) & (dataframe['Home odd'] < 1.24) & (dataframe['Away odd'] > 10)),
        ((dataframe['Draw odd'] >= 4) & (dataframe['Expected home goals'] > 4) & (dataframe['Expected away goals'] < 0.72))]

    dataframe['Category'] = np.select(conditions, categories, default='other')

    dataframe = dataframe[dataframe['Category'] != 'other']

    dataframe = dataframe.rename(columns={'Home rank': 'H Pos', 'Away rank': 'A Pos', 'Home points': 'H Pts', 'Away points': 'A Pts', 'Home team form': 'H Form', 'Away team form': 'A Form'})

    dataframe['Result'] = np.where(dataframe['Home goals'] > dataframe['Away goals'], 'H', np.where(dataframe['Home goals'] < dataframe['Away goals'], 'A', 'D'))

    dataframe = dataframe[['Date', 'Result', 'Home team', 'Away team', 'League', 'Country', 'Season', 'Category', 'Home goals', 'Away goals', 'Home odd', 'Draw odd', 'Away odd', 'Expected home goals', 'Expected away goals', 'H Pos', 'A Pos', 'H Pts', 'A Pts', 'H Form', 'A Form']]


    filtered_df = dataframe_explorer(dataframe, case=False)
    st.markdown('##')

    number_of_matches = len(filtered_df)
    number_of_gold_matches = len(filtered_df[filtered_df['Category'] == 'Gold'])
    number_of_silver_matches = len(filtered_df[filtered_df['Category'] == 'Silver'])
    number_of_bronze_matches = len(filtered_df[filtered_df['Category'] == 'Bronze'])
    number_of_higher_odds_matches = len(filtered_df[filtered_df['Category'] == 'Higher Odds'])
    
    number_of_matches_won = len(filtered_df[filtered_df['Result'] == 'H'])
    number_of_gold_matches_won = len(filtered_df[(filtered_df['Category'] == 'Gold') & (filtered_df['Result'] == 'H')])
    number_of_silver_matches_won = len(filtered_df[(filtered_df['Category'] == 'Silver') & (filtered_df['Result'] == 'H')])
    number_of_bronze_matches_won = len(filtered_df[(filtered_df['Category'] == 'Bronze') & (filtered_df['Result'] == 'H')])
    number_of_higher_odds_matches_won = len(filtered_df[(filtered_df['Category'] == 'Higher Odds') & (filtered_df['Result'] == 'H')])

    col1, col2, col3, col4, col5 = st.columns(5)
    if number_of_matches > 0:
        col1.metric("Total home favourites", f"{number_of_matches_won / number_of_matches * 100:.2f}%", delta=f"{number_of_matches_won} of {number_of_matches}")
    else:
        col1.metric("Total home favourites", "0.00%", "0 of 0")
    if number_of_gold_matches > 0:
        col2.metric("Total Gold matches", f"{number_of_gold_matches_won / number_of_gold_matches * 100:.2f}%",f"{number_of_gold_matches_won} of {number_of_gold_matches}")
    else:
        col2.metric("Total Gold matches", "0.00%", "0 of 0")
    if number_of_silver_matches > 0:
        col3.metric("Total Silver matches", f"{number_of_silver_matches_won / number_of_silver_matches * 100:.2f}%", f"{number_of_silver_matches_won} of {number_of_silver_matches}")
    else:
        col3.metric("Total Silver matches", "0.00%", "0 of 0")
    if number_of_bronze_matches > 0:
        col4.metric("Total Bronze matches", f"{number_of_bronze_matches_won / number_of_bronze_matches * 100:.2f}%",f"{number_of_bronze_matches_won} of {number_of_bronze_matches}")
    else:
        col4.metric("Total Bronze matches", "0.00%", "0 of 0")
    if number_of_higher_odds_matches > 0:
        col5.metric("Total Higher Odds matches", f"{number_of_higher_odds_matches_won / number_of_higher_odds_matches * 100:.2f}%",f"{number_of_higher_odds_matches_won} of {number_of_higher_odds_matches}")
    else:
        col5.metric("Total Higher Odds matches", "0.00%", "0 of 0")

    style_metric_cards()

    filtered_df.sort_values(by='Date', ascending=False, inplace=True)
    
    
    def color_result(row):
        if row['Result'] == 'H':
            return ['background-color: #D7EED7'] * len(row)
        elif row['Result'] == 'D':
            return ['background-color: #FFCCCB'] * len(row)
        elif row['Result'] == 'A':
            return ['background-color: #FFCCCB'] * len(row)
        return [''] * len(row)

    styled_df = filtered_df.style.apply(color_result, axis=1)
    styled_df = styled_df.format({
        'Home odd': '{:.2f}',
        'Draw odd': '{:.2f}',
        'Away odd': '{:.2f}',
        'Home goals': '{:.0f}',
        'Away goals': '{:.0f}',
        'Expected home goals': '{:.2f}',
        'Expected away goals': '{:.2f}',
        'H Pos': '{:.0f}',
        'A Pos': '{:.0f}',
        'H Pts': '{:.0f}',
        'A Pts': '{:.0f}'
    })

    st.dataframe(styled_df, use_container_width=True, height=600, hide_index=True)

    # Group dataframe by league and calculate home win percentage
    league_stats = dataframe.groupby('League').agg({
        'Result': lambda x: (x == 'H').mean(),
        'Home team': 'count',  # Count total matches
        'Country': 'first'  # Get the first (and presumably only) country for each league
    }).reset_index()

    league_stats = league_stats[league_stats['Home team'] > 10]
    
    league_stats = league_stats.rename(columns={'Result': 'Home Win %', 'Home team': 'Matches'})
    league_stats['Home Win %'] = league_stats['Home Win %'] * 100

    league_stats = league_stats[['League', 'Country', 'Home Win %', 'Matches']]
    
    # Sort by home win percentage in descending order
    league_stats = league_stats.sort_values('Home Win %', ascending=False)
    
    # Display the league statistics
    st.subheader("Home Win Percentage by League")
    st.dataframe(league_stats.style.format({'Home Win %': '{:.2f}%'}), use_container_width=True, hide_index=True)

    # Optionally, create a bar chart
    fig = px.bar(league_stats, x='League', y='Home Win %', 
                 title='Home Win Percentage by League',
                 labels={'Home Win %': 'Home Win Percentage'})
    st.plotly_chart(fig, use_container_width=True)


    # Group dataframe by home team and calculate home win percentage
    hometeam_stats = dataframe.groupby('Home team').agg({
        'Result': lambda x: (x == 'H').mean(),
        'League': 'count',  # Count total matches
        'Country': 'first'  # Get the first (and presumably only) country for each league
    }).reset_index()

    hometeam_stats = hometeam_stats[hometeam_stats['League'] > 10]
    
    hometeam_stats = hometeam_stats.rename(columns={'Result': 'Home Win %', 'League': 'Matches'})
    hometeam_stats['Home Win %'] = hometeam_stats['Home Win %'] * 100

    hometeam_stats = hometeam_stats[['Home team', 'Country', 'Home Win %', 'Matches']]
    
    # Sort by home win percentage in descending order
    hometeam_stats = hometeam_stats.sort_values('Home Win %', ascending=False)
    # Display the league statistics
    st.subheader("Home Win Percentage by Home team")
    st.dataframe(hometeam_stats.style.format({'Home Win %': '{:.2f}%'}), use_container_width=True, hide_index=True)

    # Optionally, create a bar chart
    fig2 = px.bar(hometeam_stats, x='Home team', y='Home Win %', 
                 title='Home Win Percentage by Home team',
                 labels={'Home Win %': 'Home Win Percentage'})
    st.plotly_chart(fig2, use_container_width=True)


def upcoming_draws_ui():
    st.header("Upcoming Draws")

    day = date.today()
    dataframe = import_json_files_as_dataframe(day)
    dataframe['Played'] = np.where(dataframe['Home goals'].isnull(), 0, 1)

    dataframe['Date'] = pd.to_datetime(dataframe['Date'])  # Convert 'Date' to datetime
    dataframe = dataframe[dataframe['Date'] > now_date]  # Compare with UTC now_date

    dataframe = dataframe.drop(columns='Fixture')

    dataframe['Home odd'] = pd.to_numeric(dataframe['Home odd'])
    dataframe['Draw odd'] = pd.to_numeric(dataframe['Draw odd'])
    dataframe['Away odd'] = pd.to_numeric(dataframe['Away odd'])


    dataframe = dataframe[dataframe['Draw odd'] < 3.2]
    dataframe = dataframe[dataframe['Away odd'] < 3.5]
    dataframe = dataframe[dataframe['Home odd'] < 3.2]


    dataframe['Expected home goals'] = pd.to_numeric(dataframe['Expected home goals']).round(2)
    dataframe['Expected away goals'] = pd.to_numeric(dataframe['Expected away goals']).round(2)

    dataframe = dataframe.rename(columns={'Home rank': 'H Pos', 'Away rank': 'A Pos', 'Home points': 'H Pts', 'Away points': 'A Pts', 'Home team form': 'H Form', 'Away team form': 'A Form'})

    dataframe = dataframe[['Date', 'H Pos', 'Home team', 'Away team', 'A Pos', 'League', 'Country', 'Home odd', 'Draw odd', 'Away odd', 'Expected home goals', 
                           'Expected away goals', 'H Pts', 'A Pts', 'H Form', 'A Form']]

    filtered_df = dataframe_explorer(dataframe, case=False)
    st.markdown('##')

    filtered_df.sort_values(by='Date', ascending=True, inplace=True)

    st.dataframe(filtered_df, use_container_width=True, height=600, hide_index=True)


def draws_history_ui():
    st.header("Draws history")
    
    day = date.today()
    dataframe = import_json_files_as_dataframe(day)
    dataframe['Played'] = np.where(dataframe['Home goals'].isnull(), 0, 1)

    dataframe['Date'] = pd.to_datetime(dataframe['Date'])  # Convert 'Date' to datetime
    dataframe = dataframe[dataframe['Date'] < now_date]  # Compare with UTC now_date

    dataframe = dataframe.drop(columns='Fixture')

    dataframe['Home odd'] = pd.to_numeric(dataframe['Home odd'])
    dataframe['Draw odd'] = pd.to_numeric(dataframe['Draw odd'])
    dataframe['Away odd'] = pd.to_numeric(dataframe['Away odd'])

    dataframe = dataframe[dataframe['Draw odd'] < 3.2]
    dataframe = dataframe[dataframe['Away odd'] < 3.5]
    dataframe = dataframe[dataframe['Home odd'] < 3.2]

    # categories = ['Gold', 'Silver', 'Bronze']
    # conditions = [
    #     ((dataframe['Draw odd'] >= 7) & (dataframe['Home odd'] < 1.2) & (dataframe['Away odd'] > 10)),
    #     ((dataframe['Draw odd'] >= 6) & (dataframe['Home odd'] < 1.25) & (dataframe['Away odd'] > 9)),
    #     ((dataframe['Draw odd'] >= 5) & (dataframe['Home odd'] < 1.3) & (dataframe['Away odd'] > 8))]


    # dataframe['Category'] = np.select(conditions, categories, default='other')

    dataframe['Expected home goals'] = pd.to_numeric(dataframe['Expected home goals']).round(2)
    dataframe['Expected away goals'] = pd.to_numeric(dataframe['Expected away goals']).round(2)

    dataframe = dataframe.rename(columns={'Home rank': 'H Pos', 'Away rank': 'A Pos', 'Home points': 'H Pts', 'Away points': 'A Pts', 'Home team form': 'H Form', 'Away team form': 'A Form'})

    dataframe['Result'] = np.where(dataframe['Home goals'] > dataframe['Away goals'], 'H', np.where(dataframe['Home goals'] < dataframe['Away goals'], 'A', 'D'))

    dataframe = dataframe[['Date', 'Result', 'Home team', 'Away team', 'League', 'Country', 'Season', 'Home goals', 'Away goals', 'Home odd', 'Draw odd', 'Away odd', 'Expected home goals', 'Expected away goals', 'H Pos', 'A Pos', 'H Pts', 'A Pts', 'H Form', 'A Form']]


    filtered_df = dataframe_explorer(dataframe, case=False)
    st.markdown('##')

    number_of_matches = len(filtered_df)
    number_of_home_matches_won = len(filtered_df[filtered_df['Result'] == 'H'])
    number_of_draw_matches_won = len(filtered_df[filtered_df['Result'] == 'D'])
    number_of_away_matches_won = len(filtered_df[filtered_df['Result'] == 'A'])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total matches", f"{number_of_matches}")
    col2.metric("% games won at home", f"{number_of_home_matches_won / number_of_matches * 100:.2f}%")
    col3.metric("% draw", f"{number_of_draw_matches_won / number_of_matches * 100:.2f}%")
    col4.metric("% games won away", f"{number_of_away_matches_won / number_of_matches * 100:.2f}%")

    style_metric_cards()

    filtered_df.sort_values(by='Date', ascending=False, inplace=True)
    
    
    def color_result(row):
        if row['Result'] == 'D':
            return ['background-color: #D7EED7'] * len(row)
        elif row['Result'] == 'H':
            return ['background-color: #FFCCCB'] * len(row)
        elif row['Result'] == 'A':
            return ['background-color: #FFCCCB'] * len(row)
        return [''] * len(row)

    styled_df = filtered_df.style.apply(color_result, axis=1)
    styled_df = styled_df.format({
        'Home odd': '{:.2f}',
        'Draw odd': '{:.2f}',
        'Away odd': '{:.2f}',
        'Home goals': '{:.0f}',
        'Away goals': '{:.0f}',
        'Expected home goals': '{:.2f}',
        'Expected away goals': '{:.2f}',
        'H Pos': '{:.0f}',
        'A Pos': '{:.0f}',
        'H Pts': '{:.0f}',
        'A Pts': '{:.0f}'
    })

    st.dataframe(styled_df, use_container_width=True, height=600, hide_index=True)

    # Group dataframe by league and calculate home win percentage
    league_stats = dataframe.groupby('League').agg({
        'Result': lambda x: (x == 'D').mean(),
        'Home team': 'count',  # Count total matches
        'Country': 'first'  # Get the first (and presumably only) country for each league
    }).reset_index()

    league_stats = league_stats[league_stats['Home team'] > 3]
    
    league_stats = league_stats.rename(columns={'Result': 'Draw %', 'Home team': 'Matches'})
    league_stats['Draw %'] = league_stats['Draw %'] * 100

    league_stats = league_stats[['League', 'Country', 'Draw %', 'Matches']]
    
    # Sort by home win percentage in descending order
    league_stats = league_stats.sort_values('Draw %', ascending=False)
    
    # Display the league statistics
    st.subheader("Draw Percentage by League")
    st.dataframe(league_stats.style.format({'Draw %': '{:.2f}%'}), use_container_width=True, hide_index=True)

    # Optionally, create a bar chart
    fig = px.bar(league_stats, x='League', y='Draw %', 
                 title='Draw Percentage by League',
                 labels={'Draw %': 'Draw Percentage'})
    st.plotly_chart(fig, use_container_width=True)


    # # Group dataframe by home team and calculate home win percentage
    # hometeam_stats = dataframe.groupby('Home team').agg({
    #     'Result': lambda x: (x == 'D').mean(),
    #     'League': 'count',  # Count total matches
    #     'Country': 'first'  # Get the first (and presumably only) country for each league
    # }).reset_index()

    # hometeam_stats = hometeam_stats[hometeam_stats['League'] > 10]
    
    # hometeam_stats = hometeam_stats.rename(columns={'Result': 'Draw %', 'League': 'Matches'})
    # hometeam_stats['Draw %'] = hometeam_stats['Draw %'] * 100

    # hometeam_stats = hometeam_stats[['Home team', 'Country', 'Home Win %', 'Matches']]
    
    # # Sort by home win percentage in descending order
    # hometeam_stats = hometeam_stats.sort_values('Home Win %', ascending=False)
    # # Display the league statistics
    # st.subheader("Home Win Percentage by Home team")
    # st.dataframe(hometeam_stats.style.format({'Home Win %': '{:.2f}%'}), use_container_width=True, hide_index=True)

    # # Optionally, create a bar chart
    # fig2 = px.bar(hometeam_stats, x='Home team', y='Home Win %', 
    #              title='Home Win Percentage by Home team',
    #              labels={'Home Win %': 'Home Win Percentage'})
    # st.plotly_chart(fig2, use_container_width=True)


def upcoming_over_2_5_ui():
    st.header("Upcoming Over 2.5 goals")
    
    day = date.today()
    dataframe = import_json_files_as_dataframe(day)
    dataframe['Played'] = np.where(dataframe['Home goals'].isnull(), 0, 1)

    dataframe['Date'] = pd.to_datetime(dataframe['Date'])  # Convert 'Date' to datetime
    dataframe = dataframe[dataframe['Date'] > now_date]  # Compare with UTC now_date

    dataframe = dataframe.drop(columns='Fixture')

    dataframe['Home odd'] = pd.to_numeric(dataframe['Home odd'])
    dataframe['Draw odd'] = pd.to_numeric(dataframe['Draw odd'])
    dataframe['Away odd'] = pd.to_numeric(dataframe['Away odd'])

    dataframe['Expected home goals'] = pd.to_numeric(dataframe['Expected home goals']).round(2)
    dataframe['Expected away goals'] = pd.to_numeric(dataframe['Expected away goals']).round(2)

    dataframe['Expected total goals'] = dataframe['Expected home goals'] + dataframe['Expected away goals']
    dataframe['Expected goal difference'] = np.abs(dataframe['Expected home goals'] - dataframe['Expected away goals'])
    
    dataframe['Total goals'] = dataframe['Home goals'] + dataframe['Away goals']

    dataframe['Over 2.5'] = np.where(dataframe['Total goals'] > 2.5, 1, 0)

    #Filter out matches where expected total goals are less than 2.5
    dataframe = dataframe[dataframe['Expected total goals'] > 2.5]
    #Filter out matches where the expected goal difference is more than 3
    dataframe = dataframe[dataframe['Expected goal difference'] > 3]

    dataframe = dataframe.rename(columns={'Home rank': 'H Pos', 'Away rank': 'A Pos', 'Home points': 'H Pts', 'Away points': 'A Pts', 'Home team form': 'H Form', 'Away team form': 'A Form'})

    dataframe['Result'] = np.where(dataframe['Home goals'] > dataframe['Away goals'], 'H', np.where(dataframe['Home goals'] < dataframe['Away goals'], 'A', 'D'))

    dataframe = dataframe[['Date', 'Home team', 'Away team', 'League', 'Country', 'Season', 'Expected total goals', 'Expected home goals', 'Expected away goals']]


    filtered_df = dataframe_explorer(dataframe, case=False)
    st.markdown('##')

    filtered_df.sort_values(by='Date', ascending=True, inplace=True)

    st.dataframe(filtered_df, use_container_width=True, height=600, hide_index=True)


def over_2_5_history_ui():
    st.header("Over 2.5 goals history")
    
    day = date.today()
    dataframe = import_json_files_as_dataframe(day)
    dataframe['Played'] = np.where(dataframe['Home goals'].isnull(), 0, 1)

    dataframe['Date'] = pd.to_datetime(dataframe['Date'])  # Convert 'Date' to datetime
    dataframe = dataframe[dataframe['Date'] < now_date]  # Compare with UTC now_date

    dataframe = dataframe.drop(columns='Fixture')

    dataframe['Home odd'] = pd.to_numeric(dataframe['Home odd'])
    dataframe['Draw odd'] = pd.to_numeric(dataframe['Draw odd'])
    dataframe['Away odd'] = pd.to_numeric(dataframe['Away odd'])

    dataframe['Expected home goals'] = pd.to_numeric(dataframe['Expected home goals']).round(2)
    dataframe['Expected away goals'] = pd.to_numeric(dataframe['Expected away goals']).round(2)

    dataframe['Expected total goals'] = dataframe['Expected home goals'] + dataframe['Expected away goals']
    dataframe['Expected goal difference'] = np.abs(dataframe['Expected home goals'] - dataframe['Expected away goals'])
    
    dataframe['Total goals'] = dataframe['Home goals'] + dataframe['Away goals']

    dataframe['Over 2.5'] = np.where(dataframe['Total goals'] > 2.5, 1, 0)

    #Filter out matches where expected total goals are less than 2.5
    dataframe = dataframe[dataframe['Expected total goals'] > 2.5]
    #Filter out matches where the match was not played
    dataframe = dataframe[dataframe['Played'] == 1]
    #Filter out matches where the expected goal difference is more than 3
    dataframe = dataframe[dataframe['Expected goal difference'] > 3]

    dataframe = dataframe.rename(columns={'Home rank': 'H Pos', 'Away rank': 'A Pos', 'Home points': 'H Pts', 'Away points': 'A Pts', 'Home team form': 'H Form', 'Away team form': 'A Form'})

    dataframe['Result'] = np.where(dataframe['Home goals'] > dataframe['Away goals'], 'H', np.where(dataframe['Home goals'] < dataframe['Away goals'], 'A', 'D'))

    dataframe = dataframe[['Date', 'Result', 'Home team', 'Away team', 'League', 'Country', 'Season', 'Expected total goals', 'Total goals', 'Over 2.5', 'Home goals', 'Away goals', 'Home odd', 'Draw odd', 'Away odd', 'Expected home goals', 'Expected away goals', 'H Pos', 'A Pos', 'H Pts', 'A Pts', 'H Form', 'A Form']]


    filtered_df = dataframe_explorer(dataframe, case=False)
    st.markdown('##')

    number_of_matches = len(filtered_df)

    number_of_matches_expected_over_2_5 = len(filtered_df[filtered_df['Expected total goals'] > 2.5])
    
    number_of_matches_over_2_5 = len(filtered_df[filtered_df['Over 2.5'] == 1])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total matches", f"{number_of_matches}")
    col2.metric("Total Over 2.5 matches", f"{number_of_matches_over_2_5}")
    col3.metric("Total Expected Over 2.5 matches", f"{number_of_matches_expected_over_2_5}")
    col4.metric("Total Over 2.5 matches", f"{number_of_matches_over_2_5 / number_of_matches_expected_over_2_5 * 100:.2f}%", delta=f"{number_of_matches_over_2_5} of {number_of_matches_expected_over_2_5}")

    style_metric_cards()

    filtered_df.sort_values(by='Date', ascending=False, inplace=True)
    
    def color_result(row):
        if row['Over 2.5'] == 1:
            return ['background-color: #D7EED7'] * len(row)
        elif row['Over 2.5'] == 0:
            return ['background-color: #FFCCCB'] * len(row)
        return [''] * len(row)

    styled_df = filtered_df.style.apply(color_result, axis=1)
    styled_df = styled_df.format({
        'Home odd': '{:.2f}',
        'Draw odd': '{:.2f}',
        'Away odd': '{:.2f}',
        'Home goals': '{:.0f}',
        'Away goals': '{:.0f}',
        'Expected home goals': '{:.2f}',
        'Expected away goals': '{:.2f}',
        'Expected total goals': '{:.2f}',
        'Total goals': '{:.2f}',
        'H Pos': '{:.0f}',
        'A Pos': '{:.0f}',
        'H Pts': '{:.0f}',
        'A Pts': '{:.0f}'
    })

    st.dataframe(styled_df, use_container_width=True, height=600, hide_index=True)


def playground_ui():
    st.header("Playground")
    
    day = date.today()
    dataframe = import_json_files_as_dataframe(day)
    dataframe['Played'] = np.where(dataframe['Home goals'].isnull(), 0, 1)

    dataframe['Date'] = pd.to_datetime(dataframe['Date'])  # Convert 'Date' to datetime
    dataframe = dataframe[dataframe['Date'] < now_date]  # Compare with UTC now_date

    dataframe = dataframe.drop(columns='Fixture')

    dataframe['Home odd'] = pd.to_numeric(dataframe['Home odd'])
    dataframe['Draw odd'] = pd.to_numeric(dataframe['Draw odd'])
    dataframe['Away odd'] = pd.to_numeric(dataframe['Away odd'])

    dataframe['Expected home goals'] = pd.to_numeric(dataframe['Expected home goals']).round(2)
    dataframe['Expected away goals'] = pd.to_numeric(dataframe['Expected away goals']).round(2)

    dataframe['Expected total goals'] = dataframe['Expected home goals'] + dataframe['Expected away goals']
    dataframe['Expected goal difference'] = np.abs(dataframe['Expected home goals'] - dataframe['Expected away goals'])
    
    dataframe['Total goals'] = dataframe['Home goals'] + dataframe['Away goals']

    dataframe['Over 2.5'] = np.where(dataframe['Total goals'] > 2.5, 1, 0)

    categories = ['Gold', 'Silver', 'Bronze']
    conditions = [
        ((dataframe['Draw odd'] >= 4) & (dataframe['Home odd'] < 1.5) & (dataframe['Expected home goals'] > 4.06) & (dataframe['Expected away goals'] < 0.8)),
        ((dataframe['Draw odd'] >= 8) & (dataframe['Home odd'] < 1.2) & (dataframe['Away odd'] > 11)),
        ((dataframe['Draw odd'] >= 7) & (dataframe['Home odd'] < 1.22) & (dataframe['Away odd'] > 10))]


    dataframe['Category'] = np.select(conditions, categories, default='other')

    # Drop rows where 'Home goals' is null or NaN
    dataframe = dataframe.dropna(subset=['Home goals'])

    dataframe['Result'] = np.where(dataframe['Home goals'] > dataframe['Away goals'], 'H', np.where(dataframe['Home goals'] < dataframe['Away goals'], 'A', 'D'))

    dataframe = dataframe[['Date', 'Result', 'Home team', 'Away team', 'League', 'Country', 'Season', 'Category', 'Home goals', 'Away goals', 'Home odd', 'Draw odd', 'Away odd']]


    filtered_df = dataframe_explorer(dataframe, case=False)
    st.markdown('##')

    number_of_matches = len(filtered_df)
    number_of_home_matches_won = len(filtered_df[filtered_df['Result'] == 'H'])
    number_of_draw_matches_won = len(filtered_df[filtered_df['Result'] == 'D'])
    number_of_away_matches_won = len(filtered_df[filtered_df['Result'] == 'A'])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total home favourites", f"{number_of_matches}")
    col2.metric("Total Gold matches", f"{number_of_home_matches_won / number_of_matches * 100:.2f}%")
    col3.metric("Total Silver matches", f"{number_of_draw_matches_won / number_of_matches * 100:.2f}%")
    col4.metric("Total Bronze matches", f"{number_of_away_matches_won / number_of_matches * 100:.2f}%")

    style_metric_cards()

    filtered_df.sort_values(by='Date', ascending=False, inplace=True)

    st.dataframe(filtered_df, use_container_width=True, height=600, hide_index=True)

st.set_page_config(layout="wide")
home_wins_page = st.Page(upcoming_home_wins_ui, title="Home wins")
home_wins_history_page = st.Page(home_wins_history_ui, title="Home wins history")
draws_page = st.Page(upcoming_draws_ui, title="Draws (WIP)")
draw_history_page = st.Page(draws_history_ui, title="Draw history")
upcoming_over_2_5_page = st.Page(upcoming_over_2_5_ui, title="Over 2.5 (WIP)")
over_2_5_history_page = st.Page(over_2_5_history_ui, title="Over 2.5 history")
playground_page = st.Page(playground_ui, title="Playground")
pages = [home_wins_page, home_wins_history_page, draws_page, upcoming_over_2_5_page]
pg = st.navigation(pages)
pg.run()
