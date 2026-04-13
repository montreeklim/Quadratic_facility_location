"""
Module for caching optimization results to disk to avoid re-solving models.

This module provides utilities to:
1. Save model results to JSON files with a consistent cache key based on model parameters
2. Load cached results if they exist
3. Manage result cache lifecycle
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Optional, Tuple, Any


def get_cache_key(region: str, instance_number: int, budget_factor: float, 
                  strict_assign_to_one: bool = False, cap_factor: float = 1.5,
                  cutoff: float = 0.2, max_access: bool = False) -> str:
    """
    Generate a unique cache key for a model configuration.
    
    :param region: Region name (e.g., 'Hampshire', 'Bavaria_1')
    :param instance_number: Instance number
    :param budget_factor: Budget factor used in the model
    :param strict_assign_to_one: Whether strict assignment is enabled
    :param cap_factor: Capacity factor
    :param cutoff: Travel probability cutoff
    :param max_access: Whether maximizing access
    :return: String hash representing the configuration
    """
    key_str = f"{region}_{instance_number}_{budget_factor}_{strict_assign_to_one}_{cap_factor}_{cutoff}_{max_access}"
    return hashlib.md5(key_str.encode()).hexdigest()


def get_cache_filename(cache_key: str, cache_dir: str) -> str:
    """
    Get the full path to a cache file.
    
    :param cache_key: The cache key (hash)
    :param cache_dir: Directory where cache files are stored
    :return: Full path to the cache file
    """
    return os.path.join(cache_dir, f"result_{cache_key}.json")


def ensure_cache_dir(cache_dir: str) -> str:
    """
    Ensure cache directory exists, creating it if necessary.
    
    :param cache_dir: Path to cache directory
    :return: Absolute path to cache directory
    """
    abs_cache_dir = os.path.abspath(cache_dir)
    os.makedirs(abs_cache_dir, exist_ok=True)
    return abs_cache_dir


def save_result(results: Dict[str, Any], region: str, instance_number: int, 
                budget_factor: float, cache_dir: str, strict_assign_to_one: bool = False,
                cap_factor: float = 1.5, cutoff: float = 0.2, 
                max_access: bool = False) -> str:
    """
    Save model results to cache.
    
    :param results: Dictionary containing model results
    :param region: Region name
    :param instance_number: Instance number
    :param budget_factor: Budget factor
    :param cache_dir: Directory to store cache
    :param strict_assign_to_one: Whether strict assignment is enabled
    :param cap_factor: Capacity factor
    :param cutoff: Travel probability cutoff
    :param max_access: Whether maximizing access
    :return: Path to the saved cache file
    """
    cache_key = get_cache_key(region, instance_number, budget_factor, 
                             strict_assign_to_one, cap_factor, cutoff, max_access)
    abs_cache_dir = ensure_cache_dir(cache_dir)
    cache_file = get_cache_filename(cache_key, abs_cache_dir)
    
    # Convert assignment dict keys to strings for JSON serialization
    # (pyomo might use various types as keys)
    results_serializable = json.loads(json.dumps(results, default=str))
    
    with open(cache_file, 'w') as f:
        json.dump(results_serializable, f, indent=2)
    
    print(f"   [CACHE] Saved result to: {cache_file}")
    return cache_file


def load_result(region: str, instance_number: int, budget_factor: float, 
                cache_dir: str, strict_assign_to_one: bool = False,
                cap_factor: float = 1.5, cutoff: float = 0.2, 
                max_access: bool = False) -> Optional[Dict[str, Any]]:
    """
    Load model results from cache if they exist.
    
    :param region: Region name
    :param instance_number: Instance number
    :param budget_factor: Budget factor
    :param cache_dir: Directory where cache files are stored
    :param strict_assign_to_one: Whether strict assignment is enabled
    :param cap_factor: Capacity factor
    :param cutoff: Travel probability cutoff
    :param max_access: Whether maximizing access
    :return: Dictionary containing results, or None if not cached
    """
    cache_key = get_cache_key(region, instance_number, budget_factor,
                             strict_assign_to_one, cap_factor, cutoff, max_access)
    abs_cache_dir = ensure_cache_dir(cache_dir)
    cache_file = get_cache_filename(cache_key, abs_cache_dir)
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                results = json.load(f)
            
            # Convert assignment dictionary keys and values from strings back to integers
            # JSON serialization converts all keys to strings, but we need numeric keys and values
            if 'solution_details' in results and 'assignment' in results['solution_details']:
                assignment = results['solution_details']['assignment']
                # Convert string keys and values back to integers
                converted_assignment = {}
                for k, v in assignment.items():
                    # Handle various types for keys
                    if isinstance(k, str) and k.lstrip('-').isdigit():
                        new_key = int(k)
                    else:
                        new_key = k
                    
                    # Handle various types for values (facility IDs)
                    if isinstance(v, (int, float)):
                        new_val = int(v)
                    elif isinstance(v, str) and v.lstrip('-').isdigit():
                        new_val = int(v)
                    elif isinstance(v, dict):
                        # If value is a dict, something is wrong with the cache file
                        raise ValueError(f"Assignment value for key {k} is a dict: {v}. Cache file may be corrupted.")
                    else:
                        new_val = v
                    
                    converted_assignment[new_key] = new_val
                
                results['solution_details']['assignment'] = converted_assignment
            
            # Ensure model_details lists are properly typed
            if 'model_details' in results:
                # Convert users list to integers if needed
                if 'users' in results['model_details']:
                    users = results['model_details']['users']
                    if users and isinstance(users, list):
                        results['model_details']['users'] = [
                            int(u) if isinstance(u, str) and u.lstrip('-').isdigit() else u 
                            for u in users
                        ]
                # Convert facs list to integers if needed
                if 'facs' in results['model_details']:
                    facs = results['model_details']['facs']
                    if facs and isinstance(facs, list):
                        results['model_details']['facs'] = [
                            int(f) if isinstance(f, str) and f.lstrip('-').isdigit() else f 
                            for f in facs
                        ]
            
            # Ensure solution_details lists are properly typed
            if 'solution_details' in results:
                # Convert open_facs list to integers if needed
                if 'open_facs' in results['solution_details']:
                    open_facs = results['solution_details']['open_facs']
                    if open_facs and isinstance(open_facs, list):
                        results['solution_details']['open_facs'] = [
                            int(f) if isinstance(f, str) and f.lstrip('-').isdigit() else f 
                            for f in open_facs
                        ]
            
            print(f"   [CACHE] Loaded result from: {cache_file}")
            return results
        except Exception as e:
            print(f"   [CACHE] Error loading cache file {cache_file}: {e}")
            return None
    
    return None


def clear_cache(cache_dir: str, region: Optional[str] = None) -> int:
    """
    Clear cache files, optionally filtered by region.
    
    :param cache_dir: Directory containing cache files
    :param region: Optional region name to filter by
    :return: Number of files deleted
    """
    abs_cache_dir = ensure_cache_dir(cache_dir)
    deleted_count = 0
    
    if not os.path.exists(abs_cache_dir):
        return 0
    
    for file in os.listdir(abs_cache_dir):
        if file.startswith("result_") and file.endswith(".json"):
            if region is None or region in file:
                file_path = os.path.join(abs_cache_dir, file)
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"   [CACHE] Error deleting {file_path}: {e}")
    
    return deleted_count


def list_cached_results(cache_dir: str, region: Optional[str] = None) -> list:
    """
    List all cached results, optionally filtered by region.
    
    :param cache_dir: Directory containing cache files
    :param region: Optional region name to filter by
    :return: List of tuples (cache_file, file_size_mb)
    """
    abs_cache_dir = ensure_cache_dir(cache_dir)
    cached_files = []
    
    if not os.path.exists(abs_cache_dir):
        return []
    
    for file in os.listdir(abs_cache_dir):
        if file.startswith("result_") and file.endswith(".json"):
            if region is None or region in file:
                file_path = os.path.join(abs_cache_dir, file)
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                cached_files.append((file, size_mb))
    
    return sorted(cached_files)
