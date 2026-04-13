# Quadratic Facility Location

## Project Overview

This repository contains optimization models and analysis tools for solving the **Quadratic Facility Location Problem** with capacity constraints. The framework supports multiple datasets including:
- **Hampshire** - Household Waste Recycling Centers (HWRCs) in Hampshire, UK
- **Bavaria** - Facility location in Bavaria region, Germany
- **Custom regions** - Easily extend to your own dataset

**Key Features:**
- Mixed-integer quadratic programming (MIQP) models using Pyomo and Gurobi
- Heuristic solutions (greedy algorithms)
- Result caching system for efficient batch processing
- Comprehensive visualization (choropleth maps, heatmaps)

---

## Repository Structure

```
Quadratic_facility_location/
├── data/
│   ├── Hampshire_*.csv              # Hampshire region: users/facilities/capacity
│   ├── Hampshire_*.json.pbz2        # Hampshire: travel/distance dicts (compressed)
│   ├── Bavaria_*.csv                # Bavaria region: users/facilities/capacity
│   ├── Bavaria_*.json.pbz2          # Bavaria: travel/distance dicts (compressed)
│   ├── instance_*.json.pbz2         # Other custom instances
│   └── map_data/
│       ├── all_sectors.geojson      # UK postcode sector boundaries
│       ├── Counties_and_Unitary_Authorities_*.geojson  # Administrative boundaries
│       ├── plz-5stellig.geojson     # German 5-digit PLZ polygon boundaries
│       └── bayern.geojson           # German state boundaries (used for Bavaria border)
├── src/
│   └── models/
│       ├── model.py                 # MIQP optimization model
│       ├── BFLP_MIP.py              # Exact BFLP model
│       ├── BFLP_heuristics.py       # Greedy heuristics for BFLP
│       ├── BUAP_MIP.py              # Exact BUAP model
│       ├── BUAP_heuristics.py       # Heuristics for BUAP
│       ├── result_cache.py          # Caching system (MD5-based key generation)
│       ├── solve_and_cache_models.py  # Pre-solver script (generates all results)
│       ├── heatmap_plot.py          # Visualize maps (Matplotlib + Folium)
│       ├── reassignment_table.py    # Reassignment analysis
│       ├── create_region_figures.py     # Region-parameterized figure generation
│       ├── create_region_tables.py      # Region-parameterized table generation
│       ├── greedy_heuristic.py      # Greedy heuristic algorithms
│       ├── utils.py                 # Data loading and helper functions
│       ├── plotting.py              # Plotting utilities
│       ├── results.py               # Results processing utilities
│       ├── results_heuristics.py    # Heuristic results processing
│       └── figures_and_tables.py    # General figure/table generation
├── own_results/
│   ├── model_cache/                 # Cached JSON results
│   ├── heat_maps/                   # Generated PDF maps
│   ├── reassignment_outputs/        # Reassignment Excel tables
└── README.md                        # This file
```

---

## Installation & Setup

### Prerequisites
- **Python 3.8+**
- **Gurobi 10.0+** (requires license; free academic license available)
- **conda** (recommended for environment management)

### Step 1: Clone and Navigate
```bash
cd Quadratic_facility_location
```

### Step 2: Install Dependencies
```bash
conda create -n facility-loc python=3.10
conda activate facility-loc

# Install required packages
pip install gurobipy pyomo pandas numpy scipy scikit-learn geopy geopandas folium matplotlib contextily adjustText openpyxl
```

### Step 3: Verify Gurobi Installation
```bash
python -c "import gurobipy; print(gurobipy.gurobi.version())"
```

---

## Quick Start Workflow

### Option A: Full Automated Pipeline (Recommended)

```bash
cd src/models

# 1. Pre-solve and cache all models for your region
# For Hampshire (instance 1):
python solve_and_cache_models.py --region Hampshire --instance 1

# For Bavaria (instance 1):
python solve_and_cache_models.py --region Bavaria --instance 1

# For Bavaria (instance 3 or 4):
python solve_and_cache_models.py --region Bavaria --instance 3

# 2. Generate heatmaps (loads from cache)
python heatmap_plot.py --region Hampshire --instance 1
# Output: own_results/heat_maps/{region}_map_static_b*.pdf

# 3. Generate reassignment tables (loads from cache)
python reassignment_table.py --region Hampshire --instance 1
# Output: own_results/reassignment_outputs/Reassignment_*.xlsx
```

