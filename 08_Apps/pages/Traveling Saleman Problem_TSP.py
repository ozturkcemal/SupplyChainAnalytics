import streamlit as st
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import openrouteservice
import folium
from streamlit_folium import st_folium
import pandas as pd
from folium.plugins import AntPath

# Cache API calls to improve performance
@st.cache_data(show_spinner=False)
def get_distance_matrix(locations, profile, api_key):
    """
    Fetch distance matrix from OpenRouteService.
    Cached to prevent redundant API calls for the same inputs.
    """
    client = openrouteservice.Client(key=api_key)
    matrix = client.distance_matrix(
        locations=locations,
        profile=profile,
        metrics=['distance'],
        units='m'
    )
    return matrix['distances']

@st.cache_data(show_spinner=False)
def get_directions(coordinates, profile, api_key):
    """
    Fetch route geometry from OpenRouteService.
    Cached to prevent redundant API calls for the same inputs.
    """
    client = openrouteservice.Client(key=api_key)
    route = client.directions(
        coordinates=coordinates,
        profile=profile,
        format='geojson'
    )
    return [(c[1], c[0]) for c in route['features'][0]['geometry']['coordinates']]

def solve_tsp(distance_matrix, depot_index=0):
    """
    Solve TSP using Google OR-Tools.
    Returns the optimized path indices and the total distance.
    """
    num_locations = len(distance_matrix)
    num_vehicles = 1
    
    # Create routing model
    manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(distance_matrix[from_node][to_node])

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        index = routing.Start(0)
        route_indices = []
        while not routing.IsEnd(index):
            route_indices.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        route_indices.append(manager.IndexToNode(index))  # Return to depot
        
        return route_indices, solution.ObjectiveValue()
    return None, 0

st.title('TSP Solver')
st.write('Calculate the shortest route for an uncapacitated single vehicle to visit multiple locations')

st.markdown("---")
st.markdown("**References**")
st.markdown(
    "[1] Traveling Salesman Problem. "
    "https://www.math.uwaterloo.ca/tsp/"
)
st.markdown(
    "[2] Google OR-Tools. "
    "https://developers.google.com/optimization/routing/tsp"
)
st.markdown(
    "[3] OpenRouteService. "
    "https://openrouteservice.org/"
)
st.markdown("---")

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = None


st.header('Step 1: Enter OpenRouteService API Key')
api_key = st.text_input('API Key:', type='password', help='Get your free API key from https://openrouteservice.org/')

