#import the package and bring the content
import stockpyl
import pandas as pd
import streamlit as st
# bringing WW module from the stockpyl package and importing 
from stockpyl.wagner_whitin import wagner_whitin

st.title('Periodic Review (Wagner-Whitin Algorithm)')

# Input parameters
nbPeriods = st.number_input('Enter the number of periods:', min_value=1, max_value=20, value=5, step=1)
holdingCost = st.number_input('Enter the holding cost:', value=1.0, format="%.2f")
fixedCost = st.number_input('Enter the fixed ordering cost:', value=100.0, format="%.2f")

# Demand input using dataframe - dynamically create based on nbPeriods
period_list = list(range(1, int(nbPeriods) + 1))
demand_default = [10.0] * int(nbPeriods)  # Default demand of 10.0 for each period
df_demand = pd.DataFrame({'Period': period_list, 'Demand': demand_default})
edited_df_demand = st.data_editor(df_demand)
demand = edited_df_demand['Demand'].tolist()

# Calling the WW function with given parameters
if st.button('Calculate Periodic Review'):
    Q, cost, carriedCost, nextOrder = wagner_whitin(int(nbPeriods), holdingCost, fixedCost, demand)
    
    st.write(f'The total cost of inventory policy is: {cost:.2f}')
    
    # Display results in dataframes
    st.subheader('Order Quantities by Period')
    df_results = pd.DataFrame({
        'Period': list(range(0, int(nbPeriods))),
        'Quantity Ordered (Q)': [f"{q:.2f}" for q in Q]
    })
    st.dataframe(df_results)
    
    st.subheader('Cost Carried to Next Period')
    df_carried = pd.DataFrame({
        'Period': list(range(1, len(carriedCost))),
        'Carried Cost': [f"{c:.2f}" for c in carriedCost]
    })
    st.dataframe(df_carried)
    
    st.subheader('Next Order Period')
    df_nextorder = pd.DataFrame({
        'Period': list(range(0, len(nextOrder))),
        'Next Order Period': nextOrder
    })
    st.dataframe(df_nextorder)
