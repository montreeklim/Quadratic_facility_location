"""
Script to create all figures for a chosen region/instance.
"""
from figures_and_tables import (
    create_figure3a, create_figure3b, create_figure4a,
    create_figure4b, create_figure5a, create_figure5b,
    create_figure6, create_figure7, create_figure8,
)
import argparse
import os
from pathlib import Path


def _slugify_region(region: str) -> str:
    return region.strip().replace(" ", "_")


def _resolve_paths(base_dir: str | None) -> tuple[str, str, str]:
    if base_dir:
        workspace_root = os.path.abspath(base_dir)
    else:
        workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_abs_path = os.path.join(workspace_root, "own_results")
    data_abs_path = os.path.join(workspace_root, "data")
    return workspace_root, output_abs_path, data_abs_path


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def run_all_figures(region: str, instance_number: int, base_dir: str | None = None) -> None:
    region_slug = _slugify_region(region)
    workspace_root, output_abs_path, data_abs_path = _resolve_paths(base_dir)
    _ensure_dir(output_abs_path)

    print("=" * 70)
    print(f"Creating all figures for region: {region}")
    print("=" * 70)
    print(f"Workspace root: {workspace_root}")
    print(f"Data directory: {data_abs_path}")
    print(f"Output directory: {output_abs_path}\n")

    print("\n1. Creating Figure 3a (Overall Access)...")
    create_figure3a(
        output_filename=f"{region_slug}_figure3a_overall_access.pdf",
        output_abs_path=output_abs_path,
        input_data_abs_path=data_abs_path,
        region=region,
        instance_number=instance_number,
        cache_only=True,
        allow_missing=True,
    )
    print(f"   Saved: {region_slug}_figure3a_overall_access.pdf")

    print("\n2. Creating Figure 3b (Distance Percentiles)...")
    create_figure3b(
        output_filename=f"{region_slug}_figure3b_distance_percentiles.pdf",
        output_abs_path=output_abs_path,
        input_data_abs_path=data_abs_path,
        region=region,
        instance_number=instance_number,
        cache_only=True,
        allow_missing=True,
    )
    print(f"   Saved: {region_slug}_figure3b_distance_percentiles.pdf")

    print("\n3. Creating Figure 4a (Utilization Percentiles)...")
    create_figure4a(
        output_filename=f"{region_slug}_figure4a_utilization_percentiles.pdf",
        output_abs_path=output_abs_path,
        input_data_abs_path=data_abs_path,
        region=region,
        instance_number=instance_number,
        cache_only=True,
        allow_missing=True,
    )
    print(f"   Saved: {region_slug}_figure4a_utilization_percentiles.pdf")

    print("\n4. Creating Figure 4b (Utilization Distribution)...")
    create_figure4b(
        output_filename=f"{region_slug}_figure4b_utilization_distribution.pdf",
        output_abs_path=output_abs_path,
        input_data_abs_path=data_abs_path,
        region=region,
        instance_number=instance_number,
        cache_only=True,
        allow_missing=True,
    )
    print(f"   Saved: {region_slug}_figure4b_utilization_distribution.pdf")

    print("\n5. Creating Figure 5a (Strict vs Loose)...")
    create_figure5a(
        output_filename=f"{region_slug}_figure5a_strict_vs_loose.pdf",
        output_abs_path=output_abs_path,
        input_data_abs_path=data_abs_path,
        region=region,
        instance_number=instance_number,
        cache_only=True,
        allow_missing=True,
    )
    print(f"   Saved: {region_slug}_figure5a_strict_vs_loose.pdf")

    print("\n6. Creating Figure 5b (Cutoff vs No Cutoff)...")
    create_figure5b(
        output_filename=f"{region_slug}_figure5b_cutoff_vs_nocutoff.pdf",
        output_abs_path=output_abs_path,
        input_data_abs_path=data_abs_path,
        region=region,
        instance_number=instance_number,
        cache_only=True,
        allow_missing=True,
    )
    print(f"   Saved: {region_slug}_figure5b_cutoff_vs_nocutoff.pdf")

    print("\n7. Creating Figure 6 (Capacity vs Access)...")
    create_figure6(
        output_filename=f"{region_slug}_figure6_cap_vs_access.pdf",
        output_abs_path=output_abs_path,
        input_data_abs_path=data_abs_path,
        region=region,
        instance_number=instance_number,
        cache_only=True,
        allow_missing=True,
    )
    print(f"   Saved: {region_slug}_figure6_cap_vs_access.pdf")

    print("\n8. Creating Figure 7 (Utilization Distribution - Rural)...")
    create_figure7(
        output_filename=f"{region_slug}_figure7_utilization_distribution_rural.pdf",
        output_abs_path=output_abs_path,
        input_data_abs_path=data_abs_path,
        region=region,
        instance_number=instance_number,
        cache_only=True,
        allow_missing=True,
    )
    print(f"   Saved: {region_slug}_figure7_utilization_distribution_rural.pdf")

    print("\n9. Creating Figure 8 (Utilization Distribution - Urban)...")
    create_figure8(
        output_filename=f"{region_slug}_figure8_utilization_distribution_urban.pdf",
        output_abs_path=output_abs_path,
        input_data_abs_path=data_abs_path,
        region=region,
        instance_number=instance_number,
        cache_only=True,
        allow_missing=True,
    )
    print(f"   Saved: {region_slug}_figure8_utilization_distribution_urban.pdf")

    print("\n" + "=" * 70)
    print("All figures created successfully!")
    print("=" * 70)
    print(f"\nAll figures have been saved to: {output_abs_path}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create all figures for a chosen region/instance.")
    parser.add_argument("--region", required=True, help="Region name (e.g., Hampshire, Bavaria)")
    parser.add_argument("--instance-number", type=int, default=1, help="Instance number to use")
    parser.add_argument(
        "--base-dir",
        default=None,
        help="Workspace root directory; defaults to auto-detected root",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    run_all_figures(region=args.region, instance_number=args.instance_number, base_dir=args.base_dir)


if __name__ == "__main__":
    main()
