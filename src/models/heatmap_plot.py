import argparse
import pandas as pd
import numpy as np
import json
import bz2
import os
from geopy import distance as geopy_distance
from plotting import *
from utils import *
from typing import List, Tuple, Optional
import geopandas as gpd
import folium
import matplotlib.pyplot as plt
import matplotlib as mpl
import contextily as cx  # type: ignore
from adjustText import adjust_text

# === Parse arguments ===
parser = argparse.ArgumentParser(description="Generate heatmap plots for facility location results.")
parser.add_argument("--region", default="Hampshire", help="Region name (e.g., Hampshire, Bavaria)")
parser.add_argument("--instance", type=int, default=1, help="Instance number")
args = parser.parse_args()
REGION = args.region
INSTANCE = args.instance

# === Set up paths relative to script location ===
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))

# Use cached results rather than a single JSON
from result_cache import load_result, ensure_cache_dir
cache_dir = os.path.join(project_root, "own_results", "model_cache")
output_dir = os.path.join(project_root, "own_results", "heat_maps")
os.makedirs(output_dir, exist_ok=True)

# Toggle Folium HTML output (set False to only produce static figures)
GENERATE_FOLIUM_HTML = True

# === Region configuration ===
_bavaria_cap = {1: 1.5, 3: 0.8, 4: 0.8}
REGION_CONFIGS = {
    "Hampshire": dict(
        csv_path=os.path.join(project_root, "data", "Hampshire_users_and_facs.csv"),
        zipcode_col="Postcode Sectors",
        facility_name_col="Facility name",
        lat_col="centroid_lat",
        lon_col="centroid_lon",
        rc_lat_col="rc_centroid_lat",
        rc_lon_col="rc_centroid_lon",
        target_budgets=[1.0, 21/26, 14/26, 9/26],
        primary_params=dict(strict_assign_to_one=False, cap_factor=1.5, cutoff=0.2, max_access=False),
        fallback_params=dict(strict_assign_to_one=True, cap_factor=1.0, cutoff=0.0, max_access=False),
        geojson_path=os.path.join(project_root, "data", "map_data", "all_sectors.geojson"),
        boundary_path=os.path.join(project_root, "data", "map_data",
            "Counties_and_Unitary_Authorities_April_2019_Ultra_Generalised_Boundaries_EW_2022_1790725369940793023.geojson"),
        map_center=[51.0, -1.3],
        distance_vmax=15.0,
        distance_bins=[0, 5, 10, 15, 20, 25, 30, 35],
        distance_unit='miles',
        show_labels=True,
        state_boundary=None,
        local_boundary_path=os.path.join(project_root, "data", "map_data",
            "Counties_and_Unitary_Authorities_April_2019_Ultra_Generalised_Boundaries_EW_2022_1790725369940793023.geojson"),
        local_boundary_names={"Hampshire", "Southampton", "Portsmouth"},
        local_boundary_col="ctyua19nm",
    ),
}

# Bavaria config is instance-dependent, so we build it now
_bavaria_cap_factor = _bavaria_cap.get(INSTANCE, 1.0)
REGION_CONFIGS["Bavaria"] = dict(
    csv_path=os.path.join(project_root, "data", f"Bavaria_{INSTANCE}_users_and_facs.csv"),
    zipcode_col="zipcode",
    facility_name_col=None,  # no facility name column in Bavaria data
    lat_col="centroid_lat",
    lon_col="centroid_lon",
    rc_lat_col="rc_centroid_lat",
    rc_lon_col="rc_centroid_lon",
    target_budgets=[0.1 * b for b in range(3, 11)],
    primary_params=dict(strict_assign_to_one=False, cap_factor=_bavaria_cap_factor, cutoff=0.2, max_access=False),
    fallback_params=dict(strict_assign_to_one=True, cap_factor=1.0, cutoff=0.0, max_access=False),
    geojson_path=os.path.join(project_root, "data", "map_data", "plz-5stellig.geojson"),
    boundary_path=None,
    map_center=[48.8, 11.5],
    distance_vmax=25.0,
    distance_bins=[0, 10, 20, 30, 50, 75, 100],
    distance_unit='km',
    show_labels=False,
    state_boundary=None,
    local_boundary_path=os.path.join(project_root, "data", "map_data", "bayern.geojson"),
    local_boundary_names={"Bayern"},
    local_boundary_col="name",
    use_spatial_join=True,  # zone indices need spatial join to PLZ polygons
)

