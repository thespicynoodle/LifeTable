import streamlit as st
import os
from dotenv import load_dotenv
import pandas as pd
from supabase import create_client, Client

load_dotenv()

# Supabase credentials
url = os.getenv("PROJECT_URL")
key = os.getenv("SECRET_PROJECT_API_KEY")

# Initialize Supabase client
supabase: Client = create_client(url, key)


def load_data():
    """Fetch data from Supabase table 'LifeTables' with pagination"""
    # Initialize an empty list to hold all data
    data_list = []
    
    # Fetch data in chunks to avoid hitting any row limits
    start_row = 0
    batch_size = 1000  # Adjust the batch size if needed
    
    while True:
        response = supabase.table('PopulationData').select("*").range(start_row, start_row + batch_size - 1).execute()
        batch_data = response.data
        
        # If no more data is fetched, break the loop
        if not batch_data:
            break
        
        # Append fetched batch data to the list
        data_list.extend(batch_data)
        start_row += batch_size
    
    # Convert the list of data to a DataFrame
    return pd.DataFrame(data_list)

# Load data from Supabase
df = load_data()
st.set_page_config(layout="wide")
st.title('Data Viewer')


# Debugging: Display unique countries
#st.sidebar.write(f"Unique countries in data: {df['location_name'].unique()}")

# Create multi-select filters for year, age, gender, and country
years = df['year'].unique()
ages = df['age_name'].unique()
genders = df['sex_name'].unique()
countries = df['location_name'].unique()

selected_years = st.sidebar.multiselect('Select Year(s)', years, default=years)
selected_ages = st.sidebar.multiselect('Select Age Group(s)', ages, default=ages)
selected_genders = st.sidebar.multiselect('Select Gender(s)', genders, default=genders)
selected_countries = st.sidebar.multiselect('Select Country(ies)', countries, default=countries)

# Filter data based on selections
filtered_df = df[
    (df['year'].isin(selected_years)) &
    (df['age_name'].isin(selected_ages)) &
    (df['sex_name'].isin(selected_genders)) &
    (df['location_name'].isin(selected_countries))
]

# Display the filtered dataframe in wide format
st.dataframe(filtered_df)
