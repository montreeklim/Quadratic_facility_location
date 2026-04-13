"""
Plotting functions for facility location models with caching support.
"""

import os
from utils import get_access, get_utilization, get_distances_to_assigned, get_region_list, safe_percentile, get_overall_access
from result_cache import load_result, save_result, ensure_cache_dir
from results import (
    write_overall_results,
    write_fairness_results,
    write_pof_results,
    write_strict_vs_loose_results,
)
from model import solve_model_naively
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.ticker as mtick
import scipy.stats as stats


def get_default_threads():
    """
    Get the optimal number of threads for parallel processing.
    Returns the number of CPU cores available, or 1 if unable to determine.
    """
    try:
        threads = os.cpu_count()
        return threads if threads is not None else 1
    except:
        return 1


def get_default_cap_factor(region, instance_number):
    """
    Determine the appropriate cap_factor based on region and instance.
    
    :param region: region name (e.g., 'Hampshire', 'Bavaria')
    :param instance_number: instance number
    :return: appropriate cap_factor value
    """
    if region is None:
        return 1.0
    
    region_lower = region.lower() if isinstance(region, str) else ''
    
    # Hampshire: always 1.0
    if 'hampshire' in region_lower:
        return 1.0
    
    # Bavaria instances
    if 'bavaria' in region_lower:
        if instance_number == 1:
            return 1.5
        elif instance_number in [3, 4]:
            return 0.8
        else:
            # For sufficient capacity instances or other instances
            return 1.0
    
    # Default for other regions
    return 1.0


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


def plot_overall_access(results_list, users_and_facs_df, travel_dict, output_filename='overall_access.pdf',
                        output_abs_path=None):
    """
    plot the overall access for different budgets
    :param results_list: list of dictionaries of the results
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    """
    # make sure the results are sorted in increasing order by budget
    results_list = sorted(results_list, key=lambda d: d['model_details']['budget_factor'])

    # get relevant data
    overall_access_dict = {
        region: [get_overall_access(results, users_and_facs_df, travel_dict, user_region=region) * 100 for results in
                 results_list] for region in ['all', 'rural', 'urban']}
    budget_factor_list = [round(results['model_details']['budget_factor'] * 100) for results in results_list]

    # plot the figure
    tnr_font = {'fontname': 'Times New Roman'}
    plt.rcParams["figure.figsize"] = (10, 2 / 3 * 10)
    plt.plot(budget_factor_list, overall_access_dict['all'], label='all', color='blue')
    plt.plot(budget_factor_list, overall_access_dict['rural'], label='rural', color='green')
    plt.plot(budget_factor_list, overall_access_dict['urban'], label='urban', color='red')
    plt.legend(loc="lower right", prop={'family': 'Times New Roman', 'size': 'xx-large'})
    plt.xlabel('Budget [%]', fontsize="xx-large", **tnr_font)
    plt.ylabel('Overall access [%]', fontsize="xx-large", **tnr_font)
    plt.ylim()
    plt.tick_params(labelsize="x-large")
    plt.xticks(**tnr_font)
    plt.yticks(**tnr_font)
    plt.xlim([None, budget_factor_list[-1]])

    # save the figure
    if not output_abs_path:
        output_abs_path = os.getcwd() + "\\own_results"
    if not os.path.exists(output_abs_path):
        os.makedirs(output_abs_path)
    plt.savefig(output_abs_path + "\\" + output_filename, dpi=1200)
    plt.clf()

def plot_cap_vs_access(results, users_and_facs_df, travel_dict, output_filename='cap_vs_access.pdf',
                       output_abs_path=None, facility_region='all'):
    """
    make a capacity vs access scatter plot for the open facilities
    :param results: dictionary of the results
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param facility_region: string indicating the considered region of location for the facilities:
        "urban", "rural" or "all"
    """
    # get relevant data
    open_facs = results['solution_details']['open_facs']
    cap_factor = results['model_details']['cap_factor']
    _, facility_region_list = get_region_list(facility_region=facility_region)
    capacity = {j: users_and_facs_df.at[j, 'capacity'] * cap_factor
                for j in open_facs if users_and_facs_df.at[j, 'regional spatial type'] in facility_region_list}
    access = get_access(results, users_and_facs_df, travel_dict, facility_region=facility_region)
    capacity_array = np.array(list(capacity.values())).reshape((-1, 1))
    access_array = np.array(list(access.values()))

    # fit a linear function
    model = LinearRegression(fit_intercept=False).fit(capacity_array, access_array)

    # plot the figure
    tnr_font = {'fontname': 'Times New Roman'}
    plt.rcParams["figure.figsize"] = (10, 2 / 3 * 10)
    plt.scatter(capacity_array, access_array)
    plt.plot(capacity_array, model.coef_ * capacity_array, "r")
    plt.xlabel('Capacity', fontsize="xx-large", **tnr_font)
    plt.ylabel('Access', fontsize="xx-large", **tnr_font)
    plt.tick_params(labelsize="x-large")
    plt.xticks(**tnr_font)
    plt.yticks(**tnr_font)
    plt.ticklabel_format(style='sci', axis='both', scilimits=(0, 0))
    plt.xlim([0, None])
    plt.ylim([0, None])

    # save the figure
    if not output_abs_path:
        output_abs_path = os.getcwd() + "\\own_results"
    if not os.path.exists(output_abs_path):
        os.makedirs(output_abs_path)
    plt.savefig(output_abs_path + "\\" + output_filename, dpi=1200)
    plt.clf()