# Select config for this run
region_key = "Bavaria" if REGION.lower().startswith("bavar") else "Hampshire"
cfg = REGION_CONFIGS[region_key]

users_facs_path = cfg["csv_path"]
TARGET_BUDGETS = cfg["target_budgets"]
PRIMARY_PARAMS = cfg["primary_params"]
FALLBACK_PARAMS = cfg["fallback_params"]
geojson_path = cfg["geojson_path"]
boundary_path = cfg["boundary_path"]
summary_output_path = os.path.join(project_root, "own_results", f"{region_key.lower()}_{INSTANCE}_summary.csv")
output_map_file = os.path.join(output_dir, f"{region_key.lower()}_{INSTANCE}_map.html")

ZIPCODE_COL = cfg["zipcode_col"]
FACILITY_NAME_COL = cfg["facility_name_col"]
LAT_COL = cfg["lat_col"]
LON_COL = cfg["lon_col"]
RC_LAT_COL = cfg["rc_lat_col"]
RC_LON_COL = cfg["rc_lon_col"]
DISTANCE_UNIT = cfg.get("distance_unit", "miles")

# === 1. Load data ===
users_and_facs_df = pd.read_csv(users_facs_path)

ensure_cache_dir(cache_dir)

budget_to_result = {}
for b in TARGET_BUDGETS:
    res = load_result(REGION, INSTANCE, b, cache_dir, **PRIMARY_PARAMS)
    if res is None:
        res = load_result(REGION, INSTANCE, b, cache_dir, **FALLBACK_PARAMS)
    if res is None:
        print(f"[WARN] Missing cached result for budget {b:.6f}. Skipping.")
    else:
        budget_to_result[b] = res

results_list = list(budget_to_result.values())

if not results_list:
    raise RuntimeError("No cached results found for requested budgets. Run solve_and_cache_models.py first.")

result_100 = budget_to_result.get(1.0, results_list[0])
if result_100['model_details']['budget_factor'] != 1.0:
    print(f"[INFO] Exact 100% not in cache; using budget {result_100['model_details']['budget_factor']*100:.0f}% for preview computations.")

# Clean population and capacity columns
users_and_facs_df['population'] = pd.to_numeric(
    users_and_facs_df['population'].astype(str).str.replace(',', '').str.strip(), errors='coerce')
users_and_facs_df['capacity'] = pd.to_numeric(
    users_and_facs_df['capacity'].astype(str).str.replace(',', '').str.strip(), errors='coerce')
users_and_facs_df['capacity'] = users_and_facs_df['capacity'].fillna(0)

# === 2. Calculate distances ===
assignment = result_100['solution_details']['assignment']
open_facs = result_100['solution_details']['open_facs']

user_distances = []
for user_idx_str, facility_idx in assignment.items():
    user_idx = int(user_idx_str)
    user_lat = users_and_facs_df.at[user_idx, LAT_COL]
    user_lon = users_and_facs_df.at[user_idx, LON_COL]
    fac_lat = users_and_facs_df.at[facility_idx, RC_LAT_COL]
    fac_lon = users_and_facs_df.at[facility_idx, RC_LON_COL]
    dist_km = geopy_distance.distance((user_lat, user_lon), (fac_lat, fac_lon)).km
    dist_value = dist_km if DISTANCE_UNIT == 'km' else dist_km * 0.621371
    user_distances.append({
        'user': user_idx,
        'facility': facility_idx,
        'zipcode': users_and_facs_df.at[user_idx, ZIPCODE_COL],
        'distance': dist_value,
    })

result_df = pd.DataFrame(user_distances)
plot_df = result_df.groupby('zipcode').agg({'distance': 'mean'}).reset_index()
plot_df.rename(columns={'distance': 'value'}, inplace=True)

