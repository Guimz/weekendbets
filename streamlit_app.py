import pandas as pd
import numpy as np
import os
import json
import streamlit as st
from datetime import datetime, timezone
from streamlit_extras.dataframe_explorer import dataframe_explorer
from streamlit_extras.metric_cards import style_metric_cards

now_date = datetime.now(timezone.utc)  # Set now_date to UTC

def result_colour(val):
    color = '#D7EED7' if val == 'H' else '#FFCCCB'
    return f"color: {color}"

@st.cache_data
def import_json_files_as_dataframe(folder_path):
    dataframes = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            with open(os.path.join(folder_path, filename), 'r') as f:
                data = json.load(f)
                df = pd.DataFrame(data)
                dataframes.append(df)
    return pd.concat(dataframes, ignore_index=True)

def upcoming_home_wins_ui():
    st.header("Upcoming Home Wins")

    st.write("This page shows upcoming home teams that are favourites to win, based on the odds from various bookmakers. The idea behind this is that we do the homework for you, so you don't have to. "
             "The categories are based on historical data that we have narrowed down certain type of matches that have occured in the past and the % each of those scenarios have won. "
             "This ensures that by selecting games that fall into these categories, you are more likely to find value in the bets you make. As we move forward, we will be adding more details to each match to show "
             "league positions, form, attacking and defensive strength of the teams, all of which will have a score and based on this, we will be able to show you which fixtures have the higher chance of winning."
             "This is a work in progress but we hope you find this useful even as it is and continues to grow.")
    # st.write("The categories are based on historical data that we have narrowed down certain type of matches that have occured in the past and the % each of those scenarios have won.")
    # st.write("This ensures that by selecting games that fall into these categories, you are more likely to find value in the bets you make.")
    # st.write("As we move forward, we will be adding more details to each match to show league positions, form, attacking and defensive strength of the teams, all of which will have a score and based on this, we will be able to show you which fixtures have the higher chance of winning.")
    # st.write("This is a work in progress but we hope you find this useful even as it is and continues to grow.")

    st.write("You can filter the below table by date, league, category and more to find the matches that you are interested in. This list below will only ever show the upcoming favourite home wins for the next 8 days."
             "If you want to see the history of home wins, you can go to the 'Home wins history' page.")

    st.markdown("---")

    dataframe = import_json_files_as_dataframe('json/transformed/fixtures_with_odds')
    dataframe['Played'] = np.where(dataframe['Home goals'].isnull(), 0, 1)

    dataframe['Date'] = pd.to_datetime(dataframe['Date'])  # Convert 'Date' to datetime
    dataframe = dataframe[dataframe['Date'] > now_date]  # Compare with UTC now_date

    dataframe = dataframe.drop(columns='Fixture')

    dataframe['Home odd'] = pd.to_numeric(dataframe['Home odd'])
    dataframe['Draw odd'] = pd.to_numeric(dataframe['Draw odd'])
    dataframe['Away odd'] = pd.to_numeric(dataframe['Away odd'])


    dataframe = dataframe[dataframe['Draw odd'] >= 5]  # filter out fixtures with a draw odd of below 5
    dataframe = dataframe[dataframe['Away odd'] > 8]  # filter out fixtures with a away odd of below 8
    dataframe = dataframe[dataframe['Home odd'] < 1.3]  # filter out fixtures with a home odd of above 1.3

    categories = ['Gold', 'Silver', 'Bronze']
    conditions = [
        ((dataframe['Draw odd'] >= 7) & (dataframe['Home odd'] < 1.2) & (dataframe['Away odd'] > 10)),
        ((dataframe['Draw odd'] >= 6) & (dataframe['Home odd'] < 1.25) & (dataframe['Away odd'] > 9)),
        ((dataframe['Draw odd'] >= 5) & (dataframe['Home odd'] < 1.3) & (dataframe['Away odd'] > 8))]


    dataframe['Category'] = np.select(conditions, categories, default='other')

    dataframe = dataframe[['Date', 'Home team', 'Away team', 'League', 'Category', 'Home odd', 'Draw odd', 'Away odd']]

    filtered_df = dataframe_explorer(dataframe, case=False)
    st.markdown('##')

    filtered_df.sort_values(by='Date', ascending=True, inplace=True)

    st.dataframe(filtered_df, use_container_width=True, height=600, hide_index=True)


