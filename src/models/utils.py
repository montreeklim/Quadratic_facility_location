"""
Utility and help functions
"""

import os
from math import exp
import numpy as np
import pandas as pd
from geopy import distance
import json
import bz2
import _pickle as cPickle
import random
# from typing import List
from pathlib import Path

# functions for computing travel probabilities

# Bavaria travel probability functions
def f_urban_bavaria(d):
    if d < 5:
        return exp(-0.2550891696011455 * d ** 0.8674531576586394)
    else:
        return 4.639450774188538 * exp(-1.4989521421856289 * d ** 0.3288777336829004)


def f_rural_bavaria(d):
    if d < 5:
        return exp(-0.24990116894290326 * d ** 0.8201058149904008)
    else:
        return 1.6114912595353221 * exp(-0.6887217475464711 * d ** 0.43652329253292316)


# Hampshire travel probability functions
def f_urban_hampshire(d):
    return 1.02 * exp(-0.113 * d ** 1.01)


def f_rural_hampshire(d):
    return 1.02 * exp(-0.0762 * d ** 1.19)


# Default functions (Bavaria for backward compatibility)
def f_urban(d):
    return f_urban_bavaria(d)


def f_rural(d):
    return f_rural_bavaria(d)


def create_travel_dict(users_and_facs_df, users, facs, output_filename = 'travel_dict', region='Bavaria'):
    """
    Create the travel dictionary that specifies the probabilities for each travel combination
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param users: list of the users used in the instance
    :param facs: list of the facilities used in the instance
    :param output_filename: filename for saving the travel dictionary
    :param region: region name ('Bavaria' or 'Hampshire') to determine which travel probability functions and distance units to use
    :return: travel dictionary that specifies the probabilities for each travel combination
    """
    # Select the appropriate travel probability functions and distance units based on region
    if region == 'Hampshire':
        f_urban_region = f_urban_hampshire
        f_rural_region = f_rural_hampshire
        use_miles = True  # Hampshire uses miles
    else:  # Default to Bavaria
        f_urban_region = f_urban_bavaria
        f_rural_region = f_rural_bavaria
        use_miles = False  # Bavaria uses kilometers
    
    travel_dict = {i: {} for i in users}
    for i in users:
        print('user', i)
        regiotype = users_and_facs_df.at[i, 'regional spatial type']
        lat_1 = users_and_facs_df.at[i, 'centroid_lat']
        lon_1 = users_and_facs_df.at[i, 'centroid_lon']
            
        for j in facs:
            lat_2 = users_and_facs_df.at[j, 'rc_centroid_lat']
            lon_2 = users_and_facs_df.at[j, 'rc_centroid_lon']
            
            # Use region-specific distance units
            dist = distance.distance((lat_1, lon_1), (lat_2, lon_2)).miles if use_miles else distance.distance((lat_1, lon_1), (lat_2, lon_2)).km
            if regiotype == "urban":
                travel_dict[i][j] = f_urban_region(dist)
            else:
                travel_dict[i][j] = f_rural_region(dist)
    #with open(output_filename + '.json', 'w') as outfile:
    #    json.dump(travel_dict, outfile)
    save_travel_dict(travel_dict, travel_dict_filename=output_filename+ ".json.pbz2")


def create_distance_dict(users_and_facs_df, users, facs, region='Bavaria'):
    """
    Build a dictionary of user→facility geodesic distances.

    Uses rc_centroid coordinates when available, falling back to centroid.
    Skips pairs where either endpoint lacks valid coordinates.
    
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param users: list of the users used in the instance
    :param facs: list of the facilities used in the instance
    :param region: region name ('Bavaria' or 'Hampshire') to determine distance units (km for Bavaria, miles for Hampshire)
    :return: dictionary of user→facility distances
    """
    # Use region-specific distance units
    use_miles = region == 'Hampshire'
    
    distance_dict = {i: {} for i in users}
    for i in users:
        lat_1 = users_and_facs_df.at[i, 'centroid_lat']
        lon_1 = users_and_facs_df.at[i, 'centroid_lon']

        for j in facs:
            lat_2 = users_and_facs_df.at[j, 'rc_centroid_lat']
            lon_2 = users_and_facs_df.at[j, 'rc_centroid_lon']

            distance_dict[i][j] = distance.distance((lat_1, lon_1), (lat_2, lon_2)).miles if use_miles else distance.distance((lat_1, lon_1), (lat_2, lon_2)).km

    return distance_dict


