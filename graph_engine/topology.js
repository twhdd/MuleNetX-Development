export function detectFanOut(nodes, edges) {
  const counts = {};
  edges.forEach(edge => {
    counts[edge.source] = (counts[edge.source] || 0) + 1;
  });
  return Object.entries(counts)
    .filter(([_, count]) => count >= 4)
    .map(([id]) => id);
}
