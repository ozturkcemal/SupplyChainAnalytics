import streamlit as st
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import openrouteservice
import folium
from streamlit_folium import st_folium
import pandas as pd
import time
import math

st.set_page_config(page_title="VRP Solver", layout="wide")

st.title('Capacitated Vehicle Routing Problem (CVRP) Solver')
st.write('Optimize routes for multiple vehicles with load constraints')

st.markdown("---")
st.markdown("**References**")
st.markdown(
    "[1] Vehicle Routing Problem. "
    "https://en.wikipedia.org/wiki/Vehicle_routing_problem"
)
st.markdown(
    "[2] Google OR-Tools CVRP. "
    "https://developers.google.com/optimization/routing/cvrp"
)
st.markdown(
    "[3] OpenRouteService. "
    "https://openrouteservice.org/"
)
st.markdown("---")

# Initialize session state
if 'vrp_results' not in st.session_state:
    st.session_state.vrp_results = None

# Step 1: API Configuration
st.header('Step 1: Configuration')
api_key = st.text_input('OpenRouteService API Key:', type='password', help='Get your free API key from https://openrouteservice.org/')

col1, col2 = st.columns(2)
with col1:
    transport_profile = st.selectbox(
        'Transport Profile:',
        options=['foot-walking', 'driving-car', 'cycling-regular', 'driving-hgv'],
        index=0
    )
with col2:
    st.info("The first location in your list will always be treated as the **Depot** (Starting/Ending point).")

# Step 2: Locations & Demands
st.header('Step 2: Locations & Demands')

# Option to upload CSV or use manual entry
input_method = st.radio(
    'Select input method:',
    options=['Manual Entry', 'Upload CSV File'],
    index=0,
    horizontal=True
)

if input_method == 'Upload CSV File':
    st.info('ℹ️ **Format:** CSV with 4 columns: Name, Latitude, Longitude, Demand. The first row is the Depot.')
    uploaded_file = st.file_uploader('Choose a CSV file', type=['csv'])
    
    if uploaded_file is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_file, header=None, names=['Name', 'Latitude', 'Longitude', 'Demand'])
            st.session_state.vrp_locations_df = uploaded_df
            st.success(f'✓ Loaded {len(uploaded_df)} locations')
        except Exception as e:
            st.error(f'Error: {str(e)}')
else:
    # Default values based on the Cork pubs example
    default_data = {
        'Name': ["Liberty Bar", "Dwyers", "Costigans", "Franciscan Well", "Tom Barry's", "Corner House", "Sin E'", "An Spailpin Fanach", "The Oval", "Charlies", "Fionbarra", "The Oliver Plunkett"],
        'Latitude': [51.898011, 51.897545, 51.897412, 51.901227, 51.893765, 51.901992, 51.901995, 51.896701, 51.896777, 51.897178, 51.893796, 51.898439],
        'Longitude': [-8.477301, -8.478392, -8.480129, -8.482102, -8.478174, -8.470903, -8.471133, -8.476589, -8.476649, -8.466700, -8.470990, -8.469605],
        'Demand': [0, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
    }
    
    if 'vrp_locations_df' not in st.session_state:
        st.session_state.vrp_locations_df = pd.DataFrame(default_data)

    edited_df = st.data_editor(
        st.session_state.vrp_locations_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Name": st.column_config.TextColumn("Name", required=True),
            "Latitude": st.column_config.NumberColumn("Lat", required=True, format="%.6f"),
            "Longitude": st.column_config.NumberColumn("Long", required=True, format="%.6f"),
            "Demand": st.column_config.NumberColumn("Demand", required=True, min_value=0)
        }
    )
    st.session_state.vrp_locations_df = edited_df

# Step 3: Fleet Settings
st.header('Step 3: Fleet Configuration')
total_demand = st.session_state.vrp_locations_df['Demand'].sum()
max_demand = st.session_state.vrp_locations_df['Demand'].max()

col_v1, col_v2 = st.columns(2)
with col_v1:
    vehicle_capacity = st.number_input('Vehicle Capacity (units):', min_value=1, max_value=10000, value=400)
    
    if vehicle_capacity < max_demand:
        st.warning(f"⚠️ **Caution:** Your vehicle capacity ({vehicle_capacity}) is less than the maximum demand of a single location ({max_demand}). This will make the problem impossible to solve.")

with col_v2:
    suggested_vehicles = math.ceil(total_demand / vehicle_capacity) if vehicle_capacity > 0 else 1
    num_vehicles = st.number_input(
        'Number of Vehicles:', 
        min_value=1, 
        max_value=20, 
        value=max(1, suggested_vehicles),
        help=f"Based on total demand ({total_demand}) and capacity ({vehicle_capacity}), the minimum required is {suggested_vehicles}."
    )

