---
name: neo4j-schema-guardrail
description: A Neo4j schema enforcement skill that validates every Cypher request against your database schema before generating queries. Works with an existing database or a new one defined from CSV data. Designed to complement the neo4j-skills ecosystem — use alongside the Cypher and Modeling skills as the validation layer that runs before any query is written.
---

## What This Skill Does

Prevents AI coding agents from hallucinating non-existent nodes, relationships, and properties when generating Cypher queries. Validates every request against a local `assets/schema.json` file — no live database connection required.

Works in two scenarios:
- **Existing database** — schema pulled from live Neo4j via APOC
- **New database from CSV or description** — schema defined by the agent before the database exists

---

## Setup

### Scenario A — Existing Database

Set credentials and run:
```bash
# Linux / macOS
export NEO4J_URI="neo4j+s://<your-instance>.databases.neo4j.io"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"
python scripts/generate_schema.py
```

```powershell
# Windows PowerShell
$env:NEO4J_URI     = "neo4j+s://<your-instance>.databases.neo4j.io"
$env:NEO4J_USERNAME = "neo4j"
$env:NEO4J_PASSWORD = "your-password"
$env:PYTHONUTF8    = "1"
python scripts/generate_schema.py
```

Requires APOC installed on your Neo4j instance (`CALL apoc.meta.schema()`).

### Scenario B — New Database (CSV or Description)

Tell the agent what data you have. The agent will run `define_schema.py` and fill in node labels, properties, and relationships automatically based on your CSV structure or description. No manual input required.

```bash
python scripts/define_schema.py
```

The agent reads your data structure and drives the script. Schema is written to `assets/schema.json` and the agent can immediately generate validated Cypher import scripts to build the database.

### Scenario C — Neo4j Standard JSON Format

If you have a schema from `graph-schema-introspector`, `graph-schema-json-js-utils`, or `mcp-neo4j-data-modeling`:
```bash
python scripts/import_neo4j_schema.py path/to/your-neo4j-schema.json
```

---

## Validation Rules

Once `assets/schema.json` exists, apply these rules before generating any Cypher:

1. **Dynamic Schema Ingestion** — read `assets/schema.json` before every query. Do not rely on pre-trained assumptions about the data structure.

2. **Strict Entity Verification** — extract all node labels, relationship types, and properties from the user's request. Cross-reference against `assets/schema.json`.

3. **Synonym Mapping** — if a requested entity is not found, check for close matches in the schema before halting. Suggest the closest match:
   ```
   ⚠️ 'Minifigure' not found. Did you mean: Minifig?
   ```

4. **The Hallucination Firewall** — if no close match exists, halt immediately and output a Schema Validation matrix. Do not invent or guess.
   ```
   Schema Validation Report
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Requested Entity    | Status
   ─────────────────── | ──────
   Node: Character     | ❌ NOT FOUND in schema
   Node: Movie         | ❌ NOT FOUND in schema
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Halting. No Cypher generated.
   ```

5. **Property Type Enforcement** — for every property used in a filter or comparison, check its declared type (`STRING`, `INTEGER`, etc.). If the value does not match, halt and report a type mismatch.
   ```
   Schema Validation Report
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Filter                  | Schema Type | Supplied | Status
   ────────────────────── | ─────────── | ──────── | ──────
   Set.pieces = 'unknown' | INTEGER     | STRING   | ❌ TYPE MISMATCH
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

6. **Relationship Direction Enforcement** — read the `direction` field from `assets/schema.json`. Always emit the arrow in the declared direction (`out` = `(a)-[:REL]->(b)`, `in` = `(b)-[:REL]->(a)`). If the prompt implies the wrong direction, correct it and note the correction.
   ```
   Direction Check
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Relationship | Schema Direction | Prompt Direction | Action
   ──────────── | ─────────────── | ──────────────── | ──────
   HAS_SET      | Theme ──→ Set   | Set ──→ Theme    | ↩ Corrected
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

7. **Cypher Generation** — if all validation passes, generate clean Cypher 25 using `$param` parameter syntax. Restrict returned fields strictly to properties declared in the schema.

---

## Schema Format

`assets/schema.json` uses the APOC meta.schema format:

```json
{
  "value": {
    "Theme": {
      "type": "node",
      "count": 13,
      "properties": {
        "name": { "type": "STRING", "indexed": false, "unique": false },
        "theme_id": { "type": "INTEGER", "indexed": false, "unique": false }
      },
      "relationships": {
        "HAS_SET": { "direction": "out", "labels": ["Set"], "properties": {} }
      }
    },
    "Set": {
      "type": "node",
      "count": 1267,
      "properties": {
        "name": { "type": "STRING" },
        "id": { "type": "STRING" },
        "year": { "type": "INTEGER" },
        "pieces": { "type": "INTEGER" },
        "parent_theme": { "type": "STRING" }
      },
      "relationships": {
        "HAS_SET": { "direction": "in", "labels": ["Theme"], "properties": {} },
        "HAS_MINIFIG": { "direction": "out", "labels": ["Minifig"], "properties": { "quantity": { "type": "INTEGER" } } }
      }
    },
    "Minifig": {
      "type": "node",
      "count": 1528,
      "properties": {
        "name": { "type": "STRING" },
        "fig_num": { "type": "STRING" },
        "num_parts": { "type": "INTEGER" }
      },
      "relationships": {
        "HAS_MINIFIG": { "direction": "in", "labels": ["Set"], "properties": {} }
      }
    },
    "HAS_SET": { "type": "relationship", "count": 698, "properties": {} },
    "HAS_MINIFIG": { "type": "relationship", "count": 2272, "properties": { "quantity": { "type": "INTEGER" } } }
  }
}
```

---

## Example — Valid Query

**Prompt:** "List all minifigures in the Cloud City set."

**Validation:**
```
Node: Set          | ✅ FOUND
Node: Minifig      | ✅ FOUND
Rel: HAS_MINIFIG   | ✅ FOUND (Set → Minifig)
Property: id       | ✅ STRING
Property: name     | ✅ STRING
```

**Generated Cypher 25:**
```cypher
MATCH (s:Set {id: $setId})-[:HAS_MINIFIG]->(m:Minifig)
RETURN m.name AS minifigName, m.fig_num AS figNum, m.num_parts AS numParts
ORDER BY m.name
```
```
Parameters: { setId: "10123-1" }
```

---

## Example — Blocked Query

**Prompt:** "Find all Character nodes linked to a Movie."

**Validation:**
```
Schema Validation Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Node: Character     | ❌ NOT FOUND in schema
Node: Movie         | ❌ NOT FOUND in schema
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Halting. No Cypher generated.
```

---

## Example — Synonym Suggestion

**Prompt:** "Find all Minifigures in a set."

**Validation:**
```
⚠️ 'Minifigure' not found in schema. Did you mean: Minifig?
```
Proceeding with `Minifig` if confirmed.
