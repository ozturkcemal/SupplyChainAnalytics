# Supply Chain Analytics Suite

A comprehensive Streamlit-based web application for supply chain optimization, featuring both inventory management and routing analytics tools.

## 📁 Project Structure

```
08_Apps/
├── SupplyChainAnalyticSuite.py         # Main entry point
├── pages/                               # Multi-page Streamlit apps
│   ├── 1_EOQ_Calculator.py             # Economic Order Quantity
│   ├── 2_EOQ_wBackorders.py            # EOQ with Backorders
│   ├── 3_JointReplenishment.py         # Joint Replenishment Problem
│   ├── 4_Newsvendor.py                 # Newsvendor Model
│   ├── 5_PeriodicReview(WagnerWhitin).py # Wagner-Whitin Algorithm
│   ├── RoutingApps.py                  # Routing optimization hub
│   ├── Traveling Saleman Problem_TSP.py # Traveling Salesman Problem solver
│   └── Vehicle_Routing_Problem_VRP.py   # Vehicle Routing Problem solver (CVRP)
├── routing/                             # Routing notebooks and data
│   └── TSP_singleCellNotebook.ipynb
├── .streamlit/                          # Streamlit configuration
│   └── config.toml                     # App configuration
└── requirements.txt                     # Python dependencies
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Streamlit

### Installation

```bash
pip install -r requirements.txt
```

### Running the Application

```bash
streamlit run SupplyChainAnalyticSuite.py
```

The application will start and be accessible at `http://localhost:8501`

## 📊 Features

### Inventory Optimization Tools

- **EOQ Calculator**: Calculate optimal order quantities for inventory management
- **EOQ with Backorders**: EOQ model allowing for planned stockouts
- **Joint Replenishment**: Optimize ordering for multiple products
- **Newsvendor Model**: Optimize inventory for products with uncertain demand
- **Periodic Review (Wagner-Whitin)**: Dynamic lot-sizing algorithm

### Routing Optimization Tools

- **TSP (Traveling Salesman Problem)**: Solve the classic TSP to find the shortest route visiting all locations for a single uncapacitated vehicle.
- **VRP (Vehicle Routing Problem)**: Solve the Capacitated Vehicle Routing Problem (CVRP) for a fleet of vehicles with load constraints.
  - **Dynamic Fleet Configuration**: Specify number of vehicles and individual vehicle capacities.
  - **Demand Management**: Assign specific "order sizes" or demands to each location.
  - **Multi-Route Visualization**: Each vehicle's path is rendered in a distinct color for easy identification.
  - **Stop Sequence Markers**: Clear numbering of stops for each vehicle route.
  - **ORS & OR-Tools**: Similar to TSP, leverages OpenRouteService for road data and Google OR-Tools for optimization.

## 🏗️ Architecture

This application uses Streamlit's multi-page app architecture:

- **Main App (`SupplyChainAnalyticSuite.py`)**: Landing page with navigation
- **Pages Folder**: Each file in `pages/` becomes a separate app accessible via sidebar navigation
- **Configuration**: `.streamlit/config.toml` specifies the main entry file

## 📝 Configuration

The `.streamlit/config.toml` file configures the application:

```toml
[server]
mainfile = "08_Apps/SupplyChainAnalyticSuite.py"
```

## 🔑 API Keys

The TSP and VRP solvers require an OpenRouteService API key:
1. Sign up for a free account at [openrouteservice.org](https://openrouteservice.org/)
2. Generate your API key
3. Enter the key in the application interface (it will be remembered for the session)

## 🤝 Contributing

Feel free to submit issues or pull requests to improve the application.

## 📧 Contact

For questions or feedback: cemalettin.ozturk01@gmail.com

## 📄 License

See LICENSE file for details.
