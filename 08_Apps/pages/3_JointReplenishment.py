#import the package and bring the content
import stockpyl

import streamlit as st

# bringing eoq module from the stockpyl package and importing the joint replenishment function of the module
from stockpyl.eoq import joint_replenishment_problem_silver_heuristic

st.title('Joint Replenishment Optimizer (Silver\'s Heuristic)')

shared_fixed_cost = st.number_input('Enter the shared fixed ordering cost:', value=600.0, format="%.2f")
individual_fixed_costs = st.number_input('Enter the individual fixed ordering costs:', value=[120.0, 840.0, 300.0], format="%.2f")
holding_costs = st.number_input('Enter the holding costs:', value=[160.0, 20.0, 50.0], format="%.2f")
demand_rates = st.number_input('Enter the demand rates:', value=[1.0, 1.0, 1.0], format="%.2f")



# Calling the Solver's function with given parameters

Q,T,m_n,cost=joint_replenishment_problem_silver_heuristic(shared_fixed_cost,individual_fixed_costs,holding_costs,demand_rates)
st.write(f'Order quantities are: {Q}')
st.write(f'Order cycle time is: {T}')
st.write(f'Order multiples is: {m_n}')
st.write(f'The total cost is: {cost}')