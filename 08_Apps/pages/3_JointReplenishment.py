#import the package and bring the content
import stockpyl
import pandas as pd
import streamlit as st

# bringing eoq module from the stockpyl package and importing the joint replenishment function of the module
from stockpyl.eoq import joint_replenishment_problem_silver_heuristic

st.title('Joint Replenishment Optimizer (Silver\'s Heuristic)')

# Shared fixed cost input
shared_fixed_cost = st.number_input('Enter the shared fixed ordering cost:', value=600.0, format="%.2f")

st.subheader('Item Parameters')
# Consolidated item data
default_data = {
    'Fixed Cost': [120.0, 840.0, 300.0],
    'Holding Cost': [160.0, 20.0, 50.0],
    'Demand Rate': [1.0, 1.0, 1.0]
}
df = pd.DataFrame(default_data)

# Single dynamic data editor
edited_df = st.data_editor(
    df, 
    num_rows="dynamic", 
    use_container_width=True,
    column_config={
        "Fixed Cost": st.column_config.NumberColumn(format="%.2f"),
        "Holding Cost": st.column_config.NumberColumn(format="%.2f"),
        "Demand Rate": st.column_config.NumberColumn(format="%.2f"),
    }
)

# Extracting individual lists from the consolidated table
individual_fixed_costs = edited_df['Fixed Cost'].tolist()
individual_holding_costs = edited_df['Holding Cost'].tolist()
demand_rates = edited_df['Demand Rate'].tolist()

if st.button('Calculate Joint Replenishment'):
    # Calling the Solver's function with given parameters
    Q, T, m_n, cost = joint_replenishment_problem_silver_heuristic(
        shared_fixed_cost, 
        individual_fixed_costs, 
        individual_holding_costs,
        demand_rates
    )
    
    st.markdown("### Results")
    st.write(f'**Order quantities (Q):** {", ".join([f"{q:.2f}" for q in Q])}')
    st.write(f'**Order cycle time (T):** {T:.2f}') 
    st.write(f'**Order multiples (m_n):** {m_n}')
    st.write(f'**The total cost:** {cost:.2f}')

st.markdown("---")
st.markdown("**References**")
st.markdown(
    "[1] Silver, Edward A. 1976. *Joint Replenishment Optimizer*. Management Science 22(12):1351-1361. "
    "Available at: https://pubsonline.informs.org/doi/abs/10.1287/mnsc.22.12.1351"
)
st.markdown(
    "[2] Snyder, Lawrence V. 2023. *Stockpyl*. GitHub repository. "
    "Available at: https://github.com/LarrySnyder/stockpyl"
)