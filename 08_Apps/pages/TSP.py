import streamlit as st
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import openrouteservice
import folium
from streamlit_folium import st_folium
import time

st.title('TSP Solver')
st.write('Calculate the shortest route for a single vehicle to visit multiple locations')

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = None
if 'animate' not in st.session_state:
    st.session_state.animate = False

# Default coordinates
default_coordinates = [
    [-8.4773019737901, 51.89801157949557, "Liberty Bar"],
    [-8.47839267379017, 51.89754580132632, "Dwyers"],
    [-8.480129616118258, 51.897412860783, "Costigans"],
    [-8.48210270262587, 51.90122750985092, "Franciscan Well"],
    [-8.478174116118428, 51.89376597099192, "Tom Barry's"],
    [-8.470903544953982, 51.901992373046355, "Corner House"],
    [-8.47113337564154, 51.90199549372547, "Sin E'"],
    [-8.4765895179699, 51.896701021615215, "An Spailpin Fanach"],
    [-8.47664922081232, 51.89677734873688, "The Oval"],
    [-8.466700360297953, 51.897178061440265, "Charlies"],
    [-8.470990660298165, 51.89379653393844, "Fionbarra"],
    [-8.469605244954147, 51.89843912054248, "The Oliver Plunkett"]
]

st.header('Step 1: Enter OpenRouteService API Key')
api_key = st.text_input('API Key:', type='password', help='Get your free API key from https://openrouteservice.org/')

