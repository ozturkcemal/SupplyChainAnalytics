#import the package and bring the content
import stockpyl
import streamlit as st

# bringing newsvendor_normal function of the module
from stockpyl.newsvendor import newsvendor_normal

st.title("News Vendor Inventory Optimization Problem");

holdingCost=st.number_input("Enter the holding cost: ",value=20.0, format="%.2f")
stockoutCost=st.number_input("Enter the fstock out cost: ",value=10.0, format="%.2f")
demandMean=st.number_input("Enter the mean demand: ",value=1000.0, format="%.2f")
demandStd=st.number_input("Enter the standard deviation of demand: ",value=50.0, format="%.2f")

if st.button("Compute Optimal Stock Level and Inventory Cost"):
    stockLevel,cost=newsvendor_normal(holdingCost,stockoutCost,demandMean,demandStd)
    st.write(f'The optimal stock level is {stockLevel:.2f}')
    st.write(f'The cost of inventory is {cost:.2f}')

st.markdown("---")
st.markdown("**References**")
st.markdown(
    "[1] Newsvendor model "
    "https://en.wikipedia.org/wiki/Newsvendor_model"
)
st.markdown(
    "[2] Snyder, Lawrence V. 2023. *Stockpyl*. GitHub repository. "
    "Available at: https://github.com/LarrySnyder/stockpyl"
)