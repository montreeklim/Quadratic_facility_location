# Quadratic Facility Location with Capacity Constraints

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
│       └── Counties_and_Unitary_Authorities_*.geojson  # Administrative boundaries
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
│   ├── model_cache/                 # Cached JSON results (auto-generated)
│   ├── heat_maps/                   # Generated PDF maps
│   ├── reassignment_outputs/        # Reassignment Excel tables
│   └── hampshire_summary.csv        # Summary statistics
├── CACHING_QUICKREF.md              # One-page caching reference
└── README.md                        # This file
```

---

## Generate Figures & Tables (Any Region)

From src/models:

```bash
# Figures (3a–8)
python create_region_figures.py --region Hampshire --instance-number 1
python create_region_figures.py --region Bavaria --instance-number 3

# Tables (1–4 by default)
python create_region_tables.py --region Hampshire --instance-number 1

# Tables (1–7, heavy)
python create_region_tables.py --region Bavaria --instance-number 3 --run-heavy
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

# 2. Generate heatmaps (loads from cache, ~30 seconds)
python heatmap_plot.py --region Hampshire --instance 1
# Output: own_results/heat_maps/{region}_map_static_b*.pdf

# 3. Generate reassignment tables (loads from cache, ~10 seconds)
python reassignment_table.py --region Hampshire --instance 1
# Output: own_results/reassignment_outputs/Reassignment_*.xlsx
```

### Option B: Generate Individual Outputs

**If models are already cached (from Option A):**

```bash
# Generate static maps for a specific region
python heatmap_plot.py --region Hampshire --instance 1
# Output: own_results/heat_maps/hampshire_map_static_b*.pdf (4 files for 4 budgets)

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
- Takes ~5-10 minutes (depending on Gurobi settings and problem size)

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
**When to use:** After models are cached (or for re-generating visualizations)

```bash
# Generate maps for any region and instance
python heatmap_plot.py --region <REGION> --instance <INSTANCE>

# Examples:
python heatmap_plot.py --region Hampshire --instance 1
python heatmap_plot.py --region Bavaria --instance 3
```

**What it does:**
- Loads cached results for 4 budget levels for Hampshire dataset: [1.0, 21/26 ≈ 0.808, 14/26 ≈ 0.538, 9/26 ≈ 0.346] and 8 budget levels from 0.3 to 1.0 for other datasets.
- Computes mean user→facility distance per postcode sector
- Computes facility utilization %
- Generates 4 static Matplotlib maps as PDFs
- Generates optional Folium HTML maps

**Output:**
- `own_results/heat_maps/{region}_map_static_b35.pdf` (35% budget)
- `own_results/heat_maps/{region}_map_static_b54.pdf` (54% budget)
- `own_results/heat_maps/{region}_map_static_b81.pdf` (81% budget)
- `own_results/heat_maps/{region}_map_static_b100.pdf` (100% budget)
- `own_results/{region}_summary.csv` (distance statistics)

**Requirements:**
- Cached models (from `solve_and_cache_models.py`)
- GeoJSON files (if available) for choropleth regions

---

### 3. **reassignment_table.py** - Reassignment Analysis
**Purpose:** Analyzes how users are reassigned when facilities close due to budget constraints  
**When to use:** After models are cached

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
**Purpose:** Generates Figures 3a–8 for a chosen region/instance (same outputs as the Hampshire-only script)  
**When to use:** After models are cached (recommended)

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
**Purpose:** Generates Tables 1–7 for a chosen region/instance (same outputs as the Hampshire-only script)  
**When to use:** After models are cached (recommended)

```bash
# From src/models
# Quick mode (tables 1–4 only)
python create_region_tables.py --region Hampshire --instance-number 1

# Full mode (tables 1–7 including heavy tables)
python create_region_tables.py --region Bavaria --instance-number 3 --run-heavy
```

**Arguments:**
- `--region`: region name (e.g., Hampshire, Bavaria)
- `--instance-number`: dataset instance (default: 1)
- `--run-heavy` (optional): also generate tables 5–7 (very heavy, may take hours)
- `--base-dir` (optional): workspace root if auto-detection fails

