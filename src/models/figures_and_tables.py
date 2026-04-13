"""
module for creating the exact figures and tables included in the paper
"""

import os
from plotting import *
from plotting import (
    save_overall_access_plot_cached,
    save_distance_percentiles_plot_cached,
    save_utilization_percentiles_plot_cached,
    save_utilization_distribution_plot_cached,
    save_strict_vs_loose_plot_cached,
    save_cutoff_vs_nocutoff_plot_cached,
    save_cap_vs_access_plot_cached,
    write_table_overall_results_cached,
    write_table_strict_vs_loose_results_cached,
    write_table_fairness_results_cached,
    write_table_pof_results_cached,
)
from results import *
from results import save_fairness_results, save_pof_results, save_greedy_results, save_strict_vs_loose_results, save_cutoff_results, save_overall_results


# ============================================================================
# CACHING SUPPORT
# ============================================================================
# To use result caching:
# 1. First run: python solve_and_cache_models.py --region Hampshire --instance 1
# 2. Then run create_hampshire_figures.py or create_hampshire_tables.py
#
# To disable caching, set USE_CACHE = False or pass use_cache=False to functions

USE_CACHE = True  # Set to False to disable caching globally

def get_default_budget_factor_list(region):
    """
    Get the appropriate budget_factor_list based on region.
    
    :param region: region name (e.g., 'Hampshire', 'Bavaria')
    :return: list of budget factors
    """
    if region is None:
        return [0.1 * b for b in range(3, 11)]
    
    region_lower = region.lower() if isinstance(region, str) else ''
    
    # Hampshire: specific closures
    if 'hampshire' in region_lower:
        return [9/26, 14/26, 21/26, 1.0]  # Corresponding to closure of 17, 12, 5, 0
    
    # Bavaria: default list
    if 'bavaria' in region_lower:
        return [0.1 * b for b in range(3, 11)]
    
    # Default
    return [0.1 * b for b in range(3, 11)]

def get_default_cutoff(region):
    """
    Get the default cutoff value for a region.
    
    :param region: Region name (e.g., 'Bavaria', 'Hampshire')
    :return: cutoff value
    """
    if region is None:
        return 0.0
    
    region_lower = region.lower() if isinstance(region, str) else ''
    
    # Hampshire: cutoff = 0.0
    if 'hampshire' in region_lower:
        return 0.0
    
    # Bavaria: cutoff = 0.2
    if 'bavaria' in region_lower:
        return 0.2
    
    # Default
    return 0.0

def get_cache_dir():
    """Get the cache directory for results."""
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(workspace_root, 'own_results', 'model_cache')

def _get_plotting_function(use_cache):
    """
    Get the appropriate plotting function based on cache setting.
    
    :param use_cache: Whether to use caching
    :return: Module with plotting functions
    """
    # All functions now include caching support built-in
    return sys.modules[__name__]


import sys

# create the figures included in the paper



def create_figure3a(output_filename='overall_access.pdf', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1, use_cache=None, cache_only=False, allow_missing=False):
    """
    creates figure 3a of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    :param use_cache: whether to use cached results (default: USE_CACHE global setting)
    """
    if use_cache is None:
        use_cache = USE_CACHE
    
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    budget_factor_list = get_default_budget_factor_list(region)
    
    save_overall_access_plot_cached(
        users_and_facs_df, travel_dict, users, facs, output_filename, output_abs_path,
        budget_factor_list, cache_dir=get_cache_dir(), region=region, instance_number=instance_number,
        use_cache=use_cache, cache_only=cache_only, allow_missing=allow_missing
    )


def create_figure3b(output_filename='distance_percentiles.pdf', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1, use_cache=None, cache_only=False, allow_missing=False):
    """
    creates figure 3b of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    :param use_cache: whether to use cached results (default: USE_CACHE global setting)
    """
    if use_cache is None:
        use_cache = USE_CACHE
    
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    budget_factor_list = get_default_budget_factor_list(region)
    percentiles = [10, 50, 90]
    
    save_distance_percentiles_plot_cached(
        users_and_facs_df, travel_dict, users, facs, output_filename, output_abs_path,
        percentiles, budget_factor_list, cache_dir=get_cache_dir(), region=region, instance_number=instance_number,
        use_cache=use_cache, cache_only=cache_only, allow_missing=allow_missing
    )


