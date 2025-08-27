import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import h3
from collections import defaultdict

st.set_page_config(layout="wide")
st.title("🌍 Tree of Life + Species Richness Hex Map")

# ------------------ UTILS ------------------

def gbif_match(name):
    res = requests.get(f"https://api.gbif.org/v1/species/match?name={name}").json()
    return res.get("usageKey")

def gbif_children(parent_key):
    res = requests.get(f"https://api.gbif.org/v1/species/{parent_key}/children?limit=1000").json()
    return res.get("results", [])

def get_taxonomy_levels(start_key, depth=5):
    tree = []
    queue = [(start_key, 0)]
    while queue:
        key, level = queue.pop(0)
        if level >= depth:
            continue
        children = gbif_children(key)
        tree.append((level, key, children))
        for child in children:
            queue.append((child["key"], level + 1))
    return tree

# ------------------ SIDEBAR TAXONOMY BROWSER ------------------

st.sidebar.header("📚 Taxonomic Tree")
root_taxa = ["Animalia", "Plantae", "Fungi", "Bacteria", "Protozoa", "Chromista"]
selected_families = []

def browse_tree(name, level=0):
    key = gbif_match(name)
    if not key:
        return
    children = gbif_children(key)
    grouped = defaultdict(list)
    for c in children:
        grouped[c["rank"]].append(c)
    
    rank_order = ["PHYLUM", "CLASS", "ORDER", "FAMILY"]
    next_rank = rank_order[level] if level < len(rank_order) else None

    for taxon in sorted(grouped.get(next_rank, []), key=lambda x: x["scientificName"]):
        label = f'{"  " * level}- {taxon["scientificName"]}'
        if taxon["rank"] == "FAMILY":
            if st.sidebar.checkbox(label, key=taxon["key"]):
                selected_families.append((taxon["key"], taxon["scientificName"]))
        else:
            if st.sidebar.expander(label, expanded=False):
                browse_tree(taxon["scientificName"], level + 1)

for root in root_taxa:
    with st.sidebar.expander(root, expanded=False):
        browse_tree(root)

# ------------------ MAP + RICHNESS ------------------

def fetch_occurrences(family_key):
    url = f"https://api.gbif.org/v1/occurrence/search?taxonKey={family_key}&hasCoordinate=true&limit=300"
    all_results = []
    offset = 0
    max_records = 2000
    while offset < max_records:
        try:
            r = requests.get(url + f"&offset={offset}").json()
            results = r.get("results", [])
            if not results:
                break
            all_results.extend(results)
            offset += len(results)
        except:
            break
    return all_results

def compute_hex_richness(records, resolution=4):
    hex_map = defaultdict(set)
    for rec in records:
        try:
            lat = rec["decimalLatitude"]
            lon = rec["decimalLongitude"]
            species = rec.get("species", "Unknown species")
            h = h3.geo_to_h3(lat, lon, resolution)
            hex_map[h].add(species)
        except:
            continue
    data = []
    for h, species_set in hex_map.items():
        lat, lon = h3.h3_to_geo(h)
        data.append({
            "hex": h,
            "lat": lat,
            "lon": lon,
            "richness": len(species_set),
            "species_list": ", ".join(sorted(species_set))[:500]
        })
    return pd.DataFrame(data)

# ------------------ MAIN ------------------

if selected_families:
    st.subheader("🧬 Selected Families")
    st.markdown(", ".join([f[1] for f in selected_families]))

    all_records = []
    for key, name in selected_families:
        st.write(f"Fetching: {name}")
        occ = fetch_occurrences(key)
        for o in occ:
            o["familyName"] = name
        all_records.extend(occ)

    if not all_records:
        st.warning("No occurrence data found.")
    else:
        df = compute_hex_richness(all_records)

        fig = px.density_mapbox(
            df,
            lat="lat",
            lon="lon",
            z="richness",
            hover_data=["richness", "species_list"],
            radius=10,
            center=dict(lat=20, lon=0),
            zoom=1,
            mapbox_style="carto-positron",
            title="Species Richness Hex Map"
        )
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Select at least one family from the tree to render the map.")

