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

# Initialize session state with default data if not present
default_data = {
    'Name': ["Liberty Bar", "Dwyers", "Costigans", "Franciscan Well", "Tom Barry's", "Corner House", "Sin E'", "An Spailpin Fanach", "The Oval", "Charlies", "Fionbarra", "The Oliver Plunkett"],
    'Latitude': [51.898011, 51.897545, 51.897412, 51.901227, 51.893765, 51.901992, 51.901995, 51.896701, 51.896777, 51.897178, 51.893796, 51.898439],
    'Longitude': [-8.477301, -8.478392, -8.480129, -8.482102, -8.478174, -8.470903, -8.471133, -8.476589, -8.476649, -8.466700, -8.470990, -8.469605],
    'Demand': [0, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
}

# 1. Initialize ALL session state keys used by widgets
if 'vrp_locations_df' not in st.session_state:
    st.session_state.vrp_locations_df = pd.DataFrame(default_data)
if 'editor_version' not in st.session_state:
    st.session_state.editor_version = 0

# Calculated values for initial state
current_max_demand = int(st.session_state.vrp_locations_df['Demand'].max())
total_demand_init = int(st.session_state.vrp_locations_df['Demand'].sum())
capacity_init = max(1, current_max_demand)
vehicles_init = (total_demand_init // capacity_init) + (1 if total_demand_init % capacity_init > 0 else 0)

# Pre-initialize widget keys to avoid instantiation errors
if 'vrp_num_locations' not in st.session_state:
    st.session_state.vrp_num_locations = len(st.session_state.vrp_locations_df)
if 'vrp_capacity' not in st.session_state:
    st.session_state.vrp_capacity = capacity_init
if 'vrp_num_vehicles' not in st.session_state:
    st.session_state.vrp_num_vehicles = max(1, vehicles_init)

# 2. CSV UPLOAD LOGIC (Must come BEFORE widgets set their keys)
with st.expander("📂 Optional: Upload Locations via CSV"):
    st.info('ℹ️ **Format:** CSV with 4 columns: Name, Latitude, Longitude, Demand. The first row is the Depot.')
    uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])
    if uploaded_file is not None:
        # Use a unique ID (name + size) to ensure we only process this file once and avoid rerun loops
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get('last_processed_file') != file_id:
            try:
                uploaded_df = pd.read_csv(uploaded_file, header=None, names=['Name', 'Latitude', 'Longitude', 'Demand'])
                
                # Update data
                st.session_state.vrp_locations_df = uploaded_df
                
                # Update dependent widget values in session state BEFORE they are rendered
                new_max_demand = int(uploaded_df['Demand'].max())
                new_total_demand = int(uploaded_df['Demand'].sum())
                
                st.session_state.vrp_num_locations = len(uploaded_df)
                st.session_state.vrp_capacity = max(1, new_max_demand)
                st.session_state.vrp_num_vehicles = max(1, (new_total_demand // st.session_state.vrp_capacity) + (1 if new_total_demand % st.session_state.vrp_capacity > 0 else 0))
                st.session_state.editor_version += 1 # Force refresh of the table
                
                # Mark as processed to prevent infinite loops
                st.session_state.last_processed_file = file_id
                
                st.success(f"✅ Successfully loaded {len(uploaded_df)} locations!")
                st.rerun() 
            except Exception as e:
                st.error(f"❌ Error reading CSV: {e}")
    else:
        # Reset identifier when no file is selected
        st.session_state.last_processed_file = None

# 3. MANUAL ROW COUNT CONTROL
current_count = len(st.session_state.vrp_locations_df)
new_count = st.number_input(
    'Number of Locations:', 
    min_value=1, 
    max_value=50, 
    value=st.session_state.vrp_num_locations, # Use state value
    key='vrp_num_locations',
    help="Set the number of rows in the table below. Adding locations will append empty rows; reducing will remove rows from the bottom."
)

if new_count != current_count:
    if new_count < current_count:
        st.session_state.vrp_locations_df = st.session_state.vrp_locations_df.iloc[:new_count]
    else:
        # Append empty rows
        to_add = new_count - current_count
        new_rows = pd.DataFrame({
            'Name': [f"Location {current_count + i + 1}" for i in range(to_add)],
            'Latitude': [51.89] * to_add,
            'Longitude': [-8.47] * to_add,
            'Demand': [100] * to_add
        })
        st.session_state.vrp_locations_df = pd.concat([st.session_state.vrp_locations_df, new_rows], ignore_index=True)
    st.rerun()

# 4. DATA EDITOR
st.subheader("Edit Locations & Demands Below")
edited_df = st.data_editor(
    st.session_state.vrp_locations_df,
    num_rows="dynamic",
    use_container_width=True,
    key=f"editor_{st.session_state.editor_version}",
    column_config={
        "Name": st.column_config.TextColumn("Name", required=True),
        "Latitude": st.column_config.NumberColumn("Lat", required=True, format="%.6f"),
        "Longitude": st.column_config.NumberColumn("Long", required=True, format="%.6f"),
        "Demand": st.column_config.NumberColumn("Demand", required=True, min_value=0)
    }
)

# Update session state with edited values
st.session_state.vrp_locations_df = edited_df

# Step 3: Fleet Settings
st.header('Step 3: Fleet Configuration')

# Recalculate demands for Step 3 logic
total_demand = int(st.session_state.vrp_locations_df['Demand'].sum())
max_demand = int(st.session_state.vrp_locations_df['Demand'].max())

col_v1, col_v2 = st.columns(2)
with col_v1:
    vehicle_capacity = st.number_input(
        'Vehicle Capacity (units):', 
        min_value=1, 
        max_value=10000, 
        value=st.session_state.vrp_capacity, # Use state value
        key='vrp_capacity'
    )
    
    if vehicle_capacity < max_demand:
        st.warning(f"⚠️ **Caution:** Your vehicle capacity ({vehicle_capacity}) is less than the maximum demand of a single location ({max_demand}). This will make the problem impossible to solve.")

with col_v2:
    suggested_vehicles = (total_demand // vehicle_capacity) + (1 if total_demand % vehicle_capacity > 0 else 0)
    num_vehicles = st.number_input(
        'Number of Vehicles:', 
        min_value=1, 
        max_value=20, 
        value=st.session_state.vrp_num_vehicles, # Use state value
        key='vrp_num_vehicles',
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
            node_to_vehicle = {} # Map node names to assigned vehicle numbers
            for vehicle_id in range(data['num_vehicles']):
                index = routing.Start(vehicle_id)
                route = []
                seq = 0
                while not routing.IsEnd(index):
                    node_idx = manager.IndexToNode(index)
                    node_name = names[node_idx]
                    route.append({'name': node_name, 'coord': coords[node_idx], 'demand': demands[node_idx]})
                    if node_idx != 0: # Skip depot for mapping
                        node_to_vehicle[node_name] = f"Vehicle {vehicle_id + 1} (Stop {seq})"
                    index = solution.Value(routing.NextVar(index))
                    seq += 1
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
                'node_to_vehicle': node_to_vehicle,
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
    
    # Calculate bounds to capture all locations
    lats = st.session_state.vrp_locations_df['Latitude']
    lons = st.session_state.vrp_locations_df['Longitude']
    sw = [lats.min(), lons.min()]
    ne = [lats.max(), lons.max()]
    
    fmap = folium.Map()
    fmap.fit_bounds([sw, ne])

    # Add markers for all specified locations
    node_to_vehicle = res.get('node_to_vehicle', {})
    for idx, row in st.session_state.vrp_locations_df.iterrows():
        assignment_text = node_to_vehicle.get(row['Name'], "Unassigned/Depot")
        folium.Marker(
            [row['Latitude'], row['Longitude']],
            popup=f"<b>{row['Name']}</b><br>Demand: {row['Demand']}<br>Assigned to: {assignment_text}",
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
                    popup=f"Vehicle {i+1} - Stop {seq}: {point['name']}",
                    tooltip=f"Vehicle {i+1} - Stop {seq}"
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