# === 3. Define bins ===
max_value = plot_df["value"].max()
if pd.isna(max_value) or max_value <= 0:
    max_value = 1
base_bins = cfg["distance_bins"]
bins = sorted(set(base_bins + [max(base_bins[-1], max_value)]))

# === 4. Calculate facility utilization ===
utilization_dict = {}
for fac_idx in open_facs:
    num_assigned = sum(1 for _, assigned_fac in assignment.items() if assigned_fac == fac_idx)
    capacity = users_and_facs_df.at[fac_idx, 'capacity']
    cap_factor = result_100['model_details']['cap_factor']
    effective_capacity = capacity * cap_factor
    if effective_capacity > 0:
        pop_assigned = sum(users_and_facs_df.at[int(u), 'population']
                          for u, f in assignment.items() if f == fac_idx)
        utilization = (pop_assigned / effective_capacity) * 100
    else:
        utilization = 0
    utilization_dict[fac_idx] = utilization

# === 5. Prepare facility points ===
open_facility_locations = []
for fac_idx in open_facs:
    lat = users_and_facs_df.at[fac_idx, RC_LAT_COL]
    lon = users_and_facs_df.at[fac_idx, RC_LON_COL]
    utilization = utilization_dict[fac_idx]
    if FACILITY_NAME_COL and FACILITY_NAME_COL in users_and_facs_df.columns:
        facility_name = users_and_facs_df.at[fac_idx, FACILITY_NAME_COL]
    else:
        facility_name = f"Facility {fac_idx}"
    if pd.notna(lat) and pd.notna(lon):
        open_facility_locations.append((lat, lon, utilization, facility_name))


# === 6. Folium HTML map (optional) ===
def plotMap(
    df: pd.DataFrame,
    value_column: str,
    geojson_path: str = "./data/all_sectors.geojson",
    boundary_path: str = None,
    output_file_name: str = "./own_results/heat_maps/map.html",
    bins: List[float] = [0, 0.2, 0.4, 0.6, 0.8, 1],
    open_facility_locations: List[Tuple[float, float]] = [],
    rural_zipcodes: List[str] = None,
    urban_zipcodes: List[str] = None,
    geojson_key: str = "properties.sector",
    map_center: List[float] = [51.0, -1.3],
):
    _tf_key = "bdd3d8f0c5c34c858dc7b57d1fc6c573"
    map_obj = folium.Map(
        location=map_center,
        tiles=f"https://{{s}}.tile.thunderforest.com/mobile-atlas/{{z}}/{{x}}/{{y}}.png?apikey={_tf_key}",
        attr="Thunderforest",
        zoom_start=8,
    )

    if boundary_path and os.path.exists(boundary_path):
        gdf = gpd.read_file(boundary_path, engine='fiona')
        if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
            gdf = gdf.to_crs(epsg=4326)
        target_names = {"Hampshire", "Southampton", "Portsmouth"}
        gdf_filtered = gdf[gdf["ctyua19nm"].isin(target_names)]
        temp_boundary = "temp_boundary.geojson"
        gdf_filtered.to_file(temp_boundary, driver="GeoJSON", engine='fiona')
        border = folium.GeoJson(
            temp_boundary,
            style_function=lambda _: {"color": "#000000", "weight": 1, "fillOpacity": 0}
        )
        border.add_to(map_obj)
        map_obj.fit_bounds(border.get_bounds())

    if geojson_path and os.path.exists(geojson_path) and not df.empty:
        with open(geojson_path) as f:
            zip_codes_geojson = json.load(f)
        df_zip_codes = list(df['zipcode'])
        df_zip_code_geojsons = [
            geo for geo in zip_codes_geojson["features"]
            if geo["properties"].get("sector") in df_zip_codes
        ]
        zip_codes_geojson["features"] = df_zip_code_geojsons
        if rural_zipcodes is None and urban_zipcodes is None:
            folium.Choropleth(
                geo_data=zip_codes_geojson,
                data=df,
                columns=['zipcode', value_column],
                key_on=geojson_key,
                fill_color="BuPu",
                fill_opacity=0.3,
                line_opacity=0.1,
                legend_name="Distance (miles)",
                bins=bins
            ).add_to(map_obj)

    if open_facility_locations and len(open_facility_locations[0]) >= 3:
        for fac in open_facility_locations:
            lat, lon, burden = fac[0], fac[1], fac[2]
            name = fac[3] if len(fac) >= 4 else ""
            if burden <= 3:
                color = "green"
            elif burden <= 10:
                color = "orange"
            else:
                color = "red"
            folium.CircleMarker(
                location=(lat, lon),
                radius=13,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                popup=f"Burden: {burden:.2f}%"
            ).add_to(map_obj)
            if name:
                folium.map.Marker(
                    location=(lat, lon),
                    icon=folium.DivIcon(
                        html=f'<div style="font-size: 17px; color: black; white-space: nowrap; transform: translate(15px, -10px);">{name}</div>'
                    )
                ).add_to(map_obj)

        legend_html = """
        <div style="position:fixed;bottom:30px;right:30px;z-index:9999;background-color:white;
                    padding:10px;border:2px solid grey;font-size:14px;">
        <b>Facility Burden Change Rate</b><br>
        <div style="display:flex;align-items:center;">
            <div style="width:20px;height:20px;background:green;border:1px solid black;"></div>
            <span style="margin-left:5px;">0% – 3%</span></div>
        <div style="display:flex;align-items:center;">
            <div style="width:20px;height:20px;background:orange;border:1px solid black;"></div>
            <span style="margin-left:5px;">3% – 10%</span></div>
        <div style="display:flex;align-items:center;">
            <div style="width:20px;height:20px;background:red;border:1px solid black;"></div>
            <span style="margin-left:5px;">> 10%</span></div>
        </div>"""
        map_obj.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl().add_to(map_obj)
    os.makedirs(os.path.dirname(output_file_name), exist_ok=True)
    map_obj.save(output_file_name)
    try:
        if 'temp_boundary' in locals() and os.path.exists(temp_boundary):
            os.remove(temp_boundary)
    except OSError:
        pass


