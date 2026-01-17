#import the package and bring the content
import stockpyl

import streamlit as st

# bringing eoq module from the stockpyl package and importing the economic_order_quantity function of the module
from stockpyl.eoq import economic_order_quantity_with_backorders

st.title('Economic Order Quantity (EOQ) with Backorders Calculator')

# Providing parameters; fixed cost, holding cost and demand rate of the instance
fixedCost=st.number_input('Enter the fixed ordering cost:', value=15.0, format="%.2f")
holdingCost=st.number_input('Enter the holding cost:', value=4.0, format="%.2f")
demandRate=st.number_input('Enter the demand rate:', value=12.0, format="%.2f")
stockOutCost=st.number_input('Enter the stock out cost:', value=20.0, format="%.2f")


# Calling the EOQ function with given parameters

if st.button('Calculate EOQ with backorders'):
    Q,s,cost=economic_order_quantity_with_backorders(fixedCost,holdingCost,stockOutCost,demandRate)
    st.write(f'Economic Order Quantity (Q): {Q:.2f}')
    st.write(f'Total Inventory Cost: {cost:.2f}')
    st.write(f'The stock out shortege rate: {s:.2f}')
    st.write(f'Total inventory holding cost: {cost-s:.2f}')

st.markdown("---")
st.markdown("**References**")
st.markdown(
    "[1] Economic order quantity with backorders. "
    "https://en.wikipedia.org/wiki/Economic_order_quantity"
)
st.markdown(
    "[2] Snyder, Lawrence V. 2023. *Stockpyl*. GitHub repository. "
    "Available at: https://github.com/LarrySnyder/stockpyl"
)