# Supply Chain Analytics Suite

A comprehensive Streamlit-based web application for supply chain optimization, featuring both inventory management and routing analytics tools.

## 📁 Project Structure

```
08_Apps/
├── SupplyChainAnalyticSuite.py  # Main entry point
├── pages/                        # Multi-page Streamlit apps
│   ├── RoutingApps.py           # Routing optimization tools
│   ├── TSP.py                   # Traveling Salesman Problem solver
│   ├── 1_EOQ_Calculator.py      # Economic Order Quantity
│   ├── 2_EOQ_wBackorders.py     # EOQ with Backorders
│   ├── 3_JointReplenishment.py  # Joint Replenishment Problem
│   ├── 4_Newsvendor.py          # Newsvendor Model
│   └── 5_PeriodicReview(WagnerW..)# Wagner-Whitin Algorithm
├── routing/                      # Routing notebooks and data
│   └── TSP_singleCellNotebook.ipynb
├── .streamlit/                   # Streamlit configuration
│   └── config.toml              # App configuration
└── requirements.txt              # Python dependencies
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

- **TSP (Traveling Salesman Problem)**: Solve the classic TSP to find the shortest route visiting all locations
  - **Multiple Transport Profiles**: Choose from foot-walking, driving-car, cycling-regular, or driving-hgv
  - **Flexible Location Input**: Enter locations manually or upload via CSV file
  - **Interactive Map Visualization**: View optimized routes with numbered markers on an interactive map
  - **Real-world Routing**: Uses OpenRouteService API for actual road network routing
  - **Google OR-Tools Integration**: Leverages powerful optimization algorithms for finding optimal solutions

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

The TSP solver requires an OpenRouteService API key:
1. Sign up for a free account at [openrouteservice.org](https://openrouteservice.org/)
2. Generate your API key
3. Enter the key in the TSP application interface

## 🤝 Contributing

Feel free to submit issues or pull requests to improve the application.

## 📧 Contact

For questions or feedback: cemalettin.ozturk01@gmail.com

## 📄 License

See LICENSE file for details.