if api_key:
    # Transport profile selection
    st.header('Step 2: Select Transport Profile')
    transport_profile = st.selectbox(
        'Select routing profile:',
        options=['foot-walking', 'driving-car', 'cycling-regular', 'driving-hgv'],
        index=0,
        help='Choose how the route should be calculated'
    )

    
    st.header('Step 3: Locations')

    # Option to upload CSV or use manual entry
    st.write('**Choose input method:**')
    input_method = st.radio(
        'Select how to enter locations:',
        options=['Manual Entry', 'Upload CSV File'],
        index=0,
        horizontal=True
    )
    
    if input_method == 'Upload CSV File':
        st.info('ℹ️ **CSV File Format:** Your CSV file must contain exactly 3 columns: Location, Latitude, Longitude. No headers are required, and the number of rows should equal the number of locations you want to visit.')
        
        uploaded_file = st.file_uploader(
            'Choose a CSV file',
            type=['csv'],
            help='Upload a CSV file with columns: Location, Latitude, Longitude'
        )
        
        if uploaded_file is not None:
            try:
                # Read the CSV file
                uploaded_df = pd.read_csv(uploaded_file, header=None, names=['Location', 'Latitude', 'Longitude'])
                
                # Validate the dataframe
                if len(uploaded_df.columns) != 3:
                    st.error('CSV file must have exactly 3 columns: Location, Latitude, Longitude')
                elif uploaded_df.empty:
                    st.error('CSV file is empty')
                else:
                    # Update session state
                    st.session_state.num_locations = len(uploaded_df)
                    st.session_state.locations_df = uploaded_df
                    st.success(f'✓ Successfully loaded {len(uploaded_df)} locations from CSV')
                    
                    # Display the uploaded data
                    st.write('**Uploaded locations:**')
                    st.dataframe(uploaded_df, use_container_width=True)
                    
            except Exception as e:
                st.error(f'Error reading CSV file: {str(e)}')
    
    else:  # Manual Entry
        # Initialize session state for locations
        if 'num_locations' not in st.session_state:
            st.session_state.num_locations = 5
        if 'locations_df' not in st.session_state:
            st.session_state.locations_df = pd.DataFrame({
                'Location': [''] * st.session_state.num_locations,
                'Latitude': [0.0] * st.session_state.num_locations,
                'Longitude': [0.0] * st.session_state.num_locations
            })
        
        # Ask for number of locations
        num_locations = st.number_input(
            'Number of locations (N):',
            min_value=2,
            max_value=50,
            value=st.session_state.num_locations,
            step=1,
            help='Enter the number of locations to visit'
        )
        
        # Update dataframe if number changed
        if num_locations != st.session_state.num_locations:
            st.session_state.num_locations = num_locations
            st.session_state.locations_df = pd.DataFrame({
                'Location': [''] * num_locations,
                'Latitude': [0.0] * num_locations,
                'Longitude': [0.0] * num_locations
            })
        
        # Display data editor
        st.write('Enter location details:')
        edited_df = st.data_editor(
            st.session_state.locations_df,
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "Location": st.column_config.TextColumn("Location", required=True),
                "Latitude": st.column_config.NumberColumn("Latitude", required=True, format="%.6f"),
                "Longitude": st.column_config.NumberColumn("Longitude", required=True, format="%.6f")
            }
        )
        
        st.session_state.locations_df = edited_df
    
    # Convert dataframe to coordinates list format (works for both input methods)
    coordinates = []
    if 'locations_df' in st.session_state:
        for idx, row in st.session_state.locations_df.iterrows():
            if row['Location'] and row['Latitude'] != 0.0 and row['Longitude'] != 0.0:
                # ORS requires [Longitude, Latitude]
                coordinates.append([row['Longitude'], row['Latitude'], row['Location']])
    
    if st.button('Solve TSP', type='primary'):
        try:
            with st.spinner('Calculating optimal route...'):
                locations_coords = [coord[:2] for coord in coordinates]
                
                # Get distance matrix
                distance_matrix = get_distance_matrix(locations_coords, transport_profile, api_key)
                
                # Solve TSP
                route_indices, total_distance = solve_tsp(distance_matrix)
                
                if route_indices:
                    # Get optimized order
                    optimized_coords = [coordinates[i] for i in route_indices]
                    
                    # Get actual route from ORS
                    route_coords = get_directions(
                        [coord[:2] for coord in optimized_coords],
                        transport_profile,
                        api_key
                    )
                    
                    st.session_state.results = {
                        'optimized_coords': optimized_coords,
                        'route_coords': route_coords,
                        'total_distance': total_distance
                    }
                else:
                    st.error('No solution found.')
            
        except Exception as e:
            st.error(f'Error: {str(e)}')

# Display results if available
if st.session_state.results:
    results = st.session_state.results
    
    st.success('✓ Route optimized successfully!')
    
    # Display route information
    st.header('Optimized Route')
    route_labels = [label for _, _, label in results['optimized_coords']]
    st.write(' → '.join(route_labels))
    
    st.metric('Total Distance', f"{results['total_distance'] / 1000:.2f} km")
    
    # Create and display complete map with full route
    st.header('Route Map')
    fmap = folium.Map(
        location=[results['optimized_coords'][0][1], results['optimized_coords'][0][0]],
        zoom_start=15
    )
    
    # Add numbered markers
    for idx, (lon, lat, label) in enumerate(results['optimized_coords'][:-1]):
        folium.Marker(
            [lat, lon],
            popup=f"{idx + 1}. {label}",
            icon=folium.Icon(color='red' if idx == 0 else 'blue')
        ).add_to(fmap)
    
    # Draw complete route with AntPath
    AntPath(
        locations=results['route_coords'],
        color='blue',
        weight=5,
        opacity=0.7,
        delay=1000,
        pulse_color='#FFFFFF'
    ).add_to(fmap)
    
    st_folium(fmap, width=700, height=500)
else:
    st.info('👆 Please enter your OpenRouteService API key to start (https://openrouteservice.org/)')
