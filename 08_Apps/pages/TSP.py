import streamlit as st
import os
import sys

# Add routing folder to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../routing'))

st.title('TSP Solver')
st.write('Calculate the shortest route for a single vehicle to visit multiple locations')

st.info('This application uses the TSP_singleCellNotebook for solving Traveling Salesman Problems.')

st.write('### Features:')
st.write('- Interactive map visualization')
st.write('- OR-Tools optimization')
st.write('- OpenRouteService integration')

st.write('###Note:')
st.write('The full interactive TSP solver from the notebook will be integrated here.')
st.write('For now, please refer to the routing/TSP_singleCellNotebook.ipynb for the complete implementation.')

# Placeholder for future notebook integration
st.write('---')
st.write('Coming soon: Interactive TSP solver with map interface!')