# functions for loading and saving data files

def save_travel_dict(travel_dict, travel_dict_filename, abs_path=None):
    if not abs_path:
        # Use PROJECT_ROOT/data if abs_path not provided
        abs_path = DATA_DIR
    if not os.path.exists(abs_path):
        os.makedirs(abs_path)
    with bz2.BZ2File(Path(abs_path) / travel_dict_filename, "w") as f:
        cPickle.dump(travel_dict, f)


# compute project_root once
MODULE_DIR   = Path(__file__).resolve().parent        # src/models
PROJECT_ROOT = MODULE_DIR.parent.parent               # project root
DATA_DIR     = PROJECT_ROOT / "data"

def load_users_and_facs(dataset_name_or_filename="users_and_facilities.csv",
                        abs_path: str | Path = None):
    """
    Load users and facilities data from CSV file.
    
    :param dataset_name_or_filename: either a dataset name like "Bavaria_1" which will be 
                                     expanded to "Bavaria_1_users_and_facs.csv", or a full filename
    :param abs_path: absolute path to data directory (defaults to DATA_DIR)
    :return: dataframe with users and facilities data
    """
    data_dir = Path(abs_path) if abs_path else DATA_DIR
    
    # If the input looks like a dataset name (no underscore followed by "users_and_facs"),
    # construct the full filename
    if not dataset_name_or_filename.endswith('.csv'):
        filename = f"{dataset_name_or_filename}_users_and_facs.csv"
    else:
        filename = dataset_name_or_filename
    
    file_path = data_dir / filename
    return pd.read_csv(file_path)

def load_travel_dict(dataset_name_or_filename="travel_dict.json.pbz2",
                     abs_path: str | Path = None):
    """
    Load travel dictionary from compressed file.
    
    :param dataset_name_or_filename: either a dataset name like "Bavaria_1" which will be 
                                     expanded to "Bavaria_1_travel_dict.json.pbz2", or a full filename
    :param abs_path: absolute path to data directory (defaults to DATA_DIR)
    :return: travel dictionary with travel probabilities
    """
    data_dir = Path(abs_path) if abs_path else DATA_DIR
    
    # If the input looks like a dataset name (no .pbz2 extension),
    # construct the full filename
    if not dataset_name_or_filename.endswith('.pbz2'):
        filename = f"{dataset_name_or_filename}_travel_dict.json.pbz2"
    else:
        filename = dataset_name_or_filename
    
    with bz2.BZ2File(data_dir / filename, 'rb') as f:
        raw = cPickle.load(f)
    return {int(i): {int(j): raw[i][j] for j in raw[i]} for i in raw}

def load_facility_distance_dict(facility_distance_dict_filename="facility_distance_dict.json.pbz2",
                                abs_path: str | Path = None):
    data_dir = Path(abs_path) if abs_path else DATA_DIR
    with bz2.BZ2File(data_dir / facility_distance_dict_filename, 'rb') as f:
        raw = cPickle.load(f)
    return {int(i): {int(j): raw[i][j] for j in raw[i]} for i in raw}

def load_input_data(
    users_and_facilities_filename="users_and_facilities.csv",
    travel_dict_filename="travel_dict.json.pbz2",
    abs_path=None
):
    users_and_facs_df = load_users_and_facs(users_and_facilities_filename, abs_path)
    travel_dict = load_travel_dict(travel_dict_filename, abs_path)
    return users_and_facs_df, travel_dict

