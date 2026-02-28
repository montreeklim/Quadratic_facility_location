import pandas as pd
import numpy as np
import json
import bz2
import os
from geopy import distance as geopy_distance
from plotting import *
from utils import *
from typing import List, Tuple
import geopandas as gpd
import folium
import matplotlib.pyplot as plt
import matplotlib as mpl
import contextily as cx  # type: ignore
from adjustText import adjust_text

# === Set up paths relative to script location ===
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))

# Use cached results rather than a single JSON
from result_cache import load_result, ensure_cache_dir
cache_dir = os.path.join(project_root, "own_results", "model_cache")
users_facs_path = os.path.join(project_root, "data", "Hampshire_users_and_facs.csv")
output_dir = os.path.join(project_root, "own_results", "heat_maps")
summary_output_path = os.path.join(project_root, "own_results", "hampshire_summary.csv")

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Toggle Folium HTML output (set False to only produce static figures)
GENERATE_FOLIUM_HTML = False

# === 1. Load Hampshire data ===
# Load users/facilities and then load cached results for target budgets

# Load users and facilities data
users_and_facs_df = pd.read_csv(users_facs_path)

# Target budgets for Hampshire
TARGET_BUDGETS = [1.0, 21/26, 14/26, 9/26]

# Primary cache parameters (match figure/table defaults)
PRIMARY_PARAMS = dict(strict_assign_to_one=False, cap_factor=1.5, cutoff=0.2, max_access=False)
# Fallback params (match earlier JSON example)
FALLBACK_PARAMS = dict(strict_assign_to_one=True, cap_factor=1.0, cutoff=0.0, max_access=False)

ensure_cache_dir(cache_dir)

budget_to_result = {}
for b in TARGET_BUDGETS:
    res = load_result("Hampshire", 1, b, cache_dir, **PRIMARY_PARAMS)
    if res is None:
        res = load_result("Hampshire", 1, b, cache_dir, **FALLBACK_PARAMS)
    if res is None:
        print(f"[WARN] Missing cached result for budget {b:.6f}. Skipping.")
    else:
        budget_to_result[b] = res

results_list = list(budget_to_result.values())

if not results_list:
    raise RuntimeError("No cached results found for requested budgets. Run solve_and_cache_models.py first.")

# Prefer exact 100% if available, else pick the first loaded result
result_100 = budget_to_result.get(1.0, results_list[0])
if result_100['model_details']['budget_factor'] != 1.0:
    print(f"[INFO] Exact 100% not in cache; using budget {result_100['model_details']['budget_factor']*100:.0f}% for preview computations.")

# Clean population and capacity columns (remove commas and spaces, convert to numeric)
users_and_facs_df['population'] = pd.to_numeric(users_and_facs_df['population'].astype(str).str.replace(',', '').str.strip(), errors='coerce')
users_and_facs_df['capacity'] = pd.to_numeric(users_and_facs_df['capacity'].astype(str).str.replace(',', '').str.strip(), errors='coerce')
users_and_facs_df['capacity'] = users_and_facs_df['capacity'].fillna(0)

# === 2. Calculate distances for each user to their assigned facility ===
assignment = result_100['solution_details']['assignment']
open_facs = result_100['solution_details']['open_facs']

# Create list to store user data with distances
user_distances = []
for user_idx_str, facility_idx in assignment.items():
    user_idx = int(user_idx_str)
    
    # Get user's postcode sector
    user_postcode = users_and_facs_df.at[user_idx, 'Postcode Sectors']
    
    # Calculate distance using geopy
    user_lat = users_and_facs_df.at[user_idx, 'centroid_lat']
    user_lon = users_and_facs_df.at[user_idx, 'centroid_lon']
    fac_lat = users_and_facs_df.at[facility_idx, 'rc_centroid_lat']
    fac_lon = users_and_facs_df.at[facility_idx, 'rc_centroid_lon']
    
    # Distance in miles (geopy returns distance in km by default, so we convert)
    dist_km = geopy_distance.distance((user_lat, user_lon), (fac_lat, fac_lon)).km
    dist_miles = dist_km * 0.621371
    
    user_distances.append({
        'user': user_idx,
        'facility': facility_idx,
        'zipcode': user_postcode,
        'distance': dist_miles
    })

result_df = pd.DataFrame(user_distances)

# Prepare DataFrame for choropleth (average distance per postcode sector)
plot_df = result_df.groupby('zipcode').agg({'distance': 'mean'}).reset_index()
plot_df.rename(columns={'distance': 'value'}, inplace=True)

