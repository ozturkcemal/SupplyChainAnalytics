import streamlit as st
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import openrouteservice
import folium
from streamlit_folium import st_folium
import pandas as pd

st.title('TSP Solver')
st.write('Calculate the shortest route for a single vehicle to visit multiple locations')

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = None


st.header('Step 1: Enter OpenRouteService API Key')
api_key = st.text_input('API Key:', type='password', help='Get your free API key from https://openrouteservice.org/')

if api_key:
    client = openrouteservice.Client(key=api_key)

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
        st.info('ℹ️ **CSV File Format:** Your CSV file must contain exactly 3 columns: Name, Longitude, Latitude. No headers are required, and the number of rows should equal the number of locations you want to visit.')
        
        uploaded_file = st.file_uploader(
            'Choose a CSV file',
            type=['csv'],
            help='Upload a CSV file with columns: Name, Longitude, Latitude'
        )
        
        if uploaded_file is not None:
            try:
                # Read the CSV file
                uploaded_df = pd.read_csv(uploaded_file, header=None, names=['Name', 'Longitude', 'Latitude'])
                
                # Validate the dataframe
                if len(uploaded_df.columns) != 3:
                    st.error('CSV file must have exactly 3 columns: Name, Longitude, Latitude')
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
                'Name': [''] * st.session_state.num_locations,
                'Longitude': [0.0] * st.session_state.num_locations,
                'Latitude': [0.0] * st.session_state.num_locations
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
                'Name': [''] * num_locations,
                'Longitude': [0.0] * num_locations,
                'Latitude': [0.0] * num_locations
            })
        
        # Display data editor
        st.write('Enter location details:')
        edited_df = st.data_editor(
            st.session_state.locations_df,
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "Name": st.column_config.TextColumn("Name", required=True),
                "Longitude": st.column_config.NumberColumn("Longitude", required=True, format="%.6f"),
                "Latitude": st.column_config.NumberColumn("Latitude", required=True, format="%.6f")
            }
        )
        
        st.session_state.locations_df = edited_df
        
        # Convert dataframe to coordinates list format
        coordinates = []
        for idx, row in edited_df.iterrows():
            if row['Name'] and row['Longitude'] != 0.0 and row['Latitude'] != 0.0:
                coordinates.append([row['Longitude'], row['Latitude'], row['Name']])    
    if st.button('Solve TSP', type='primary'):
        try:
            with st.spinner('Calculating optimal route...'):
                # Get distance matrix
                matrix = client.distance_matrix(
                    locations=[coord[:2] for coord in coordinates],
                    profile=transport_profile,
                    metrics=['distance'],
                    units='m'
                )
                distance_matrix = matrix['distances']
                
                # Create data model
                data = {}
                data['distance_matrix'] = distance_matrix
                data['num_vehicles'] = 1
                data['depot'] = 0
                
                # Create routing model
                manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), 
                                                       data['num_vehicles'], 
                                                       data['depot'])
                routing = pywrapcp.RoutingModel(manager)
                
                def distance_callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    return int(data['distance_matrix'][from_node][to_node])
                
                transit_callback_index = routing.RegisterTransitCallback(distance_callback)
                routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
                
                search_parameters = pywrapcp.DefaultRoutingSearchParameters()
                search_parameters.first_solution_strategy = (
                    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
                
                solution = routing.SolveWithParameters(search_parameters)
                
                if solution:
                    # Get optimized order
                    optimized_coords = []
                    index = routing.Start(0)
                    while not routing.IsEnd(index):
                        node_index = manager.IndexToNode(index)
                        optimized_coords.append(coordinates[node_index])
                        index = solution.Value(routing.NextVar(index))
                    optimized_coords.append(coordinates[manager.IndexToNode(index)])
                    
                    # Get actual route from ORS
                    route = client.directions(
                        coordinates=[coord[:2] for coord in optimized_coords],
                        profile=transport_profile,
                        format='geojson'
                    )
                    
                    # Extract route coordinates
                    route_coords = [(c[1], c[0]) for c in route['features'][0]['geometry']['coordinates']]
                    
                    # Calculate total distance
                    coordinate_to_index = {
                        (lon, lat): idx for idx, (lon, lat, _) in enumerate(coordinates)
                    }
                    total_distance = 0
                    for i in range(len(optimized_coords) - 1):
                        lon1, lat1, _ = optimized_coords[i]
                        lon2, lat2, _ = optimized_coords[i + 1]
                        idx1 = coordinate_to_index[(lon1, lat1)]
                        idx2 = coordinate_to_index[(lon2, lat2)]
                        total_distance += distance_matrix[idx1][idx2]
                    
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
    
    # Draw complete route
    folium.PolyLine(
        locations=results['route_coords'],
        color='blue',
        weight=5,
        opacity=0.7
    ).add_to(fmap)
    
    st_folium(fmap, width=700, height=500)
else:
    st.info('👆 Please enter your OpenRouteService API key to start (https://openrouteservice.org/)')