if GENERATE_FOLIUM_HTML:
    plotMap(
        df=plot_df,
        value_column="value",
        geojson_path=geojson_path,
        boundary_path=boundary_path,
        output_file_name=output_map_file,
        bins=bins,
        open_facility_locations=open_facility_locations,
        map_center=cfg["map_center"],
    )
    print(f"Map generated successfully: {output_map_file}")

print(f"Number of open facilities: {len(open_facs)}")
print(f"Average distance to assigned facility: {plot_df['value'].mean():.2f} {DISTANCE_UNIT}")

summary_stats = pd.DataFrame({
    'Metric': [
        'Total open facilities',
        f'Average distance ({DISTANCE_UNIT})', f'Min distance ({DISTANCE_UNIT})',
        f'Max distance ({DISTANCE_UNIT})', f'Median distance ({DISTANCE_UNIT})',
    ],
    'Value': [len(open_facs), plot_df['value'].mean(), plot_df['value'].min(),
              plot_df['value'].max(), plot_df['value'].median()]
})
summary_stats.to_csv(summary_output_path, index=False)
print(f"Summary statistics saved to: {summary_output_path}")


# ============================================================================
# Static Map (Matplotlib)
# ============================================================================

def _get_result_for_budget(results_list: list, target_budget: float) -> dict:
    if not results_list:
        raise ValueError("Empty results_list")
    return min(results_list, key=lambda r: abs(float(r['model_details']['budget_factor']) - target_budget))


def _compute_sector_distance_df(result: dict, users_and_facs_df: pd.DataFrame,
                                 zipcode_col: str, lat_col: str, lon_col: str,
                                 rc_lat_col: str, rc_lon_col: str,
                                 distance_unit: str = 'miles') -> pd.DataFrame:
    assignment = result['solution_details']['assignment']
    rows = []
    for user_idx_str, facility_idx in assignment.items():
        ui = int(user_idx_str)
        fac = int(facility_idx)
        user_lat = users_and_facs_df.at[ui, lat_col]
        user_lon = users_and_facs_df.at[ui, lon_col]
        fac_lat = users_and_facs_df.at[fac, rc_lat_col]
        fac_lon = users_and_facs_df.at[fac, rc_lon_col]
        dist_km = geopy_distance.distance((user_lat, user_lon), (fac_lat, fac_lon)).km
        dist_value = dist_km if distance_unit == 'km' else dist_km * 0.621371
        rows.append({
            'zipcode': users_and_facs_df.at[ui, zipcode_col],
            'distance': dist_value,
        })
    df = pd.DataFrame(rows)
    out = df.groupby('zipcode', as_index=False)['distance'].mean()
    out.rename(columns={'distance': 'value'}, inplace=True)
    return out


