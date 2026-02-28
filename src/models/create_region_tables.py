"""
Script to create tables 1–7 for a chosen region/instance.
Defaults to tables 1–4; heavy tables 5–7 are optional.
"""
import argparse
import os
from pathlib import Path

from figures_and_tables import (
    create_table1, create_table2, create_table3,
    create_table4, create_table5, create_table6, create_table7,
)


def _slugify_region(region: str) -> str:
    return region.strip().replace(" ", "_")


def _resolve_output_dir(base_dir: str | None) -> str:
    if base_dir:
        workspace_root = os.path.abspath(base_dir)
    else:
        workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(workspace_root, "own_results")


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def run_all_tables(region: str, instance_number: int, run_heavy: bool = False, base_dir: str | None = None) -> None:
    region_slug = _slugify_region(region)
    output_abs_path = _resolve_output_dir(base_dir)
    _ensure_dir(output_abs_path)

    print("=" * 70)
    print(f"Creating tables for region: {region}")
    print("=" * 70)
    print(f"Output directory: {output_abs_path}\n")

    print("1) Table 1: overall_results.xlsx (cache-only, allow missing)")
    create_table1(
        output_filename=f"{region_slug}_table1_overall_results.xlsx",
        output_abs_path=output_abs_path,
        region=region,
        instance_number=instance_number,
        cache_only=True,
        allow_missing=True,
    )
    print(f" Saved: {region_slug}_table1_overall_results.xlsx")

    print("\n2) Table 2: strict_vs_loose_results.xlsx (using cutoff=0.0 for feasibility, cache-only, allow missing)")
    create_table2(
        output_filename=f"{region_slug}_table2_strict_vs_loose_results.xlsx",
        output_abs_path=output_abs_path,
        region=region,
        instance_number=instance_number,
        cutoff=0.0,
        cache_only=True,
        allow_missing=True,
    )
    print(f" Saved: {region_slug}_table2_strict_vs_loose_results.xlsx")

    print("\n3) Table 3: fairness_results.xlsx (cache-only, allow missing)")
    create_table3(
        output_filename=f"{region_slug}_table3_fairness_results.xlsx",
        output_abs_path=output_abs_path,
        region=region,
        instance_number=instance_number,
        cache_only=True,
        allow_missing=True,
    )
    print(f" Saved: {region_slug}_table3_fairness_results.xlsx")

    print("\n4) Table 4: pof_results.xlsx (cache-only, allow missing)")
    create_table4(
        output_filename=f"{region_slug}_table4_pof_results.xlsx",
        output_abs_path=output_abs_path,
        region=region,
        instance_number=instance_number,
        cache_only=True,
        allow_missing=True,
    )
    print(f" Saved: {region_slug}_table4_pof_results.xlsx")

    if run_heavy:
        print("\nNOTE: Tables 5–7 are heavy and may take hours. Running anyway because --run-heavy was set.\n")

        print("5) Table 5: greedy_results_nocutoff.xlsx (heavy)")
        create_table5(
            output_filename=f"{region_slug}_table5_greedy_results_nocutoff.xlsx",
            output_abs_path=output_abs_path,
            region=region,
            instance_number=instance_number,
        )
        print(f" Saved: {region_slug}_table5_greedy_results_nocutoff.xlsx")

        print("\n6) Table 6: cutoff_results.xlsx (very heavy)")
        create_table6(
            output_filename=f"{region_slug}_table6_cutoff_results.xlsx",
            output_abs_path=output_abs_path,
            region=region,
            instance_number=instance_number,
        )
        print(f" Saved: {region_slug}_table6_cutoff_results.xlsx")

        print("\n7) Table 7: greedy_results_cutoff.xlsx (very heavy)")
        create_table7(
            output_filename=f"{region_slug}_table7_greedy_results_cutoff.xlsx",
            output_abs_path=output_abs_path,
            region=region,
            instance_number=instance_number,
        )
        print(f" Saved: {region_slug}_table7_greedy_results_cutoff.xlsx")

    print("\nAll done!")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create tables 1–7 for a chosen region/instance.")
    parser.add_argument("--region", required=True, help="Region name (e.g., Hampshire, Bavaria)")
    parser.add_argument("--instance-number", type=int, default=1, help="Instance number to use")
    parser.add_argument(
        "--run-heavy",
        action="store_true",
        help="Also generate tables 5–7 (heavy/very heavy runtime)",
    )
    parser.add_argument(
        "--base-dir",
        default=None,
        help="Workspace root directory; defaults to auto-detected root",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    run_all_tables(
        region=args.region,
        instance_number=args.instance_number,
        run_heavy=args.run_heavy,
        base_dir=args.base_dir,
    )


if __name__ == "__main__":
    main()
