"""
Vehicle Routing Problem (VRP) Solver
Optimizes routes for multiple vehicles with load constraints using Google OR-Tools and OpenRouteService.
"""

import streamlit as st
import pandas as pd
import openrouteservice
import folium
from typing import List, Dict, Tuple, Any, cast
from streamlit_folium import st_folium
from ortools.constraint_solver import routing_enums_pb2, pywrapcp

# ─────────────────────────────────────────────────────────────────────────────
# Constants & Defaults
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_LOCATIONS = {
    'Name': [
        "Liberty Bar", "Dwyers", "Costigans", "Franciscan Well",
        "Tom Barry's", "Corner House", "Sin E'", "An Spailpin Fanach",
        "The Oval", "Charlies", "Fionbarra", "The Oliver Plunkett",
    ],
    'Latitude': [
        51.898011, 51.897545, 51.897412, 51.901227, 51.893765, 51.901992,
        51.901995, 51.896701, 51.896777, 51.897178, 51.893796, 51.898439,
    ],
    'Longitude': [
        -8.477301, -8.478392, -8.480129, -8.482102, -8.478174, -8.470903,
        -8.471133, -8.476589, -8.476649, -8.466700, -8.470990, -8.469605,
    ],
    'Demand': [0, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
}

ROUTE_COLORS = [
    'blue', 'red', 'green', 'purple', 'orange',
    'cadetblue', 'darkred', 'darkgreen', 'darkpurple', 'pink',
]


# ─────────────────────────────────────────────────────────────────────────────
# Core Logic & Caching
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def get_distance_matrix(api_key: str, coords: List[List[float]], profile: str) -> List[List[float]]:
    """Fetch distance matrix from OpenRouteService. Cached to save API quota."""
    client = openrouteservice.Client(key=api_key)
    matrix = client.distance_matrix(
        locations=coords,
        profile=profile,
        metrics=['distance'],
        units='m'
    )
    return matrix['distances']


@st.cache_data(show_spinner=False)
def get_route_geometries(api_key: str, routes: List[List[Dict[str, Any]]], profile: str) -> List[List[Tuple[float, float]]]:
    """Fetch street-level routing geometries for all routes. Cached."""
    client = openrouteservice.Client(key=api_key)
    geometries = []
    
    # Batching is not supported by standard directions API in single call for multiple unconnected routes,
    # so we loop. Caching helps if the same route is requested again.
    for route in routes:
        if len(route) < 2:
            geometries.append([])
            continue
            
        coords = [p['coord'] for p in route]
        resp = client.directions(
            coordinates=coords,
            profile=profile,
            format='geojson'
        )
        # Flip (lon, lat) to (lat, lon) for Folium
        path = [(c[1], c[0]) for c in resp['features'][0]['geometry']['coordinates']]
        geometries.append(path)
        
    return geometries


def solve_cvrp(
    distance_matrix: List[List[float]],
    demands: List[int],
    vehicle_capacity: int,
    num_vehicles: int,
    depot_index: int = 0
) -> Dict[str, Any]:
    """
    Solve the Capacitated Vehicle Routing Problem using Google OR-Tools.
    Returns the solution assignment and routing index manager.
    """
    # Create the routing index manager
    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), num_vehicles, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    # 1. Define Distance Callback (Arc Cost)
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(distance_matrix[from_node][to_node])

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # 2. Define Demand Callback (Capacity Constraint)
    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return demands[from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        [vehicle_capacity] * num_vehicles,  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity'
    )

    # 3. Parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    # 4. Solve
    solution = routing.SolveWithParameters(search_parameters)
    
    return {
        "solution": solution,
        "manager": manager,
        "routing": routing
    }