def extract_users_and_facs(users_and_facs_df):
    """
    Extract users and facilities from dataframe.
    Works with both 'capacity' and 'rc_capacity' column names.
    Handles capacity values with commas (e.g., '1,000' or '1,000 ').
    Only includes users with valid (non-NaN) coordinates.
    
    :param users_and_facs_df: dataframe with users and facilities data
    :return: tuple of (users list, facs list)
    """
    import math
    users = []
    
    # Check which capacity column exists
    capacity_col = None
    if 'capacity' in users_and_facs_df.columns:
        capacity_col = 'capacity'
    elif 'rc_capacity' in users_and_facs_df.columns:
        capacity_col = 'rc_capacity'
    else:
        raise ValueError("Neither 'capacity' nor 'rc_capacity' column found in dataframe")
    
    # Extract users with valid coordinates (not NaN)
    for i in users_and_facs_df.index:
        try:
            # Check if user has valid coordinates
            lat = users_and_facs_df.at[i, 'centroid_lat']
            lon = users_and_facs_df.at[i, 'centroid_lon']
            if math.isnan(lat) or math.isnan(lon):
                # Skip users with invalid coordinates
                continue
            users.append(i)
        except (ValueError, TypeError):
            # Skip rows where coordinates can't be checked
            pass
    
    # Convert capacity to numeric and filter for positive values
    facs = []
    for i in users_and_facs_df.index:
        try:
            cap_str = str(users_and_facs_df.at[i, capacity_col]).strip()
            # Remove commas from the string (e.g., '1,000' -> '1000')
            cap_str = cap_str.replace(',', '')
            cap_value = float(cap_str)
            if cap_value > 0:
                facs.append(i)
        except (ValueError, TypeError):
            # Skip rows where capacity can't be converted to float
            pass
    
    return users, facs

def write_results_list(results, output_filename, output_abs_path = None):
    # save the table
    if not output_abs_path:
        output_abs_path = os.getcwd() + "/own_results"
    if not os.path.exists(output_abs_path):
        os.makedirs(output_abs_path)
    with open(Path(output_abs_path + "/" + output_filename), 'w') as f:
        json.dump(results, f)

def read_results_list(filename, abs_path = None):
    """
    Read a results list and fix keys being string instead of int
    :param filename: filename, if no abs_path given in own_results folder
    :return: results list with fixed keys being int
    """
    if not abs_path:
        abs_path = os.getcwd() + "/own_results"
    with open(Path(abs_path+"/"+filename), 'r') as infile:
        results_list = json.load(infile)
    for results in results_list:
        results['solution_details']['assignment'] = {int(i): j for (i, j) in
                                                     results['solution_details']['assignment'].items()}
    return results_list

def geodesic_distance(users_and_facs_df, i, j):
    """
    Compute the geodesic distance from user i to facility j
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param i: index of the user
    :param j: index of the facility
    :return: distance in miles from user i to facility j
    """
    return distance.distance(
        (users_and_facs_df.at[i, 'centroid_lat'], users_and_facs_df.at[i, 'centroid_lon']),
        (users_and_facs_df.at[j, 'rc_centroid_lat'],
         users_and_facs_df.at[j, 'rc_centroid_lon'])).miles


def capacity_constraints_slack(users_and_facs_df, travel_dict,cap_dict, facs, assignment):
    """
    Compute how much capacity is left for each facility given an assignment.
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param cap_dict: dictionary of capacities of the facilities
    :param facs: list of the facilities used in the instance
    :param assignment: dictionary of key user, value facility
    :return: return a dictionary of slack for each facility, 
        array of facilities who do not have their capacity constraint satisfied,
        dictionary with key facilities and value list of users assigned to that facility in assignment
    """
    slacks = cap_dict.copy()
    assigned_users = {j: [] for j in facs}
    for i, j in assignment.items():
        assigned_users[j].append(i)
        slacks[j] = slacks[j] - users_and_facs_df.at[i, 'population'] * travel_dict[i][j]
    not_satisfed = [j for j in facs if slacks[j] < 0]
    return slacks, not_satisfed, assigned_users


