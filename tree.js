const container = document.getElementById("tree-container");

// Start at taxonKey = 0 to get true root (top-level kingdoms)
initRoot();

async function initRoot() {
  const children = await fetchChildren(0); // Top-level domains/kingdoms
  for (const child of children) {
    createNode(child.key, container, 0);
  }
}

async function createNode(taxonKey, parentElement, depth) {
  const taxon = await fetchTaxonWithCommonName(taxonKey);

  const wrapper = document.createElement("div");
  wrapper.className = "tree-node";
  wrapper.style.paddingLeft = `${depth * 20}px`;

  const toggle = document.createElement("div");
  toggle.className = "toggle";
  toggle.textContent = "+";

  const label = document.createElement("div");
  label.className = "tree-label";
  label.innerText = `${taxon.scientificName}${taxon.commonName ? ` (${taxon.commonName})` : ""}`;

  // Toggle behavior
  toggle.onclick = async (e) => {
    e.stopPropagation();
    if (toggle.textContent === "+") {
      toggle.textContent = "−";
      const children = await fetchChildren(taxon.key);
      for (const child of children) {
        createNode(child.key, wrapper, depth + 1);
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

  const hasChildren = await hasChildTaxa(taxon.key);
  if (!hasChildren) toggle.classList.add("invisible");
}

async function hasChildTaxa(taxonKey) {
  const url = `https://api.gbif.org/v1/species/${taxonKey}/children?limit=1`;
  const res = await fetch(url);
  const data = await res.json();
  return data.results.length > 0;
}

async function fetchChildren(taxonKey) {
  const url = `https://api.gbif.org/v1/species/${taxonKey}/children?limit=1000`;
  const res = await fetch(url);
  const data = await res.json();

  return data.results.filter(t =>
    ["KINGDOM", "PHYLUM", "CLASS", "ORDER", "FAMILY", "GENUS"].includes(t.rank)
  );
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
