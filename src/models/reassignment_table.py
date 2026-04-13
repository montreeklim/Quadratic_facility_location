import pandas as pd 
import numpy as np
import gurobipy as gp
from gurobipy import GRB
from collections import defaultdict
import os
import json
import bz2
from pathlib import Path
from utils import *
from result_cache import load_result, ensure_cache_dir

# Get the directory of this script
SCRIPT_DIR = Path(__file__).parent

# Set up cache
cache_dir = PROJECT_ROOT / "own_results" / "model_cache"
ensure_cache_dir(str(cache_dir))

# Primary cache parameters
# cap_factor: 1.0 (default for Hampshire), 1.5 (Bavaria 1), 0.8 (Bavaria 3&4)
# cutoff: 0.0 (default), 0.2 (Bavaria)
PRIMARY_PARAMS = dict(strict_assign_to_one=False, cap_factor=1.0, cutoff=0.0, max_access=False)
# Fallback params
FALLBACK_PARAMS = dict(strict_assign_to_one=True, cap_factor=1.0, cutoff=0.0, max_access=False)


def _norm(name: str) -> str:
    """Lightweight normalizer to align facility names across files."""
    n = (name or "").strip()
    n = n.replace("Portmouth", "Portsmouth")
    return " ".join(n.split()).lower()


# --------------------------------------------
# 1. Load Hampshire data (CSV/pbz2 bundle)
# --------------------------------------------
users_and_facs_df, travel_dict, users, facs = load_an_instance(
    instance_number=1,
    region="Hampshire",
    sufficient_cap=False,
)

# Keep only facilities (positive capacity) and build helper lookups
facility_df = users_and_facs_df.loc[facs].copy()
population = users_and_facs_df.loc[users, 'population']

# Distance lookup (miles) using rc_centroid fallbacks
distance_dict = create_distance_dict(users_and_facs_df, users, facs)

# --------------------------------------------
# 2. Read assignment results (place Excel files in own_results/assignments)
# --------------------------------------------
assign_dir = PROJECT_ROOT / 'own_results' / 'assignments'
assign_dir.mkdir(parents=True, exist_ok=True)

orig_filename = 'Result_100%.xlsx'     # Original assignment
new_filename  = 'Result_81%.xlsx'      # New assignment

orig_path = assign_dir / orig_filename
new_path  = assign_dir / new_filename

if not orig_path.exists() or not new_path.exists():
    raise FileNotFoundError(
        f"Expected assignment files in {assign_dir} (missing one of {orig_filename}, {new_filename})."
    )

df = pd.read_excel(orig_path, usecols=[0, 1, 2]).dropna()
assignment_df = pd.read_excel(new_path, usecols=[0, 1, 2]).dropna()

# --------------------------------------------
# 3. Facility mapping driven by Hampshire data
# --------------------------------------------
facility_ids = list(facility_df.index)
facility_names_raw = facility_df['Facility name'].astype(str).tolist()

name_to_id_map = {_norm(n): idx for idx, n in zip(facility_ids, facility_names_raw)}
id_to_name_map  = {idx: "Portsmouth" if n.strip() == "Portmouth" else n.strip()
                         for idx, n in zip(facility_ids, facility_names_raw)}

# Facilities to close (update as needed)
closed_fac_names = [
    "Alresford", "Bishops Waltham", "Hedge End", "Hartley Wintney", "Hayling Island"
]
closed_fac_ids = [name_to_id_map[_norm(name)] for name in closed_fac_names if _norm(name) in name_to_id_map]

# ============================================================================
# Generate reassignment tables for each budget level
# ============================================================================
TARGET_BUDGETS = [1.0, 21/26, 14/26, 9/26]
BUDGET_LABELS = {1.0: '100%', 21/26: '81%', 14/26: '54%', 9/26: '35%'}

