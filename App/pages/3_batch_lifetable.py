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
    data_list = []
    start_row = 0
    batch_size = 1000

    while True:
        response = supabase.table('PopulationData').select("*").range(start_row, start_row + batch_size - 1).execute()
        batch_data = response.data
        
        if not batch_data:
            break
        
        data_list.extend(batch_data)
        start_row += batch_size
    
    return pd.DataFrame(data_list)

def calculate_life_table(deaths, population):
    """Calculate life table from deaths and population data"""
    df = pd.DataFrame({
        'Age': ['<1 year', '12-23 months', '2-4 years', '5-9 years', '10-14 years', '15-19 years', '20-24 years', 
                '25-29 years', '30-34 years', '35-39 years', '40-44 years', '45-49 years', '50-54 years', 
                '55-59 years', '60-64 years', '65-69 years', '70-74 years', '75-79 years', '80-84 years', 
                '85-89 years', '90-94 years', '95+ years'],
        'Years in Interval (n)': [1, 1, 3, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 0],
        'Deaths (nDx)': deaths,
        'Reported Population (nNx)': population
    })

    df['Mortality Rate (nmx)'] = df['Deaths (nDx)'] / df['Reported Population (nNx)']
    
    df['Linearity Adjustment (nax)'] = 0.5
    df.loc[0, 'Linearity Adjustment (nax)'] = 0.1
    df.loc[1, 'Linearity Adjustment (nax)'] = 0.3
    df.loc[2, 'Linearity Adjustment (nax)'] = 0.4

    df['Probability of Dying (nqx)'] = df['Years in Interval (n)'] * df['Mortality Rate (nmx)'] / \
                                       (1 + (1 - df['Linearity Adjustment (nax)']) * df['Mortality Rate (nmx)']*df['Years in Interval (n)'])
    
    df['Probability of Surviving (npx)'] = 1 - df['Probability of Dying (nqx)']
    
    df['Individuals Surviving (lx)'] = 100000
    for i in range(1, len(df)):
        df.loc[i, 'Individuals Surviving (lx)'] = df.loc[i - 1, 'Individuals Surviving (lx)'] * df.loc[i - 1, 'Probability of Surviving (npx)']
    
    df['Deaths in Interval (ndx)'] = df['Individuals Surviving (lx)'] * df['Probability of Dying (nqx)']
    df.at[len(df)-1, 'Deaths in Interval (ndx)'] = df.at[len(df)-1, 'Individuals Surviving (lx)']

    df['Years Lived in Interval (nLx)'] = df['Years in Interval (n)'] * ((df['Individuals Surviving (lx)'] + df['Individuals Surviving (lx)'].shift(-1)) / 2)
    df.at[0, 'Years Lived in Interval (nLx)'] = df.at[0,'Years in Interval (n)'] * (df.at[1, 'Individuals Surviving (lx)'] + (df.at[0, 'Linearity Adjustment (nax)'] * df.at[0, 'Deaths in Interval (ndx)'])) 
    df.at[1, 'Years Lived in Interval (nLx)'] = df.at[1, 'Years in Interval (n)'] * (df.at[2, 'Individuals Surviving (lx)'] + (df.at[1, 'Linearity Adjustment (nax)'] * df.at[1, 'Deaths in Interval (ndx)'])) 
    df.at[2, 'Years Lived in Interval (nLx)'] = df.at[2, 'Years in Interval (n)'] * (df.at[3, 'Individuals Surviving (lx)'] + (df.at[2, 'Linearity Adjustment (nax)'] * df.at[2, 'Deaths in Interval (ndx)']))
    df.at[len(df)-1, 'Years Lived in Interval (nLx)'] = df.at[len(df)-1, 'Individuals Surviving (lx)'] / df.at[len(df)-1, 'Mortality Rate (nmx)']
    
    df['Cumulative Years Lived (Tx)'] = df['Years Lived in Interval (nLx)'][::-1].cumsum()[::-1]
    
    df['Expectancy of Life at Age x (ex)'] = df['Cumulative Years Lived (Tx)'] / df['Individuals Surviving (lx)']
    
    return df

# New Streamlit page for multiple life tables
st.title('Multiple Life Table Calculator')

# Load data from Supabase
df = load_data()

# Define the correct order of age groups
age_order = ['<1 year', '12-23 months', '2-4 years', '5-9 years', '10-14 years', '15-19 years', 
             '20-24 years', '25-29 years', '30-34 years', '35-39 years', '40-44 years', 
             '45-49 years', '50-54 years', '55-59 years', '60-64 years', '65-69 years', 
             '70-74 years', '75-79 years', '80-84 years', '85-89 years', '90-94 years', '95+ years']

df['age_name'] = pd.Categorical(df['age_name'], categories=age_order, ordered=True)
df = df.sort_values('age_name')

# User selections for multiple years, country, and gender
selected_years = st.sidebar.multiselect('Select Years', df['year'].unique())
selected_country = st.sidebar.selectbox('Select Country', df['location_name'].unique())
selected_gender = st.sidebar.selectbox('Select Gender', df['sex_name'].unique())

if st.button('Calculate and Save Life Tables'):
    if selected_years:
        # Create an Excel writer
        with pd.ExcelWriter('life_tables.xlsx') as writer:
            life_tables = {}
            for year in selected_years:
                filtered_df = df[
                    (df['year'] == year) &
                    (df['location_name'] == selected_country) &
                    (df['sex_name'] == selected_gender)
                ]

                if not filtered_df.empty:
                    deaths = filtered_df['total_deaths'].tolist()
                    population = filtered_df['population'].tolist()

                    life_table = calculate_life_table(deaths, population)
                    life_tables[year] = life_table

                    # Write each life table to a different sheet
                    life_table.to_excel(writer, sheet_name=str(year), index=False)
                else:
                    st.write(f"No data available for {selected_country} ({selected_gender}) in {year}")

        # Display CSV data on the front end
        for year, life_table in life_tables.items():
            st.write(f"Life Table for {selected_country} ({selected_gender}) in {year}")
            st.dataframe(life_table)

        # Provide download link for the Excel file
        with open('life_tables.xlsx', 'rb') as file:
            st.download_button(
                label="Download Life Tables",
                data=file,
                file_name='life_tables.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
    else:
        st.write("Please select at least one year.")