# === 3. Define bins for choropleth (distance in miles) ===
max_value = plot_df["value"].max()
# Ensure max_value is valid and create monotonically increasing bins
if pd.isna(max_value) or max_value <= 0:
    max_value = 1
bins = [0, 5, 10, 15, 20, 25, 30, 35, max(35, max_value)]
# Remove duplicates and ensure monotonic increase
bins = sorted(list(set(bins)))

# === 4. Calculate facility utilization ===
utilization_dict = {}
for fac_idx in open_facs:
    # Count number of users assigned to this facility
    num_assigned = sum(1 for user_idx_str, assigned_fac in assignment.items() if assigned_fac == fac_idx)
    # Get capacity
    capacity = users_and_facs_df.at[fac_idx, 'capacity']
    cap_factor = result_100['model_details']['cap_factor']
    effective_capacity = capacity * cap_factor
    
    if effective_capacity > 0:
        # Get population assigned
        pop_assigned = sum(users_and_facs_df.at[int(user_idx_str), 'population'] 
                          for user_idx_str, assigned_fac in assignment.items() 
                          if assigned_fac == fac_idx)
        utilization = (pop_assigned / effective_capacity) * 100
    else:
        utilization = 0
    
    utilization_dict[fac_idx] = utilization

# === 5. Prepare facility points for visualization ===
# For 100% budget, we'll just show the facilities with their utilization as "burden"
open_facility_locations = []
for fac_idx in open_facs:
    lat = users_and_facs_df.at[fac_idx, 'rc_centroid_lat']
    lon = users_and_facs_df.at[fac_idx, 'rc_centroid_lon']
    facility_name = users_and_facs_df.at[fac_idx, 'Facility name']
    utilization = utilization_dict[fac_idx]
    
    # Only add if we have valid coordinates and name
    if pd.notna(lat) and pd.notna(lon) and pd.notna(facility_name):
        open_facility_locations.append((lat, lon, utilization, facility_name))

# === 6. Plot map (Folium; optional) ===
# Note: This requires GeoJSON files for UK postcode sectors and administrative boundaries
# If the files don't exist, you'll need to download them:
# - all_sectors.geojson: UK postcode sector boundaries
# - Counties_and_Unitary_Authorities...geojson: UK administrative boundaries

geojson_path = os.path.join(project_root, "data", "map_data", "all_sectors.geojson")
boundary_path = os.path.join(project_root, "data", "map_data", "Counties_and_Unitary_Authorities_April_2019_Ultra_Generalised_Boundaries_EW_2022_1790725369940793023.geojson")
output_map_file = os.path.join(output_dir, "hampshire_map.html")