def _compute_facility_utilization_df(result: dict, users_and_facs_df: pd.DataFrame,
                                      rc_lat_col: str, rc_lon_col: str,
                                      facility_name_col: Optional[str]) -> pd.DataFrame:
    assignment = result['solution_details']['assignment']
    open_facs_local = result['solution_details']['open_facs']
    cap_factor = float(result['model_details'].get('cap_factor', 1.0))

    pop_by_fac = {}
    for user_idx_str, fac in assignment.items():
        ui = int(user_idx_str)
        fac = int(fac)
        pop_by_fac[fac] = pop_by_fac.get(fac, 0.0) + float(users_and_facs_df.at[ui, 'population'])

    rows = []
    for fac in open_facs_local:
        capacity = float(users_and_facs_df.at[fac, 'capacity']) * cap_factor
        util = 0.0 if capacity <= 0 else 100.0 * float(pop_by_fac.get(fac, 0.0)) / capacity
        if facility_name_col and facility_name_col in users_and_facs_df.columns:
            name = users_and_facs_df.at[fac, facility_name_col]
        else:
            name = f"Facility {fac}"
        rows.append({
            'facility_id': fac,
            'name': name,
            'lat': float(users_and_facs_df.at[fac, rc_lat_col]),
            'lon': float(users_and_facs_df.at[fac, rc_lon_col]),
            'utilization': util,
        })
    return pd.DataFrame(rows)


def _build_sector_gdf(plot_df: pd.DataFrame, geojson_path: Optional[str]) -> Optional[gpd.GeoDataFrame]:
    if not geojson_path or not os.path.exists(geojson_path):
        return None
    try:
        sectors = gpd.read_file(geojson_path, engine='pyogrio')
    except Exception:
        sectors = gpd.read_file(geojson_path, engine='fiona')
    if sectors.crs and sectors.crs.to_string() != 'EPSG:4326':
        sectors = sectors.to_crs(epsg=4326)
    src_crs = sectors.crs
    merged = sectors[['sector', 'geometry']].merge(
        plot_df.rename(columns={'zipcode': 'sector'}), on='sector', how='inner'
    )
    if merged.empty:
        return None
    # Pandas merge can drop the CRS; restore it explicitly
    merged = gpd.GeoDataFrame(merged, geometry='geometry', crs=src_crs)
    return merged