def plot_utilization_percentiles(results_list, users_and_facs_df, travel_dict,
                                 output_filename='utilization_percentiles.pdf', output_abs_path=None, percentiles=None):
    """
    plot the utilization of open facilities for three different percentiles for different budgets
    :param results_list: list of dictionaries of the results
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param percentiles: list of the three considered percentiles. Values must be between 0 and 100
    """
    # init
    regions = ['all', 'rural', 'urban']
    if percentiles is None or len(percentiles) != 3:
        percentiles = [10, 50, 90]

    # make sure the results are sorted in increasing order by budget
    results_list = sorted(results_list, key=lambda d: d['model_details']['budget_factor'])
    nr_of_results = len(results_list)

    # get relevant data
    utilization_dict = \
        {region: [[u * 100
                   for u in get_utilization(results, users_and_facs_df, travel_dict, facility_region=region).values()]
                  for results in results_list] for region in regions}
    budget_factor_list = [round(results['model_details']['budget_factor'] * 100) for results in results_list]

    # compute the percentiles of the utilization of open facilities for each instance and each region
    percentiles_dict = {region: {p: [safe_percentile(utilization_dict[region][i], p) for i in range(nr_of_results)]
                                 for p in percentiles}
                        for region in regions}

    # plot the figure
    tnr_font = {'fontname': 'Times New Roman'}
    plt.rcParams["figure.figsize"] = (10, 2 / 3 * 10)
    plt.plot(budget_factor_list, percentiles_dict['all'][percentiles[0]], ls="dashed", color='blue')
    plt.plot(budget_factor_list, percentiles_dict['rural'][percentiles[0]], ls="dashed", color='green')
    plt.plot(budget_factor_list, percentiles_dict['urban'][percentiles[0]], ls="dashed", color='red')
    line_all, = plt.plot(budget_factor_list, percentiles_dict['all'][percentiles[1]], label='all', color='blue')
    line_rural, = plt.plot(budget_factor_list, percentiles_dict['rural'][percentiles[1]], label='rural', color='green')
    line_urban, = plt.plot(budget_factor_list, percentiles_dict['urban'][percentiles[1]], label='urban', color='red')
    plt.plot(budget_factor_list, percentiles_dict['all'][percentiles[2]], ls="dotted", color='blue', linewidth=2)
    plt.plot(budget_factor_list, percentiles_dict['rural'][percentiles[2]], ls="dotted", color='green', linewidth=2)
    plt.plot(budget_factor_list, percentiles_dict['urban'][percentiles[2]], ls="dotted", color='red', linewidth=2)
    # plt.legend(handles=[line_all, line_rural, line_urban], fontsize="xx-large",
    #            prop={'family': 'Times New Roman', 'size': 'xx-large'})
    legend = plt.legend(handles=[line_all, line_rural, line_urban], fontsize="xx-large",
                        prop={'family': 'Times New Roman', 'size': 'xx-large'}, loc='upper right',
                        bbox_to_anchor=(0.7, 1))
    # dummy lines for legend
    line_10, = plt.plot([], [], label=str(percentiles[0])+'th percentile', ls="dashed", color='black')
    line_50, = plt.plot([], [], label=str(percentiles[1])+'th percentile', color='black')
    line_90, = plt.plot([], [], label=str(percentiles[2])+'th percentile', ls="dotted", color='black')
    plt.gca().add_artist(legend)
    plt.legend(handles=[line_10, line_50, line_90], fontsize="xx-large",
               prop={'family': 'Times New Roman', 'size': 'xx-large'}, loc='upper right')
    plt.xlabel('Budget [%]', fontsize="xx-large", **tnr_font)
    plt.ylabel('Utilization [%]', fontsize="xx-large", **tnr_font)
    plt.ylim()
    plt.tick_params(labelsize="x-large")
    plt.xticks(**tnr_font)
    plt.yticks(**tnr_font)
    plt.xlim([None, budget_factor_list[-1]])

    # save the figure
    if not output_abs_path:
        output_abs_path = os.getcwd() + "\\own_results"
    if not os.path.exists(output_abs_path):
        os.makedirs(output_abs_path)
    plt.savefig(output_abs_path + "\\" + output_filename, dpi=1200)
    plt.clf()

def plot_utilization_distribution(results_list, users_and_facs_df, travel_dict,
                                  output_filename='utilization_distribution.pdf', output_abs_path=None,
                                  facility_region='all'):
    """
    plot the the distribution in the utilization of open facilities for different budgets
    :param results_list: list of dictionaries of the results
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param travel_dict: dictionary of the travel probabilities from each user to each facility
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param facility_region: string indicating the considered region of location for the facilities:
        "urban", "rural" or "all"
    """
    if len(results_list) > 12:
        print('Number of instances exceeds the feasible amount (12)')
        return None

    # make sure the results are sorted in increasing order by budget
    results_list = sorted(results_list, key=lambda d: d['model_details']['budget_factor'])

    # initialize the figure
    tnr_font = {'fontname': 'Times New Roman'}
    plt.rcParams["figure.figsize"] = (10, 2 / 3 * 10)
    markers = {0: 'o', 1: '', 2: 7}
    colors = {0: 'blue', 1: 'red', 2: 'green', 3: 'orange'}
    fig, ax = plt.subplots()
    x = np.linspace(0, 100, 250)

    for i, results in enumerate(results_list):
        # get relevant data
        utilization_list = [100 * u for u in get_utilization(results, users_and_facs_df, travel_dict,
                                                             facility_region=facility_region).values()]
        if len(utilization_list) < 2:
            print(f" Skipping Case {i}: utilization_list too short (len = {len(utilization_list)}) "
                  f"for budget = {results['model_details']['budget_factor']}")
            continue
        
        budget_factor_list = [round(results['model_details']['budget_factor'] * 100) for results in results_list]
        density = stats.gaussian_kde(utilization_list)

        # plot the figure
        plt.plot(x, density(x), label=str(budget_factor_list[i]) + '% ' + 'Budget',
                 marker=markers[i // 4], markevery=10, color=colors[i % 4])
        plt.xlabel('Utilization [%]', fontsize="xx-large", **tnr_font)
        plt.ylabel('Open facilities [%]', fontsize="xx-large", **tnr_font)
        plt.ylim(0, 0.05)
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, symbol=None))
        plt.legend(loc='upper center', ncol=3, prop={'family': 'Times New Roman', 'size': 'xx-large'})
        plt.tick_params(labelsize="x-large")
        plt.xticks(**tnr_font)
        plt.yticks(**tnr_font)
        plt.xlim(0, 100)

        # save the figure
        if not output_abs_path:
            output_abs_path = os.getcwd() + "\\own_results"
        if not os.path.exists(output_abs_path):
            os.makedirs(output_abs_path)
        plt.savefig(output_abs_path + "\\" + output_filename, dpi=1200)
    plt.clf()

