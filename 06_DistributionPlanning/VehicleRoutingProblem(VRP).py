
# Step 0 : Install and import necessary libraries
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import openrouteservice
from ipyleaflet import Map, Polyline, Marker, Popup
from ipywidgets import HTML
from IPython.display import display
import time
import getpass
import folium

from pathlib import Path

# Step 1: Set coordinates with labels and API key
coordinates = [
    [-8.4773019737901, 51.89801157949557, "Liberty Bar",100],
    [-8.47839267379017, 51.89754580132632, "Dwyers",100],
    [-8.480129616118258, 51.897412860783, "Costigans",100],
    [-8.48210270262587, 51.90122750985092, "Franciscan Well",100],
    [-8.478174116118428, 51.89376597099192, "Tom Barry's",100],
    [-8.470903544953982, 51.901992373046355, "Corner House",100],
    [-8.47113337564154, 51.90199549372547, "Sin E'",100],
    [-8.4765895179699, 51.896701021615215, "An Spailpin Fanach",100],
    [-8.47664922081232, 51.89677734873688, "The Oval",100],
    [-8.466700360297953, 51.897178061440265, "Charlies",100],
    [-8.470990660298165, 51.89379653393844, "Fionbarra",100],
    [-8.469605244954147, 51.89843912054248, "The Oliver Plunkett",100]
]

# Get ORS API key
api_key = input('Enter your OpenRouteService API key: ')
client = openrouteservice.Client(key=api_key)

# Step 2: Get distance matrix
matrix = client.distance_matrix(
    locations=[coord[:2] for coord in coordinates],  # Extract only lon, lat
    profile='foot-walking',
    metrics=['distance'],
    units='m'
)
distance_matrix = matrix['distances']

# Step 3: OR-Tools VRP solver (CVRP)
def create_data_model():
    data = {}
    data['distance_matrix'] = distance_matrix
    data['demands'] = [coord[3] for coord in coordinates]
    data['num_vehicles'] = 4  # Increased to handle multiple routes
    data['vehicle_capacities'] = [400] * data['num_vehicles']  # Each vehicle can carry 400 units
    data['depot'] = 0
    return data

data = create_data_model()
manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), data['num_vehicles'], data['depot'])
routing = pywrapcp.RoutingModel(manager)

def distance_callback(from_index, to_index):
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    return int(data['distance_matrix'][from_node][to_node])

transit_callback_index = routing.RegisterTransitCallback(distance_callback)
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

# Add Capacity constraint.
def demand_callback(from_index):
    """Returns the demand of the node."""
    # Convert from routing variable Index to distance matrix NodeIndex.
    from_node = manager.IndexToNode(from_index)
    return data['demands'][from_node]

demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
routing.AddDimensionWithVehicleCapacity(
    demand_callback_index,
    0,  # null capacity slack
    data['vehicle_capacities'],  # vehicle maximum capacities
    True,  # start cumul to zero
    'Capacity')

search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

solution = routing.SolveWithParameters(search_parameters)

# Step 4: Get optimized routes for all vehicles
all_routes_coords = []
if solution:
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        vehicle_route = []
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            vehicle_route.append(coordinates[node_index])
            index = solution.Value(routing.NextVar(index))
        vehicle_route.append(coordinates[manager.IndexToNode(index)])
        
        # Only add routes that leave the depot
        if len(vehicle_route) > 2:
            all_routes_coords.append(vehicle_route)
else:
    print("No solution found.")

# Step 5: Request actual routes from ORS for each vehicle
all_vehicle_geometries = []
for optimized_coords in all_routes_coords:
    route = client.directions(
        coordinates=[coord[:2] for coord in optimized_coords],
        profile='foot-walking',
        format='geojson'
    )
    # Extract route coordinates in (lat, lon)
    route_coords = [(c[1], c[0]) for c in route['features'][0]['geometry']['coordinates']]
    all_vehicle_geometries.append(route_coords)

# Step 6: Animate the routes on notebook and save the final routes as a static map
# Colors for different vehicles
colors = ['blue', 'red', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen']

# Animate with ipyleaflet (notebook only)
m = Map(center=(coordinates[0][1], coordinates[0][0]), zoom=14, scroll_wheel_zoom=True, layout={'height': '700px'})
display(m)

# Add markers for all locations once
for lon, lat, label, demand in coordinates:
    popup_text = f"<b>{label}</b><br>Demand: {demand}"
    popup = Popup(location=(lat, lon), child=HTML(value=popup_text), close_button=True, auto_close=False, close_on_click=True)
    m.add_layer(Marker(location=(lat, lon), popup=popup))

# Set animation speed
speed = 0.05  # seconds between segments

# Animate each vehicle's route
for v_idx, route_coords in enumerate(all_vehicle_geometries):
    color = colors[v_idx % len(colors)]
    for i in range(len(route_coords) - 1):
        segment = [route_coords[i], route_coords[i + 1]]
        pl = Polyline(locations=segment, color=color, weight=5)
        m.add_layer(pl)
        time.sleep(speed)

# Save static version of the map using folium
fmap = folium.Map(location=[coordinates[0][1], coordinates[0][0]], zoom_start=14)

# Add markers
for lon, lat, label, demand in coordinates:
    popup_text = f"{label} (Demand: {demand})"
    folium.Marker([lat, lon], popup=popup_text).add_to(fmap)

# Draw all optimized routes
for v_idx, route_coords in enumerate(all_vehicle_geometries):
    color = colors[v_idx % len(colors)]
    folium.PolyLine(locations=route_coords, color=color, weight=5, tooltip=f"Vehicle {v_idx+1}").add_to(fmap)

# Save to HTML
script_dir = Path(__file__).parent
html_file_path = script_dir / 'optimized_vrp_route_map.html'
fmap.save(html_file_path)
print(f"\nStatic VRP route map saved to '{html_file_path}'")

# Step 7: Final report with optimized routes and distances
print("\n" + "="*30)
print("VRP FINAL REPORT")
print("="*30)

total_distance_all_vehicles = 0
for v_idx, optimized_coords in enumerate(all_routes_coords):
    route_labels = [coord[2] for coord in optimized_coords]
    
    # Calculate route distance
    route_distance = 0
    route_demand = 0
    for i in range(len(optimized_coords) - 1):
        # We need the original index to look up distances
        # Finding by label/coord match (simple approach for this specific script)
        c1 = optimized_coords[i]
        c2 = optimized_coords[i+1]
        
        # Match coordinates back to original distance matrix indices
        idx1 = next(idx for idx, c in enumerate(coordinates) if c[0] == c1[0] and c[1] == c1[1])
        idx2 = next(idx for idx, c in enumerate(coordinates) if c[0] == c2[0] and c[1] == c2[1])
        
        route_distance += distance_matrix[idx1][idx2]
        route_demand += coordinates[idx2][3] if i < len(optimized_coords) - 1 else 0 # Don't add depot demand twice

    print(f"\nVehicle {v_idx + 1} Route ({color}):")
    print(" -> ".join(route_labels))
    print(f"Distance: {route_distance / 1000:.2f} km | Load: {route_demand}")
    total_distance_all_vehicles += route_distance

print("\n" + "="*30)
print(f"Total Fleet Distance: {total_distance_all_vehicles / 1000:.2f} km")
print("="*30)