def _build_sector_gdf_spatial_join(
    sec_df: pd.DataFrame,
    users_and_facs_df: pd.DataFrame,
    zipcode_col: str,
    lat_col: str,
    lon_col: str,
    plz_geojson_path: str,
) -> Optional[gpd.GeoDataFrame]:
    """
    Build a polygon GeoDataFrame for Bavaria by assigning each PLZ polygon
    the distance of its nearest zone centroid.

    Reversed join direction (PLZ → nearest zone) ensures every PLZ polygon
    in the coverage area gets a value, eliminating grey no-data patches.

    sec_df: DataFrame with 'zipcode' (int zone index) and 'value' (distance)
    users_and_facs_df: full CSV with lat/lon for each zone row
    plz_geojson_path: path to plz-5stellig.geojson (property key 'plz')
    """
    if not plz_geojson_path or not os.path.exists(plz_geojson_path):
        return None
    try:
        try:
            plz_gdf = gpd.read_file(plz_geojson_path, engine='pyogrio')
        except Exception:
            plz_gdf = gpd.read_file(plz_geojson_path, engine='fiona')
        if plz_gdf.crs is None:
            plz_gdf = plz_gdf.set_crs(epsg=4326)
        elif plz_gdf.crs.to_string() != 'EPSG:4326':
            plz_gdf = plz_gdf.to_crs(epsg=4326)
        plz_gdf = plz_gdf[['plz', 'geometry']].copy()

        # Build zone centroid GeoDataFrame with distance values
        zone_indices = set(sec_df['zipcode'].unique())
        zip_locs = (
            users_and_facs_df[[zipcode_col, lat_col, lon_col]]
            .rename(columns={zipcode_col: 'zone_idx', lat_col: 'lat', lon_col: 'lon'})
            .drop_duplicates(subset=['zone_idx'])
        )
        zip_locs = zip_locs[zip_locs['zone_idx'].isin(zone_indices)].reset_index(drop=True)
        zip_locs = zip_locs.merge(
            sec_df.rename(columns={'zipcode': 'zone_idx'}), on='zone_idx', how='inner'
        )

        zones_gdf = gpd.GeoDataFrame(
            zip_locs,
            geometry=gpd.points_from_xy(zip_locs['lon'], zip_locs['lat']),
            crs='EPSG:4326',
        )

        # Clip PLZ polygons to the zone coverage area (convex hull + small buffer)
        zone_hull = zones_gdf.geometry.unary_union.convex_hull.buffer(0.1)
        plz_in_area = plz_gdf[plz_gdf.geometry.intersects(zone_hull)].copy()

        # For each PLZ polygon, find the nearest zone centroid and take its distance.
        # Use PLZ polygon centroids as representative points for the join.
        plz_centroids = plz_in_area.copy()
        plz_centroids['geometry'] = plz_in_area.geometry.centroid

        # Project to metric CRS for accurate nearest-neighbour distances
        plz_proj = plz_centroids[['plz', 'geometry']].to_crs(epsg=3857)
        zones_proj = zones_gdf[['zone_idx', 'value', 'geometry']].to_crs(epsg=3857)

        plz_to_zone = gpd.sjoin_nearest(plz_proj, zones_proj, how='left') \
            .drop_duplicates(subset=['plz'])[['plz', 'value']]

        result = plz_in_area.merge(plz_to_zone, on='plz', how='left')
        if result.empty:
            return None
        return gpd.GeoDataFrame(result, geometry='geometry', crs='EPSG:4326')
    except Exception as e:
        print(f"[WARN] _build_sector_gdf_spatial_join failed: {e}")
        return None