# Solve Button
if api_key and st.button('Optimize VRP Routes', type='primary'):
    try:
        client = openrouteservice.Client(key=api_key)
        locations_df = st.session_state.vrp_locations_df
        
        # Prepare coordinates and demands
        coords = locations_df[['Longitude', 'Latitude']].values.tolist()
        demands = locations_df['Demand'].tolist()
        names = locations_df['Name'].tolist()
        
        with st.spinner('Calculating distance matrix (OpenRouteService)...'):
            matrix = client.distance_matrix(
                locations=coords,
                profile=transport_profile,
                metrics=['distance'],
                units='m'
            )
            dist_matrix = matrix['distances']

        # OR-Tools Model
        data = {
            'distance_matrix': dist_matrix,
            'demands': demands,
            'num_vehicles': num_vehicles,
            'vehicle_capacities': [vehicle_capacity] * num_vehicles,
            'depot': 0
        }

        manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), data['num_vehicles'], data['depot'])
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            return int(data['distance_matrix'][manager.IndexToNode(from_index)][manager.IndexToNode(to_index)])

        transit_cb = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)

        def demand_callback(from_index):
            return data['demands'][manager.IndexToNode(from_index)]

        demand_cb = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(demand_cb, 0, data['vehicle_capacities'], True, 'Capacity')

        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

        with st.spinner('Solving VRP (OR-Tools)...'):
            solution = routing.SolveWithParameters(search_params)

        if solution:
            all_routes = []
            for vehicle_id in range(data['num_vehicles']):
                index = routing.Start(vehicle_id)
                route = []
                while not routing.IsEnd(index):
                    node_idx = manager.IndexToNode(index)
                    route.append({'name': names[node_idx], 'coord': coords[node_idx], 'demand': demands[node_idx]})
                    index = solution.Value(routing.NextVar(index))
                # Add depot at end
                node_idx = manager.IndexToNode(index)
                route.append({'name': names[node_idx], 'coord': coords[node_idx], 'demand': demands[node_idx]})
                
                if len(route) > 2: # Only keep non-empty routes
                    all_routes.append(route)
            
            # Get real street geometry for each route
            geometries = []
            with st.spinner('Fetching street-level geometries...'):
                for r in all_routes:
                    geom_resp = client.directions(
                        coordinates=[p['coord'] for p in r],
                        profile=transport_profile,
                        format='geojson'
                    )
                    geometries.append([(c[1], c[0]) for c in geom_resp['features'][0]['geometry']['coordinates']])

            st.session_state.vrp_results = {
                'routes': all_routes,
                'geometries': geometries,
                'summary': locations_df # For reference
            }
        else:
            st.error("No solution found. Try increasing the number of vehicles or their capacity.")

    except Exception as e:
        st.error(f"Error during optimization: {str(e)}")

# Display Results
if st.session_state.vrp_results:
    res = st.session_state.vrp_results
    st.success(f"✓ Optimized {len(res['routes'])} valid routes!")

    # Map Visualization
    st.header('Optimized Fleet Map')
    colors = ['blue', 'red', 'green', 'purple', 'orange', 'cadetblue', 'darkred', 'darkgreen', 'darkpurple', 'pink']
    
    center_lat = st.session_state.vrp_locations_df.iloc[0]['Latitude']
    center_lon = st.session_state.vrp_locations_df.iloc[0]['Longitude']
    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=14)

    # Add markers for all specified locations
    for idx, row in st.session_state.vrp_locations_df.iterrows():
        folium.Marker(
            [row['Latitude'], row['Longitude']],
            popup=f"<b>{row['Name']}</b><br>Demand: {row['Demand']}",
            icon=folium.Icon(color='black' if idx == 0 else 'gray')
        ).add_to(fmap)

    # Draw colored routes
    for i, (route, geom) in enumerate(zip(res['routes'], res['geometries'])):
        color = colors[i % len(colors)]
        folium.PolyLine(geom, color=color, weight=5, opacity=0.8, tooltip=f"Vehicle {i+1}").add_to(fmap)
        
        # Add numbered sequence markers for the active locations in this route
        for seq, point in enumerate(route[:-1]):
             if seq > 0: # Skip depot marker since we added it
                folium.CircleMarker(
                    [point['coord'][1], point['coord'][0]],
                    radius=10,
                    color=color,
                    fill=True,
                    fill_color=color,
                    popup=f"Stop {seq}: {point['name']}"
                ).add_to(fmap)

    st_folium(fmap, use_container_width=True, height=600)

    # Detailed Summary
    st.header('Fleet Performance Summary')
    total_dist = 0
    
    for i, route in enumerate(res['routes']):
        with st.expander(f"🚛 Vehicle {i+1} Details", expanded=True):
            r_names = [p['name'] for p in route]
            r_load = sum(p['demand'] for p in route)
            st.write(f"**Sequence:** {' → '.join(r_names)}")
            
            c1, c2 = st.columns(2)
            # Estimate distance for display (actual from ORS would be better if stored)
            c1.metric("Load Carried", f"{r_load} units")
            # For simplicity, we just show the load here. Full distance would require storing matrix sums.

    st.info("💡 Tip: You can download the map using the browser save feature or export data results.")
else:
    if not api_key:
        st.info("👋 Enter your API Key above to begin.")