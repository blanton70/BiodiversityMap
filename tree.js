// Entry point: fetch the root taxon (Life = taxonKey 1)
buildTree(1);

async function buildTree(taxonKey) {
  const rootData = await fetchTaxonWithCommonName(taxonKey);
  const root = d3.hierarchy(rootData, d => d.children);

  const width = 360;
  const dx = 10;
  const dy = 180;

  const treeLayout = d3.tree().nodeSize([dx, dy]);
  const diagonal = d3.linkHorizontal().x(d => d.y).y(d => d.x);

  const svg = d3.select("#tree")
    .append("svg")
    .attr("viewBox", [-dy / 3, -dx * 10, width, dx * 40])
    .style("font", "10px sans-serif")
    .style("user-select", "none");

  const g = svg.append("g");

  let i = 0;

  function update(source) {
    const treeData = treeLayout(root);
    const nodes = treeData.descendants();
    const links = treeData.links();

    const node = g.selectAll("g.node")
      .data(nodes, d => d.id || (d.id = ++i));

    const nodeEnter = node.enter().append("g")
      .attr("class", "node")
      .attr("transform", d => `translate(${d.y},${d.x})`)
      .on("click", async (event, d) => {
        if (d.children) {
          d._children = d.children;
          d.children = null;
        } else {
          if (!d._children && !d.children) {
            const children = await fetchChildren(d.data.key);
            d.children = children.map(child => d3.hierarchy(child));
          } else {
            d.children = d._children;
            d._children = null;
          }
        }
        update(d);
      });

    nodeEnter.append("circle").attr("r", 4);

    nodeEnter.append("text")
      .attr("x", 8)
      .attr("dy", "0.31em")
      .text(d => `${d.data.scientificName}${d.data.commonName ? " (" + d.data.commonName + ")" : ""}`);

    node.exit().remove();

    const link = g.selectAll("path.link")
      .data(links, d => d.target.id);

    link.enter().append("path")
      .attr("class", "link")
      .attr("fill", "none")
      .attr("stroke", "#ccc")
      .attr("stroke-width", 1.5)
      .attr("d", diagonal);

    link.exit().remove();
  }

  update(root);
}

async function fetchChildren(taxonKey) {
  const url = `https://api.gbif.org/v1/species/${taxonKey}/children?limit=1000`;
  const res = await fetch(url);
  const data = await res.json();

  const genusOrHigher = data.results.filter(t => {
    return ["KINGDOM", "PHYLUM", "CLASS", "ORDER", "FAMILY", "GENUS"].includes(t.rank);
  });

  const withCommonNames = await Promise.all(
    genusOrHigher.map(t => fetchTaxonWithCommonName(t.key))
  );

  return withCommonNames;
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