def plot_distance_percentiles(results_list, users_and_facs_df, output_filename='distance_percentiles.pdf',
                              output_abs_path=None, percentiles=None, facility_region='all'):
    """
    plot the distance to the assigned facilities for three different percentiles for different budgets
    :param results_list: list of dictionaries of the results
    :param users_and_facs_df: dataframe of the user and facility related input data
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    :param percentiles: list of the three considered percentiles. Values must be between 0 and 100
    :param facility_region: string indicating the considered region of location for the facilities:
        "urban", "rural" or "all"
    """
    # init
    if percentiles is None or len(percentiles) != 3:
        percentiles = [10, 50, 90]
    user_regions = ['all', 'rural', 'urban']

    # make sure the results are sorted in increasing order by budget
    results_list = sorted(results_list, key=lambda d: d['model_details']['budget_factor'])
    nr_of_results = len(results_list)

    # get relevant data
    distance_dict = {user_region: [
        [d for d in get_distances_to_assigned(results, users_and_facs_df, user_region=user_region,
                                              facility_region=facility_region).values()]
        for results in results_list] for user_region in user_regions}
    budget_factor_list = [round(results['model_details']['budget_factor'] * 100) for results in results_list]

    # compute the percentiles of the utilization of open facilities for each instance and each region
    percentiles_dict = {region: {p: [safe_percentile(distance_dict[region][i], p) for i in range(nr_of_results)]
                                 for p in percentiles}
                        for region in user_regions}

    # plot the figure
    tnr_font = {'fontname': 'Times New Roman'}
    plt.rcParams["figure.figsize"] = (10, 2 / 3 * 10)
    plt.plot(budget_factor_list, percentiles_dict['all'][percentiles[0]], ls="dashed", color='blue')
    plt.plot(budget_factor_list, percentiles_dict['rural'][percentiles[0]], ls="dashed", color='green')
    plt.plot(budget_factor_list, percentiles_dict['urban'][percentiles[0]], ls="dashed", color='red')
    line_all, = plt.plot(budget_factor_list, percentiles_dict['all'][percentiles[1]], label='all', color='blue')
    line_rural, = plt.plot(budget_factor_list, percentiles_dict['rural'][percentiles[1]], label='rural', color='green')
    line_urban, = plt.plot(budget_factor_list, percentiles_dict['urban'][percentiles[1]], label='urban', color='red')
    plt.plot(budget_factor_list, percentiles_dict['all'][percentiles[2]], ls="dotted", color='blue', linewidth=2)
    plt.plot(budget_factor_list, percentiles_dict['rural'][percentiles[2]], ls="dotted", color='green', linewidth=2)
    plt.plot(budget_factor_list, percentiles_dict['urban'][percentiles[2]], ls="dotted", color='red', linewidth=2)
    legend = plt.legend(handles=[line_all, line_rural, line_urban], fontsize="xx-large",
                        prop={'family': 'Times New Roman', 'size': 'xx-large'}, loc='upper right',
                        bbox_to_anchor=(0.7, 1))
    # dummy lines for legend
    line_10, = plt.plot([], [], label=str(percentiles[0])+'th percentile', ls="dashed", color='black')
    line_50, = plt.plot([], [], label=str(percentiles[1])+'th percentile', color='black')
    line_90, = plt.plot([], [], label=str(percentiles[2])+'th percentile', ls="dotted", color='black')
    plt.gca().add_artist(legend)
    plt.legend(handles=[line_10, line_50, line_90], fontsize="xx-large",
               prop={'family': 'Times New Roman', 'size': 'xx-large'}, loc='upper right')
    plt.xlabel('Budget [%]', fontsize="xx-large", **tnr_font)
    plt.ylabel('Distance to assigned facility [miles]', fontsize="xx-large", **tnr_font)
    plt.ylim()
    plt.tick_params(labelsize="x-large")
    plt.xticks(**tnr_font)
    plt.yticks(**tnr_font)
    plt.xlim([None, budget_factor_list[-1]])

    # save the figure
    if not output_abs_path:
        output_abs_path = os.getcwd() + "\\own_results"
    if not os.path.exists(output_abs_path):
        os.makedirs(output_abs_path)
    plt.savefig(output_abs_path + "\\" + output_filename, dpi=1200)
    plt.clf()

def plot_strict_vs_loose(strict_results_list, loose_results_list, output_filename='strict_vs_loose.pdf',
                         output_abs_path=None):
    """
    make a plot comparing the computational performance for the two different implementations of the
    assign-to-one constraint
    :param strict_results_list: list of dictionaries of the results obtained when modeling the assign-to-one constraint
        as an equality
    :param loose_results_list: list of dictionaries of the results obtained when modeling the assign-to-one constraint
        as an inequality
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    """
    # make sure the results are sorted in increasing order by budget
    strict_results_list = sorted(strict_results_list, key=lambda d: d['model_details']['budget_factor'])
    loose_results_list = sorted(loose_results_list, key=lambda d: d['model_details']['budget_factor'])

    # get relevant data
    strict_obj_list = [results['solution_details']['objective_value'] for results in strict_results_list]
    strict_solving_time_list = [results['solution_details']['solving_time'] for results in strict_results_list]
    strict_budget_factor_list = [round(results['model_details']['budget_factor'] * 100)
                                 for results in strict_results_list]
    loose_obj_list = [results['solution_details']['objective_value'] for results in loose_results_list]
    loose_solving_time_list = [results['solution_details']['solving_time'] for results in loose_results_list]
    loose_budget_factor_list = [round(results['model_details']['budget_factor'] * 100)
                                for results in loose_results_list]

    # plot the figure
    tnr_font = {'fontname': 'Times New Roman'}
    plt.rcParams["figure.figsize"] = (10, 2 / 3 * 10)
    fig, ax1 = plt.subplots()
    ax1.set_xlabel('Budget [%]', fontsize="xx-large", **tnr_font)
    ax1.set_ylabel('Solving times [s]', fontsize="xx-large", color="blue", **tnr_font)
    ax1.tick_params(axis='y', labelcolor="blue", labelsize="x-large")
    ax1.tick_params(axis='x', labelsize="x-large")
    for tick in ax1.get_xticklabels():
        tick.set_fontname("Times New Roman")
    for tick in ax1.get_yticklabels():
        tick.set_fontname("Times New Roman")
    plt.plot(loose_budget_factor_list, loose_solving_time_list, label='Loose', color="blue")
    plt.plot(strict_budget_factor_list, strict_solving_time_list, label='Strict', color="blue", ls="dashed")
    ax1.set_ylim([0, None])
    ax2 = ax1.twinx()
    ax2.set_ylabel('Objective value', fontsize="xx-large", color="red", **tnr_font)
    ax2.tick_params(axis='y', labelcolor="red", labelsize="x-large")
    ax2.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))
    for tick in ax2.get_yticklabels():
        tick.set_fontname("Times New Roman")
    plt.plot(loose_budget_factor_list, loose_obj_list, color="red")
    plt.plot(strict_budget_factor_list, strict_obj_list, color="red", ls="dashed")
    # dummy lines to put on legend
    line_strict, = plt.plot([], [], label='Strict', ls="dashed", color='black')
    line_loose, = plt.plot([], [], label='Loose', color='black')
    plt.legend(fontsize="xx-large", handles=[line_strict, line_loose],
               prop={'family': 'Times New Roman', 'size': 'xx-large'})
    plt.xlim([None, max(loose_budget_factor_list[-1], strict_budget_factor_list[-1])])
    fig.tight_layout()  # otherwise the right y-label is slightly clipped

    # save the figure
    if not output_abs_path:
        output_abs_path = os.getcwd() + "\\own_results"
    if not os.path.exists(output_abs_path):
        os.makedirs(output_abs_path)
    plt.savefig(output_abs_path + "\\" + output_filename, dpi=1200)
    plt.clf()

