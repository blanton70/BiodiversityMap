const container = document.getElementById("tree-container");
const rankOrder = ["KINGDOM", "PHYLUM", "CLASS", "ORDER", "FAMILY", "GENUS"];

// Define root kingdoms manually
const roots = [
  "Animalia",
  "Plantae",
  "Fungi",
  "Bacteria",
  "Protozoa",
  "Chromista",
  "Viruses"
];

initRoot();

async function initRoot() {
  for (const name of roots) {
    const taxon = await matchTaxon(name);
    if (taxon) createNode(taxon, container, 0);
  }
}

async function matchTaxon(name) {
  const url = `https://api.gbif.org/v1/species/match?name=${encodeURIComponent(name)}`;
  const res = await fetch(url);
  const data = await res.json();
  if (data.usageKey) {
    return await fetchTaxonWithCommonName(data.usageKey);
  } else {
    console.warn(`Taxon not found or matched: ${name}`);
    return null;
  }
}

async function createNode(taxon, parentElement, depth) {
  const wrapper = document.createElement("div");
  wrapper.className = "tree-node";
  wrapper.style.paddingLeft = `${depth * 20}px`;

  const toggle = document.createElement("div");
  toggle.className = "toggle";
  toggle.textContent = "+";

  const label = document.createElement("div");
  label.className = "tree-label";
  label.innerText = `${taxon.scientificName}${taxon.commonName ? ` (${taxon.commonName})` : ""}`;

  toggle.onclick = async (e) => {
    e.stopPropagation();
    if (toggle.textContent === "+") {
      toggle.textContent = "−";
      const children = await fetchChildren(taxon.key, taxon.rank);
      for (const child of children) {
        createNode(child, wrapper, depth + 1);
      }
    } else {
      toggle.textContent = "+";
      const toRemove = wrapper.querySelectorAll(`.tree-node[data-depth="${depth + 1}"]`);
      toRemove.forEach(el => el.remove());
    }
  };

  wrapper.appendChild(toggle);
  wrapper.appendChild(label);
  wrapper.setAttribute("data-depth", depth);
  parentElement.appendChild(wrapper);

  const hasChildren = await hasChildTaxa(taxon.key, taxon.rank);
  if (!hasChildren) toggle.classList.add("invisible");
}

async function fetchChildren(taxonKey, parentRank) {
  const url = `https://api.gbif.org/v1/species/${taxonKey}/children?limit=500`;
  const res = await fetch(url);
  const data = await res.json();

  const targetRankIndex = rankOrder.indexOf(parentRank) + 1;
  if (targetRankIndex < 0 || targetRankIndex >= rankOrder.length) return [];

  const targetRank = rankOrder[targetRankIndex];
  const filtered = data.results.filter(t => t.rank === targetRank);
  return Promise.all(filtered.map(t => fetchTaxonWithCommonName(t.key)));
}

async function hasChildTaxa(taxonKey, parentRank) {
  const children = await fetchChildren(taxonKey, parentRank);
  return children.length > 0;
}

async function fetchTaxonWithCommonName(taxonKey) {
  const url = `https://api.gbif.org/v1/species/${taxonKey}`;
  const res = await fetch(url);
  const data = await res.json();
  return {
    key: data.key,
    scientificName: data.scientificName,
    commonName: data.vernacularName || null,
    rank: data.rank
  };
}
