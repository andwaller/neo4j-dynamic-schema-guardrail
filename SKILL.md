---
name: neo4j-schema-guardrail
description: Validates Cypher requests against a local schema snapshot before generation — blocks hallucinated labels, properties, and relationship types. Use when building a new Neo4j graph from CSV data (schema defined before DB exists), or when schema must be versioned in the repo for CI/team use. Does NOT generate Cypher syntax — use neo4j-cypher-skill. Does NOT handle DB administration — use neo4j-cli-tools-skill.
version: 1.2.0
---

## When to Use
- Building a new graph database from CSV data — no live DB yet
- Schema must be versioned in repo (CI pipelines, team visibility)
- Agent is generating Cypher and no live DB connection available

## When NOT to Use
- **Writing, optimizing, or debugging Cypher** → `neo4j-cypher-skill`
- **DB administration** → `neo4j-cli-tools-skill`
- **Live DB connected and schema already known** → skip this skill; cypher-skill handles schema introspection via `apoc.meta.schema()`

---

## Setup

Install driver (skip if using HTTP API):
```bash
pip install neo4j
```

## Which Path?

| Situation | Path |
|---|---|
| No database yet — have CSV or data description | **A** — `define_schema.py` |
| Existing Neo4j database with APOC | **B** — `generate_schema.py` |
| Have Neo4j standard JSON or graphrag schema file | **C** — `import_neo4j_schema.py` |

### Path A — New database from CSV or description
Tell agent what data you have. Agent runs `define_schema.py`, fills labels/properties/relationships from CSV structure. No manual input.
```bash
python scripts/define_schema.py
```
Then ask agent to generate Cypher 25 import scripts. Run imports to build DB. Verify:
```bash
python scripts/generate_schema.py
```

### Path B — Existing database
Credentials are read from environment variables. Store in `.env` — verify `.env` is in `.gitignore` before proceeding. Never hardcode credentials.

```bash
python scripts/generate_schema.py
```

If fails with `APOC not found`: APOC is not installed on your instance. Either install the [APOC plugin](https://neo4j.com/labs/apoc/) or use the HTTP API fallback:
```bash
# HTTP API — no neo4j driver needed, plain Python
curl -X POST https://<instance>.databases.neo4j.io/db/neo4j/query/v2 \
  -u <username>:<password> -H "Content-Type: application/json" \
  -d '{"statement": "CALL db.schema.visualization()"}'
```

If connection fails: check `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` are set. Do NOT hardcode values — use env vars only.

### Path C — Neo4j standard JSON (graphrag, graph-schema-introspector, mcp-neo4j-data-modeling)
```bash
python scripts/import_neo4j_schema.py path/to/schema.json
```
Accepts: `graph-schema-introspector`, `graph-schema-json-js-utils`, `mcp-neo4j-data-modeling`, and `neo4j-graphrag-python` SchemaBuilder format.

If fails with `Unrecognised schema format`: schema does not match graphrag or Neo4j standard JSON structure. Use Path A or B to generate schema directly.

---

## Validation Rules

Apply in order before generating any Cypher:

**1. Read schema** — open `assets/schema.json`. Never use pre-trained assumptions.

**2. Entity verification** — extract all node labels, relationship types, properties from request. Cross-reference against schema.

**3. Synonym mapping** — if entity not found, check for close match:
- Unambiguous match → resolve silently, continue, note substitution:
  ```
  ℹ️ Resolved 'Minifigure' → 'Minifig' (schema name). Proceeding.
  ```
- Ambiguous match → suggest and halt:
  ```
  ⚠️ 'Fig' not found. Did you mean: Minifig, figNum? Clarify before proceeding.
  ```

**4. Hallucination firewall** — no close match → halt, output validation matrix, do not guess:
```
Schema Validation Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Requested Entity    | Status
─────────────────── | ──────
Node: Character     | ❌ NOT FOUND
Node: Movie         | ❌ NOT FOUND
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Halting. Verify entity names against assets/schema.json.
```

**5. Property type enforcement** — check declared type (`STRING`, `INTEGER`, etc.) for every filter value. Mismatch → halt:
```
Filter                  | Schema Type | Supplied | Status
────────────────────── | ─────────── | ──────── | ──────
Set.pieces = 'unknown' | INTEGER     | STRING   | ❌ MISMATCH
```

**6. Relationship direction** — read `direction` field from schema. `out` = `(a)-[:REL]->(b)`. `in` = `(b)-[:REL]->(a)`. Wrong direction → correct silently, note:
```
HAS_SET | Schema: Theme──→Set | Prompt: Set──→Theme | ↩ Corrected
```

**7. Generate** — all checks pass → generate Cypher 25 using `$param` syntax. Return only properties declared in schema.

---

## Schema Format (APOC meta.schema)

`assets/schema.json` uses APOC format — not Aura modeling tool, not GraphRAG package:

```json
{
  "value": {
    "Theme": {
      "type": "node",
      "properties": {
        "name": { "type": "STRING" },
        "theme_id": { "type": "INTEGER" }
      },
      "relationships": {
        "HAS_SET": { "direction": "out", "labels": ["Set"], "properties": {} }
      }
    },
    "Set": {
      "type": "node",
      "properties": {
        "name": { "type": "STRING" },
        "id": { "type": "STRING" },
        "year": { "type": "INTEGER" },
        "pieces": { "type": "INTEGER" }
      },
      "relationships": {
        "HAS_SET": { "direction": "in", "labels": ["Theme"], "properties": {} },
        "HAS_MINIFIG": { "direction": "out", "labels": ["Minifig"],
          "properties": { "quantity": { "type": "INTEGER" } } }
      }
    },
    "Minifig": {
      "type": "node",
      "properties": {
        "name": { "type": "STRING" },
        "fig_num": { "type": "STRING" },
        "num_parts": { "type": "INTEGER" }
      }
    },
    "HAS_MINIFIG": { "type": "relationship", "count": 2272,
      "properties": { "quantity": { "type": "INTEGER" } } }
  }
}
```

---

## Examples

### Valid query
```
User: "List minifigures in the Cloud City set"

✅ Set — FOUND | ✅ Minifig — FOUND | ✅ HAS_MINIFIG — FOUND (Set→Minifig)

MATCH (s:Set {id: $setId})-[:HAS_MINIFIG]->(m:Minifig)
RETURN m.name AS minifigName, m.fig_num AS figNum, m.num_parts AS numParts
ORDER BY m.name
// Parameters: { setId: "10123-1" }
```

### Blocked query
```
User: "Find all Character nodes linked to a Movie"

❌ Character — NOT FOUND | ❌ Movie — NOT FOUND
Halting. No Cypher generated.
```

### Synonym resolved
```
User: "Find all Minifigures in a set"

ℹ️ Resolved 'Minifigure' → 'Minifig'. Proceeding.

MATCH (s:Set {id: $setId})-[:HAS_MINIFIG]->(m:Minifig)
RETURN m.name AS minifigName, m.fig_num AS figNum
// Parameters: { setId: $setId }
```

---

## Checklist
- [ ] `assets/schema.json` exists and is current
- [ ] All node labels verified against schema
- [ ] All relationship types and directions verified
- [ ] All property types checked against filter values
- [ ] Synonyms resolved or halted with clear report
- [ ] Generated Cypher uses `$param` syntax only
- [ ] Returned fields restricted to schema-declared properties