def plot_cutoff_vs_nocutoff(cutoff_results_list, nocutoff_results_list, output_filename='cutoff_vs_nocutoff.pdf',
                            output_abs_path=None):
    """
    make a plot comparing the computational performance of the reduced model with the true model
    :param cutoff_results_list: list of dictionaries of the results obtained solving a reduced model
    :param nocutoff_results_list: list of dictionaries of the results obtained solving the true model
    :param output_filename: string containing the name of the output file
    :param output_abs_path: string containing the absolute path of the desired output directory;
        if None, the output file will be created in a folder called "own_results"
    """
    # make sure the results are sorted in increasing order by budget
    cutoff_results_list = sorted(cutoff_results_list, key=lambda d: d['model_details']['budget_factor'])
    nocutoff_results_list = sorted(nocutoff_results_list, key=lambda d: d['model_details']['budget_factor'])

    # get relevant data
    if not len(set(results['model_details']['cutoff'] for results in cutoff_results_list)) == 1:
        print('Not all instances use the same cutoff')
        return None
    else:
        cutoff = cutoff_results_list[0]['model_details']['cutoff'] * 100
    cutoff_obj_list = [results['solution_details']['objective_value'] for results in cutoff_results_list]
    cutoff_solving_time_list = [results['solution_details']['solving_time'] for results in cutoff_results_list]
    cutoff_budget_factor_list = [round(results['model_details']['budget_factor'] * 100)
                                 for results in cutoff_results_list]
    nocutoff_obj_list = [results['solution_details']['objective_value'] for results in nocutoff_results_list]
    nocutoff_solving_time_list = [results['solution_details']['solving_time'] for results in nocutoff_results_list]
    nocutoff_budget_factor_list = [round(results['model_details']['budget_factor'] * 100)
                                   for results in nocutoff_results_list]

    # plot the figure
    tnr_font = {'fontname': 'Times New Roman'}
    plt.rcParams["figure.figsize"] = (10, 2 / 3 * 10)
    fig, ax1 = plt.subplots()
    ax1.set_xlabel('Budget [%]', fontsize="xx-large", **tnr_font)
    ax1.set_ylabel('Solving times [s]', fontsize="xx-large", color="blue", **tnr_font)
    ax1.tick_params(axis='y', labelcolor="blue", labelsize="x-large")
    ax1.tick_params(axis='x', labelsize="x-large")
    for tick in ax1.get_xticklabels():
        tick.set_fontname("Times New Roman")
    for tick in ax1.get_yticklabels():
        tick.set_fontname("Times New Roman")
    plt.plot(cutoff_budget_factor_list, cutoff_solving_time_list, label=str(round(cutoff)) + '% cutoff', color="blue")
    plt.plot(nocutoff_budget_factor_list, nocutoff_solving_time_list, label='0% cutoff', color="blue", ls="dashed")
    ax1.set_ylim([0, None])
    ax2 = ax1.twinx()
    ax2.set_ylabel('Objective value', fontsize="xx-large", color="red", **tnr_font)
    ax2.tick_params(axis='y', labelcolor="red", labelsize="x-large")
    ax2.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))
    for tick in ax2.get_yticklabels():
        tick.set_fontname("Times New Roman")
    plt.plot(cutoff_budget_factor_list, cutoff_obj_list, color="red")
    plt.plot(nocutoff_budget_factor_list, nocutoff_obj_list, color="red", ls="dashed")
    # dummy lines to put on legend
    line_cutoff, = plt.plot([], [], label=str(round(cutoff)) + '% cutoff', color='black')
    line_nocutoff, = plt.plot([], [], label='0% cutoff', ls="dashed", color='black')
    plt.legend(fontsize="xx-large", handles=[line_nocutoff, line_cutoff],
               prop={'family': 'Times New Roman', 'size': 'xx-large'}, loc='upper right', bbox_to_anchor=(1, 0.95))
    plt.xlim([None, max(cutoff_budget_factor_list[-1], nocutoff_budget_factor_list[-1])])
    fig.tight_layout()  # otherwise the right y-label is slightly clipped

    # save the figure
    if not output_abs_path:
        output_abs_path = os.getcwd() + "\\own_results"
    if not os.path.exists(output_abs_path):
        os.makedirs(output_abs_path)
    plt.savefig(output_abs_path + "\\" + output_filename, dpi=1200)
    plt.clf()

