"""
Pre-solve optimization models and cache results to avoid re-solving during table/figure generation.

This script solves all optimization models needed for tables and figures ONCE and caches the results.
Then, the table and figure generation scripts can load cached results instead of re-solving.

Usage:
    python solve_and_cache_models.py --region Hampshire --instance 1
    
This will solve all models needed for Hampshire instance 1 and cache the results in:
    own_results/model_cache/
"""

import os
import sys
import argparse
from pathlib import Path

# Add src/models to path for imports
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

from model import solve_model_naively
from utils import load_an_instance
from result_cache import save_result, load_result, ensure_cache_dir, list_cached_results

# Define all model configurations needed for tables and figures
HAMPSHIRE_MODELS = {
    "table1_overall": {
        "budget_factors": [0.1 * b for b in range(3, 11)],  # 0.3 to 1.0
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
    "table2_strict_vs_loose_loose": {
        "budget_factors": [0.3],  # Single budget factor for table 2
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
    "table2_strict_vs_loose_strict": {
        "budget_factors": [0.3],  # Single budget factor for table 2
        "params": {"strict_assign_to_one": True, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
    "table3_fairness": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
    "table4_pof_optimal": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
    "table4_pof_maximum": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": True}
    },
    "figure3a_overall_access": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
    "figure3b_distance_percentiles": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
    "figure4a_utilization_percentiles": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
    "figure4b_utilization_distribution": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
    "figure5a_strict_vs_loose": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
    "figure5b_cutoff_vs_nocutoff": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
    "figure6_cap_vs_access": {
        "budget_factors": [0.3],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
    "figure7_utilization_rural": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
    "figure8_utilization_urban": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.0, "cutoff": 0.0, "max_access": False}
    },
}

# Bavaria model configurations (same structure as Hampshire)
BAVARIA_MODELS = {
    "table1_overall": {
        "budget_factors": [0.1 * b for b in range(3, 11)],  # 0.3 to 1.0
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.2, "max_access": False}
    },
    "table2_strict_vs_loose_loose": {
        "budget_factors": [0.3],  # Single budget factor for table 2
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.0, "max_access": False}
    },
    "table2_strict_vs_loose_strict": {
        "budget_factors": [0.3],  # Single budget factor for table 2
        "params": {"strict_assign_to_one": True, "cap_factor": 1.5, "cutoff": 0.0, "max_access": False}
    },
    "table3_fairness": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.2, "max_access": False}
    },
    "table4_pof_optimal": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.2, "max_access": False}
    },
    "table4_pof_maximum": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.2, "max_access": True}
    },
    "figure3a_overall_access": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.2, "max_access": False}
    },
    "figure3b_distance_percentiles": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.2, "max_access": False}
    },
    "figure4a_utilization_percentiles": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.2, "max_access": False}
    },
    "figure4b_utilization_distribution": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.2, "max_access": False}
    },
    "figure5a_strict_vs_loose": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.2, "max_access": False}
    },
    "figure5b_cutoff_vs_nocutoff": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.2, "max_access": False}
    },
    "figure6_cap_vs_access": {
        "budget_factors": [0.3],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.2, "max_access": False}
    },
    "figure7_utilization_rural": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.2, "max_access": False}
    },
    "figure8_utilization_urban": {
        "budget_factors": [0.1 * b for b in range(3, 11)],
        "params": {"strict_assign_to_one": False, "cap_factor": 1.5, "cutoff": 0.2, "max_access": False}
    },
}


