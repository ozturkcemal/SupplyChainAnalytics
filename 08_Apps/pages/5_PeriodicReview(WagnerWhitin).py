#import the package and bring the content
import stockpyl
import pandas as pd
import streamlit as st
# bringing WW module from the stockpyl package and importing 
from stockpyl.wagner_whitin import wagner_whitin

st.title('Periodic Review (Wagner-Whitin Algorithm)')

# Input parameters
holdingCost = st.number_input('Enter the holding cost:', value=1.0, format="%.2f")
fixedCost = st.number_input('Enter the fixed ordering cost:', value=100.0, format="%.2f")

# Demand input using dataframe
df_demand = pd.DataFrame({'Period': [1, 2, 3, 4, 5], 'Demand': [10.0, 20.0, 30.0, 15.0, 25.0]})
edited_df_demand = st.data_editor(df_demand)
demand = edited_df_demand['Demand'].tolist()
nbPeriods = len(demand)

# Calling the Solver's function with given parameters
if st.button('Calculate Periodic Review'):
    Q, cost, carriedCost, nextOrder = wagner_whitin(nbPeriods, holdingCost, fixedCost, demand)
    
    st.write(f'The total cost of inventory policy is: {cost:.2f}')
    
    # Display results in dataframes
    st.subheader('Order Quantities by Period')
    df_results = pd.DataFrame({
        'Period': list(range(1, nbPeriods + 1)),
        'Quantity Ordered (Q)': [f"{q:.2f}" for q in Q]
    })
    st.dataframe(df_results)
    
    st.subheader('Cost Carried to Next Period')
    df_carried = pd.DataFrame({
        'Period': list(range(1, len(carriedCost) + 1)),
        'Carried Cost': [f"{c:.2f}" for c in carriedCost]
    })
    st.dataframe(df_carried)
    
    st.subheader('Next Order Period')
    df_nextorder = pd.DataFrame({
        'Period': list(range(1, len(nextOrder) + 1)),
        'Next Order Period': nextOrder
    })
    st.dataframe(df_nextorder)