def cached_solve_models(users_and_facs_df, travel_dict, users, facs, 
                        budget_factor_list, cache_dir, region=None, instance_number=None,
                        strict_assign_to_one=False, cap_factor=1.0, cutoff=0.0, max_access=False,
                        main_threads=None, main_tolerance=5e-3, main_time_limit=20000,
                        main_print_sol=False, main_log_file=None, main_preqlinearize=-1,
                        post_threads=None, post_tolerance=0.0, post_print_sol=False,
                        post_log_file=None, post_preqlinearize=-1, cache_only=False, allow_missing=False):
    """
    Solve models with caching support. Loads from cache if available, otherwise solves and caches.
    
    :param users_and_facs_df: dataframe of user and facility data
    :param travel_dict: dictionary of travel probabilities
    :param users: list of users
    :param facs: list of facilities
    :param budget_factor_list: list of budget factors to solve for
    :param cache_dir: directory for caching results
    :param region: region name (required for caching)
    :param instance_number: instance number (required for caching)
    :param strict_assign_to_one: strict assignment constraint
    :param cap_factor: capacity factor
    :param cutoff: travel probability cutoff
    :param max_access: maximize access objective
    :param main_threads: number of threads for main optimization
    :param main_tolerance: tolerance for main optimization
    :param main_time_limit: time limit for main optimization
    :param main_print_sol: print solution in main optimization
    :param main_log_file: log file for main optimization
    :param main_preqlinearize: PreQLinearize parameter for main optimization
    :param post_threads: number of threads for post-processing
    :param post_tolerance: tolerance for post-processing
    :param post_print_sol: print solution in post-processing
    :param post_log_file: log file for post-processing
    :param post_preqlinearize: PreQLinearize parameter for post-processing
    :return: list of results dictionaries
    """
    
    results_list = []
    
    # Set default thread counts if not specified
    if main_threads is None:
        main_threads = get_default_threads()
    if post_threads is None:
        post_threads = get_default_threads()
    
    # Create cache directory if caching is enabled
    abs_cache_dir = None
    use_cache = region is not None and instance_number is not None and cache_dir is not None
    if use_cache:
        abs_cache_dir = ensure_cache_dir(cache_dir)
    elif cache_only:
        raise ValueError("cache_only=True requires region, instance_number, and cache_dir for loading cached results.")
    
    for budget_factor in budget_factor_list:
        # Try to load from cache
        if use_cache:
            cached_result = load_result(
                region, instance_number, budget_factor,
                abs_cache_dir,
                strict_assign_to_one=strict_assign_to_one,
                cap_factor=cap_factor,
                cutoff=cutoff,
                max_access=max_access
            )
            if cached_result is not None:
                results_list.append(cached_result)
                continue
        
        # If cache-only is requested, do not solve
        if cache_only:
            message = (
                "Cached result not found for "
                f"region={region}, instance={instance_number}, budget_factor={budget_factor}, "
                f"strict_assign_to_one={strict_assign_to_one}, cap_factor={cap_factor}, "
                f"cutoff={cutoff}, max_access={max_access}."
            )
            if allow_missing:
                print(f"   [CACHE] Missing cache (skipping): {message}")
                continue
            raise FileNotFoundError(message)

        # Solve the model if not cached
        is_feasible, results = solve_model_naively(
            users_and_facs_df, travel_dict, users, facs, budget_factor,
            strict_assign_to_one, cap_factor, cutoff, max_access,
            main_threads, main_tolerance, main_time_limit, main_print_sol,
            main_log_file, main_preqlinearize, post_threads, post_tolerance,
            post_print_sol, post_log_file, post_preqlinearize
        )
        
        if not is_feasible:
            print('   [WARNING] Infeasible model')
            continue
        
        # Cache the result
        if use_cache:
            save_result(
                results, region, instance_number, budget_factor,
                abs_cache_dir,
                strict_assign_to_one=strict_assign_to_one,
                cap_factor=cap_factor,
                cutoff=cutoff,
                max_access=max_access
            )
        
        results_list.append(results)
    
    return results_list


def save_overall_access_plot_cached(users_and_facs_df, travel_dict, users, facs,
                                    output_filename='overall_access.pdf',
                                    output_abs_path=None, budget_factor_list=None,
                                    cache_dir=None, region=None, instance_number=None,
                                    strict_assign_to_one=False, cap_factor=None,
                                    cutoff=None, max_access=False,
                                    main_threads=None, main_tolerance=5e-3, main_time_limit=20000,
                                    main_print_sol=False, main_log_file=None, main_preqlinearize=-1,
                                    post_threads=None, post_tolerance=0.0, post_print_sol=False,
                                    post_log_file=None, post_preqlinearize=-1, use_cache=True,
                                    cache_only=False, allow_missing=False):
    """
    Save overall access plot using cached results when available.
    """
    if budget_factor_list is None:
        budget_factor_list = [0.1 * b for b in range(3, 11)]
    
    if cap_factor is None:
        cap_factor = get_default_cap_factor(region, instance_number)
    if cutoff is None:
        cutoff = get_default_cutoff(region)
    if main_threads is None:
        main_threads = get_default_threads()
    if post_threads is None:
        post_threads = get_default_threads()
    
    if not use_cache:
        print(f"   [CACHE] Caching disabled, using regular solving")
        plot_overall_access(None, users_and_facs_df, travel_dict, output_filename, output_abs_path)
        return
    
    print(f"   [CACHE] Attempting to load/solve models (region={region}, instance={instance_number})")
    results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, budget_factor_list,
        cache_dir, region, instance_number,
        strict_assign_to_one, cap_factor, cutoff, max_access,
        main_threads, main_tolerance, main_time_limit, main_print_sol,
        main_log_file, main_preqlinearize, post_threads, post_tolerance,
        post_print_sol, post_log_file, post_preqlinearize,
        cache_only=cache_only, allow_missing=allow_missing
    )
    
    if len(results_list) == 0 and allow_missing:
        print(f"   [CACHE] No cached results available; skipping figure {output_filename}")
        return
    
    # Use the original plotting function with the results
    plot_overall_access(results_list, users_and_facs_df, travel_dict, output_filename, output_abs_path)


def save_distance_percentiles_plot_cached(users_and_facs_df, travel_dict, users, facs,
                                         output_filename='distance_percentiles.pdf',
                                         output_abs_path=None, percentiles=None,
                                         budget_factor_list=None,
                                         cache_dir=None, region=None, instance_number=None,
                                         strict_assign_to_one=False, cap_factor=None,
                                         cutoff=None, max_access=False,
                                         main_threads=None, main_tolerance=5e-3, main_time_limit=20000,
                                         main_print_sol=False, main_log_file=None, main_preqlinearize=-1,
                                         post_threads=None, post_tolerance=0.0, post_print_sol=False,
                                         post_log_file=None, post_preqlinearize=-1, use_cache=True,
                                         cache_only=False, allow_missing=False):
    """
    Save distance percentiles plot using cached results when available.
    """
    if budget_factor_list is None:
        budget_factor_list = [0.1 * b for b in range(3, 11)]
    if percentiles is None or len(percentiles) != 3:
        percentiles = [10, 50, 90]
    
    if cap_factor is None:
        cap_factor = get_default_cap_factor(region, instance_number)
    if cutoff is None:
        cutoff = get_default_cutoff(region)
    if main_threads is None:
        main_threads = get_default_threads()
    if post_threads is None:
        post_threads = get_default_threads()
    
    print(f"   [CACHE] Attempting to load/solve models (region={region}, instance={instance_number})")
    results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, budget_factor_list,
        cache_dir, region, instance_number,
        strict_assign_to_one, cap_factor, cutoff, max_access,
        main_threads, main_tolerance, main_time_limit, main_print_sol,
        main_log_file, main_preqlinearize, post_threads, post_tolerance,
        post_print_sol, post_log_file, post_preqlinearize,
        cache_only=cache_only, allow_missing=allow_missing
    )
    
    if len(results_list) == 0 and allow_missing:
        print(f"   [CACHE] No cached results available; skipping figure {output_filename}")
        return
    
    plot_distance_percentiles(results_list, users_and_facs_df, output_filename,
                             output_abs_path, percentiles)


