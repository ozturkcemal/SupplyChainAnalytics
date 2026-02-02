# Supply Chain Analytics Suite

A comprehensive Streamlit-based web application for supply chain optimization, featuring both inventory management and routing analytics tools.

## 📁 Project Structure

```
08_Apps/
├── SupplyChainAnalyticSuite.py    # Main entry point
├── pages/                          # Multi-page Streamlit apps
│   ├── RoutingApps.py             # Routing optimization tools
│   ├── 1_EOQ_Calculator.py        # Economic Order Quantity
│   ├── 2_EOQ_wBackorders.py       # EOQ with Backorders
│   ├── 3_JointReplenishment.py    # Joint Replenishment Problem
│   ├── 4_Newsvendor.py            # Newsvendor Model
│   └── 5_PeriodicReview(WagnerW..)# Wagner-Whitin Algorithm
├── routing/                        # Routing notebooks and data
│   └── TSP_singleCellNotebook.ipynb
├── .streamlit/                     # Streamlit configuration
│   └── config.toml                # App configuration
└── requirements.txt                # Python dependencies
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
- **TSP (Traveling Salesman Problem)**: Find shortest route visiting all locations
- **VRP (Vehicle Routing Problem)**: Optimize routes for multiple vehicles
- **mVRP (Multi-depot VRP)**: Route optimization with multiple depots
- **VRPTW (VRP with Time Windows)**: Route optimization with delivery time constraints

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

## 🤝 Contributing

Feel free to submit issues or pull requests to improve the application.

## 📧 Contact

For questions or feedback: cemalettin.ozturk01@gmail.com

## 📄 License

See LICENSE file for details.
