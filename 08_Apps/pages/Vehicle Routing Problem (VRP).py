import streamlit as st
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
import openrouteservice
import folium
from streamlit_folium import st_folium
import pandas as pd

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
ROUTE_COLORS = [
    'blue', 'red', 'green', 'purple', 'orange',
    'cadetblue', 'darkred', 'darkgreen', 'darkpurple', 'pink',
]

DEFAULT_DATA = {
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


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────
def calc_fleet_defaults(df: pd.DataFrame) -> tuple[int, int]:
    """Return (capacity, num_vehicles) derived from the dataframe demands."""
    max_demand = max(1, int(df['Demand'].max()))
    total = int(df['Demand'].sum())
    return max_demand, max(1, -(-total // max_demand))  # ceil division


def init_state() -> None:
    """One-shot initialisation of all session-state keys."""
    defaults = {
        'vrp_results': None,
        'vrp_locations_df': pd.DataFrame(DEFAULT_DATA),
        'editor_version': 0,
        'last_processed_file': None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Widget-bound keys must also be pre-set once
    if 'vrp_num_locations' not in st.session_state:
        st.session_state.vrp_num_locations = len(st.session_state.vrp_locations_df)
    cap, n_veh = calc_fleet_defaults(st.session_state.vrp_locations_df)
    if 'vrp_capacity' not in st.session_state:
        st.session_state.vrp_capacity = cap
    if 'vrp_num_vehicles' not in st.session_state:
        st.session_state.vrp_num_vehicles = n_veh


def process_csv(uploaded_file) -> None:
    """Process a CSV upload exactly once per unique file, then rerun."""
    file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.get('last_processed_file') == file_id:
        return  # Already processed

    try:
        df = pd.read_csv(
            uploaded_file, header=None,
            names=['Name', 'Latitude', 'Longitude', 'Demand'],
        )
        st.session_state.vrp_locations_df = df
        cap, n_veh = calc_fleet_defaults(df)
        st.session_state.vrp_num_locations = len(df)
        st.session_state.vrp_capacity = cap
        st.session_state.vrp_num_vehicles = n_veh
        st.session_state.editor_version += 1
        st.session_state.last_processed_file = file_id
        st.success(f"✅ Successfully loaded {len(df)} locations!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error reading CSV: {e}")


def resize_df(new_count: int) -> None:
    """Resize the locations dataframe and rerun if the count changed."""
    df = st.session_state.vrp_locations_df
    current = len(df)
    if new_count == current:
        return

    if new_count < current:
        st.session_state.vrp_locations_df = df.iloc[:new_count]
    else:
        to_add = new_count - current
        new_rows = pd.DataFrame({
            'Name': [f"Location {current + i + 1}" for i in range(to_add)],
            'Latitude': [51.89] * to_add,
            'Longitude': [-8.47] * to_add,
            'Demand': [100] * to_add,
        })
        st.session_state.vrp_locations_df = pd.concat(
            [df, new_rows], ignore_index=True,
        )
    st.rerun()


def solve_vrp(
    client: openrouteservice.Client,
    profile: str,
    locations_df: pd.DataFrame,
    capacity: int,
    n_vehicles: int,
) -> dict | None:
    """Run the CVRP solver and return results dict, or None on failure."""
    coords = locations_df[['Longitude', 'Latitude']].values.tolist()
    demands = locations_df['Demand'].tolist()
    names = locations_df['Name'].tolist()

    with st.spinner('Calculating distance matrix (OpenRouteService)...'):
        matrix = client.distance_matrix(
            locations=coords, profile=profile,
            metrics=['distance'], units='m',
        )

    data = {
        'distance_matrix': matrix['distances'],
        'demands': demands,
        'num_vehicles': n_vehicles,
        'vehicle_capacities': [capacity] * n_vehicles,
        'depot': 0,
    }

    manager = pywrapcp.RoutingIndexManager(
        len(data['distance_matrix']), n_vehicles, 0,
    )
    routing = pywrapcp.RoutingModel(manager)

    def distance_cb(from_i, to_i):
        return int(data['distance_matrix']
                    [manager.IndexToNode(from_i)]
                    [manager.IndexToNode(to_i)])

    routing.SetArcCostEvaluatorOfAllVehicles(
        routing.RegisterTransitCallback(distance_cb),
    )

    def demand_cb(from_i):
        return data['demands'][manager.IndexToNode(from_i)]

    routing.AddDimensionWithVehicleCapacity(
        routing.RegisterUnaryTransitCallback(demand_cb),
        0, data['vehicle_capacities'], True, 'Capacity',
    )

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    with st.spinner('Solving VRP (OR-Tools)...'):
        solution = routing.SolveWithParameters(params)

    if not solution:
        return None

    # Extract routes and vehicle assignments
    all_routes, node_to_vehicle = [], {}
    for vid in range(n_vehicles):
        idx = routing.Start(vid)
        route, seq = [], 0
        while not routing.IsEnd(idx):
            nid = manager.IndexToNode(idx)
            route.append({
                'name': names[nid],
                'coord': coords[nid],
                'demand': demands[nid],
            })
            if nid != 0:
                node_to_vehicle[names[nid]] = f"Vehicle {vid + 1} (Stop {seq})"
            idx = solution.Value(routing.NextVar(idx))
            seq += 1
        # Close the loop back to depot
        nid = manager.IndexToNode(idx)
        route.append({
            'name': names[nid], 'coord': coords[nid], 'demand': demands[nid],
        })
        if len(route) > 2:
            all_routes.append(route)

    # Fetch street-level geometries
    geometries = []
    with st.spinner('Fetching street-level geometries...'):
        for r in all_routes:
            resp = client.directions(
                coordinates=[p['coord'] for p in r],
                profile=profile, format='geojson',
            )
            geometries.append([
                (c[1], c[0])
                for c in resp['features'][0]['geometry']['coordinates']
            ])

    return {
        'routes': all_routes,
        'geometries': geometries,
        'node_to_vehicle': node_to_vehicle,
    }


def render_map(results: dict, locations_df: pd.DataFrame) -> None:
    """Render the optimized fleet map with Folium."""
    st.header('Optimized Fleet Map')

    lats = locations_df['Latitude']
    lons = locations_df['Longitude']
    fmap = folium.Map()
    fmap.fit_bounds([[lats.min(), lons.min()], [lats.max(), lons.max()]])

    # Location markers
    n2v = results.get('node_to_vehicle', {})
    for idx, row in locations_df.iterrows():
        assignment = n2v.get(row['Name'], "Depot")
        folium.Marker(
            [row['Latitude'], row['Longitude']],
            popup=(
                f"<b>{row['Name']}</b><br>"
                f"Demand: {row['Demand']}<br>"
                f"Assigned to: {assignment}"
            ),
            icon=folium.Icon(color='black' if idx == 0 else 'gray'),
        ).add_to(fmap)

    # Route polylines and sequence markers
    for i, (route, geom) in enumerate(
        zip(results['routes'], results['geometries'])
    ):
        color = ROUTE_COLORS[i % len(ROUTE_COLORS)]
        folium.PolyLine(
            geom, color=color, weight=5, opacity=0.8,
            tooltip=f"Vehicle {i + 1}",
        ).add_to(fmap)

        for seq, pt in enumerate(route[:-1]):
            if seq > 0:  # Skip depot
                folium.CircleMarker(
                    [pt['coord'][1], pt['coord'][0]],
                    radius=10, color=color, fill=True, fill_color=color,
                    popup=f"Vehicle {i + 1} - Stop {seq}: {pt['name']}",
                    tooltip=f"Vehicle {i + 1} - Stop {seq}",
                ).add_to(fmap)

    st_folium(fmap, use_container_width=True, height=600)


def render_summary(results: dict) -> None:
    """Render the fleet performance summary expanders."""
    st.header('Fleet Performance Summary')
    for i, route in enumerate(results['routes']):
        with st.expander(f"🚛 Vehicle {i + 1} Details", expanded=True):
            names = [p['name'] for p in route]
            load = sum(p['demand'] for p in route)
            st.write(f"**Sequence:** {' → '.join(names)}")
            st.metric("Load Carried", f"{load} units")
    st.info(
        "💡 Tip: You can download the map using the browser save feature "
        "or export data results."
    )


# ──────────────────────────────────────────────
# Page Config & State
# ──────────────────────────────────────────────
st.set_page_config(page_title="VRP Solver", layout="wide")
init_state()

# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────
st.title('Capacitated Vehicle Routing Problem (CVRP) Solver')
st.write('Optimize routes for multiple vehicles with load constraints')

st.markdown("---")
st.markdown("**References**")
st.markdown(
    "[1] Vehicle Routing Problem — "
    "https://en.wikipedia.org/wiki/Vehicle_routing_problem"
)
st.markdown(
    "[2] Google OR-Tools CVRP — "
    "https://developers.google.com/optimization/routing/cvrp"
)
st.markdown(
    "[3] OpenRouteService — "
    "https://openrouteservice.org/"
)
st.markdown("---")

# ── Step 1: Configuration ────────────────────
st.header('Step 1: Configuration')
api_key = st.text_input(
    'OpenRouteService API Key:', type='password',
    help='Get your free API key from https://openrouteservice.org/',
)
col1, col2 = st.columns(2)
with col1:
    transport_profile = st.selectbox(
        'Transport Profile:',
        options=['foot-walking', 'driving-car', 'cycling-regular', 'driving-hgv'],
    )
with col2:
    st.info(
        "The first location in your list will always be treated as the "
        "**Depot** (Starting/Ending point)."
    )

# ── Step 2: Locations & Demands ──────────────
st.header('Step 2: Locations & Demands')

# CSV upload (must precede widgets that share state keys)
with st.expander("📂 Optional: Upload Locations via CSV"):
    st.info(
        'ℹ️ **Format:** CSV with 4 columns: Name, Latitude, Longitude, Demand. '
        'The first row is the Depot.'
    )
    uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])
    if uploaded_file is not None:
        process_csv(uploaded_file)
    else:
        st.session_state.last_processed_file = None

# Row count control
new_count = st.number_input(
    'Number of Locations:', min_value=1, max_value=50,
    value=st.session_state.vrp_num_locations,
    key='vrp_num_locations',
    help=(
        "Set the number of rows in the table below. "
        "Adding locations will append empty rows; "
        "reducing will remove rows from the bottom."
    ),
)
resize_df(new_count)

# Data editor
st.subheader("Edit Locations & Demands Below")
edited_df = st.data_editor(
    st.session_state.vrp_locations_df,
    num_rows="dynamic", use_container_width=True,
    key=f"editor_{st.session_state.editor_version}",
    column_config={
        "Name": st.column_config.TextColumn("Name", required=True),
        "Latitude": st.column_config.NumberColumn(
            "Lat", required=True, format="%.6f",
        ),
        "Longitude": st.column_config.NumberColumn(
            "Long", required=True, format="%.6f",
        ),
        "Demand": st.column_config.NumberColumn(
            "Demand", required=True, min_value=0,
        ),
    },
)
st.session_state.vrp_locations_df = edited_df

# ── Step 3: Fleet Configuration ──────────────
st.header('Step 3: Fleet Configuration')
total_demand = int(edited_df['Demand'].sum())
max_demand = int(edited_df['Demand'].max())

col_v1, col_v2 = st.columns(2)
with col_v1:
    vehicle_capacity = st.number_input(
        'Vehicle Capacity (units):', min_value=1, max_value=10000,
        value=st.session_state.vrp_capacity, key='vrp_capacity',
    )
    if vehicle_capacity < max_demand:
        st.warning(
            f"⚠️ **Caution:** Your vehicle capacity ({vehicle_capacity}) is less "
            f"than the maximum demand of a single location ({max_demand}). "
            "This will make the problem impossible to solve."
        )

with col_v2:
    suggested = -(-total_demand // vehicle_capacity)  # ceil division
    num_vehicles = st.number_input(
        'Number of Vehicles:', min_value=1, max_value=20,
        value=st.session_state.vrp_num_vehicles, key='vrp_num_vehicles',
        help=(
            f"Based on total demand ({total_demand}) and capacity "
            f"({vehicle_capacity}), the minimum required is {suggested}."
        ),
    )

# ── Solve ─────────────────────────────────────
if api_key and st.button('Optimize VRP Routes', type='primary'):
    try:
        client = openrouteservice.Client(key=api_key)
        result = solve_vrp(
            client, transport_profile, edited_df,
            vehicle_capacity, num_vehicles,
        )
        if result:
            st.session_state.vrp_results = result
        else:
            st.error(
                "No solution found. Try increasing the number of "
                "vehicles or their capacity."
            )
    except Exception as e:
        st.error(f"Error during optimization: {e}")

# ── Results ───────────────────────────────────
if st.session_state.vrp_results:
    res = st.session_state.vrp_results
    st.success(f"✓ Optimized {len(res['routes'])} valid routes!")
    render_map(res, st.session_state.vrp_locations_df)
    render_summary(res)
elif not api_key:
    st.info("👋 Enter your API Key above to begin.")