def check_valid_solution(users_and_facs_df, travel_dict, facs, open_facs, users, assignment,
                          budget_factor, cap_factor = 1.5):
    """"
    Check if assignment is valid solution to a BFLP / BUAP instance
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param facs: list of the open facilities used in the instance
    :param users: list of users
    :param assignment: dictionary of key user, value facility
    :param budget_factor: proportion of facilities that should be open at a maximum
    :param cap_factor: factor by which all capacities are scaled
    :return: true if assignment is valid, false otherwise.
    """
    # check each user assigned to a facility
    if(not all(i in assignment.keys() for i in users)):
        print("Some user is not assigned a facility")
        return False
    # check only open facilities used 
    if(not all(j in open_facs for j in assignment.values())):
        print("Some user is assigned to a closed facility")
        return False
    # check capacity constraints satisfied
    slacks = {j: cap_factor * users_and_facs_df.at[j, 'capacity'] for j in facs}
    for i, j in assignment.items():
        slacks[j] = slacks[j] - users_and_facs_df.at[i, 'population'] * travel_dict[i][j]
    not_satisfed = [j for j in facs if slacks[j] < 0]
    if len(not_satisfed) > 0:
        print("Capacity constraints not satisfied")
        print(not_satisfed)
        return False
    # check correct number of open facilities
    if len(open_facs) > round(budget_factor*len(facs)):
        print("Too many facilities open ")
        return False
    objective = sum(cap_factor*users_and_facs_df.at[j, "capacity"]*(slacks[j]/(cap_factor*users_and_facs_df.at[j, "capacity"]))**2 for j in facs)
    print("Objective: " + str(objective))
    return True


def check_valid_solution_with_unassigned(users_and_facs_df, travel_dict, facs, open_facs, users,
                                          assignment, budget_factor, cap_factor = 1.5):
    """"
    Check if assignment is valid solution, apart from allowing some users being unassigned.
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param facs: list of the open facilities used in the instance
    :param users: list of users
    :param assignment: dictionary of key user, value facility
    :param budget_factor: proportion of open facilities
    :param cap_factor: factor by which all capacities are scaled
    :return: true if assignment is valid, false otherwise
    """
    # check each user assigned to a facility
    if(not all(i in assignment.keys() for i in users)):
        print("Some user is not assigned a facility")
        return False
    # check only open facilities used 
    if(not all(j in open_facs or j=="unassigned" for j in assignment.values())):
        print("Some user is assigned to a closed facility")
        return False
    # check capacity constraints satisfied
    slacks = {j: cap_factor * users_and_facs_df.at[j, 'capacity'] for j in facs}
    for i, j in assignment.items():
        if j != "unassigned":
            slacks[j] = slacks[j] - users_and_facs_df.at[i, 'population'] * travel_dict[i][j]
    not_satisfed = [j for j in facs if slacks[j] < 0]
    if len(not_satisfed) > 0:
        print("Capacity constraints not satisfied")
        print(not_satisfed)
        return False
    # check correct number of open facilities
    if len(open_facs) > round(budget_factor*len(facs)):
        print("Too many facilities open ")
        return False
    objective = sum(cap_factor*users_and_facs_df.at[j, "capacity"]*(slacks[j]/(cap_factor*users_and_facs_df.at[j, "capacity"]))**2 for j in facs)
    print("Objective: " + str(objective))
    return True