### Option B: Generate Individual Outputs

**If models are already cached (from Option A):**

```bash
# Generate heatmaps for a specific region
python heatmap_plot.py --region Hampshire --instance 1
# Output: own_results/heat_maps/hampshire_map_static_b*.pdf 

# Or for Bavaria:
python heatmap_plot.py --region Bavaria --instance 3
# Output: own_results/heat_maps/bavaria_map_static_b*.pdf

# Generate reassignment tables for a specific region
python reassignment_table.py --region Hampshire --instance 1
# Output: own_results/reassignment_outputs/Reassignment_*.xlsx
```

---

## Core Scripts & Usage

### 1. **solve_and_cache_models.py** - Pre-Solver
**Purpose:** Solves optimization models and caches results as JSON  
**When to use:** First time setup or when updating model parameters  

```bash
# Solve for any region and instance
python solve_and_cache_models.py --region <REGION> --instance <INSTANCE>

# Examples:
python solve_and_cache_models.py --region Hampshire --instance 1
python solve_and_cache_models.py --region Bavaria --instance 1
python solve_and_cache_models.py --region Bavaria --instance 3
```

**What it does:**
- Loads dataset for specified region and instance
- Solves MIP model for multiple budget levels: [0.3, 0.4, ..., 1.0] by default
- Caches results as `result_<MD5_hash>.json` in `own_results/model_cache/`

**Region Examples:**
- **Hampshire** - 266 users, 26 facilities
- **Bavaria** (inst 1) - 2060 users, 1394 facilities
- **Bavaria** (inst 3) - 5000 users, 2497 facilities
- **Bavaria** (inst 4) - 1500 users, 425 facilities 

**Output:**
- `own_results/model_cache/result_*.json` (cached results, region-agnostic)

---

### 2. **heatmap_plot.py** - Visualization
**Purpose:** Generates choropleth maps showing distance and utilization by budget  

```bash
# Generate maps for any region and instance
python heatmap_plot.py --region <REGION> --instance <INSTANCE>

# Examples:
python heatmap_plot.py --region Hampshire --instance 1
python heatmap_plot.py --region Bavaria --instance 4
```

**What it does:**
- Computes mean user→facility distance per user (miles for Hampshire, km for Bavaria)
- Computes facility utilization %
- Generates static Matplotlib PDFs

**Output:**
- `own_results/heat_maps/{region}_{instance}_map_static_b{pct}.pdf` (one PDF per budget level)

**Requirements:**
- Cached models (from `solve_and_cache_models.py`)
- `data/map_data/all_sectors.geojson` (Hampshire choropleth)
- `data/map_data/plz-5stellig.geojson` + `data/map_data/bayern.geojson` (Bavaria choropleth)

---

### 3. **reassignment_table.py** - Reassignment Analysis
**Purpose:** Analyzes how users are reassigned when facilities close due to budget constraints  

```bash
# Generate reassignment tables for any region and instance
python reassignment_table.py --region <REGION> --instance <INSTANCE>

# Examples:
python reassignment_table.py --region Hampshire --instance 1
python reassignment_table.py --region Bavaria --instance 3
```

**What it does:**
- Compares baseline scenario with reduced-budget scenarios
- Identifies facilities closed in each scenario
- Tracks which users are reassigned and to which facilities
- Computes reassignment statistics:
  - Population counts by move pair
  - % of population affected per move pair
  - Median distance for each reassignment path

**Output:**
- `own_results/reassignment_outputs/Reassignment_Details_xx%.xlsx` (detailed user-level reassignments)
- `own_results/reassignment_outputs/Reassignment_Summary_xx%.xlsx` (aggregated by move pair)

---

### 4. **create_region_figures.py** - Figure Generation (Any Region)
**Purpose:** Generates analysis plots for a chosen region/instance (same outputs as the Hampshire-only script)  

```bash
# From src/models
python create_region_figures.py --region Hampshire --instance-number 1
python create_region_figures.py --region Bavaria --instance-number 3
```

**Arguments:**
- `--region`: region name (e.g., Hampshire, Bavaria)
- `--instance-number`: dataset instance (default: 1)
- `--base-dir` (optional): workspace root if auto-detection fails

