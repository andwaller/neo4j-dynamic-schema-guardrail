"""
Converts a Neo4j standard graph schema JSON file (produced by graph-schema-introspector,
graph-schema-json-js-utils, or mcp-neo4j-data-modeling) into the guardrail's
APOC-compatible assets/schema.json format.

Usage:
    python scripts/import_neo4j_schema.py <path-to-neo4j-schema.json>
"""

import json
import os
import sys


def neo4j_type_to_apoc(type_def):
    if not isinstance(type_def, dict):
        return "STRING"
    mapping = {
        "string": "STRING",
        "integer": "INTEGER",
        "float": "FLOAT",
        "boolean": "BOOLEAN",
        "date": "DATE",
        "datetime": "DATETIME",
        "array": "LIST",
    }
    return mapping.get(type_def.get("type", "string").lower(), "STRING")


def resolve_ref(ref, node_labels, node_obj_types):
    key = ref.lstrip("#")
    if key in node_labels:
        return node_labels[key]
    if key in node_obj_types:
        obj = node_obj_types[key]
        label_ref = obj.get("labels", [{}])[0].get("$ref", "").lstrip("#")
        return node_labels.get(label_ref, key)
    return key


def convert(neo4j_schema):
    graph = neo4j_schema.get("graphSchemaRepresentation", {}).get("graphSchema", {})

    node_labels = {nl["$id"]: nl["token"] for nl in graph.get("nodeLabels", [])}
    rel_types = {rt["$id"]: rt["token"] for rt in graph.get("relationshipTypes", [])}
    node_obj_types = {n["$id"]: n for n in graph.get("nodeObjectTypes", [])}
    rel_obj_types = graph.get("relationshipObjectTypes", [])

    apoc = {"value": {}}

    for nid, nobj in node_obj_types.items():
        label_ref = nobj.get("labels", [{}])[0].get("$ref", "").lstrip("#")
        label = node_labels.get(label_ref, nid)
        properties = {}
        for prop in nobj.get("properties", []):
            properties[prop["token"]] = {
                "type": neo4j_type_to_apoc(prop.get("type", {})),
                "indexed": False,
                "unique": False,
                "existence": not prop.get("nullable", True),
            }
        apoc["value"][label] = {
            "type": "node",
            "count": 0,
            "properties": properties,
            "relationships": {},
            "labels": [],
        }

    for robj in rel_obj_types:
        rel_token = rel_types.get(robj["type"]["$ref"].lstrip("#"), "UNKNOWN")
        from_label = resolve_ref(robj["from"]["$ref"], node_labels, node_obj_types)
        to_label = resolve_ref(robj["to"]["$ref"], node_labels, node_obj_types)

        rel_props = {}
        for prop in robj.get("properties", []):
            rel_props[prop["token"]] = {
                "type": neo4j_type_to_apoc(prop.get("type", {})),
                "indexed": False,
                "unique": False,
                "existence": not prop.get("nullable", True),
                "array": False,
            }

        if from_label in apoc["value"]:
            apoc["value"][from_label]["relationships"][rel_token] = {
                "direction": "out",
                "labels": [to_label],
                "count": 0,
                "properties": rel_props,
            }

        if to_label in apoc["value"]:
            apoc["value"][to_label]["relationships"][rel_token] = {
                "direction": "in",
                "labels": [from_label],
                "count": 0,
                "properties": rel_props,
            }

        apoc["value"][rel_token] = {
            "type": "relationship",
            "count": 0,
            "properties": {k: {kk: vv for kk, vv in v.items() if kk != "array"} for k, v in rel_props.items()},
        }

    return apoc


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_neo4j_schema.py <path-to-neo4j-schema.json>")
        sys.exit(1)

    input_path = sys.argv[1]
    with open(input_path, "r", encoding="utf-8") as f:
        neo4j_schema = json.load(f)

    apoc = convert(neo4j_schema)

    output_path = os.path.join("assets", "schema.json")
    os.makedirs("assets", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(apoc, f, indent=2)

    node_count = sum(1 for v in apoc["value"].values() if v.get("type") == "node")
    rel_count = sum(1 for v in apoc["value"].values() if v.get("type") == "relationship")
    print(f"✅ Converted: {node_count} node types, {rel_count} relationship types")
    print(f"   Saved to {output_path}")


if __name__ == "__main__":
    main()