def create_figure4a(output_filename='utilization_percentiles.pdf', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1, use_cache=None, cache_only=False, allow_missing=False):
    """
    creates figure 4a of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    :param use_cache: whether to use cached results (default: USE_CACHE global setting)
    """
    if use_cache is None:
        use_cache = USE_CACHE
    
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    percentiles = [10, 50, 90]
    budget_factor_list = get_default_budget_factor_list(region)
    
    save_utilization_percentiles_plot_cached(
        users_and_facs_df, travel_dict, users, facs, output_filename, output_abs_path,
        percentiles, budget_factor_list, cache_dir=get_cache_dir(), region=region, instance_number=instance_number,
        use_cache=use_cache, cache_only=cache_only, allow_missing=allow_missing
    )


def create_figure4b(output_filename='utilization_distribution.pdf', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1, use_cache=None, cache_only=False, allow_missing=False):
    """
    creates figure 4b of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    :param use_cache: whether to use cached results (default: USE_CACHE global setting)
    """
    if use_cache is None:
        use_cache = USE_CACHE
    
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    budget_factor_list = get_default_budget_factor_list(region)
    
    save_utilization_distribution_plot_cached(
        users_and_facs_df, travel_dict, users, facs, output_filename, output_abs_path,
        budget_factor_list, cache_dir=get_cache_dir(), region=region, instance_number=instance_number,
        use_cache=use_cache, cache_only=cache_only, allow_missing=allow_missing
    )


def create_figure5a(output_filename='strict_vs_loose.pdf', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1, use_cache=None, cache_only=False, allow_missing=False):
    """
    creates figure 5a of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    :param use_cache: whether to use cached results (default: USE_CACHE global setting)
    """
    if use_cache is None:
        use_cache = USE_CACHE
    
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    budget_factor_list = get_default_budget_factor_list(region)
    
    save_strict_vs_loose_plot_cached(
        users_and_facs_df, travel_dict, users, facs, output_filename, output_abs_path,
        budget_factor_list, cache_dir=get_cache_dir(), region=region, instance_number=instance_number,
        use_cache=use_cache, cache_only=cache_only, allow_missing=allow_missing
    )


def create_figure5b(output_filename='cutoff_vs_nocutoff.pdf', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1, use_cache=None, cache_only=False, allow_missing=False):
    """
    creates figure 5b of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    :param use_cache: whether to use cached results (default: USE_CACHE global setting)
    """
    if use_cache is None:
        use_cache = USE_CACHE
    
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    users = users[:round(len(users) * 0.3)]
    facs = facs[:round(len(facs) * 0.3)]
    budget_factor_list = get_default_budget_factor_list(region)
    
    save_cutoff_vs_nocutoff_plot_cached(
        users_and_facs_df, travel_dict, users, facs, output_filename, output_abs_path,
        budget_factor_list, cache_dir=get_cache_dir(), region=region, instance_number=instance_number,
        main_preqlinearize=1, use_cache=use_cache, cache_only=cache_only, allow_missing=allow_missing
    )


def create_figure6(output_filename='cap_vs_access.pdf', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1, use_cache=None, cache_only=False, allow_missing=False):
    """
    creates figure 6 of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    :param use_cache: whether to use cached results (default: USE_CACHE global setting)
    """
    if use_cache is None:
        use_cache = USE_CACHE
    
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    
    save_cap_vs_access_plot_cached(
        users_and_facs_df, travel_dict, users, facs, output_filename, output_abs_path,
        budget_factor=0.3, cache_dir=get_cache_dir(), region=region, instance_number=instance_number,
        use_cache=use_cache, cache_only=cache_only, allow_missing=allow_missing
    )


def create_figure7(output_filename='utilization_distribution_rural.pdf', output_abs_path=None,
                   input_data_abs_path=None, region="Bavaria", instance_number=1, use_cache=None,
                   cache_only=False, allow_missing=False):
    """
    creates figure S1a of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    :param use_cache: whether to use cached results (default: USE_CACHE global setting)
    """
    if use_cache is None:
        use_cache = USE_CACHE
    
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    budget_factor_list = get_default_budget_factor_list(region)
    
    save_utilization_distribution_plot_cached(
        users_and_facs_df, travel_dict, users, facs, output_filename, output_abs_path,
        budget_factor_list, facility_region='rural', cache_dir=get_cache_dir(), region=region, instance_number=instance_number,
        use_cache=use_cache, cache_only=cache_only, allow_missing=allow_missing
    )


def create_figure8(output_filename='utilization_distribution_urban.pdf', output_abs_path=None,
                   input_data_abs_path=None, region="Bavaria", instance_number=1, use_cache=None,
                   cache_only=False, allow_missing=False):
    """
    creates figure S1b of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    :param use_cache: whether to use cached results (default: USE_CACHE global setting)
    """
    if use_cache is None:
        use_cache = USE_CACHE
    
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    budget_factor_list = get_default_budget_factor_list(region)
    
    save_utilization_distribution_plot_cached(
        users_and_facs_df, travel_dict, users, facs, output_filename, output_abs_path,
        budget_factor_list, facility_region='urban', cache_dir=get_cache_dir(), region=region, instance_number=instance_number,
        use_cache=use_cache, cache_only=cache_only, allow_missing=allow_missing
    )