def generate_reassignment_table(result_100, result_option, budget_label):
    """
    Generate a reassignment table comparing two budget scenarios.
    
    Args:
        result_100: cached result dict for 100% budget (baseline)
        result_option: cached result dict for option budget
        budget_label: string label for the budget (e.g., '81%')
    """
    # Extract assignments from cache results
    assignment_100 = result_100['solution_details']['assignment']
    assignment_option = result_option['solution_details']['assignment']
    open_facs_100 = set(result_100['solution_details']['open_facs'])
    open_facs_option = set(result_option['solution_details']['open_facs'])
    
    # Closed facilities in option scenario (compared to 100%)
    closed_in_option = open_facs_100 - open_facs_option
    
    if not closed_in_option:
        print(f"[INFO] No facilities closed in {budget_label} scenario; skipping reassignment table.")
        return None
    
    # Find affected users (those assigned to facilities that closed in option scenario)
    affected_users = []
    for user_idx_str, fac_idx in assignment_100.items():
        if int(fac_idx) in closed_in_option:
            affected_users.append({
                'user': int(user_idx_str),
                'facility_old': int(fac_idx),
                'facility_new': int(assignment_option.get(user_idx_str, -1))
            })
    
    if not affected_users:
        print(f"[INFO] No affected users in {budget_label} scenario; skipping reassignment table.")
        return None
    
    # Build comparison dataframe
    comparison_df = pd.DataFrame(affected_users)
    comparison_df['population'] = comparison_df['user'].map(population.to_dict())
    
    # Build detailed reassignment table
    reassignment_details = comparison_df[['user', 'facility_old', 'facility_new', 'population']].copy()
    reassignment_details.rename(columns={
        'facility_old': 'Old Facility ID',
        'facility_new': 'New Facility ID',
        'population': 'Population'
    }, inplace=True)
    reassignment_details['Old Facility (Closed)'] = reassignment_details['Old Facility ID'].map(id_to_name_map)
    reassignment_details['New Assigned Facility'] = reassignment_details['New Facility ID'].map(id_to_name_map)
    
    # Add distance column
    def _get_distance(user_idx, fac_id):
        try:
            d = distance_dict[user_idx][fac_id]
            if isinstance(d, (list, tuple, np.ndarray, pd.Series)):
                return float(np.median(d)) if len(d) > 0 else np.nan
            return float(d)
        except (KeyError, TypeError):
            return np.nan
    
    reassignment_details['Distance'] = reassignment_details.apply(
        lambda r: _get_distance(r['user'], r['New Facility ID']),
        axis=1
    )
    reassignment_details['Distance'] = pd.to_numeric(
        reassignment_details['Distance'], errors='coerce'
    )
    
    # Build summary table
    population_by_move = reassignment_details.groupby(
        ['Old Facility (Closed)', 'New Assigned Facility']
    )['Population'].sum()
    
    total_population_per_closed = reassignment_details.groupby(
        'Old Facility (Closed)'
    )['Population'].sum()
    
    percentage_summary = (population_by_move / total_population_per_closed) * 100
    summary_df = percentage_summary.reset_index().rename(columns={'Population': 'Percentage of Population'})
    
    # Median distance for each (Old -> New) pair
    median_distance_by_move = reassignment_details.groupby(
        ['Old Facility (Closed)', 'New Assigned Facility']
    )['Distance'].median().reset_index().rename(columns={'Distance': 'Distance (miles)'})
    
    summary_df = summary_df.merge(
        median_distance_by_move,
        on=['Old Facility (Closed)', 'New Assigned Facility'],
        how='left'
    )
    
    return {
        'details': reassignment_details,
        'summary': summary_df
    }


# Load cached results for each budget
print("Loading cached results for each budget level...")
budget_to_result = {}
for b in TARGET_BUDGETS:
    res = load_result("Hampshire", 1, b, str(cache_dir), **PRIMARY_PARAMS)
    if res is None:
        res = load_result("Hampshire", 1, b, str(cache_dir), **FALLBACK_PARAMS)
    if res is None:
        print(f"[WARN] Missing cached result for budget {b:.6f}. Skipping.")
    else:
        budget_to_result[b] = res
        print(f"[OK] Loaded budget {BUDGET_LABELS[b]}")

if not budget_to_result:
    raise RuntimeError("No cached results found for requested budgets. Run solve_and_cache_models.py first.")

# Get the 100% baseline result
result_100 = budget_to_result.get(1.0)
if result_100 is None:
    raise RuntimeError("100% budget result not found in cache.")

# Generate reassignment tables for each option budget
output_dir = PROJECT_ROOT / "own_results" / "reassignment_outputs"
output_dir.mkdir(parents=True, exist_ok=True)

for budget, result_option in budget_to_result.items():
    if budget == 1.0:
        continue  # Skip 100% (it's the baseline)
    
    budget_label = BUDGET_LABELS[budget]
    print(f"\nGenerating reassignment table for {budget_label}...")
    
    result = generate_reassignment_table(result_100, result_option, budget_label)
    
    if result is None:
        continue
    
    # Save details and summary
    pct_str = budget_label.replace('%', '')
    details_path = output_dir / f"Reassignment_Details_{pct_str}.xlsx"
    summary_path = output_dir / f"Reassignment_Summary_{pct_str}.xlsx"
    
    result['details'].to_excel(details_path, index=False)
    result['summary'].to_excel(summary_path, index=False)
    
    print(f" Saved: {details_path.name}")
    print(f" Saved: {summary_path.name}")

print("\nReassignment tables generation complete!")