def save_utilization_percentiles_plot_cached(users_and_facs_df, travel_dict, users, facs,
                                            output_filename='utilization_percentiles.pdf',
                                            output_abs_path=None, percentiles=None,
                                            budget_factor_list=None,
                                            cache_dir=None, region=None, instance_number=None,
                                            strict_assign_to_one=False, cap_factor=None,
                                            cutoff=None, max_access=False,
                                            main_threads=None, main_tolerance=5e-3, main_time_limit=20000,
                                            main_print_sol=False, main_log_file=None, main_preqlinearize=-1,
                                            post_threads=None, post_tolerance=0.0, post_print_sol=False,
                                            post_log_file=None, post_preqlinearize=-1, use_cache=True,
                                            cache_only=False, allow_missing=False):
    """
    Save utilization percentiles plot using cached results when available.
    """
    if budget_factor_list is None:
        budget_factor_list = [0.1 * b for b in range(3, 11)]
    if percentiles is None or len(percentiles) != 3:
        percentiles = [10, 50, 90]
    
    if cap_factor is None:
        cap_factor = get_default_cap_factor(region, instance_number)
    if cutoff is None:
        cutoff = get_default_cutoff(region)
    if main_threads is None:
        main_threads = get_default_threads()
    if post_threads is None:
        post_threads = get_default_threads()
    
    print(f"   [CACHE] Attempting to load/solve models (region={region}, instance={instance_number})")
    results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, budget_factor_list,
        cache_dir, region, instance_number,
        strict_assign_to_one, cap_factor, cutoff, max_access,
        main_threads, main_tolerance, main_time_limit, main_print_sol,
        main_log_file, main_preqlinearize, post_threads, post_tolerance,
        post_print_sol, post_log_file, post_preqlinearize,
        cache_only=cache_only, allow_missing=allow_missing
    )
    
    if len(results_list) == 0 and allow_missing:
        print(f"   [CACHE] No cached results available; skipping figure {output_filename}")
        return
    
    plot_utilization_percentiles(results_list, users_and_facs_df, travel_dict, output_filename,
                                output_abs_path, percentiles)


def save_utilization_distribution_plot_cached(users_and_facs_df, travel_dict, users, facs,
                                             output_filename='utilization_distribution.pdf',
                                             output_abs_path=None, budget_factor_list=None,
                                             facility_region='all',
                                             cache_dir=None, region=None, instance_number=None,
                                             strict_assign_to_one=False, cap_factor=None,
                                             cutoff=None, max_access=False,
                                             main_threads=None, main_tolerance=5e-3, main_time_limit=20000,
                                             main_print_sol=False, main_log_file=None, main_preqlinearize=-1,
                                             post_threads=None, post_tolerance=0.0, post_print_sol=False,
                                             post_log_file=None, post_preqlinearize=-1, use_cache=True,
                                             cache_only=False, allow_missing=False):
    """
    Save utilization distribution plot using cached results when available.
    """
    if budget_factor_list is None:
        budget_factor_list = [0.1 * b for b in range(3, 11)]
    
    if cap_factor is None:
        cap_factor = get_default_cap_factor(region, instance_number)
    if cutoff is None:
        cutoff = get_default_cutoff(region)
    if main_threads is None:
        main_threads = get_default_threads()
    if post_threads is None:
        post_threads = get_default_threads()
    
    print(f"   [CACHE] Attempting to load/solve models (region={region}, instance={instance_number})")
    results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, budget_factor_list,
        cache_dir, region, instance_number,
        strict_assign_to_one, cap_factor, cutoff, max_access,
        main_threads, main_tolerance, main_time_limit, main_print_sol,
        main_log_file, main_preqlinearize, post_threads, post_tolerance,
        post_print_sol, post_log_file, post_preqlinearize,
        cache_only=cache_only, allow_missing=allow_missing
    )
    
    if len(results_list) == 0 and allow_missing:
        print(f"   [CACHE] No cached results available; skipping figure {output_filename}")
        return
    
    plot_utilization_distribution(results_list, users_and_facs_df, travel_dict, output_filename,
                                 output_abs_path, facility_region)


def save_strict_vs_loose_plot_cached(users_and_facs_df, travel_dict, users, facs,
                                    output_filename='strict_vs_loose.pdf',
                                    output_abs_path=None, budget_factor_list=None,
                                    cache_dir=None, region=None, instance_number=None,
                                    strict_assign_to_one=False, cap_factor=None,
                                    cutoff=None, max_access=False,
                                    main_threads=None, main_tolerance=5e-3, main_time_limit=20000,
                                    main_print_sol=False, main_log_file=None, main_preqlinearize=-1,
                                    post_threads=None, post_tolerance=0.0, post_print_sol=False,
                                    post_log_file=None, post_preqlinearize=-1, use_cache=True,
                                    cache_only=False, allow_missing=False):
    """
    Save strict vs loose plot using cached results when available.
    """
    if budget_factor_list is None:
        budget_factor_list = [0.1 * b for b in range(3, 11)]
    
    if cap_factor is None:
        cap_factor = get_default_cap_factor(region, instance_number)
    if cutoff is None:
        cutoff = get_default_cutoff(region)
    if main_threads is None:
        main_threads = get_default_threads()
    if post_threads is None:
        post_threads = get_default_threads()
    
    print(f"   [CACHE] Attempting to load/solve models (region={region}, instance={instance_number})")
    
    # Solve with strict assignment constraint
    strict_results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, budget_factor_list,
        cache_dir, region, instance_number,
        strict_assign_to_one=True, cap_factor=cap_factor, cutoff=cutoff, max_access=max_access,
        main_threads=main_threads, main_tolerance=main_tolerance, main_time_limit=main_time_limit, main_print_sol=main_print_sol,
        main_log_file=main_log_file, main_preqlinearize=main_preqlinearize, post_threads=post_threads, post_tolerance=post_tolerance,
        post_print_sol=post_print_sol, post_log_file=post_log_file, post_preqlinearize=post_preqlinearize,
        cache_only=cache_only, allow_missing=allow_missing
    )
    
    # Solve with loose assignment constraint
    loose_results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, budget_factor_list,
        cache_dir, region, instance_number,
        strict_assign_to_one=False, cap_factor=cap_factor, cutoff=cutoff, max_access=max_access,
        main_threads=main_threads, main_tolerance=main_tolerance, main_time_limit=main_time_limit, main_print_sol=main_print_sol,
        main_log_file=main_log_file, main_preqlinearize=main_preqlinearize, post_threads=post_threads, post_tolerance=post_tolerance,
        post_print_sol=post_print_sol, post_log_file=post_log_file, post_preqlinearize=post_preqlinearize,
        cache_only=cache_only, allow_missing=allow_missing
    )
    
    if (len(strict_results_list) == 0 or len(loose_results_list) == 0) and allow_missing:
        print(f"   [CACHE] No cached results available; skipping figure {output_filename}")
        return
    
    plot_strict_vs_loose(strict_results_list, loose_results_list, output_filename, output_abs_path)


