import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import h3
from collections import defaultdict
import streamlit as st
import requests

st.set_page_config(layout="wide")
st.title("🌳 Tree of Life — Taxonomic Browser")

RANK_ORDER = ["KINGDOM", "PHYLUM", "CLASS", "ORDER", "FAMILY"]
ROOT_TAXA = ["Animalia", "Plantae", "Fungi", "Bacteria", "Protozoa", "Chromista"]

# Global UI tweaks
st.markdown("""
    <style>
    .stCheckbox > div {
        padding-top: 0.1rem;
        padding-bottom: 0.1rem;
    }
    .stMarkdown p {
        margin-bottom: 0.1rem;
    }
    label, input, div {
        font-size: 13px !important;
    }
    </style>
""", unsafe_allow_html=True)


# -------------------------------
# Utilities
# -------------------------------
def get_next_rank(rank):
    try:
        idx = RANK_ORDER.index(rank)
        return RANK_ORDER[idx + 1] if idx + 1 < len(RANK_ORDER) else None
    except ValueError:
        return None

@st.cache_data(show_spinner=False)
def match_taxon(name):
    res = requests.get(f"https://api.gbif.org/v1/species/match?name={name}")
    data = res.json()
    if data.get("usageKey"):
        return fetch_taxon(data["usageKey"])
    return None

@st.cache_data(show_spinner=False)
def fetch_taxon(key):
    res = requests.get(f"https://api.gbif.org/v1/species/{key}")
    data = res.json()
    return {
        "key": data["key"],
        "scientificName": data["scientificName"],
        "commonName": data.get("vernacularName", None),
        "rank": data["rank"]
    }

@st.cache_data(show_spinner=False)
def fetch_children(taxon_key):
    res = requests.get(f"https://api.gbif.org/v1/species/{taxon_key}/children?limit=1000")
    return res.json().get("results", [])

# -------------------------------
# Recursive Tree Renderer
# -------------------------------
def render_node(taxon, depth=0):
    indent = "&nbsp;" * (depth * 4)
    label = f"{taxon['scientificName']}"
    if taxon["commonName"]:
        label += f" ({taxon['commonName']})"
    next_rank = get_next_rank(taxon["rank"])

    key = f"{taxon['key']}_{depth}"

    # Checkbox for FAMILY level
    if taxon["rank"] == "FAMILY":
        checked = st.checkbox(f"{indent}{label}", key=key)
        if checked:
            st.session_state["selected_families"].add(taxon["key"])
    else:
        with st.container():
            col1, col2 = st.columns([0.05, 0.95])
            with col1:
                expand = st.toggle("", key=f"toggle_{key}", label_visibility="collapsed")
            with col2:
                st.markdown(f"{indent}**{label}**", unsafe_allow_html=True)

        if expand and next_rank:
            children = fetch_children(taxon["key"])
            for child in children:
                if child.get("rank") == next_rank:
                    child_taxon = fetch_taxon(child["key"])
                    render_node(child_taxon, depth + 1)

st.markdown("---")
if st.button("🗺️ Map Selected Families"):
    st.session_state["plot_trigger"] = True

# -------------------------------
# Session State Init
# -------------------------------
if "selected_families" not in st.session_state:
    st.session_state["selected_families"] = set()

# -------------------------------
# Sidebar Layout
# -------------------------------
with st.sidebar:
    st.header("🌿 Taxonomic Tree")
    for root in ROOT_TAXA:
        root_taxon = match_taxon(root)
        if root_taxon:
            render_node(root_taxon, depth=0)

    st.markdown("---")
    if st.session_state["selected_families"]:
        st.markdown("### ✅ Selected Families")
        for key in st.session_state["selected_families"]:
            st.markdown(f"- Taxon Key: `{key}`")
    else:
        st.info("No families selected yet.")



# --------- MAP & HEXBIN PLOTTING ---------
st.title("📍 GBIF Species Occurrence Map")

def fetch_occurrences(taxon_key, max_records=2000):
    all_coords = []
    limit = 300
    for offset in range(0, max_records, limit):
        url = f"https://api.gbif.org/v1/occurrence/search?taxonKey={taxon_key}&hasCoordinate=true&limit={limit}&offset={offset}"
        res = requests.get(url)
        if res.status_code != 200:
            continue
        data = res.json().get("results", [])
        coords = [
            (rec["decimalLatitude"], rec["decimalLongitude"])
            for rec in data
            if "decimalLatitude" in rec and "decimalLongitude" in rec
        ]
        all_coords.extend(coords)
    return all_coords
    
if st.session_state.get("plot_trigger", False):
    st.session_state["plot_trigger"] = False  # Reset

    all_coords = []
    for taxon_key in st.session_state["selected_families"]:
        coords = fetch_occurrences(taxon_key)
        all_coords.extend(coords)

    if all_coords:
        df = compute_hex_richness(all_coords)

        fig = px.density_mapbox(
            df, lat="lat", lon="lon", z="richness",
            radius=10, center=dict(lat=20, lon=0), zoom=1,
            mapbox_style="open-street-map", hover_name="richness",
            title="Species Richness per Hex Tile"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No valid coordinates found.")



def compute_hex_richness(coords, resolution=3):
    bins = defaultdict(set)
    for lat, lon in coords:
        hex_id = h3.geo_to_h3shape(lat, lon, resolution)
        bins[hex_id].add((lat, lon))  # could add species name if known
    data = []
    for h, points in bins.items():
        lat, lon = h3.h3shape_to_geo(h)
        data.append({
            "hex": h,
            "lat": lat,
            "lon": lon,
            "richness": len(points),
            "species": points
        })
    return pd.DataFrame(data)

if st.button("📊 Map Selected Families"):
    all_coords = []
    for taxon_key in st.session_state["selected_families"]:
        coords = fetch_occurrences(taxon_key)
        all_coords.extend(coords)

    if all_coords:
        df = compute_hex_richness(all_coords)

        fig = px.density_mapbox(
            df, lat="lat", lon="lon", z="richness",
            radius=10, center=dict(lat=20, lon=0), zoom=1,
            mapbox_style="open-street-map", hover_name="richness",
            title="Species Richness per Hex Tile"
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No valid coordinates found.")


