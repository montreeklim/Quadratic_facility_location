"""
Script to create tables 1–7 for the Hampshire dataset.
Defaults to generating tables 1–4 now (fast-ish). Heavy tables 5–7 are optional.
"""
import os
import pandas as pd
from figures_and_tables import (
    create_table1, create_table2, create_table3,
    create_table4, create_table5, create_table6, create_table7
)

# Toggle heavy tables (long runtimes)
RUN_HEAVY = True  # Running only tables 5-7

if __name__ == '__main__':
    # Workspace root: go up from src/models
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_abs_path = os.path.join(workspace_root, 'own_results')
    if not os.path.exists(output_abs_path):
        os.makedirs(output_abs_path)

    print('='*70)
    # Table 1
    print('1) Table 1: overall_results.xlsx')
    create_table1(
        output_filename='Hampshire_table1_overall_results.xlsx',
        output_abs_path=output_abs_path,
        region='Hampshire',
        instance_number=1
    )
    print(' Saved: Hampshire_table1_overall_results.xlsx')

    # Table 2
    print('\n2) Table 2: strict_vs_loose_results.xlsx (using cutoff=0.0 for feasibility)')
    create_table2(
        output_filename='Hampshire_table2_strict_vs_loose_results.xlsx',
        output_abs_path=output_abs_path,
        region='Hampshire',
        instance_number=1,
        cutoff=0.0  # Use no cutoff to ensure strict model is feasible
    )
    print(' Saved: Hampshire_table2_strict_vs_loose_results.xlsx')

    # Table 3
    print('\n3) Table 3: fairness_results.xlsx')
    create_table3(
        output_filename='Hampshire_table3_fairness_results.xlsx',
        output_abs_path=output_abs_path,
        region='Hampshire',
        instance_number=1
    )
    print(' Saved: Hampshire_table3_fairness_results.xlsx')

    # Table 4
    print('\n4) Table 4: pof_results.xlsx')
    create_table4(
        output_filename='Hampshire_table4_pof_results.xlsx',
        output_abs_path=output_abs_path,
        region='Hampshire',
        instance_number=1
    )
    print(' Saved: Hampshire_table4_pof_results.xlsx')

    if RUN_HEAVY:
        print("\nNOTE: Tables 5-7 are heavy and may take hours. Running anyway because RUN_HEAVY=True.\n")

        # Table 5
        print('5) Table 5: greedy_results_nocutoff.xlsx (heavy)')
        create_table5(
            output_filename='Hampshire_table5_greedy_results_nocutoff.xlsx',
            output_abs_path=output_abs_path,
            region='Hampshire',
            instance_number=1
        )
        print(' Saved: Hampshire_table5_greedy_results_nocutoff.xlsx')

        # Table 6
        print('\n6) Table 6: cutoff_results.xlsx (very heavy)')
        create_table6(
            output_filename='Hampshire_table6_cutoff_results.xlsx',
            output_abs_path=output_abs_path,
            region='Hampshire',
            instance_number=1
        )
        print(' Saved: Hampshire_table6_cutoff_results.xlsx')

        # Table 7
        print('\n7) Table 7: greedy_results_cutoff.xlsx (very heavy)')
        create_table7(
            output_filename='Hampshire_table7_greedy_results_cutoff.xlsx',
            output_abs_path=output_abs_path,
            region='Hampshire',
            instance_number=1
        )
        print(' Saved: Hampshire_table7_greedy_results_cutoff.xlsx')

    print('\nAll done!')
