"""Knowledge graph exports (FR-112; Neo4j in production, ADR-005): `graph.html` and `graph.cypher`.

Nodes are persons and works; edges are person relationships and work relations, coloured by assertion
(stated vs inferred). `graph.html` embeds the data and loads vis-network from cdnjs (pinned);
`graph.cypher` holds idempotent `MERGE` statements for a Neo4j import. Both are derived outputs and are
rebuilt byte-identically from `enrichment.db` (`ilm-engine rebuild-derived`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from string import Template
from typing import Any

VIS_NETWORK = "https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/standalone/umd/vis-network.min.js"
COLOURS = {"stated": "#2f6f4f", "inferred": "#b26b00", "person": "#1f5f8b", "work": "#6b4c9a"}


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    type: str
    assertion: str
    kind: str | None = None


def build_graph(
    entities: list[Any], works: list[Any], relationships: list[Edge], work_relations: list[Edge]
) -> dict[str, Any]:
    """Nodes and edges, sorted by ID so the output never depends on input order."""
    nodes = [
        {"id": e.entity_id, "label": e.canonical_name, "group": "person", "gender": e.gender}
        for e in sorted(entities, key=lambda e: e.entity_id)
    ] + [
        {"id": w.work_id, "label": w.title, "group": "work", "status": w.status}
        for w in sorted(works, key=lambda w: w.work_id)
    ]
    edges = [
        {"from": e.source, "to": e.target, "type": e.type, "assertion": e.assertion, "kind": e.kind}
        for e in sorted(
            [*relationships, *work_relations], key=lambda e: (e.type, e.source, e.target, e.assertion)
        )
    ]
    return {"nodes": nodes, "edges": edges}


_PAGE = Template("""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Knowledge graph</title>
<style>
:root { --bg: #fbfaf7; --fg: #1d1d1f; --muted: #6b6b70; }
@media (prefers-color-scheme: dark) { :root { --bg: #16171a; --fg: #ececef; --muted: #a0a0a8; } }
body { margin: 0; background: var(--bg); color: var(--fg);
       font: 15px/1.5 system-ui, "Noto Naskh Arabic", serif; }
header { padding: 12px 16px; } h1 { font-size: 1.2rem; margin: 0; }
.legend { color: var(--muted); direction: ltr; text-align: left; font-size: .85rem; }
#graph { height: calc(100vh - 80px); }
</style></head><body>
<header><h1>$title</h1>
<div class="legend">$node_count nodes, $edge_count edges ·
<span style="color:$stated">stated</span> · <span style="color:$inferred">inferred</span> ·
<span style="color:$person">person</span> · <span style="color:$work">work</span></div></header>
<div id="graph"></div>
<script src="$library"></script>
<script>
const graph = $data;
const colours = $colours;
const nodes = graph.nodes.map(n => ({
  id: n.id, label: n.label, color: colours[n.group], shape: n.group === "work" ? "box" : "dot",
}));
const edges = graph.edges.map(e => ({
  from: e.from, to: e.to, label: e.kind ? e.type + " (" + e.kind + ")" : e.type,
  color: colours[e.assertion], dashes: e.assertion === "inferred",
  arrows: e.type === "sibling_of" ? "" : "to", font: {size: 9},
}));
const target = document.getElementById("graph");
if (window.vis) {
  new vis.Network(target, {nodes, edges}, {physics: {stabilization: {iterations: 150}}});
} else {
  target.textContent = "vis-network could not be loaded (offline): "
    + nodes.length + " nodes, " + edges.length + " edges.";
}
</script></body></html>
""")


def render_html(graph: dict[str, Any], title: str) -> str:
    return _PAGE.substitute(
        title=escape(title),
        node_count=len(graph["nodes"]),
        edge_count=len(graph["edges"]),
        library=VIS_NETWORK,
        data=json.dumps(graph, ensure_ascii=False, sort_keys=True).replace("</", "<\\/"),
        colours=json.dumps(COLOURS),
        **COLOURS,
    )


def _cypher_string(value: Any) -> str:
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def render_cypher(graph: dict[str, Any]) -> str:
    lines = ["// Neo4j import: idempotent MERGE statements (ilm-engine graph export)"]
    for node in graph["nodes"]:
        label = "Person" if node["group"] == "person" else "Work"
        identifier, name = _cypher_string(node["id"]), _cypher_string(node["label"])
        lines.append(f"MERGE (n:{label} {{id: {identifier}}}) SET n.name = {name};")
    for edge in graph["edges"]:
        rel = edge["type"].upper()
        lines.append(
            f"MATCH (a {{id: {_cypher_string(edge['from'])}}}), (b {{id: {_cypher_string(edge['to'])}}}) "
            f"MERGE (a)-[r:{rel} {{assertion: {_cypher_string(edge['assertion'])}}}]->(b)"
            + (f" SET r.kind = {_cypher_string(edge['kind'])};" if edge["kind"] else ";")
        )
    return "\n".join(lines) + "\n"


def edges_from_records(relationships: list[Any], work_relations: list[Any]) -> tuple[list[Edge], list[Edge]]:
    people = [
        Edge(r.subject_entity_id, r.object_entity_id, r.type, r.assertion, r.attrs.kind)
        for r in relationships
    ]
    works = [Edge(r.subject_work_id, r.object_work_id, r.type, r.assertion) for r in work_relations]
    return people, works
