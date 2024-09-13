import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Supabase credentials
url = os.getenv("PROJECT_URL")
key = os.getenv("SECRET_PROJECT_API_KEY")

# Initialize Supabase client
supabase: Client = create_client(url, key)

# Load data function
def load_data():
    """Fetch data from Supabase table 'PopulationData'."""
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

# Life table calculation
def calculate_life_table(deaths, population):
    """Calculate life table from deaths and population data."""
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
    
    # Add linearly adjusted probabilities
    df['Linearity Adjustment (nax)'] = 0.5
    df.loc[0, 'Linearity Adjustment (nax)'] = 0.1
    df.loc[1, 'Linearity Adjustment (nax)'] = 0.3
    df.loc[2, 'Linearity Adjustment (nax)'] = 0.4

    df['Probability of Dying (nqx)'] = df['Years in Interval (n)'] * df['Mortality Rate (nmx)'] / \
                                       (1 + (1 - df['Linearity Adjustment (nax)']) * df['Mortality Rate (nmx)'] * df['Years in Interval (n)'])
    
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

# Decomposition calculation
def calculate_life_expectancy_contribution(life_table_1, life_table_2):
    """Calculate the contribution of each age group to life expectancy difference between two years."""
    # Ensure that the dataframes are aligned on age groups
    if not (life_table_1['Age'].equals(life_table_2['Age'])):
        raise ValueError("Age groups in the two life tables must match")

    contributions = []

    for i in range(len(life_table_1)):
        if i == len(life_table_1) - 1:  # Last age group (open-ended)
            delta_x = (life_table_1.loc[i, 'Individuals Surviving (lx)'] / life_table_1.loc[0, 'Individuals Surviving (lx)']) * \
                      (life_table_2.loc[i, 'Cumulative Years Lived (Tx)'] / life_table_2.loc[i, 'Individuals Surviving (lx)'] - \
                       life_table_1.loc[i, 'Cumulative Years Lived (Tx)'] / life_table_1.loc[i, 'Individuals Surviving (lx)'])
        else:
            # First term
            first_term = (life_table_1.loc[i, 'Individuals Surviving (lx)'] / life_table_1.loc[0, 'Individuals Surviving (lx)']) * \
                         (life_table_2.loc[i, 'Years Lived in Interval (nLx)'] / life_table_2.loc[i, 'Individuals Surviving (lx)'] - \
                          life_table_1.loc[i, 'Years Lived in Interval (nLx)'] / life_table_1.loc[i, 'Individuals Surviving (lx)'])
            
            # Second term
            second_term = (life_table_2.loc[i+1, 'Cumulative Years Lived (Tx)'] / life_table_1.loc[0, 'Individuals Surviving (lx)']) * \
                          ((life_table_1.loc[i, 'Individuals Surviving (lx)'] / life_table_2.loc[i, 'Individuals Surviving (lx)']) - \
                           (life_table_1.loc[i+1, 'Individuals Surviving (lx)'] / life_table_2.loc[i+1, 'Individuals Surviving (lx)']))
            
            delta_x = first_term + second_term

        contributions.append(delta_x)

    # Create a DataFrame for the contributions
    contribution_df = pd.DataFrame({
        'Age': life_table_1['Age'],
        'Contribution to LE difference (years)': contributions
    })

    # Add a row for the sum of contributions
    total_contribution = sum(contributions)
    total_row = pd.DataFrame({
        'Age': ['Life expectancy difference'],
        'Contribution to LE difference (years)': [total_contribution]
    })
    contribution_df = pd.concat([contribution_df, total_row], ignore_index=True)

    return contribution_df

# Streamlit app logic
st.title('Life Expectancy Decomposition Tool')

# Load the data from Supabase
df = load_data()

# Check if data is loaded properly
if df.empty:
    st.error("No data loaded from Supabase.")
else:
    st.success("Data successfully loaded.")

# User selection
selected_years = st.sidebar.multiselect('Select Years', df['year'].unique(), default=None)
selected_country = st.sidebar.selectbox('Select Country', df['location_name'].unique(), index=0)
selected_gender = st.sidebar.selectbox('Select Gender', df['sex_name'].unique(), index=0)

if st.button('Calculate Life Expectancy Difference Decomposition'):
    if len(selected_years) == 2:
        # Filter data for the selected country, gender, and years
        filtered_df_1 = df[
            (df['year'] == selected_years[0]) &
            (df['location_name'] == selected_country) &
            (df['sex_name'] == selected_gender)
        ]
        filtered_df_2 = df[
            (df['year'] == selected_years[1]) &
            (df['location_name'] == selected_country) &
            (df['sex_name'] == selected_gender)
        ]

        # Display the filtered data
        st.write(f"Filtered Data for {selected_years[0]}:")
        st.dataframe(filtered_df_1)
        st.write(f"Filtered Data for {selected_years[1]}:")
        st.dataframe(filtered_df_2)

        if filtered_df_1.empty or filtered_df_2.empty:
            st.error("No data available for the selected filters.")
        else:
            # Calculate life tables for both years
            life_table_1 = calculate_life_table(filtered_df_1['total_deaths'].tolist(), filtered_df_1['population'].tolist())
            life_table_2 = calculate_life_table(filtered_df_2['total_deaths'].tolist(), filtered_df_2['population'].tolist())

            # Display the life tables
            st.write(f"Life Table for {selected_years[0]}:")
            st.dataframe(life_table_1)
            st.write(f"Life Table for {selected_years[1]}:")
            st.dataframe(life_table_2)

            # Calculate the contribution to the life expectancy difference
            le_contributions = calculate_life_expectancy_contribution(life_table_1, life_table_2)

            # Display the decomposition results
            st.write(f"Life Expectancy Contribution by Age Group ({selected_years[0]} vs {selected_years[1]}):")
            st.dataframe(le_contributions)
    else:
        st.warning("Please select exactly two years for decomposition.")
