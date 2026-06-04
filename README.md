# Neo4j Dynamic Schema Guardrail & Cypher 25 Assistant

> A **graph modeling and import tool for new databases** — define your schema from CSV data before the database exists, generate validated Cypher 25 import scripts, and build your graph with confidence. Also works as a file-based schema enforcement layer for existing databases.

> A **Neo4j Agent Skill** built on the Agent Instruction Protocol (AIP). Designed to complement the [neo4j-skills](https://github.com/neo4j-contrib/neo4j-skills) ecosystem — particularly useful before a database exists, where the neo4j-cypher-skill's live schema introspection cannot yet run.

**Primary use case:** You have CSV data and want to build a Neo4j graph. The agent reads your data, defines the schema, generates validated import scripts, and builds the database — all before a live connection exists.

**Secondary use case:** Schema versioned as a file in the repo — works offline, in CI, and across teams without requiring a live database connection.

---

## Skill In Action

```
User: "List all minifigures in the Cloud City set."

Schema Validation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Node: Set          | ✅ FOUND
Node: Minifig      | ✅ FOUND
Rel: HAS_MINIFIG   | ✅ FOUND (Set → Minifig)
Property: id       | ✅ STRING
Property: name     | ✅ STRING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MATCH (s:Set {id: $setId})-[:HAS_MINIFIG]->(m:Minifig)
RETURN m.name AS minifigName, m.fig_num AS figNum, m.num_parts AS numParts
ORDER BY m.name

Parameters: { setId: "10123-1" }
```

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Schema Sources](#schema-sources)
- [Schema Validation Example](#schema-validation-example)
- [Property Type Validation Example](#property-type-validation-example)
- [Relationship Direction Validation Example](#relationship-direction-validation-example)
- [Cypher Generation Example](#cypher-generation-example)
- [Changelog](#changelog)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

AI agents working with graph databases frequently hallucinate by inventing node labels, relationship types, or properties that do not exist. This skill eliminates that failure mode entirely by grounding every query generation step in a local schema snapshot.

**Zero-Hallucination Guardrails:**

- The agent reads `assets/schema.json` before writing a single line of Cypher.
- Any entity not found in the schema causes an immediate halt and a structured validation report.
- Close matches are suggested before halting — "Did you mean: Minifig?"
- Filter values are checked against the declared property type — type mismatches halt generation.
- Relationship directions are enforced from the schema — wrong arrows are caught and corrected.
- All generated queries use modern **Cypher 25** parameter syntax (`$param`).

---

## How It Works

### Path 1 — New Database from CSV or Description *(primary)*

```
CSV files or data description
    │
    ▼
┌─────────────────────────────────┐
│  Agent runs define_schema.py    │  ← Agent fills in labels,
│  (agent-driven, no manual input)│    properties, relationships
└────────────────┬────────────────┘    from your data automatically
                 │
    ▼
┌─────────────────────────────────┐
│  assets/schema.json             │  ← Schema defined before DB exists
└────────────────┬────────────────┘
                 │
    ▼
┌─────────────────────────────────┐
│  Agent generates import scripts │  ← Validated Cypher 25 imports
└────────────────┬────────────────┘    against defined schema
                 │
    ▼
┌─────────────────────────────────┐
│  Database built from imports    │
└────────────────┬────────────────┘
                 │
    ▼
┌─────────────────────────────────┐
│  generate_schema.py             │  ← Verify live schema matches intent
└─────────────────────────────────┘
```

### Path 2 — Existing Database *(secondary)*

Useful when you want schema versioned in the repo, available offline, or visible across the team without requiring a live connection. The neo4j-cypher-skill already handles live schema introspection well — this path adds the file-based layer on top.

```
Existing database
    │
    ▼
┌─────────────────────────────────┐
│  generate_schema.py             │  ← Pulls live schema via APOC
└────────────────┬────────────────┘
                 │
    ▼
┌─────────────────────────────────┐
│  assets/schema.json             │  ← Versioned in repo, works offline
└────────────────┬────────────────┘
                 │
    ▼
┌─────────────────────────────────┐
│  Agent reads SKILL.md           │  ← Picks up guardrail rules
└────────────────┬────────────────┘
                 │
         ┌───────┴───────┐
         │               │
    PASS ▼          FAIL ▼
┌──────────────┐  ┌──────────────────────────┐
│ Generate     │  │ Validation report        │
│ Cypher 25    │  │ halt, do not guess       │
└──────────────┘  └──────────────────────────┘
```

---

## Prerequisites

- Python 3.9 or higher
- The `neo4j` Python driver (`pip install neo4j`)
- A Neo4j instance with APOC (for Path 1 only)

Verify APOC is available:
```cypher
CALL apoc.meta.schema()
```

---

## Schema Sources

The guardrail works with `assets/schema.json` regardless of how it was created.

### Existing Database (APOC)
```bash
python scripts/generate_schema.py
```

### New Database (Agent-Driven)
Tell the agent what data you have. It will run `define_schema.py` and fill in the schema automatically from your CSV structure or description:
```bash
python scripts/define_schema.py
```

### Neo4j Standard JSON Format
```bash
python scripts/import_neo4j_schema.py path/to/your-neo4j-schema.json
```
Accepts schemas from `graph-schema-introspector`, `graph-schema-json-js-utils`, or `mcp-neo4j-data-modeling`.

---

## Schema Validation Example

**Prompt:** "Find all `Character` nodes linked to a `Movie`."

```
Schema Validation Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Requested Entity    | Status
─────────────────── | ──────
Node: Character     | ❌ NOT FOUND in schema
Node: Movie         | ❌ NOT FOUND in schema
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Halting. No Cypher generated. Please verify entity names against assets/schema.json.
```

---

## Property Type Validation Example

**Prompt:** "Find all sets where pieces is 'unknown'."

```
Schema Validation Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Requested Filter        | Schema Type | Supplied Type | Status
─────────────────────── | ─────────── | ────────────  | ──────
Set.pieces = 'unknown'  | INTEGER     | STRING        | ❌ TYPE MISMATCH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Halting. No Cypher generated. Set.pieces expects an INTEGER value.
```

**Prompt:** "Find all sets from the year 1999." *(valid — 1999 is an INTEGER)*

```cypher
MATCH (s:Set)
WHERE s.year = $year
RETURN s.name AS setName, s.id AS setId, s.pieces AS pieces
ORDER BY s.name
```
```
Parameters: { year: 1999 }
```

---

## Relationship Direction Validation Example

**Prompt:** "Find all themes for a given set." *(implies traversal from Set to Theme)*

```
Direction Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Relationship   | Schema Direction  | Prompt Direction  | Action
────────────── | ────────────────  | ────────────────  | ──────
HAS_SET        | Theme ──→ Set     | Set ──→ Theme     | ↩ Corrected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Direction corrected. Generating query with schema-compliant arrow.
```

```cypher
MATCH (t:Theme)-[:HAS_SET]->(s:Set)
WHERE s.id = $setId
RETURN t.name AS themeName
```
```
Parameters: { setId: "10123-1" }
```

---

## Cypher Generation Example

**Prompt:** "List all Sets belonging to the Theme named 'Star Wars', returning the set name, year, and piece count."

```cypher
MATCH (t:Theme {name: $themeName})-[:HAS_SET]->(s:Set)
RETURN s.name AS setName, s.year AS year, s.pieces AS pieces
ORDER BY s.year DESC
```
```
Parameters: { themeName: "Star Wars" }
```

All returned fields (`name`, `year`, `pieces`) confirmed present in the `Set` node schema before generation.

---

## Changelog

### v1.2.0 — 2026-06-04
**Added: Synonym Mapping and SKILL.md Overhaul**
- Guardrail now suggests close matches before halting — "Did you mean: Minifig?"
- `SKILL.md` expanded to include setup, schema format, and full examples.
- How It Works updated to show both existing-database and new-database-from-CSV paths.
- Screenshot replaced with copyable text output.
- Repository layout section removed.
- Cypher Generation Example updated from "Technic" to "Star Wars" to match actual data.

### v1.1.0 — 2026-06-04
**Added: Property Type Enforcement and Relationship Direction Validation**
- `SKILL.md` updated with two new guardrail rules:
  - **Rule 4 — Property Type Enforcement:** Filter values validated against declared property type. Type mismatches halt generation.
  - **Rule 5 — Relationship Direction Enforcement:** Arrow direction enforced from schema. Wrong directions corrected and flagged.
- Inspired by [graph-guard](https://github.com/c-fraser/graph-guard) and [cypher-query-validator](https://github.com/yWorks/cypher-query-validator).

**Added: Broader Schema Source Support**
- `scripts/define_schema.py` — agent-driven schema definition for new databases without a live connection.
- `scripts/import_neo4j_schema.py` — converts Neo4j standard JSON format to guardrail format.

---

## Contributing

1. Fork the repository and create a feature branch.
2. Update `assets/schema.json` by running `scripts/generate_schema.py` against a representative database.
3. Open a pull request with a clear description of the change and the schema diff.

---

## License

This project is released under the [MIT License](LICENSE).