def plotMap(
    df: pd.DataFrame,
    value_column: str,
    geojson_path: str = "./data/all_sectors.geojson", 
    boundary_path: str = "./data/Counties_and_Unitary_Authorities_April_2019_Ultra_Generalised_Boundaries_EW_2022_1790725369940793023.geojson",
    # Optional boundary file for Hampshire/Southampton/Portsmouth
    output_file_name: str = "./own_results/heat_maps/map.html",
    bins: List[float] = [0, 0.2, 0.4, 0.6, 0.8, 1],
    open_facility_locations: List[Tuple[float, float]] = [],
    rural_zipcodes: List[str] = None,
    urban_zipcodes: List[str] = None,
    geojson_key: str = "properties.sector"  # Adapted key for UK sector geojson
):
    """
    Plot a choropleth map of UK Postcode Sectors with optional overlay of selected administrative boundaries.
    Differences from the original:
      1. Adapted to UK Postcode Sector geojson and EPSG:4326 projection.
      2. Added optional administrative boundary overlay for Hampshire/Southampton/Portsmouth.
      3. Added dynamic facility point rendering with color mapping based on a third attribute.
    """

    # Load sector-level UK geojson instead of German PLZ-5
    with open(geojson_path) as f:
        zip_codes_geojson = json.load(f)

    # UK-centred map initialization (Hampshire region) instead of Germany
    map_obj = folium.Map(location=[51.0, -1.3], zoom_start=8)

    # Optional administrative boundary overlay
    if boundary_path:
        gdf = gpd.read_file(boundary_path)
        # Ensure WGS84 coordinate system
        if gdf.crs and gdf.crs.to_string() != "EPSG:4326":
            gdf = gdf.to_crs(epsg=4326)

        # Filter for specific administrative regions
        target_names = {"Hampshire", "Southampton", "Portsmouth"}
        gdf_filtered = gdf[gdf["ctyua19nm"].isin(target_names)]

        # Temporary geojson for folium rendering
        temp_boundary = "temp_boundary.geojson"
        gdf_filtered.to_file(temp_boundary, driver="GeoJSON")

        border = folium.GeoJson(
            temp_boundary,
            style_function=lambda _: {"color": "#000000", "weight": 1, "fillOpacity": 0}
        )
        border.add_to(map_obj)
        map_obj.fit_bounds(border.get_bounds())


    if not df.empty:
        df_zip_codes = list(df['zipcode'])
        df_zip_code_geojsons = [
            geo for geo in zip_codes_geojson["features"]
            if geo["properties"]["sector"] in df_zip_codes
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

        if rural_zipcodes:
            rural_features = [
                geo for geo in df_zip_code_geojsons if geo["properties"]["sector"] in rural_zipcodes
            ]
            rural_geo = {"type": "FeatureCollection", "features": rural_features}
            df_rural = df[df['zipcode'].isin(rural_zipcodes)]
            folium.Choropleth(
                geo_data=rural_geo,
                data=df_rural,
                columns=['zipcode', value_column],
                key_on=geojson_key,
                fill_color="BuGn",
                fill_opacity=0.5,
                line_opacity=0.1,
                legend_name="Rural Utilization (%)",
                bins=bins
            ).add_to(map_obj)

        if urban_zipcodes:
            urban_features = [
                geo for geo in df_zip_code_geojsons if geo["properties"]["sector"] in urban_zipcodes
            ]
            urban_geo = {"type": "FeatureCollection", "features": urban_features}
            df_urban = df[df['zipcode'].isin(urban_zipcodes)]
            folium.Choropleth(
                geo_data=urban_geo,
                data=df_urban,
                columns=['zipcode', value_column],
                key_on=geojson_key,
                fill_color="OrRd",
                fill_opacity=0.5,
                line_opacity=0.1,
                legend_name="Urban Utilization (%)",
                bins=bins
            ).add_to(map_obj)

    # Facility point rendering — supports discrete 3-color burden categories
    # Facility point rendering — 3-color burden categories with visible labels
    if open_facility_locations and len(open_facility_locations[0]) >= 3:
        for fac in open_facility_locations:
            lat, lon, burden = fac[0], fac[1], fac[2]
            name = fac[3] if len(fac) >= 4 else ""  # Optional facility name
    
            # Assign color based on burden thresholds
            if burden <= 3:       # ≤ 3% → green
                color = "green"
            elif burden <= 10:    # > 3% and ≤ 10% → orange
                color = "orange"
            else:                 # > 10% → red
                color = "red"
    
            # Plot colored circle marker
            folium.CircleMarker(
                location=(lat, lon),
                radius=13,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                popup=f"Burden: {burden:.2f}%"
            ).add_to(map_obj)
    
            # Add always-visible text label next to the marker
            if name:
                folium.map.Marker(
                    location=(lat, lon),
                    icon=folium.DivIcon(
                        html=f'<div style="font-size: 17px; color: black; white-space: nowrap; transform: translate(15px, -10px);">{name}</div>'
                    )
                ).add_to(map_obj)
    
        # Legend for the three burden categories
        legend_html = """
        <div style="
            position: fixed; 
            bottom: 30px; right: 30px; 
            z-index:9999; 
            background-color:white;
            padding: 10px; 
            border:2px solid grey;
            font-size:14px;
        ">
        <b>Facility Burden Change Rate</b><br>
        <div style="display:flex;align-items:center;">
            <div style="width:20px;height:20px;background:green;border:1px solid black;"></div>
            <span style="margin-left:5px;">0% – 3%</span>
        </div>
        <div style="display:flex;align-items:center;">
            <div style="width:20px;height:20px;background:orange;border:1px solid black;"></div>
            <span style="margin-left:5px;">3% – 10%</span>
        </div>
        <div style="display:flex;align-items:center;">
            <div style="width:20px;height:20px;background:red;border:1px solid black;"></div>
            <span style="margin-left:5px;">> 10%</span>
        </div>
        </div>
        """
        map_obj.get_root().html.add_child(folium.Element(legend_html))     

    # Add layer control and save
    folium.LayerControl().add_to(map_obj)

    os.makedirs(os.path.dirname(output_file_name), exist_ok=True)
    map_obj.save(output_file_name)

    try:
        if 'temp_boundary' in locals() and os.path.exists(temp_boundary):
            os.remove(temp_boundary)
    except OSError:
        pass

if GENERATE_FOLIUM_HTML:
    # Plot map
    if os.path.exists(geojson_path):
        # Use plotMap with full GeoJSON support
        print(f"GeoJSON file found: {geojson_path}")
        plotMap(
            df=plot_df,
            value_column="value",
            geojson_path=geojson_path,
            boundary_path=boundary_path if os.path.exists(boundary_path) else None,
            output_file_name=output_map_file,
            bins=bins,
            open_facility_locations=open_facility_locations
        )
    else:
        # Generate a basic folium map with just facility locations
        print(f"Warning: GeoJSON file not found at {geojson_path}")
        print("Generating map with facility locations only...")
        
        # Create base map centered on Hampshire region
        map_obj = folium.Map(location=[51.0, -1.3], zoom_start=8)
        
        # Add facility location markers with utilization color coding
        if open_facility_locations and len(open_facility_locations[0]) >= 3:
            for fac in open_facility_locations:
                lat, lon, utilization, name = fac[0], fac[1], fac[2], fac[3] if len(fac) >= 4 else ""
                
                # Assign color based on utilization thresholds
                if utilization <= 30:
                    color = "green"
                elif utilization <= 60:
                    color = "orange"
                else:
                    color = "red"
                
                # Add facility marker
                folium.CircleMarker(
                    location=(lat, lon),
                    radius=13,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.9,
                    popup=f"{name}<br>Utilization: {utilization:.1f}%"
                ).add_to(map_obj)
                
                # Add facility name label
                if name:
                    folium.map.Marker(
                        location=(lat, lon),
                        icon=folium.DivIcon(
                            html=f'<div style="font-size: 14px; color: black; white-space: nowrap; transform: translate(15px, -10px);">{name}</div>'
                        )
                    ).add_to(map_obj)
        
        # Add legend
        legend_html = """
        <div style="
            position: fixed; 
            bottom: 30px; right: 30px; 
            z-index:9999; 
            background-color:white;
            padding: 10px; 
            border:2px solid grey;
            font-size:14px;
        ">
        <b>Facility Utilization</b><br>
        <div style="display:flex;align-items:center;">
            <div style="width:20px;height:20px;background:green;border:1px solid black;"></div>
            <span style="margin-left:5px;">0% – 30%</span>
        </div>
        <div style="display:flex;align-items:center;">
            <div style="width:20px;height:20px;background:orange;border:1px solid black;"></div>
            <span style="margin-left:5px;">30% – 60%</span>
        </div>
        <div style="display:flex;align-items:center;">
            <div style="width:20px;height:20px;background:red;border:1px solid black;"></div>
            <span style="margin-left:5px;">> 60%</span>
        </div>
        </div>
        """
        map_obj.get_root().html.add_child(folium.Element(legend_html))
        
        # Save map
        os.makedirs(os.path.dirname(output_map_file), exist_ok=True)
        map_obj.save(output_map_file)

    print(f"Map generated successfully: {output_map_file}")

print(f"Number of open facilities: {len(open_facs)}")
print(f"Average distance to assigned facility: {plot_df['value'].mean():.2f} miles")

# Save summary statistics to CSV for reference
summary_stats = pd.DataFrame({
    'Metric': ['Total open facilities', 'Average distance (miles)', 'Min distance (miles)', 
               'Max distance (miles)', 'Median distance (miles)'],
    'Value': [len(open_facs), plot_df['value'].mean(), plot_df['value'].min(), 
              plot_df['value'].max(), plot_df['value'].median()]
})
summary_stats.to_csv(summary_output_path, index=False)
print(f"Summary statistics saved to: {summary_output_path}")


# ============================================================================
# Static Two-Panel Map (Matplotlib): Baseline vs Option I
# ============================================================================

def _get_result_for_budget(results_list: list, target_budget: float) -> dict:
    """Return the result dict with budget_factor closest to target_budget."""
    if not results_list:
        raise ValueError("Empty results_list")
    best = min(results_list, key=lambda r: abs(float(r['model_details']['budget_factor']) - target_budget))
    return best


def _compute_sector_distance_df(result: dict, users_and_facs_df: pd.DataFrame) -> pd.DataFrame:
    """Compute mean user->assigned facility distance per postcode sector (miles)."""
    assignment = result['solution_details']['assignment']
    rows = []
    for user_idx_str, facility_idx in assignment.items():
        ui = int(user_idx_str)
        fac = int(facility_idx)
        user_lat = users_and_facs_df.at[ui, 'centroid_lat']
        user_lon = users_and_facs_df.at[ui, 'centroid_lon']
        fac_lat = users_and_facs_df.at[fac, 'rc_centroid_lat']
        fac_lon = users_and_facs_df.at[fac, 'rc_centroid_lon']
        dist_km = geopy_distance.distance((user_lat, user_lon), (fac_lat, fac_lon)).km
        rows.append({
            'zipcode': users_and_facs_df.at[ui, 'Postcode Sectors'],
            'distance_miles': dist_km * 0.621371,
        })
    df = pd.DataFrame(rows)
    out = df.groupby('zipcode', as_index=False)['distance_miles'].mean()
    out.rename(columns={'distance_miles': 'value'}, inplace=True)
    return out


def _compute_facility_utilization_df(result: dict, users_and_facs_df: pd.DataFrame) -> pd.DataFrame:
    """Compute facility utilization (%) for open facilities and return lat/lon/name/utilization."""
    assignment = result['solution_details']['assignment']
    open_facs_local = result['solution_details']['open_facs']
    cap_factor = float(result['model_details'].get('cap_factor', 1.0))

    # Sum assigned population per facility
    pop_by_fac = {}
    for user_idx_str, fac in assignment.items():
        ui = int(user_idx_str)
        fac = int(fac)
        pop_by_fac[fac] = pop_by_fac.get(fac, 0.0) + float(users_and_facs_df.at[ui, 'population'])

    rows = []
    for fac in open_facs_local:
        capacity = float(users_and_facs_df.at[fac, 'capacity']) * cap_factor
        util = 0.0 if capacity <= 0 else 100.0 * float(pop_by_fac.get(fac, 0.0)) / capacity
        rows.append({
            'facility_id': fac,
            'name': users_and_facs_df.at[fac, 'Facility name'],
            'lat': float(users_and_facs_df.at[fac, 'rc_centroid_lat']),
            'lon': float(users_and_facs_df.at[fac, 'rc_centroid_lon']),
            'utilization': util,
        })
    return pd.DataFrame(rows)


def _build_sector_gdf(plot_df: pd.DataFrame, geojson_path: str) -> gpd.GeoDataFrame:
    try:
        sectors = gpd.read_file(geojson_path, engine='pyogrio')
    except Exception:
        # Fallback to fiona if pyogrio fails
        sectors = gpd.read_file(geojson_path, engine='fiona')
    if sectors.crs and sectors.crs.to_string() != 'EPSG:4326':
        sectors = sectors.to_crs(epsg=4326)
    merged = sectors[['sector', 'geometry']].merge(
        plot_df.rename(columns={'zipcode': 'sector'}), on='sector', how='inner'
    )
    return merged


def _to_web_mercator(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    try:
        return gdf.to_crs(epsg=3857)
    except Exception:
        return gdf


# Generate static single-plot maps per budget factor
try:
    def save_static_single_map(
        results_list: list,
        users_and_facs_df: pd.DataFrame,
        geojson_path: str,
        out_path: str,
        budget: float,
        distance_vmax: float = 15.0,
    ):
        res = _get_result_for_budget(results_list, budget)
        sec = _compute_sector_distance_df(res, users_and_facs_df)
        fac = _compute_facility_utilization_df(res, users_and_facs_df)

        gdf_poly = _build_sector_gdf(sec, geojson_path)
        gdf_pts = gpd.GeoDataFrame(
            fac,
            geometry=gpd.points_from_xy(fac['lon'], fac['lat']),
            crs='EPSG:4326'
        )
        gdf_poly = _to_web_mercator(gdf_poly)
        gdf_pts = _to_web_mercator(gdf_pts)
        
        # Get closed facilities
        all_facs = set(users_and_facs_df.loc[users_and_facs_df['capacity'] > 0].index)
        closed_ids = all_facs - set(fac['facility_id'])
        closed_gdf = None
        if closed_ids:
            rows = []
            for fac_id in closed_ids:
                rows.append({
                    'facility_id': fac_id,
                    'name': users_and_facs_df.at[fac_id, 'Facility name'],
                    'lat': float(users_and_facs_df.at[fac_id, 'rc_centroid_lat']),
                    'lon': float(users_and_facs_df.at[fac_id, 'rc_centroid_lon']),
                })
            closed_gdf = gpd.GeoDataFrame(
                pd.DataFrame(rows),
                geometry=gpd.points_from_xy([r['lon'] for r in rows], [r['lat'] for r in rows]),
                crs='EPSG:4326'
            )
            closed_gdf = _to_web_mercator(closed_gdf)

        fig, ax = plt.subplots(1, 1, figsize=(8, 8), constrained_layout=True)
        dist_cmap = plt.get_cmap('YlGnBu')
        dist_norm = mpl.colors.Normalize(vmin=0.0, vmax=distance_vmax)
        util_cmap = plt.get_cmap('RdYlGn_r')
        util_norm = mpl.colors.Normalize(vmin=0.0, vmax=100.0)

        gdf_poly.plot(ax=ax, column='value', cmap=dist_cmap, norm=dist_norm, linewidth=0.2, edgecolor='k', alpha=0.7)
        try:
            cx.add_basemap(ax, source=cx.providers.Stamen.TerrainBackground, crs=gdf_poly.crs, attribution='')
        except Exception:
            pass
        # Closed facilities (grey)
        if closed_gdf is not None and len(closed_gdf) > 0:
            closed_gdf.plot(
                ax=ax,
                color='#808080',
                markersize=180,
                edgecolor='white',
                linewidth=2.0,
                alpha=0.7,
            )
        # Open facilities (colored by utilization)
        gdf_pts.plot(
            ax=ax,
            column='utilization',
            cmap=util_cmap,
            norm=util_norm,
            markersize=180,
            edgecolor='white',
            linewidth=2.0,
            alpha=0.95,
        )
        # Labels with smart positioning
        texts = []
        for x, y, name in zip(gdf_pts.geometry.x, gdf_pts.geometry.y, gdf_pts['name']):
            txt = ax.text(x, y, str(name), fontsize=9, color='black',
                         bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='none', alpha=0.8),
                         ha='center')
            texts.append(txt)
        # Add closed facility labels
        if closed_gdf is not None and len(closed_gdf) > 0:
            for x, y, name in zip(closed_gdf.geometry.x, closed_gdf.geometry.y, closed_gdf['name']):
                txt = ax.text(x, y, str(name), fontsize=9, color='#606060',
                             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='none', alpha=0.8),
                             ha='center')
                texts.append(txt)
        # Adjust text positions to avoid overlap
        if texts:
            adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle='->', color='gray', lw=0.5, alpha=0.5))
        ax.set_axis_off()

        # top colorbars side-by-side
        cbar_ax1 = fig.add_axes([0.12, 0.93, 0.35, 0.02])
        cbar_ax2 = fig.add_axes([0.53, 0.93, 0.35, 0.02])
        cb1 = mpl.colorbar.ColorbarBase(cbar_ax1, cmap=dist_cmap, norm=dist_norm, orientation='horizontal')
        cb1.set_label('User to Facility Distance (miles)')
        cbar_ax1.xaxis.set_label_position('top')
        cb2 = mpl.colorbar.ColorbarBase(cbar_ax2, cmap=util_cmap, norm=util_norm, orientation='horizontal')
        cb2.set_label('Facility Utilization (%)')
        cbar_ax2.xaxis.set_label_position('top')

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        fig.savefig(out_path, dpi=300)
        plt.close(fig)

    # Generate requested budgets as single plots
    target_budgets = [1.0, 21/26, 14/26, 9/26]
    available_budgets = [float(r['model_details'].get('budget_factor', -1)) for r in results_list]
    print(f"Available budgets in results file: {sorted(set(round(100*b) for b in available_budgets))}%")
    for b in target_budgets:
        # Only generate if exact budget is available in cache
        matching = [r for r in results_list if abs(float(r['model_details']['budget_factor']) - b) < 1e-9]
        if not matching:
            print(f"[WARN] Skipping budget {b:.6f}: exact cached result not found.")
            continue
        pct = int(round(b * 100))
        out_single = os.path.join(output_dir, f'hampshire_map_static_b{pct}.pdf')
        save_static_single_map(
            results_list=matching,  # pass only the exact match to avoid ambiguity
            users_and_facs_df=users_and_facs_df,
            geojson_path=geojson_path,
            out_path=out_single,
            budget=b,
            distance_vmax=15.0,
        )
        print(f"Static map saved: {out_single}")

except Exception as e:
    print(f"Static map generation skipped due to error: {e}")

