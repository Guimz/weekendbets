import pandas as pd
import numpy as np
import os
import json
import streamlit as st
from datetime import datetime, timezone
from streamlit_extras.dataframe_explorer import dataframe_explorer
from streamlit_extras.metric_cards import style_metric_cards

now_date = datetime.now(timezone.utc)  # Set now_date to UTC

def import_json_files_as_dataframe(folder_path):
    dataframes = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            with open(os.path.join(folder_path, filename), 'r') as f:
                data = json.load(f)
                df = pd.DataFrame(data)
                dataframes.append(df)
    return pd.concat(dataframes, ignore_index=True)


st.set_page_config(page_title="Home wins", layout="wide")

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

dataframe = dataframe[['Date', 'League', 'Home team', 'Home goals', 'Home odd', 'Draw odd', 'Away odd', 'Away goals', 'Away team', 'Category']]

st.header(f"Upcoming fixtures")


filtered_df = dataframe_explorer(dataframe, case=False)
st.markdown('##')

number_of_gold_matches = len(filtered_df[filtered_df['Category'] == 'Gold'])
number_of_silver_matches = len(filtered_df[filtered_df['Category'] == 'Silver'])
number_of_bronze_matches = len(filtered_df[filtered_df['Category'] == 'Bronze'])

# col1, col2, col3 = st.columns(3)
# col1.metric("Total Gold matches", f"{number_of_gold_matches}")
# col2.metric("Total Silver matches", f"{number_of_silver_matches}")
# col3.metric("Total Bronze matches", f"{number_of_bronze_matches}")

# style_metric_cards()

filtered_df = filtered_df.iloc[:, [0, 2, 8, 1, 9, 4, 5, 6]]

st.dataframe(filtered_df, use_container_width=True, height=600, hide_index=True)