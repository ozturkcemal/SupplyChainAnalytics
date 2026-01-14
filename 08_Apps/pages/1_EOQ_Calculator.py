import streamlit as st
from stockpyl.eoq import economic_order_quantity

st.title('Economic Order Quantity (EOQ) Calculator')

fixedCost = st.number_input('Enter the fixed ordering cost:', value=15.0, format="%.2f")
holdingCost = st.number_input('Enter the holding cost:', value=4.0, format="%.2f")
demandRate = st.number_input('Enter the demand rate:', value=12.0, format="%.2f")

if st.button('Calculate EOQ'):
    Q, cost = economic_order_quantity(fixedCost, holdingCost, demandRate)
    st.write(f'Economic Order Quantity (Q): {Q:.2f}')
    st.write(f'Total Inventory Cost: {cost:.2f}')