def solve_and_cache_models(region, instance_number, cache_dir, models_config, 
                          skip_existing=True, verbose=True, sufficient_cap=False):
    """
    Solve all models in the configuration and cache results.
    
    :param region: Region name (e.g., 'Hampshire')
    :param instance_number: Instance number
    :param cache_dir: Directory to store cache files
    :param models_config: Dictionary mapping model names to their configurations
    :param skip_existing: If True, skip models that are already cached
    :param verbose: If True, print progress information
    :param sufficient_cap: If True, load sufficient capacity instance
    :return: Dictionary with solving statistics
    """
    
    # Determine the correct capacity factor based on region, instance, and sufficient_cap flag
    if sufficient_cap:
        capacity_factor = 1.0
        print(f"Using capacity factor: {capacity_factor} (sufficient capacity instance)")
    elif region.lower() == "bavaria":
        if instance_number == 1:
            capacity_factor = 1.5
        elif instance_number in [3, 4]:
            capacity_factor = 0.8
        else:
            capacity_factor = 1.0  # Default for other Bavaria instances
        print(f"Using capacity factor: {capacity_factor} (Bavaria instance {instance_number})")
    else:
        capacity_factor = 1.0  # Default for Hampshire and other regions
        print(f"Using capacity factor: {capacity_factor} (default)")
    
    # Load instance data once
    print(f"\n{'='*70}")
    print(f"Loading instance data for {region} (instance {instance_number})...")
    print(f"{'='*70}")
    users_and_facs_df, travel_dict, users, facs = load_an_instance(
        instance_number, region=region, sufficient_cap=sufficient_cap
    )
    print(f"Loaded {len(users)} users and {len(facs)} facilities")
    
    # Create cache directory
    abs_cache_dir = ensure_cache_dir(cache_dir)
    print(f"Cache directory: {abs_cache_dir}")
    
    # Collect all unique (budget_factor, params) combinations
    unique_configs = {}
    total_models = 0
    
    for model_name, config in models_config.items():
        for budget_factor in config["budget_factors"]:
            # Override the capacity factor in params with the correct one
            params = config["params"].copy()
            params["cap_factor"] = capacity_factor
            
            # Create a hashable key from params
            param_key = tuple(sorted(params.items()))
            
            config_id = f"{budget_factor}_{hash(param_key)}"
            if config_id not in unique_configs:
                unique_configs[config_id] = {
                    "budget_factor": budget_factor,
                    "params": params,
                    "sources": []
                }
            unique_configs[config_id]["sources"].append(model_name)
            total_models += 1
    
    print(f"\nTotal model configurations to solve: {total_models}")
    print(f"Unique configurations: {len(unique_configs)}")
    
    # Solve models
    solved_count = 0
    skipped_count = 0
    failed_count = 0
    
    for idx, (config_id, config_info) in enumerate(unique_configs.items(), 1):
        budget_factor = config_info["budget_factor"]
        params = config_info["params"]
        sources = config_info["sources"]
        
        print(f"\n[{idx}/{len(unique_configs)}] Budget: {budget_factor:.1f}, ", end="")
        print(f"Parameters: {params}")
        print(f"         Used for: {', '.join(sources[:2])}")
        if len(sources) > 2:
            print(f"                  + {len(sources) - 2} more")
        
        # Check if already cached
        if skip_existing:
            existing_result = load_result(
                region, instance_number, budget_factor,
                abs_cache_dir, **params
            )
            if existing_result is not None:
                skipped_count += 1
                print(f"         ✓ Already cached (skipping)")
                continue
        
        # Solve the model
        try:
            is_feasible, results = solve_model_naively(
                users_and_facs_df, travel_dict, users, facs,
                budget_factor=budget_factor,
                strict_assign_to_one=params["strict_assign_to_one"],
                cap_factor=params["cap_factor"],
                cutoff=params["cutoff"],
                max_access=params["max_access"],
                main_threads=1,
                main_tolerance=5e-3,
                main_time_limit=20000,
                main_print_sol=False,
                main_log_file=None,
                main_preqlinearize=-1,
                post_threads=1,
                post_tolerance=0.0,
                post_print_sol=False,
                post_log_file=None,
                post_preqlinearize=-1
            )
            
            if not is_feasible:
                print(f"         ✗ Model infeasible - not caching")
                failed_count += 1
                continue
            
            # Save to cache
            save_result(
                results, region, instance_number, budget_factor,
                abs_cache_dir, **params
            )
            solved_count += 1
            
        except Exception as e:
            print(f"         ✗ Error solving model: {e}")
            failed_count += 1
    
    print(f"\n{'='*70}")
    print(f"Solving Summary:")
    print(f"  - Solved and cached: {solved_count}")
    print(f"  - Skipped (already cached): {skipped_count}")
    print(f"  - Failed: {failed_count}")
    print(f"  - Total: {solved_count + skipped_count + failed_count}")
    print(f"{'='*70}")
    
    # List cached files
    print(f"\nCached files for {region}:")
    cached_files = list_cached_results(abs_cache_dir, region)
    for filename, size_mb in cached_files:
        print(f"  - {filename} ({size_mb:.2f} MB)")
    
    return {
        "solved": solved_count,
        "skipped": skipped_count,
        "failed": failed_count,
        "cache_dir": abs_cache_dir
    }


def main():
    parser = argparse.ArgumentParser(
        description="Pre-solve optimization models and cache results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Solve and cache all models for Hampshire
  python solve_and_cache_models.py --region Hampshire --instance 1
  
  # Solve without skipping existing cached models
  python solve_and_cache_models.py --region Hampshire --instance 1 --no-skip
        """
    )
    
    parser.add_argument(
        "--region",
        default="Hampshire",
        help="Region to solve models for (default: Hampshire)"
    )
    parser.add_argument(
        "--instance",
        type=int,
        default=1,
        help="Instance number (default: 1)"
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Cache directory (default: own_results/model_cache)"
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Don't skip already cached models"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Verbose output (default: True)"
    )
    parser.add_argument(
        "--sufficient-cap",
        action="store_true",
        help="Use sufficient capacity instance (sets cap_factor to 1.0)"
    )
    
    args = parser.parse_args()
    
    # Determine cache directory
    if args.cache_dir is None:
        workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cache_dir = os.path.join(workspace_root, 'own_results', 'model_cache')
    else:
        cache_dir = args.cache_dir
    
    # Select model configuration
    region_lower = args.region.lower()
    if region_lower == "hampshire":
        models_config = HAMPSHIRE_MODELS
    elif region_lower == "bavaria":
        models_config = BAVARIA_MODELS
    else:
        print(f"Error: Region '{args.region}' not configured")
        print("Available regions: Hampshire, Bavaria")
        sys.exit(1)
    
    # Solve and cache
    solve_and_cache_models(
        args.region,
        args.instance,
        cache_dir,
        models_config,
        skip_existing=not args.no_skip,
        verbose=args.verbose,
        sufficient_cap=args.sufficient_cap
    )


if __name__ == "__main__":
    main()