def save_cap_vs_access_plot_cached(users_and_facs_df, travel_dict, users, facs,
                                   output_filename='cap_vs_access.pdf',
                                   output_abs_path=None, budget_factor=None,
                                   cache_dir=None, region=None, instance_number=None,
                                   strict_assign_to_one=False, cap_factor=None,
                                   cutoff=None, max_access=False,
                                   main_threads=None, main_tolerance=5e-3, main_time_limit=20000,
                                   main_print_sol=False, main_log_file=None, main_preqlinearize=-1,
                                   post_threads=None, post_tolerance=0.0, post_print_sol=False,
                                   post_log_file=None, post_preqlinearize=-1, use_cache=True,
                                   cache_only=False, allow_missing=False):
    """
    Save capacity vs access plot using cached results when available.
    """
    if budget_factor is None:
        budget_factor = 0.3
    
    if cap_factor is None:
        cap_factor = get_default_cap_factor(region, instance_number)
    if cutoff is None:
        cutoff = get_default_cutoff(region)
    if main_threads is None:
        main_threads = get_default_threads()
    if post_threads is None:
        post_threads = get_default_threads()
    
    print(f"   [CACHE] Attempting to load/solve models (region={region}, instance={instance_number})")
    results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, [budget_factor],
        cache_dir, region, instance_number,
        strict_assign_to_one, cap_factor, cutoff, max_access,
        main_threads, main_tolerance, main_time_limit, main_print_sol,
        main_log_file, main_preqlinearize, post_threads, post_tolerance,
        post_print_sol, post_log_file, post_preqlinearize,
        cache_only=cache_only, allow_missing=allow_missing
    )
    
    if len(results_list) == 0 and allow_missing:
        print(f"   [CACHE] No cached results available; skipping figure {output_filename}")
        return
    
    if len(results_list) > 0:
        plot_cap_vs_access(results_list[0], users_and_facs_df, travel_dict, output_filename, output_abs_path)


# ============================================================================
# CACHED TABLE FUNCTIONS
# ============================================================================

def write_table_overall_results_cached(users_and_facs_df, travel_dict, users, facs,
                                      output_filename='overall_results.xlsx',
                                      output_abs_path=None, percentiles=None,
                                      budget_factor_list=None,
                                      cache_dir=None, region=None, instance_number=None,
                                      strict_assign_to_one=False, cap_factor=None,
                                      cutoff=None, max_access=False, use_cache=True, cache_only=False,
                                      allow_missing=False):
    """
    Write overall results table using cached model results.
    """
    if budget_factor_list is None:
        budget_factor_list = [0.1 * b for b in range(3, 11)]
    if percentiles is None or len(percentiles) != 3:
        percentiles = [10, 50, 90]
    
    if cap_factor is None:
        cap_factor = get_default_cap_factor(region, instance_number)
    if cutoff is None:
        cutoff = get_default_cutoff(region)
    
    print(f"   [CACHE] Attempting to load cached results for table (budget factors: {len(budget_factor_list)})...")
    results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, budget_factor_list,
        cache_dir, region, instance_number,
        strict_assign_to_one, cap_factor, cutoff, max_access,
        cache_only=cache_only, allow_missing=allow_missing
    )
    
    write_overall_results(results_list, users_and_facs_df, travel_dict, output_filename, output_abs_path, percentiles)


def write_table_fairness_results_cached(users_and_facs_df, travel_dict, users, facs,
                                        output_filename='fairness_results.xlsx',
                                        output_abs_path=None, budget_factor_list=None,
                                        cache_dir=None, region=None, instance_number=None,
                                        strict_assign_to_one=False, cap_factor=None,
                                        cutoff=None, max_access=False, use_cache=True, cache_only=False,
                                        allow_missing=False):
    """
    Write fairness results table using cached model results.
    """
    if budget_factor_list is None:
        budget_factor_list = [0.1 * b for b in range(3, 11)]
    
    if cap_factor is None:
        cap_factor = get_default_cap_factor(region, instance_number)
    if cutoff is None:
        cutoff = get_default_cutoff(region)
    
    print(f"   [CACHE] Attempting to load cached results for table (budget factors: {len(budget_factor_list)})...")
    results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, budget_factor_list,
        cache_dir, region, instance_number,
        strict_assign_to_one, cap_factor, cutoff, max_access,
        cache_only=cache_only, allow_missing=allow_missing
    )
    
    write_fairness_results(results_list, users_and_facs_df, travel_dict, output_filename, output_abs_path)


def write_table_pof_results_cached(users_and_facs_df, travel_dict, users, facs,
                                   output_filename='pof_results.xlsx',
                                   output_abs_path=None, budget_factor_list=None,
                                   cache_dir=None, region=None, instance_number=None, use_cache=True, cache_only=False,
                                   allow_missing=False):
    """
    Write POF (Price of Fairness) results table using cached model results.
    Solves both optimal and maximum access variants.
    """
    if budget_factor_list is None:
        budget_factor_list = [0.1 * b for b in range(3, 11)]
    
    print(f"   [CACHE] Attempting to load cached results for table (budget factors: {len(budget_factor_list)})...")
    
    # Load optimal results (max_access=False)
    optimal_results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, budget_factor_list,
        cache_dir, region, instance_number,
        strict_assign_to_one=False, cap_factor=1.5, cutoff=0.2, max_access=False,
        cache_only=cache_only, allow_missing=allow_missing
    )
    
    # Load maximum access results (max_access=True)
    maximum_results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, budget_factor_list,
        cache_dir, region, instance_number,
        strict_assign_to_one=False, cap_factor=1.5, cutoff=0.2, max_access=True,
        cache_only=cache_only, allow_missing=allow_missing
    )

    if allow_missing:
        optimal_by_budget = {r['model_details']['budget_factor']: r for r in optimal_results_list}
        maximum_by_budget = {r['model_details']['budget_factor']: r for r in maximum_results_list}
        common_budgets = sorted(set(optimal_by_budget.keys()) & set(maximum_by_budget.keys()))
        if len(common_budgets) < len(budget_factor_list):
            print(f"   [CACHE] Missing POF budgets (keeping {len(common_budgets)} of {len(budget_factor_list)})")
        optimal_results_list = [optimal_by_budget[b] for b in common_budgets]
        maximum_results_list = [maximum_by_budget[b] for b in common_budgets]
    
    # Pass both lists to write function
    write_pof_results(optimal_results_list, maximum_results_list, users_and_facs_df, travel_dict, output_filename, output_abs_path)