if api_key:
    client = openrouteservice.Client(key=api_key)
    
    st.header('Step 2: Locations')
    st.write('Using default Cork pub locations:')
    for coord in default_coordinates:
        st.write(f"- {coord[2]} ({coord[1]:.4f}, {coord[0]:.4f})")
    
    # Animation speed control
    animation_speed = st.slider('Animation Speed (seconds per segment)', 0.1, 2.0, 0.5, 0.1)
    
    if st.button('Solve TSP', type='primary'):
        try:
            with st.spinner('Calculating optimal route...'):
                # Get distance matrix
                matrix = client.distance_matrix(
                    locations=[coord[:2] for coord in default_coordinates],
                    profile='foot-walking',
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
                manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), data['num_vehicles'], data['depot'])
                routing = pywrapcp.RoutingModel(manager)
                
                def distance_callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    return int(data['distance_matrix'][from_node][to_node])
                
                transit_callback_index = routing.RegisterTransitCallback(distance_callback)
                routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
                
                search_parameters = pywrapcp.DefaultRoutingSearchParameters()
                search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
                
                solution = routing.SolveWithParameters(search_parameters)
                
                if solution:
                    # Get optimized order
                    optimized_coords = []
                    index = routing.Start(0)
                    while not routing.IsEnd(index):
                        node_index = manager.IndexToNode(index)
                        optimized_coords.append(default_coordinates[node_index])
                        index = solution.Value(routing.NextVar(index))
                    optimized_coords.append(default_coordinates[manager.IndexToNode(index)])
                    
                    # Get actual route from ORS
                    route = client.directions(
                        coordinates=[coord[:2] for coord in optimized_coords],
                        profile='foot-walking',
                        format='geojson'
                    )
                    
                    route_coords = [(c[1], c[0]) for c in route['features'][0]['geometry']['coordinates']]
                    
                    # Calculate total distance
                    coordinate_to_index = {(lon, lat): idx for idx, (lon, lat, _) in enumerate(default_coordinates)}
                    total_distance = 0
                    for i in range(len(optimized_coords) - 1):
                        lon1, lat1, _ = optimized_coords[i]
                        lon2, lat2, _ = optimized_coords[i + 1]
                        idx1 = coordinate_to_index[(lon1, lat1)]
                        idx2 = coordinate_to_index[(lon2, lat2)]
                        total_distance += distance_matrix[idx1][idx2]
                    
                    # Store results in session state
                    st.session_state.results = {
                        'optimized_coords': optimized_coords,
                        'route_coords': route_coords,
                        'total_distance': total_distance,
                        'distance_matrix': distance_matrix,
                        'coordinate_to_index': coordinate_to_index,
                        'animation_speed': animation_speed
                    }
                    st.session_state.animate = True
                    
                else:
                    st.error('No solution found')
                    
        except Exception as e:
            st.error(f'Error: {str(e)}')
            st.info('Please check your API key and try again.')
    
    # Display results with animation
    if st.session_state.results:
        results = st.session_state.results
        
        st.success('✅ Optimal route found!')
        
        st.header('Optimized Route')
        route_labels = [label for _, _, label in results['optimized_coords']]
        st.write(' → '.join(route_labels))
        
        # Create map with markers
        st.header('Route Visualization')
        
        # Create base map with all markers
        fmap = folium.Map(
            location=[results['optimized_coords'][0][1], results['optimized_coords'][0][0]], 
            zoom_start=15
        )
        
        # Add all markers
        for idx, (lon, lat, label) in enumerate(results['optimized_coords']):
            folium.Marker(
                [lat, lon], 
                popup=f"{idx + 1}. {label}",
                icon=folium.Icon(color='red' if idx == 0 else 'blue')
            ).add_to(fmap)
        
        # Animate route if requested
        if st.session_state.animate:
            # Find segments in the actual route
            segments = []
            segment_start = 0
            
            for i in range(len(results['optimized_coords']) - 1):
                # Find where this leg ends in route_coords
                target_lat = results['optimized_coords'][i + 1][1]
                target_lon = results['optimized_coords'][i + 1][0]
                
                for j in range(segment_start, len(results['route_coords'])):
                    if abs(results['route_coords'][j][0] - target_lat) < 0.0001 and abs(results['route_coords'][j][1] - target_lon) < 0.0001:
                        segments.append(results['route_coords'][segment_start:j+1])
                        segment_start = j
                        break
            
            # Create placeholder for map and distance
            map_placeholder = st.empty()
            distance_placeholder = st.empty()
            progress_bar = st.progress(0)
            
            # Animate each segment
            accumulated_distance = 0
            for seg_idx, segment in enumerate(segments):
                # Add this segment to map
                current_map = folium.Map(
                    location=[results['optimized_coords'][0][1], results['optimized_coords'][0][0]], 
                    zoom_start=15
                )
                
                # Add all markers
                for idx, (lon, lat, label) in enumerate(results['optimized_coords']):
                    folium.Marker(
                        [lat, lon], 
                        popup=f"{idx + 1}. {label}",
                        icon=folium.Icon(color='red' if idx == 0 else 'blue')
                    ).add_to(current_map)
                
                # Add segments up to current one
                for i in range(seg_idx + 1):
                    folium.PolyLine(
                        locations=segments[i], 
                        color='blue', 
                        weight=5, 
                        opacity=0.7
                    ).add_to(current_map)
                
                # Calculate accumulated distance
                if seg_idx < len(results['optimized_coords']) - 1:
                    lon1, lat1, _ = results['optimized_coords'][seg_idx]
                    lon2, lat2, _ = results['optimized_coords'][seg_idx + 1]
                    idx1 = results['coordinate_to_index'][(lon1, lat1)]
                    idx2 = results['coordinate_to_index'][(lon2, lat2)]
                    accumulated_distance += results['distance_matrix'][idx1][idx2]
                
                # Update displays
                with map_placeholder:
                    st_folium(current_map, width=700, height=500, key=f"map_{seg_idx}")
                
                with distance_placeholder:
                    st.metric('Distance Traveled', f"{accumulated_distance / 1000:.2f} km", 
                             f"of {results['total_distance'] / 1000:.2f} km total")
                
                progress_bar.progress((seg_idx + 1) / len(segments))
                
                # Delay before next segment
                if seg_idx < len(segments) - 1:
                    time.sleep(results['animation_speed'])
            
            st.session_state.animate = False
            progress_bar.empty()
            
        else:
            # Show final complete route
            folium.PolyLine(
                locations=results['route_coords'], 
                color='blue', 
                weight=5, 
                opacity=0.7
            ).add_to(fmap)
            
            st_folium(fmap, width=700, height=500)
            st.metric('Total Distance', f"{results['total_distance'] / 1000:.2f} km")
        
else:
    st.info('👆 Please enter your OpenRouteService API key to start')