def extract_solution_routes(
    solution: Any, 
    manager: Any, 
    routing: Any, 
    names: Any, 
    coords: Any, 
    demands: Any, 
    num_vehicles: int,
    distance_matrix: Any
) -> Tuple[List[List[Dict[str, Any]]], Dict[str, str], List[float]]:
    """Extract readable routes, node assignments, and distances from the solution."""
    all_routes = []
    node_to_vehicle = {}
    route_distances = []

    for vehicle_id in range(num_vehicles):
        index = routing.Start(vehicle_id)
        route = []
        seq = 0
        route_dist = 0.0
        
        while not routing.IsEnd(index):
            node_idx = int(manager.IndexToNode(index))
            
            # Distance calculation (cumulative)
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            
            # Add segment distance
            if not routing.IsEnd(index):
                next_node_idx = int(manager.IndexToNode(index))
                # explicit list access to avoid pyre confusion
                row = cast(list, distance_matrix)[node_idx]
                route_dist += float(row[next_node_idx])

            # Store node info
            route.append({
                'name': cast(list, names)[node_idx],
                'coord': cast(list, coords)[node_idx],
                'demand': cast(list, demands)[node_idx]
            })
            
            # Map node to vehicle
            if node_idx != 0:
                node_to_vehicle[cast(list, names)[node_idx]] = f"Vehicle {vehicle_id + 1} (Stop {seq})"
            
            seq += 1
            
        # Add End Node (Depot)
        node_idx = int(manager.IndexToNode(index))
        
        route.append({
            'name': cast(list, names)[node_idx],
            'coord': cast(list, coords)[node_idx],
            'demand': cast(list, demands)[node_idx]
        })
        
        # Only add valid routes
        if len(route) > 2:
            all_routes.append(route)
            route_distances.append(route_dist)
            
    return all_routes, node_to_vehicle, route_distances


# ─────────────────────────────────────────────────────────────────────────────
# UI Functions
# ─────────────────────────────────────────────────────────────────────────────

