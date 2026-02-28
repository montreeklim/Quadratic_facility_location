"""Utility script to generate and save travel and distance dictionaries for a chosen dataset.

Set `dataset_name` to your dataset prefix (e.g., "Bavaria_1", "Hampshire", or any new dataset)
as long as the data folder contains `<dataset_name>_users_and_facs.csv`. The script loads that CSV,
derives the users and facilities lists, and writes both `<dataset_name>_travel_dict.json.pbz2`
and `<dataset_name>_distance_dict.json.pbz2` to the data folder.
"""

from utils import (
    create_travel_dict,
    create_distance_dict,
    load_users_and_facs,
    extract_users_and_facs,
    save_travel_dict,
)

dataset_name = 'Bavaria_1'  # Change this to your desired dataset prefix
region = 'Bavaria'          # Use 'Hampshire' to compute in miles; 'Bavaria' computes in km
users_and_facs = load_users_and_facs(dataset_name)

# Extract users and facilities from the dataframe
users, facs = extract_users_and_facs(users_and_facs)

print(f"Creating travel and distance dicts for {len(users)} users and {len(facs)} facilities...")

travel_dict = create_travel_dict(
    users_and_facs,
    users,
    facs,
    output_filename=dataset_name + '_travel_dict',
    region=region,
)

# Build and save the region-aware distance dictionary (km for Bavaria, miles for Hampshire)
distance_dict = create_distance_dict(users_and_facs, users, facs, region=region)
save_travel_dict(distance_dict, travel_dict_filename=dataset_name + '_distance_dict.json.pbz2')

print(f"\nTravel dict generation complete!")
print(f"Saved: data/{dataset_name}_travel_dict.json.pbz2")
print(f"Distance dict generation complete!")
print(f"Saved: data/{dataset_name}_distance_dict.json.pbz2")