def generate_data(n_users: int, p_fac: float, output_file_name_prefix = "large_random_instance"):
    '''
    Generates random BFLP instance and saves a users_and_facs_df and a dictionary of P_ij (travel_dict) for this instance.
    :param: n_users: number of users of generated instance
    :param: p_fac: probability each ZIP code has a facility
    :param: output_file_name_prefix: First part of the name for the files in which the instance is saved
    '''
    # Longitude and latitude range for Germany
    #lon_min, lon_max = 5.8663153, 15.0419319
    #lat_min, lat_max = 47.2701114, 55.099161
    # Longitude and latitude range for Bavaria
    #lon_min, lon_max = 9.01111334936577, 13.778347475506
    #lat_min, lat_max = 47.3625560497034, 50.5248689558092

    # Quarter of Bavaria size
    lon_min, lon_max = 9.0, 11.5
    lat_min, lat_max = 47.3, 49.0

    data = []
    users = list(range(n_users))
    facs = []
    for i in range(n_users):
        zip = i
        lon = random.uniform(lon_min, lon_max)
        lat = random.uniform(lat_min, lat_max)
        population = random.randint(0, 20000)
        capacity = random.randint(0, 80000) if random.random() < p_fac else 0
        if capacity > 0:
            facs.append(i)
        spatial_type = "rural" if random.random() < 0.5 else "urban"
        data.append({'zipcode': zip,'centroid_lat': lat,'centroid_lon': lon, 
                     'regional spatial type': spatial_type,'population': population, 
                     'capacity': capacity,'rc_centroid_lat': lat + random.gauss(0.0, 0.01),
                     'rc_centroid_lon': lon + random.gauss(0.0, 0.01)})
    users_and_facs_df = pd.DataFrame(data)
    users_and_facs_df.to_csv("data/"+ output_file_name_prefix+'_users_and_facs.csv', index=False)
    create_travel_dict(users_and_facs_df, users, facs, output_filename=output_file_name_prefix+'_travel_dict')

def create_users_facs_by_zip_code_division(users_and_facs_df, users,facs):
    """
    Splits up instance 1 into small instances
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param users: list of the users used in the instance
    :param facs: list of the facilities used in the instance
    :return: list of dictionaries of users and facs split by the first two digits of their ZIP codes
    """
    zip_codes_starts = []
    for i in users:
        if str(users_and_facs_df.at[i, "zipcode"])[0:2] not in zip_codes_starts:
            zip_codes_starts.append(str(users_and_facs_df.at[i, "zipcode"])[0:2])

    split_users = {start: [] for start in zip_codes_starts}
    split_facs = {start: [] for start in zip_codes_starts}
    for i in users:
        split_users[str(users_and_facs_df.at[i, "zipcode"])[0:2]].append(i)

    for j in facs:
        split_facs[str(users_and_facs_df.at[j, "zipcode"])[0:2]].append(j)
    return split_users, split_facs

def create_larger_sets_by_combining_zip_code_starts(users_and_facs_df, users, facs):
    """
    Splits up instance 1 into medium sized instances
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param users: list of the users used in the instance
    :param facs: list of the facilities used in the instance
    :return: list of dictionaries of users and facs split by the first two digits of their ZIP codes
        but combined to larger sets
    """
    split_users, split_facs = create_users_facs_by_zip_code_division(users_and_facs_df, users,facs)
    combined_zip_codes = {"63, 97, 96, 95" : [63, 97, 96, 95], "90, 91, 92": [90, 91, 92],
                            "93, 94": [93, 94], "80, 81, 82, 83, 84, 85" : [80, 81, 82, 83, 84, 85],
                            "86, 87,88, 89": [86, 87, 88, 89]}
    split_users_combined = {start: [] for start in combined_zip_codes.keys()}
    split_facs_combined = {start: [] for start in combined_zip_codes.keys()}
    for key, value in split_users.items():
        for key_combined,value_combined  in combined_zip_codes.items():
            if int(key) in value_combined:
                split_users_combined[key_combined].extend(value)
    for key, value in split_facs.items():
        for key_combined,value_combined  in combined_zip_codes.items():
            if int(key) in value_combined:
                split_facs_combined[key_combined].extend(value)
    return split_users_combined, split_facs_combined

def get_instance_2_users_facs(users_and_facs_df, users, facs):
    '''
    Creates and returns the user and facility sets for Instance 2 from Instance 1 input
    :param users_and_facs_df: dataframe of user and facility related input data
    :param users: set of users
    :param facs: set of facilities
    :return: the users and facilities of instance 2
    '''
    users_list, facs_list = create_larger_sets_by_combining_zip_code_starts(users_and_facs_df, users, facs)
    users_2 = users_list["90, 91, 92"]
    facs_2 =  facs_list["90, 91, 92"]
    return users_2, facs_2