def init_session_state():
    """Initialize session state variables."""
    if 'vrp_locations_df' not in st.session_state:
        st.session_state.vrp_locations_df = pd.DataFrame(DEFAULT_LOCATIONS)
    if 'editor_version' not in st.session_state:
        st.session_state.editor_version = 0
    if 'vrp_results' not in st.session_state:
        st.session_state.vrp_results = None
        
    # Helpers for widget state defaults
    df = st.session_state.vrp_locations_df
    total_demand = int(df['Demand'].sum())
    max_demand = int(df['Demand'].max()) if not df.empty else 1
    
    if 'vrp_num_locations' not in st.session_state:
        st.session_state.vrp_num_locations = len(df)
        
    if 'vrp_capacity' not in st.session_state:
        cap = max(1, max_demand)
        st.session_state.vrp_capacity = cap
        
    if 'vrp_num_vehicles' not in st.session_state:
        cap = st.session_state.vrp_capacity
        needed = (total_demand // cap) + (1 if total_demand % cap > 0 else 0)
        st.session_state.vrp_num_vehicles = max(1, needed)


def handle_csv_upload():
    """Handle CSV file uploader logic."""
    with st.expander("📂 Optional: Upload Locations via CSV"):
        st.info('ℹ️ **Format:** CSV with 4 columns: Name, Latitude, Longitude, Demand. The first row is the Depot.')
        uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])
        
        if uploaded_file is not None:
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get('last_processed_file') != file_id:
                try:
                    df = pd.read_csv(uploaded_file, header=None, names=['Name', 'Latitude', 'Longitude', 'Demand'])
                    st.session_state.vrp_locations_df = df
                    st.session_state.vrp_num_locations = len(df)
                    st.session_state.editor_version += 1
                    
                    # Update defaults based on new data
                    max_d = int(df['Demand'].max())
                    tot_d = int(df['Demand'].sum())
                    cap = max(1, max_d)
                    st.session_state.vrp_capacity = cap
                    st.session_state.vrp_num_vehicles = max(1, (tot_d // cap) + (1 if tot_d % cap else 0))
                    
                    st.session_state.last_processed_file = file_id
                    st.success(f"✅ Loaded {len(df)} locations!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error reading CSV: {e}")
        else:
            st.session_state.last_processed_file = None

def render_map(routes, geometries, node_to_vehicle):
    """Render the results on a Folium map."""
    st.header('Optimized Fleet Map')
    
    df = st.session_state.vrp_locations_df
    lats, lons = df['Latitude'], df['Longitude']
    
    fmap = folium.Map()
    if not df.empty:
        fmap.fit_bounds([[lats.min(), lons.min()], [lats.max(), lons.max()]])
        
    # 1. Markers
    for idx, row in df.iterrows():
        assignment = node_to_vehicle.get(row['Name'], "Unassigned/Depot")
        folium.Marker(
            [row['Latitude'], row['Longitude']],
            popup=f"<b>{row['Name']}</b><br>Demand: {row['Demand']}<br>Assigned to: {assignment}",
            icon=folium.Icon(color='black' if idx == 0 else 'gray')
        ).add_to(fmap)
        
    # 2. Routes
    for i, (route, geom) in enumerate(zip(routes, geometries)):
        color = ROUTE_COLORS[i % len(ROUTE_COLORS)]
        
        # Path
        folium.PolyLine(
            geom, color=color, weight=5, opacity=0.8, 
            tooltip=f"Vehicle {i+1}"
        ).add_to(fmap)
        
        # Stop sequence markers (skipping depot at start)
        for seq, point in enumerate(route[:-1]):
            if seq > 0:
                folium.CircleMarker(
                    [point['coord'][1], point['coord'][0]],
                    radius=10, color=color, fill=True, fill_color=color,
                    popup=f"Vehicle {i+1} - Stop {seq}: {point['name']}",
                    tooltip=f"Vehicle {i+1} - Stop {seq}"
                ).add_to(fmap)
                
    st_folium(fmap, use_container_width=True, height=600)


def render_summary(routes, distances, capacity):
    """Render performance metrics."""
    st.header('Fleet Performance Summary')
    
    total_dist = sum(distances)
    
    for i, route in enumerate(routes):
        with st.expander(f"🚛 Vehicle {i+1} Details", expanded=True):
            r_names = [p['name'] for p in route]
            r_load = sum(p['demand'] for p in route)
            r_dist = distances[i]
            utilization = (r_load / capacity * 100) if capacity > 0 else 0
            
            st.write(f"**Sequence:** {' → '.join(r_names)}")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Distance", f"{r_dist/1000.0:.2f} km")
            c2.metric("Load Carried", f"{r_load} units")
            c3.metric("Capacity Utilization", f"{utilization:.0f}%")
            
    st.metric("Total Fleet Distance", f"{total_dist/1000.0:.2f} km")


# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="VRP Solver", layout="wide")
    
    st.title('Capacitated Vehicle Routing Problem (CVRP) Solver')
    st.write('Optimize routes for multiple vehicles with load constraints')
    
    st.markdown("---")
    st.markdown("**References**\n")
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

    init_session_state()

    # ── Step 1: Configuration ──
    st.header('Step 1: Configuration')
    api_key = st.text_input('OpenRouteService API Key:', type='password', 
                           help='Get your free API key from https://openrouteservice.org/')
    
    c1, c2 = st.columns(2)
    transport_profile = c1.selectbox(
        'Transport Profile:',
        options=['foot-walking', 'driving-car', 'cycling-regular', 'driving-hgv'],
        index=0
    )
    c2.info("The first location in your list will always be treated as the **Depot**.")

    # ── Step 2: Locations ──
    st.header('Step 2: Locations & Demands')
    handle_csv_upload()
    
    # Row Counter
    curr_rows = len(st.session_state.vrp_locations_df)
    new_rows = st.number_input(
        'Number of Locations:', min_value=1, max_value=50, 
        value=st.session_state.vrp_num_locations, key='vrp_num_locations'
    )
    
    if new_rows != curr_rows:
        if new_rows < curr_rows:
            st.session_state.vrp_locations_df = st.session_state.vrp_locations_df.iloc[:new_rows]
        else:
            to_add = new_rows - curr_rows
            extension = pd.DataFrame({
                'Name': [f"Location {curr_rows + i + 1}" for i in range(to_add)],
                'Latitude': [51.89] * to_add,
                'Longitude': [-8.47] * to_add,
                'Demand': [100] * to_add
            })
            st.session_state.vrp_locations_df = pd.concat([st.session_state.vrp_locations_df, extension], ignore_index=True)
        st.rerun()

    # Data Editor
    st.subheader("Edit Locations & Demands Below")
    edited = st.data_editor(
        st.session_state.vrp_locations_df,
        num_rows="dynamic", use_container_width=True,
        key=f"editor_{st.session_state.editor_version}",
        column_config={
            "Name": st.column_config.TextColumn("Name", required=True),
            "Latitude": st.column_config.NumberColumn("Lat", required=True, format="%.6f"),
            "Longitude": st.column_config.NumberColumn("Long", required=True, format="%.6f"),
            "Demand": st.column_config.NumberColumn("Demand", required=True, min_value=0),
        }
    )
    st.session_state.vrp_locations_df = edited

    # ── Step 3: Fleet ──
    st.header('Step 3: Fleet Configuration')
    df_clean = st.session_state.vrp_locations_df
    max_demand = int(df_clean['Demand'].max()) if not df_clean.empty else 0
    total_demand = int(df_clean['Demand'].sum())
    
    c1, c2 = st.columns(2)
    veh_cap = c1.number_input('Vehicle Capacity (units):', min_value=1, max_value=10000, 
                              value=st.session_state.vrp_capacity, key='vrp_capacity')
    
    if veh_cap < max_demand:
        c1.warning(f"⚠️ Capacity ({veh_cap}) < Max Demand ({max_demand}). Solution impossible.")

    rec_vehs = (total_demand // veh_cap) + (1 if total_demand % veh_cap else 0)
    num_vehs = c2.number_input('Number of Vehicles:', min_value=1, max_value=20, 
                               value=st.session_state.vrp_num_vehicles, key='vrp_num_vehicles',
                               help=f"Minimum required: {rec_vehs}")

    # ── Solve ──
    if api_key and st.button('Optimize VRP Routes', type='primary'):
        # Prepare Data
        coords = df_clean[['Longitude', 'Latitude']].values.tolist()
        demands = df_clean['Demand'].tolist()
        names = df_clean['Name'].tolist()
        
        try:
            with st.spinner('Calculating distances...'):
                dist_matrix = get_distance_matrix(api_key, coords, transport_profile)
                
            with st.spinner('Solving VRP...'):
                res = solve_cvrp(dist_matrix, demands, veh_cap, num_vehs)
                
            solution = res['solution']
            if solution:
                routes, n2v, dists = extract_solution_routes(
                    solution, res['manager'], res['routing'], 
                    names, coords, demands, num_vehs, dist_matrix
                )
                
                with st.spinner('Fetching geometries...'):
                    geometries = get_route_geometries(api_key, routes, transport_profile)
                
                st.session_state.vrp_results = {
                    'routes': routes,
                    'geometries': geometries,
                    'node_to_vehicle': n2v,
                    'distances': dists,
                    'capacity': veh_cap
                }
            else:
                st.error("No solution found. Try increasing vehicles or capacity.")
                
        except Exception as e:
            st.error(f"Optimization Error: {e}")

    # ── Results ──
    if st.session_state.vrp_results:
        res = st.session_state.vrp_results
        st.success(f"✓ Optimized {len(res['routes'])} active routes!")
        render_map(res['routes'], res['geometries'], res['node_to_vehicle'])
        render_summary(res['routes'], res.get('distances', []), res.get('capacity', 1))
        st.info("💡 Tip: Download map or data using browser controls.")
    elif not api_key:
        st.info("� Enter OpenRouteService API Key to begin.")


if __name__ == "__main__":
    main()