def _to_web_mercator(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    try:
        return gdf.to_crs(epsg=3857)
    except Exception:
        return gdf


def _get_state_boundary_gdf(state_name: str) -> Optional[gpd.GeoDataFrame]:
    """Load a named state boundary from Natural Earth admin-1 data via cartopy."""
    try:
        import cartopy.io.shapereader as shpreader
        path = shpreader.natural_earth(resolution='10m', category='cultural',
                                       name='admin_1_states_provinces')
        states = gpd.read_file(path, engine='fiona')
        match = states[states['name'] == state_name]
        if match.empty:
            return None
        gdf = match[['geometry']].copy()
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        elif gdf.crs.to_string() != 'EPSG:4326':
            gdf = gdf.to_crs(epsg=4326)
        return gdf
    except Exception:
        return None


try:
    def save_static_single_map(
        results_list: list,
        users_and_facs_df: pd.DataFrame,
        geojson_path: Optional[str],
        out_path: str,
        budget: float,
        distance_vmax: float = 15.0,
        zipcode_col: str = "Postcode Sectors",
        facility_name_col: Optional[str] = "Facility name",
        lat_col: str = "centroid_lat",
        lon_col: str = "centroid_lon",
        rc_lat_col: str = "rc_centroid_lat",
        rc_lon_col: str = "rc_centroid_lon",
        show_labels: bool = True,
        state_boundary: Optional[str] = None,
        local_boundary_path: Optional[str] = None,
        local_boundary_names: Optional[set] = None,
        local_boundary_col: Optional[str] = None,
        use_spatial_join: bool = False,
        distance_unit: str = 'miles',
    ):
        res = _get_result_for_budget(results_list, budget)
        sec = _compute_sector_distance_df(res, users_and_facs_df,
                                          zipcode_col, lat_col, lon_col, rc_lat_col, rc_lon_col,
                                          distance_unit=distance_unit)
        fac = _compute_facility_utilization_df(res, users_and_facs_df,
                                               rc_lat_col, rc_lon_col, facility_name_col)

        if use_spatial_join:
            gdf_poly = _build_sector_gdf_spatial_join(
                sec, users_and_facs_df, zipcode_col, lat_col, lon_col, geojson_path
            )
        else:
            gdf_poly = _build_sector_gdf(sec, geojson_path)
        gdf_pts = gpd.GeoDataFrame(
            fac,
            geometry=gpd.points_from_xy(fac['lon'], fac['lat']),
            crs='EPSG:4326'
        )
        gdf_pts = _to_web_mercator(gdf_pts)
        if gdf_poly is not None:
            gdf_poly = _to_web_mercator(gdf_poly)

        # Closed facilities
        all_facs = set(users_and_facs_df.loc[users_and_facs_df['capacity'] > 0].index)
        closed_ids = all_facs - set(fac['facility_id'])
        closed_gdf = None
        if closed_ids:
            rows = []
            for fac_id in closed_ids:
                if facility_name_col and facility_name_col in users_and_facs_df.columns:
                    name = users_and_facs_df.at[fac_id, facility_name_col]
                else:
                    name = f"Facility {fac_id}"
                rows.append({
                    'facility_id': fac_id,
                    'name': name,
                    'lat': float(users_and_facs_df.at[fac_id, rc_lat_col]),
                    'lon': float(users_and_facs_df.at[fac_id, rc_lon_col]),
                })
            closed_gdf = gpd.GeoDataFrame(
                pd.DataFrame(rows),
                geometry=gpd.points_from_xy([r['lon'] for r in rows], [r['lat'] for r in rows]),
                crs='EPSG:4326'
            )
            closed_gdf = _to_web_mercator(closed_gdf)

        # Load boundary: prefer local GeoJSON (Hampshire), fall back to Natural Earth (Bavaria)
        boundary_gdf = None
        if local_boundary_path and os.path.exists(local_boundary_path) and local_boundary_names and local_boundary_col:
            try:
                raw = gpd.read_file(local_boundary_path, engine='fiona')
                raw = raw[raw[local_boundary_col].isin(local_boundary_names)]
                if not raw.empty:
                    if raw.crs and raw.crs.to_string() != 'EPSG:4326':
                        raw = raw.to_crs(epsg=4326)
                    boundary_gdf = _to_web_mercator(raw[['geometry']].copy())
            except Exception:
                pass
        if boundary_gdf is None and state_boundary:
            raw = _get_state_boundary_gdf(state_boundary)
            if raw is not None:
                boundary_gdf = _to_web_mercator(raw)

        fig, ax = plt.subplots(1, 1, figsize=(12, 12), constrained_layout=True)
        ax.set_facecolor('#b0b0b0')
        dist_cmap = plt.get_cmap('YlGnBu')
        dist_norm = mpl.colors.Normalize(vmin=0.0, vmax=distance_vmax)
        util_cmap = plt.get_cmap('OrRd')
        util_norm = mpl.colors.Normalize(vmin=0.0, vmax=100.0)

        # Distance heatmap layer (choropleth from polygon GeoDataFrame)
        if gdf_poly is not None and not gdf_poly.empty:
            gdf_poly.plot(ax=ax, column='value', cmap=dist_cmap, norm=dist_norm,
                          linewidth=0.2, edgecolor='k', alpha=0.7)

        # Facility point layers
        if closed_gdf is not None and len(closed_gdf) > 0:
            closed_gdf.plot(ax=ax, color='#808080', markersize=180,
                            edgecolor='white', linewidth=2.0, alpha=0.7)
        gdf_pts.plot(ax=ax, column='utilization', cmap=util_cmap, norm=util_norm,
                     markersize=180, edgecolor='white', linewidth=2.0, alpha=0.95)


        texts = []
        if show_labels:
            for x, y, name in zip(gdf_pts.geometry.x, gdf_pts.geometry.y, gdf_pts['name']):
                txt = ax.text(x, y, str(name), fontsize=9, color='black',
                             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='none', alpha=0.8),
                             ha='center')
                texts.append(txt)
            if closed_gdf is not None and len(closed_gdf) > 0:
                for x, y, name in zip(closed_gdf.geometry.x, closed_gdf.geometry.y, closed_gdf['name']):
                    txt = ax.text(x, y, str(name), fontsize=9, color='#606060',
                                 bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='none', alpha=0.8),
                                 ha='center')
                    texts.append(txt)
        if texts:
            adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle='->', color='gray', lw=0.5, alpha=0.5))
        ax.set_axis_off()

        cbar_ax1 = fig.add_axes([0.12, 0.93, 0.35, 0.02])
        cbar_ax2 = fig.add_axes([0.53, 0.93, 0.35, 0.02])
        cb1 = mpl.colorbar.ColorbarBase(cbar_ax1, cmap=dist_cmap, norm=dist_norm, orientation='horizontal')
        cb1.set_label(f'User to Facility Distance ({distance_unit})')
        cbar_ax1.xaxis.set_label_position('top')
        cb2 = mpl.colorbar.ColorbarBase(cbar_ax2, cmap=util_cmap, norm=util_norm, orientation='horizontal')
        cb2.set_label('Facility Utilization (%)')
        cbar_ax2.xaxis.set_label_position('top')

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        fig.savefig(out_path, dpi=300)
        plt.close(fig)

    # Compute a consistent distance_vmax from actual data across all loaded results,
    # rounded up to the nearest 5 units. Falls back to the config value if data is empty.
    _sec_maxes = []
    for _r in results_list:
        _s = _compute_sector_distance_df(
            _r, users_and_facs_df, ZIPCODE_COL, LAT_COL, LON_COL, RC_LAT_COL, RC_LON_COL,
            distance_unit=DISTANCE_UNIT,
        )
        if not _s.empty:
            _sec_maxes.append(_s['value'].max())
    if _sec_maxes:
        _data_max = max(_sec_maxes)
        _nice_max = float(np.ceil(_data_max / 5) * 5)
        effective_vmax = min(cfg["distance_vmax"], _nice_max)
    else:
        effective_vmax = cfg["distance_vmax"]
    print(f"Distance color scale: 0 – {effective_vmax:.0f} {DISTANCE_UNIT}")

    available_budgets = [float(r['model_details'].get('budget_factor', -1)) for r in results_list]
    print(f"Available budgets in results file: {sorted(set(round(100*b) for b in available_budgets))}%")
    for b in TARGET_BUDGETS:
        matching = [r for r in results_list if abs(float(r['model_details']['budget_factor']) - b) < 1e-9]
        if not matching:
            print(f"[WARN] Skipping budget {b:.6f}: exact cached result not found.")
            continue
        pct = int(round(b * 100))
        out_single = os.path.join(output_dir, f'{region_key.lower()}_{INSTANCE}_map_static_b{pct}.pdf')
        save_static_single_map(
            results_list=matching,
            users_and_facs_df=users_and_facs_df,
            geojson_path=geojson_path,
            out_path=out_single,
            budget=b,
            distance_vmax=effective_vmax,
            zipcode_col=ZIPCODE_COL,
            facility_name_col=FACILITY_NAME_COL,
            lat_col=LAT_COL,
            lon_col=LON_COL,
            rc_lat_col=RC_LAT_COL,
            rc_lon_col=RC_LON_COL,
            show_labels=cfg["show_labels"],
            state_boundary=cfg.get("state_boundary"),
            local_boundary_path=cfg.get("local_boundary_path"),
            local_boundary_names=cfg.get("local_boundary_names"),
            local_boundary_col=cfg.get("local_boundary_col"),
            use_spatial_join=cfg.get("use_spatial_join", False),
            distance_unit=DISTANCE_UNIT,
        )
        print(f"Static map saved: {out_single}")

except Exception as e:
    print(f"Static map generation skipped due to error: {e}")
