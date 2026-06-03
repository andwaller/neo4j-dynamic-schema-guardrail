# Neo4j Dynamic Schema Guardrail & Cypher 25 Assistant

> A universally reusable, open-standard **Agent Skill** built on the Agent Instruction Protocol (AIP). This package acts as a zero-hallucination semantic adapter, forcing AI coding agents to dynamically validate prompts against your live Neo4j database structure before generating Cypher 25 queries.

Unlike generic Cypher assistants, this skill acts as a **strict compliance firewall** — preventing the agent from fabricating missing properties, nodes, or relationships that do not exist in your schema.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Step 1: Generate Your Schema](#step-1-generate-your-schema)
  - [Step 2: Activate the Skill](#step-2-activate-the-skill)
- [Schema Validation Example](#schema-validation-example)
- [Cypher Generation Example](#cypher-generation-example)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

AI agents working with graph databases frequently hallucinate — inventing node labels, relationship types, or properties that do not exist. This skill eliminates that failure mode entirely by grounding every query generation step in a live, machine-readable snapshot of your Neo4j schema.

**Key guarantees:**

- The agent reads `assets/schema.json` before writing a single line of Cypher.
- Any entity not found in the schema causes an immediate halt and a structured validation report.
- All generated queries use modern **Cypher 25** parameter syntax (`$param`).

---

## How It Works

```
User Prompt
    │
    ▼
┌─────────────────────────────────┐
│  1. Read assets/schema.json     │  ← Ground truth from your live DB
└────────────────┬────────────────┘
                 │
    ▼
┌─────────────────────────────────┐
│  2. Entity Verification         │  ← Cross-reference labels, rels, props
└────────────────┬────────────────┘
                 │
         ┌───────┴───────┐
         │               │
    PASS ▼          FAIL ▼
┌──────────────┐  ┌─────────────────────────────┐
│ Generate     │  │ Output Schema Validation     │
│ Cypher 25    │  │ Matrix — halt, do not guess  │
└──────────────┘  └─────────────────────────────┘
```

---

## Repository Layout

```text
neo4j-dynamic-schema-guardrail/
├── SKILL.md                  # AIP metadata and dynamic verification instructions
├── README.md                 # Setup, documentation, and architecture guide
├── assets/
│   └── schema.json           # Populated ground-truth graph schema (git-ignored in live use)
└── scripts/
    └── generate_schema.py    # Python sync script using Neo4j APOC metadata
```

---

## Prerequisites

- **Python** 3.9 or higher
- A running **Neo4j** instance (local or remote) with the **APOC** plugin installed
- The `neo4j` Python driver

Verify APOC is available on your instance:

```cypher
CALL apoc.meta.schema()
```

If the procedure is not found, install the [APOC plugin](https://neo4j.com/labs/apoc/) for your Neo4j version before proceeding.

---

## Installation

Clone the repository and install the Python driver:

```bash
git clone https://github.com/your-username/neo4j-dynamic-schema-guardrail.git
cd neo4j-dynamic-schema-guardrail
pip install neo4j
```

---

## Configuration

The schema generation script reads connection details from environment variables. Set them before running:

```bash
# Linux / macOS
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"
```

```powershell
# Windows PowerShell
$env:NEO4J_URI      = "bolt://localhost:7687"
$env:NEO4J_USERNAME = "neo4j"
$env:NEO4J_PASSWORD = "your-password"
```

If no environment variables are set, the script falls back to `bolt://localhost:7687` with the credentials `neo4j` / `password`.

---

## Usage

### Step 1: Generate Your Schema

Run the sync script to pull your live schema and write it to `assets/schema.json`:

```bash
python scripts/generate_schema.py
```

A successful run prints:

```
🔄 Connecting to Neo4j instance at bolt://localhost:7687...
✅ Success! Your live Neo4j schema has been mapped to assets/schema.json
```

Re-run this script any time your database schema changes to keep the guardrail in sync.

### Step 2: Activate the Skill

Add this repository as an Agent Skill in your AI coding agent (Claude Code, Cursor, Windsurf, etc.) by pointing the agent at `SKILL.md`. The agent will then automatically:

1. Read `assets/schema.json` before every Cypher generation task.
2. Validate all requested entities against the schema.
3. Either generate a valid Cypher 25 query or emit a schema validation report.

---

## Schema Validation Example

Given the example schema in `assets/schema.json` (containing `Theme` and `Set` nodes connected by `HAS_SET`), a prompt that references a non-existent label produces a validation halt:

**Prompt:** "Find all `Product` nodes linked to a `Category`."

**Agent output:**

```
Schema Validation Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Requested Entity    | Status
─────────────────── | ──────
Node: Product       | ❌ NOT FOUND in schema
Node: Category      | ❌ NOT FOUND in schema
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Halting. No Cypher generated. Please verify entity names against assets/schema.json.
```

---

## Cypher Generation Example

A valid prompt against the same schema:

**Prompt:** "List all Sets belonging to the Theme named 'Technic', returning the set name, year, and piece count."

**Generated Cypher 25:**

```cypher
MATCH (t:Theme {name: $themeName})-[:HAS_SET]->(s:Set)
RETURN s.name AS setName, s.year AS year, s.pieces AS pieces
ORDER BY s.year DESC
```

```
Parameters: { themeName: "Technic" }
```

All returned fields (`name`, `year`, `pieces`) are confirmed present in the `Set` node schema before generation.

---

## Contributing

1. Fork the repository and create a feature branch.
2. Update `assets/schema.json` by running `scripts/generate_schema.py` against a representative database.
3. Open a pull request with a clear description of the change and the schema diff.

---

## License

This project is released under the [MIT License](LICENSE).
