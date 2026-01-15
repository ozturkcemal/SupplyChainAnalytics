#import the package and bring the content
import stockpyl
import pandas as pd
import streamlit as st

# bringing eoq module from the stockpyl package and importing the joint replenishment function of the module
from stockpyl.eoq import joint_replenishment_problem_silver_heuristic

st.title('Joint Replenishment Optimizer (Silver\'s Heuristic)')

# Shared fixed cost input
shared_fixed_cost = st.number_input('Enter the shared fixed ordering cost:', value=600.0, format="%.2f")

# Individual fixed costs
df = pd.DataFrame({'Individual Fixed Costs': [120.0, 840.0, 300.0]})
edited_df = st.data_editor(df)
individual_fixed_costs = edited_df['Individual Fixed Costs'].tolist()

# Individual holding costs
df2 = pd.DataFrame({'Individual Holding Costs': [160.0, 20.0, 50.0]})
edited_df2 = st.data_editor(df2)
individual_holding_costs = edited_df2['Individual Holding Costs'].tolist()

# Individual demand rates
df3 = pd.DataFrame({'Individual Demand Rates': [1.0, 1.0, 1.0]})  # Fixed: 1.0.0 -> 1.0
edited_df3 = st.data_editor(df3)
demand_rates = edited_df3['Individual Demand Rates'].tolist()  # Fixed: edited_df -> edited_df3 and column name

# Calling the Solver's function with given parameters
Q, T, m_n, cost = joint_replenishment_problem_silver_heuristic(
    shared_fixed_cost, 
    individual_fixed_costs, 
    individual_holding_costs,  # Fixed: holding_costs -> individual_holding_costs
    demand_rates
)

if st.button('Calculate Joint Replenishment'):
    st.write(f'Order quantities are: [{", ".join([f"{q:.2f}" for q in Q])}]')
    st.write(f'Order cycle time is: {T:.2f}') 
    st.write(f'Order multiples is: {m_n}')
    st.write(f'The total cost is: {cost:.2f}')