def write_table_strict_vs_loose_results_cached(users_and_facs_df, travel_dict, users, facs,
                                               output_filename='strict_vs_loose_results.xlsx',
                                               output_abs_path=None, budget_factor=None,
                                               cache_dir=None, region=None, instance_number=None,
                                               cutoff=0.2, use_cache=True, cache_only=False,
                                               allow_missing=False):
    """
    Write strict vs loose results table using cached model results.
    Solves both strict and loose variants with cutoff=0.0 for feasibility.
    
    Note: write_strict_vs_loose_results expects 2 items per list (before/after postprocessing).
    Since cache only stores final results, we duplicate them to match expected format.
    """
    if budget_factor is None:
        budget_factor = 0.3
    
    print(f"   [CACHE] Attempting to load cached results for table (budget: {budget_factor})...")
    
    # Load loose results (strict_assign_to_one=False)
    loose_results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, [budget_factor],
        cache_dir, region, instance_number,
        strict_assign_to_one=False, cap_factor=1.5, cutoff=0.0, max_access=False,
        cache_only=cache_only, allow_missing=allow_missing
    )
    
    # Load strict results (strict_assign_to_one=True)
    strict_results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, [budget_factor],
        cache_dir, region, instance_number,
        strict_assign_to_one=True, cap_factor=1.5, cutoff=0.0, max_access=False,
        cache_only=cache_only, allow_missing=allow_missing
    )

    if allow_missing and (len(strict_results_list) == 0 or len(loose_results_list) == 0):
        print("   [CACHE] Missing strict/loose cache; writing empty strict_vs_loose table.")
        df = pd.DataFrame(columns=['Strict - Before', 'Strict - After', 'Loose - Before', 'Loose - After',
                                   'Improvement [%]'],
                          index=['Assigned zip codes [%]', 'Overall access [%]', 'Objective value',
                                 'Solving time [s]'],
                          dtype=object)
        if not output_abs_path:
            output_abs_path = os.getcwd() + "\\own_results"
        if not os.path.exists(output_abs_path):
            os.makedirs(output_abs_path)
        with pd.ExcelWriter(output_abs_path + "\\" + output_filename) as writer:
            df.to_excel(writer, index=False)
        return
    
    # Validate that we got results from both
    if not strict_results_list or not loose_results_list:
        raise Exception(f"Failed to load results: strict={len(strict_results_list)}, loose={len(loose_results_list)}")
    
    # write_strict_vs_loose_results expects each list to have 2 items (before/after postprocessing)
    # Since cached results are already final, duplicate them to create the expected format
    from copy import deepcopy
    if len(strict_results_list) == 1:
        strict_results_list = [deepcopy(strict_results_list[0]), strict_results_list[0]]
    if len(loose_results_list) == 1:
        loose_results_list = [deepcopy(loose_results_list[0]), loose_results_list[0]]
    
    # Pass both lists to write function
    write_strict_vs_loose_results(strict_results_list, loose_results_list, users_and_facs_df, travel_dict, output_filename, output_abs_path)


def save_cutoff_vs_nocutoff_plot_cached(users_and_facs_df, travel_dict, users, facs,
                                        output_filename='cutoff_vs_nocutoff.pdf',
                                        output_abs_path=None, budget_factor_list=None,
                                        cache_dir=None, region=None, instance_number=None,
                                        strict_assign_to_one=False, cap_factor=None,
                                        compared_cutoff=0.2, max_access=False,
                                        main_threads=None, main_tolerance=5e-3, main_time_limit=20000,
                                        main_print_sol=False, main_log_file=None, main_preqlinearize=-1,
                                        post_threads=None, post_tolerance=0.0, post_print_sol=False,
                                        post_log_file=None, post_preqlinearize=-1, use_cache=True,
                                        cache_only=False, allow_missing=False):
    """
    Save cutoff vs nocutoff plot using cached results when available.
    """
    if budget_factor_list is None:
        budget_factor_list = [0.1 * b for b in range(3, 11)]
    
    if cap_factor is None:
        cap_factor = get_default_cap_factor(region, instance_number)
    if main_threads is None:
        main_threads = get_default_threads()
    if post_threads is None:
        post_threads = get_default_threads()
    
    print(f"   [CACHE] Attempting to load/solve models (region={region}, instance={instance_number})")
    
    # Solve with cutoff
    cutoff_results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, budget_factor_list,
        cache_dir, region, instance_number,
        strict_assign_to_one=strict_assign_to_one, cap_factor=cap_factor, cutoff=compared_cutoff, max_access=max_access,
        main_threads=main_threads, main_tolerance=main_tolerance, main_time_limit=main_time_limit, main_print_sol=main_print_sol,
        main_log_file=main_log_file, main_preqlinearize=main_preqlinearize, post_threads=post_threads, post_tolerance=post_tolerance,
        post_print_sol=post_print_sol, post_log_file=post_log_file, post_preqlinearize=post_preqlinearize,
        cache_only=cache_only, allow_missing=allow_missing
    )
    
    # Solve without cutoff
    nocutoff_results_list = cached_solve_models(
        users_and_facs_df, travel_dict, users, facs, budget_factor_list,
        cache_dir, region, instance_number,
        strict_assign_to_one=strict_assign_to_one, cap_factor=cap_factor, cutoff=0.0, max_access=max_access,
        main_threads=main_threads, main_tolerance=main_tolerance, main_time_limit=main_time_limit, main_print_sol=main_print_sol,
        main_log_file=main_log_file, main_preqlinearize=main_preqlinearize, post_threads=post_threads, post_tolerance=post_tolerance,
        post_print_sol=post_print_sol, post_log_file=post_log_file, post_preqlinearize=post_preqlinearize,
        cache_only=cache_only, allow_missing=allow_missing
    )
    
    if (len(cutoff_results_list) == 0 or len(nocutoff_results_list) == 0) and allow_missing:
        print(f"   [CACHE] No cached results available; skipping figure {output_filename}")
        return
    
    # plotting function only expects results lists plus optional output params
    plot_cutoff_vs_nocutoff(cutoff_results_list, nocutoff_results_list, output_filename, output_abs_path)