def load_an_instance(instance_number, region="Bavaria", sufficient_cap=False):
    '''
    Helper function for getting all the data needed for a specific instance
    :param instance_number: the number of the instance; for Bavaria: 1, 3, 4; for Hampshire: 1
    :param region: the region to load; possible inputs are "Bavaria" or "Hampshire"
    :param sufficient_cap: boolean indicating whether the version of the instance where
        sum_{i in I} U_i P_ij <= C_j should be loaded
    :return: users and facilities dataframe, dictionary of P_ij, list of users, list of facilities
    '''
    if region not in ["Bavaria", "Hampshire"]:
        print(f"The region '{region}' is not supported. Use 'Bavaria' or 'Hampshire'.")
        return None
    
    if region == "Bavaria":
        if instance_number not in [1, 3, 4]:
            print("For Bavaria, instance number must be 1, 3, or 4.")
            return None
    elif region == "Hampshire":
        if instance_number != 1:
            print("For Hampshire, only instance number 1 is available.")
            return None
    
    suff_postfix = "suff_" if sufficient_cap else ""
    
    # Hampshire doesn't use instance numbers in filenames
    if region == "Hampshire":
        uaf_filename = f"{region}_{suff_postfix}users_and_facs.csv"
        td_filename = f"{region}_travel_dict.json.pbz2"
    else:
        uaf_filename = f"{region}_{instance_number}_{suff_postfix}users_and_facs.csv"
        td_filename = f"{region}_{instance_number}_travel_dict.json.pbz2"

    users_and_facs_df, travel_dict = load_input_data(users_and_facilities_filename=uaf_filename,
                                                      travel_dict_filename=td_filename)
    
    # Use extract_users_and_facs to properly handle capacity column (may contain strings)
    users, facs = extract_users_and_facs(users_and_facs_df)
    
    # Ensure capacity and population columns are numeric (some datasets have comma-formatted strings)
    users_and_facs_df['capacity'] = pd.to_numeric(
        users_and_facs_df['capacity'].astype(str).str.replace(',', ''),
        errors='coerce'
    )
    users_and_facs_df['population'] = pd.to_numeric(
        users_and_facs_df['population'].astype(str).str.replace(',', ''),
        errors='coerce'
    )

    return users_and_facs_df, travel_dict, users, facs


def load_results(results_filename, abs_path):
    with open(abs_path+"/"+results_filename, 'r') as infile:
        results_list = json.load(infile)
    for results in results_list:
        results['solution_details']['assignment'] = {int(i): j for (i, j) in
                                                     results['solution_details']['assignment'].items()}
    return results_list


def save_results(results_list, results_filename, abs_path):
    if not abs_path:
        abs_path = os.getcwd() + "/own_results"
    if not os.path.exists(abs_path):
        os.makedirs(abs_path)
    with open(abs_path + "/" + results_filename, 'w') as outfile:
        json.dump(results_list, outfile)


def safe_percentile(a, p):
    """
    compute the p-th percentile of the array a. If the array is empty, return None
    :param a: an array of values
    :param p: percentile; must be between 0 and 100
    :return: the p-th percentile of the array or None if the array is empty
    """
    if not a:
        return None
    else:
        return np.percentile(a, p)


