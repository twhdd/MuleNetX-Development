export function propagateRisk(nodes, edges) {
  const updated = [...nodes];
  edges.forEach(edge => {
    const source = updated.find(n => n.id === edge.source);
    const target = updated.find(n => n.id === edge.target);
    if (!source || !target) return;
    const transfer = source.risk * 0.08;
    target.risk = Math.min(100, target.risk + transfer);
  });
  return updated;
}