def home_wins_history_ui():
    st.header("Home wins history")

    dataframe = import_json_files_as_dataframe('json/transformed/fixtures_with_odds')
    dataframe['Played'] = np.where(dataframe['Home goals'].isnull(), 0, 1)

    dataframe['Date'] = pd.to_datetime(dataframe['Date'])  # Convert 'Date' to datetime
    dataframe = dataframe[dataframe['Date'] < now_date]  # Compare with UTC now_date

    dataframe = dataframe.drop(columns='Fixture')

    dataframe['Home odd'] = pd.to_numeric(dataframe['Home odd'])
    dataframe['Draw odd'] = pd.to_numeric(dataframe['Draw odd'])
    dataframe['Away odd'] = pd.to_numeric(dataframe['Away odd'])

    dataframe = dataframe[dataframe['Draw odd'] >= 5]  # filter out fixtures with a draw odd of below 5
    dataframe = dataframe[dataframe['Away odd'] > 8]  # filter out fixtures with a away odd of below 8
    dataframe = dataframe[dataframe['Home odd'] < 1.3]  # filter out fixtures with a home odd of above 1.3

    categories = ['Gold', 'Silver', 'Bronze']
    conditions = [
        ((dataframe['Draw odd'] >= 7) & (dataframe['Home odd'] < 1.2) & (dataframe['Away odd'] > 10)),
        ((dataframe['Draw odd'] >= 6) & (dataframe['Home odd'] < 1.25) & (dataframe['Away odd'] > 9)),
        ((dataframe['Draw odd'] >= 5) & (dataframe['Home odd'] < 1.3) & (dataframe['Away odd'] > 8))]


    dataframe['Category'] = np.select(conditions, categories, default='other')

    dataframe['Result'] = np.where(dataframe['Home goals'] > dataframe['Away goals'], 'H', np.where(dataframe['Home goals'] < dataframe['Away goals'], 'A', 'D'))

    dataframe = dataframe[['Date', 'Result', 'Home team', 'Away team', 'League', 'Category', 'Home goals', 'Away goals', 'Home odd', 'Draw odd', 'Away odd']]


    filtered_df = dataframe_explorer(dataframe, case=False)
    st.markdown('##')

    number_of_matches = len(filtered_df)
    number_of_gold_matches = len(filtered_df[filtered_df['Category'] == 'Gold'])
    number_of_silver_matches = len(filtered_df[filtered_df['Category'] == 'Silver'])
    number_of_bronze_matches = len(filtered_df[filtered_df['Category'] == 'Bronze'])
    
    number_of_matches_won = len(filtered_df[filtered_df['Result'] == 'H'])
    number_of_gold_matches_won = len(filtered_df[(filtered_df['Category'] == 'Gold') & (filtered_df['Result'] == 'H')])
    number_of_silver_matches_won = len(filtered_df[(filtered_df['Category'] == 'Silver') & (filtered_df['Result'] == 'H')])
    number_of_bronze_matches_won = len(filtered_df[(filtered_df['Category'] == 'Bronze') & (filtered_df['Result'] == 'H')])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total home favourites", f"{number_of_matches_won / number_of_matches * 100:.2f}%", delta=f"{number_of_matches_won} of {number_of_matches}")
    col2.metric("Total Gold matches", f"{number_of_gold_matches_won / number_of_gold_matches * 100:.2f}%",f"{number_of_gold_matches_won} of {number_of_gold_matches}")
    col3.metric("Total Silver matches", f"{number_of_silver_matches_won / number_of_silver_matches * 100:.2f}%",f"{number_of_silver_matches_won} of {number_of_silver_matches}")
    col4.metric("Total Bronze matches", f"{number_of_bronze_matches_won / number_of_bronze_matches * 100:.2f}%",f"{number_of_bronze_matches_won} of {number_of_bronze_matches}")

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
        'Away goals': '{:.0f}'
    })

    st.dataframe(styled_df, use_container_width=True, height=600, hide_index=True)

st.set_page_config(layout="wide")
home_wins_page = st.Page(upcoming_home_wins_ui, title="Home wins")
home_wins_history_page = st.Page(home_wins_history_ui, title="Home wins history")
pages = [home_wins_page, home_wins_history_page]
pg = st.navigation(pages)
pg.run()