# create the tables included in the paper

def create_table1(output_filename='overall_results.xlsx', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1, use_cache=None, cache_only=False, allow_missing=False):
    """
    creates table 1 of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    :param use_cache: whether to use cached results (default: USE_CACHE global setting)
    """
    if use_cache is None:
        use_cache = USE_CACHE
    
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    percentiles = [10, 50, 90]
    budget_factor_list = get_default_budget_factor_list(region)
    
    write_table_overall_results_cached(
        users_and_facs_df, travel_dict, users, facs, output_filename, output_abs_path,
        percentiles, budget_factor_list, cache_dir=get_cache_dir(), region=region, instance_number=instance_number,
        use_cache=use_cache, cache_only=cache_only, allow_missing=allow_missing
    )


def create_table2(output_filename='strict_vs_loose_results.xlsx', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1, cutoff=0.2, use_cache=None, cache_only=False, allow_missing=False):
    """
    creates table 2 of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    :param cutoff: travel combinations with a probability smaller than this value will be removed
    :param use_cache: whether to use cached results (default: USE_CACHE global setting)
    """
    if use_cache is None:
        use_cache = USE_CACHE
    
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    
    write_table_strict_vs_loose_results_cached(
        users_and_facs_df, travel_dict, users, facs, output_filename, output_abs_path,
        budget_factor=0.3, cache_dir=get_cache_dir(), region=region, instance_number=instance_number,
        cutoff=cutoff, use_cache=use_cache, cache_only=cache_only, allow_missing=allow_missing
    )


def create_table3(output_filename='fairness_results.xlsx', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1, use_cache=None, cache_only=False, allow_missing=False):
    """
    creates table 3 of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    :param use_cache: whether to use cached results (default: USE_CACHE global setting)
    """
    if use_cache is None:
        use_cache = USE_CACHE
    
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    budget_factor_list = get_default_budget_factor_list(region)
    
    write_table_fairness_results_cached(
        users_and_facs_df, travel_dict, users, facs, output_filename, output_abs_path,
        budget_factor_list, cache_dir=get_cache_dir(), region=region, instance_number=instance_number,
        use_cache=use_cache, cache_only=cache_only, allow_missing=allow_missing
    )


def create_table4(output_filename='pof_results.xlsx', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1, use_cache=None, cache_only=False, allow_missing=False):
    """
    creates table 4 of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    :param use_cache: whether to use cached results (default: USE_CACHE global setting)
    """
    if use_cache is None:
        use_cache = USE_CACHE
    
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    budget_factor_list = get_default_budget_factor_list(region)
    
    write_table_pof_results_cached(
        users_and_facs_df, travel_dict, users, facs, output_filename, output_abs_path,
        budget_factor_list, cache_dir=get_cache_dir(), region=region, instance_number=instance_number,
        use_cache=use_cache, cache_only=cache_only, allow_missing=allow_missing
    )


def create_table5(output_filename='greedy_results_nocutoff.xlsx', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1):
    """
    creates table 5 of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    """
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    save_greedy_results(users_and_facs_df, travel_dict, None, output_filename, output_abs_path,
                        budget_factor=0.7, cutoff=0.0)


def create_table6(output_filename='cutoff_results.xlsx', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1):
    """
    creates table S1 of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    """
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    save_cutoff_results(users_and_facs_df, travel_dict, None, output_filename, output_abs_path,
                        budget_factor=0.7, main_time_limit=10800, main_preqlinearize_cutoff=1)


def create_table7(output_filename='greedy_results_cutoff.xlsx', output_abs_path=None, input_data_abs_path=None, region="Bavaria", instance_number=1):
    """
    creates table S2 of the paper
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param input_data_abs_path: string containing the absolute path of the directory containing the input files;
        if None, the input files will be searched for in the same directory as this script
    :param region: region to load ("Bavaria" or "Hampshire")
    :param instance_number: instance number for the region
    """
    users_and_facs_df, travel_dict, users, facs = load_an_instance(instance_number, region=region, sufficient_cap=False)
    save_greedy_results(users_and_facs_df, travel_dict, None, output_filename, output_abs_path,
                        budget_factor=0.7, main_time_limit=10800, main_preqlinearize=1, greedy_time_limit=10800)