**Output:**
- `own_results/{region}_figure3a_overall_access.pdf`
- `own_results/{region}_figure3b_distance_percentiles.pdf`
- `own_results/{region}_figure4a_utilization_percentiles.pdf`
- `own_results/{region}_figure4b_utilization_distribution.pdf`
- `own_results/{region}_figure5a_strict_vs_loose.pdf`
- `own_results/{region}_figure5b_cutoff_vs_nocutoff.pdf`
- `own_results/{region}_figure6_cap_vs_access.pdf`
- `own_results/{region}_figure7_utilization_distribution_rural.pdf`
- `own_results/{region}_figure8_utilization_distribution_urban.pdf`

---

### 5. **create_region_tables.py** - Table Generation (Any Region)
**Purpose:** Generates analysis tables for a chosen region/instance 

```bash
# From src/models
# Quick mode
python create_region_tables.py --region Hampshire --instance-number 1

# Full mode 
python create_region_tables.py --region Bavaria --instance-number 3 --run-heavy
```

**Arguments:**
- `--region`: region name (e.g., Hampshire, Bavaria)
- `--instance-number`: dataset instance (default: 1)
- `--run-heavy` (optional): also generate tables related to heuristics 
- `--base-dir` (optional): workspace root if auto-detection fails

**Quick Mode Output (default):**
- `own_results/{region}_table1_overall_results.xlsx`
- `own_results/{region}_table2_strict_vs_loose_results.xlsx`
- `own_results/{region}_table3_fairness_results.xlsx`
- `own_results/{region}_table4_pof_results.xlsx`

**Heavy Tables (with --run-heavy):**
- `own_results/{region}_table5_greedy_results_nocutoff.xlsx` (~heavy runtime)
- `own_results/{region}_table6_cutoff_results.xlsx` (~heavy runtime)
- `own_results/{region}_table7_greedy_results_cutoff.xlsx` (~heavy runtime)

---

## Supported Regions

The framework currently supports:

| Region | Instances | Users | Facilities | Description |
|--------|-----------|-------|------------|-------------|
| **Hampshire** | 1 | 266 | 26 | Household Waste Recycling Centers (HWRCs) in Hampshire, UK |
| **Bavaria** | 1 | 2060 | 1394 | Facility locations in Bavaria region, Germany |
| **Bavaria** | 3 | 5000 | 2497 | Facility locations in Bavaria region, Germany |
| **Bavaria** | 4 | 1500 | 425 | Facility locations in Bavaria region, Germany |
| Custom | Any | Variable | Variable | Add your own dataset (see Adding New Regions below) |
---

## Adding New Regions/Datasets

To add a new region (e.g., "Yorkshire"):

### 1. Prepare Data Files
Create CSV and compressed JSON files in `data/`:
```
data/
├── Yorkshire_users_and_facs.csv      # Columns: user_id, lat, lon, population, facility_id, capacity, ...
└── map_data/
    └── yorkshire_sectors.geojson     # Optional: region boundaries for choropleth
```

### 2. Register in utils.py
Add your region to the `load_an_instance()` function:
```python
if region == "Yorkshire":
    users_facs_path = os.path.join(data_dir, "Yorkshire_users_and_facs.csv")
    travel_dict_path = os.path.join(data_dir, "Yorkshire_travel_dict.json.pbz2")
    # ... load and return data
```

### 3. Run Standard Pipeline
```bash
# Pre-solve and cache
python solve_and_cache_models.py --region Yorkshire --instance 1

# Generate visualizations
python heatmap_plot.py --region Yorkshire --instance 1
```

---

## Example: Custom Analysis

To extend the pipeline with custom analysis:

```python
from result_cache import load_result
import pandas as pd

# Load cached result for any region
region = "Hampshire"  # or "Bavaria", "Yorkshire", etc.
instance = 1

result = load_result(
    region=region,
    instance=instance,
    budget_factor=21/26,  # 81% budget
    cache_dir="own_results/model_cache",
    strict_assign_to_one=False,
    cap_factor=1.5,
    cutoff=0.2
)

if result:
    # Extract data
    assignment = result['solution_details']['assignment']
    open_facs = result['solution_details']['open_facs']
    budget = result['model_details']['budget_factor']
    total_facs = result['model_details'].get('total_facilities', len(open_facs))
    
    print(f"Region: {region}")
    print(f"Budget: {budget*100:.0f}%")
    print(f"Facilities open: {len(open_facs)}/{total_facs}")
    print(f"Users assigned: {len(assignment)}")
else:
    print(f"Result not found. Run: python solve_and_cache_models.py --region {region} --instance {instance}")
```