def get_lower_bound(users_and_facs_df, travel_dict, users, facs, budget_factor, cap_factor=1.5):
    """
    compute a lower bound on the optimal objective value
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param users: list of the users used in the instance
    :param facs: list of the facilities used in the instance
    :param budget_factor: ratio of facilities that are allowed to be opened
    :param cap_factor: factor by which all capacities are scaled
    :return: a lower bound on the optimal objective value
    """
    budget = round(budget_factor * len(facs))

    # filter the data frame by the used facilities and sort it by their capacities
    sorted_facs_df = users_and_facs_df.iloc[facs].sort_values(by=['capacity'], ascending=False)
    caps = [c * cap_factor for c in sorted_facs_df['capacity']]
    largest_caps = caps[:budget]

    max_exp_travelers = []
    for i in users:
        # Guard against sparse travel_dict entries
        fac_probs = [travel_dict.get(i, {}).get(j, 0) for j in facs if j in travel_dict.get(i, {})]
        if fac_probs:
            max_exp_travelers.append(users_and_facs_df.at[i, 'population'] * max(fac_probs))
        else:
            max_exp_travelers.append(0)
    
    # Handle edge cases: if largest_caps is empty or sum is zero, use a safe bound
    sum_largest_caps = sum(largest_caps)
    if sum_largest_caps == 0 or len(largest_caps) == 0:
        lb = sum(caps) - sum(max_exp_travelers)
    else:
        lb = min(sum(caps) + sum(max_exp_travelers) ** 2 / sum_largest_caps - 2 * sum(max_exp_travelers),
                 sum(caps) - sum(max_exp_travelers))
    return lb


# functions for computing key figures from results

def get_region_list(user_region='all', facility_region='all'):
    if user_region == 'all':
        user_region_list = ['rural', 'urban']
    else:
        user_region_list = [user_region]
    if facility_region == 'all':
        facility_region_list = ['rural', 'urban']
    else:
        facility_region_list = [facility_region]
    return user_region_list, facility_region_list


def get_distances_to_assigned(results, users_and_facs_df, user_region='all', facility_region='all'):
    """
    compute the distance from users to the respective assigned facility
    :param results: dictionary of the results
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param user_region: string indicating the considered region of origin for the users: "urban", "rural" or "all"
    :param facility_region: string indicating the considered region of location for the facilities:
        "urban", "rural" or "all"
    :return: a dictionary with the the distance from users to the respective assigned facility
    """
    assignment = results['solution_details']['assignment']
    user_region_list, facility_region_list = get_region_list(user_region, facility_region)
    distance_dict = {i: geodesic_distance(users_and_facs_df, i, j) for (i, j) in assignment.items() if
                     users_and_facs_df.at[i, 'regional spatial type'] in user_region_list and
                     users_and_facs_df.at[j, 'regional spatial type'] in facility_region_list}
    return distance_dict


def get_access(results, users_and_facs_df, travel_dict, user_region='all', facility_region='all'):
    """
    compute the abs access of facilities to users
    :param results: dictionary of the results
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param user_region: string indicating the considered region of origin for the users: "urban", "rural" or "all"
    :param facility_region: string indicating the considered region of location for the facilities:
        "urban", "rural" or "all"
    :return: a dictionary with the abs access of facilities to users
    """
    assignment = results['solution_details']['assignment']
    open_facs = results['solution_details']['open_facs']
    user_region_list, facility_region_list = get_region_list(user_region, facility_region)
    access = {j: sum(users_and_facs_df.at[i, 'population'] * travel_dict[i][j] for i in assignment.keys()
                     if assignment[i] == j and users_and_facs_df.at[i, 'regional spatial type'] in user_region_list)
              for j in open_facs if users_and_facs_df.at[j, 'regional spatial type'] in facility_region_list}
    return access


def get_overall_access(results, users_and_facs_df, travel_dict, user_region='all', facility_region='all'):
    """
    compute the overall access
    :param results: dictionary of the results
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param user_region: string indicating the considered region of origin for the users: "urban", "rural" or "all"
    :param facility_region: string indicating the considered region of location for the facilities:
        "urban", "rural" or "all"
    :return: a scalar specifying the fraction of users that has access
    """
    assignment = results['solution_details']['assignment']
    user_region_list, _ = get_region_list(user_region, facility_region)
    access = get_access(results, users_and_facs_df, travel_dict, user_region, facility_region)
    overall_access = sum(access.values()) / sum(users_and_facs_df.at[int(i), 'population']
                                                for i in assignment.keys() if
                                                users_and_facs_df.at[i, 'regional spatial type'] in user_region_list)
    return overall_access


