export function calculateDegreeCentrality(nodes, edges) {
  const map = {};
  nodes.forEach(node => {
    map[node.id] = 0;
  });
  edges.forEach(edge => {
    map[edge.source] += 1;
    map[edge.target] += 1;
  });
  return map;
}