**Quick Mode Output (default):**
- `own_results/{region}_table1_overall_results.xlsx`
- `own_results/{region}_table2_strict_vs_loose_results.xlsx`
- `own_results/{region}_table3_fairness_results.xlsx`
- `own_results/{region}_table4_pof_results.xlsx`

**Heavy Tables (with --run-heavy):**
- `own_results/{region}_table5_greedy_results_nocutoff.xlsx` (~heavy runtime)
- `own_results/{region}_table6_cutoff_results.xlsx` (~very heavy runtime)
- `own_results/{region}_table7_greedy_results_cutoff.xlsx` (~very heavy runtime)

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

## Key Output Files

### Cached Results
```
own_results/model_cache/
├── result_0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5.json
├── result_1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6.json
└── ... (one per model configuration)
```

**Structure of cached result:**
```json
{
  "model_details": {
    "region": "Hampshire",
    "instance": 1,
    "budget_factor": 0.808,
    "cap_factor": 1.5,
    "strict_assign_to_one": false,
    "cutoff": 0.2
  },
  "solution_details": {
    "open_facs": [0, 1, 2, 5, 7, ...],    // indices of open facilities
    "assignment": {"0": 5, "1": 7, ...},  // user_idx -> facility_idx mapping
    "objective_value": 123.45
  }
}
```

### Heat Maps
Four PDF files with:
- **Left subplot:** Choropleth of mean distance (0-15 miles scale, YlGnBu colormap)
- **Right subplot:** Facility markers colored by utilization % (RdYlGn_r colormap)
- Grey closed facilities visible with white-edged markers
- Smart label positioning to avoid overlaps

### Reassignment Tables
Excel files with:
- **Details sheet:** User-level reassignments (user ID, old facility, new facility, distance, population)
- **Summary sheet:** Aggregated by move pair (% of population, median distance per move)

---

## Model Parameters

### Primary Parameters (Used for Main Results)
```python
PRIMARY_PARAMS = {
    "strict_assign_to_one": False,  # Allow multi-assignment during solving
    "cap_factor": 1.5,              # Capacity multiplier (1.5x nominal capacity)
    "cutoff": 0.2,                  # Fractional assignment cutoff (≤0.2 = 0)
    "max_access": False             # Single accessibility measure
}
```

### Fallback Parameters (If Primary Not Available)
```python
FALLBACK_PARAMS = {
    "strict_assign_to_one": True,   # Strict single assignment
    "cap_factor": 1.0,              # Nominal capacity only
    "cutoff": 0.0,                  # No fractional rounding
    "max_access": False
}
```


---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| gurobi | 10.0+ | Optimization solver (MIP/MIQP) |
| gurobipy | 10.0+ | Gurobi Python API |
| pyomo | 6.0+ | Optimization modeling language |
| pandas | 1.5+ | Data processing |
| numpy | 1.23+ | Numerical computing |
| scipy | 1.9+ | Scientific computing (statistics) |
| scikit-learn | 1.1+ | Linear regression for plotting |
| geopandas | 0.12+ | Spatial data handling |
| folium | 0.14+ | Interactive web maps |
| matplotlib | 3.6+ | Static plots and visualizations |
| contextily | 1.3+ | Basemap tiles for static maps |
| adjustText | 0.7+ | Label positioning (avoid overlaps) |
| geopy | 2.3+ | Distance calculations |
| openpyxl | 3.0+ | Excel file generation |

---

## Adding New Regions/Datasets

To add a new region (e.g., "Yorkshire"):

### 1. Prepare Data Files
Create CSV and compressed JSON files in `data/`:
```
data/
├── Yorkshire_users_and_facs.csv      # Columns: user_id, lat, lon, population, facility_id, capacity, ...
├── Yorkshire_travel_dict.json.pbz2   # Dict: {user_id: {facility_id: distance, ...}, ...}
├── Yorkshire_distance_dict.json.pbz2 # Optional: pre-computed distances
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

# Analyze reassignments
python Table5.py --region Yorkshire --instance 1
```

### 4. Optional: Add GeoJSON for Maps
If choropleth maps are desired, add GeoJSON boundaries to `data/map_data/yorkshire_sectors.geojson`

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