def get_utilization(results, users_and_facs_df, travel_dict, user_region='all', facility_region='all'):
    """
    compute the utilization of open facilities
    :param results: dictionary of the results
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param user_region: string indicating the considered region of origin for the users: "urban", "rural" or "all"
    :param facility_region: string indicating the considered region of location for the facilities:
        "urban", "rural" or "all"
    :return: a dictionary with the utilization of open facilities
    """
    open_facs = results['solution_details']['open_facs']
    cap_factor = results['model_details']['cap_factor']
    _, facility_region_list = get_region_list(user_region, facility_region)
    access = get_access(results, users_and_facs_df, travel_dict, user_region, facility_region)
    utilization = {j: access[j] / (users_and_facs_df.at[j, 'capacity'] * cap_factor)
                   for j in open_facs if users_and_facs_df.at[j, 'regional spatial type'] in facility_region_list}
    return utilization


def get_weighted_utilization_figures(results, users_and_facs_df, travel_dict, facility_region='all'):
    """
    compute the weighted mean, weighted variance and the weighted Coefficient of Variation for the utilization of
    open facilites
    :param results: dictionary of the results
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param facility_region: string indicating the considered region of location for the facilities:
        "urban", "rural" or "all"
    :return: 3 scalars, the weighted mean, weighted variance and the weighted Coefficient of Variation
    for the utilization of open facilites
    """
    utilization = get_utilization(results, users_and_facs_df, travel_dict, facility_region=facility_region)
    if not utilization:
        return None, None, None
    denom = sum(users_and_facs_df.at[j, 'capacity'] for j in utilization)
    if denom == 0:
        return None, None, None
    weighted_utilization_mean = sum(users_and_facs_df.at[j, 'capacity'] * utilization[j] for j in utilization) / denom
    weighted_utilization_std = (
        sum(
            users_and_facs_df.at[j, 'capacity'] * (utilization[j] - weighted_utilization_mean) ** 2
            for j in utilization
        ) / denom
    ) ** 0.5
    if weighted_utilization_mean == 0:
        weighted_utilization_cv = None
    else:
        weighted_utilization_cv = weighted_utilization_std / weighted_utilization_mean
    return weighted_utilization_mean, weighted_utilization_std, weighted_utilization_cv


def get_dof(results, users_and_facs_df, travel_dict):
    """
    compute the DoF and the DoF'
    :param results: dictionary of the results
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :return: 2 scalars, the DoF and the DoF'
    """
    assignment = results['solution_details']['assignment']
    open_facs = results['solution_details']['open_facs']
    utilization = get_utilization(results, users_and_facs_df, travel_dict)
    j_u_tuples = [(j, utilization[j]) for j in open_facs]
    nr_of_warranted_fairness_pairs = 0
    nr_of_compensatory_fairness_pairs = 0
    for (j1, u1) in j_u_tuples:
        assigned_users = [int(i) for (i, j) in assignment.items() if j == j1]
        for (j2, u2) in j_u_tuples:
            if j2 == j1:
                continue
            is_most_preferred = True
            for i in assigned_users:
                if travel_dict[i][j1] < travel_dict[i][j2]:
                    is_most_preferred = False
                    break
            if is_most_preferred:
                nr_of_warranted_fairness_pairs += 1
            else:
                if u1 < u2:
                    nr_of_compensatory_fairness_pairs += 1

    nr_of_facility_tuples = len(open_facs) * (len(open_facs) - 1)
    dof = (nr_of_warranted_fairness_pairs + nr_of_compensatory_fairness_pairs) / nr_of_facility_tuples
    if nr_of_facility_tuples == nr_of_warranted_fairness_pairs:
        # in that case the dof_prime is not defined
        return dof, None
    dof_prime = nr_of_compensatory_fairness_pairs / (nr_of_facility_tuples - nr_of_warranted_fairness_pairs)
    return dof, dof_prime
    