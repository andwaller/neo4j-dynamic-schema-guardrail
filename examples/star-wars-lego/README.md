# Example: Star Wars LEGO Graph

This example loads a complete Star Wars LEGO dataset into Neo4j — all 5 themes, 1,122 sets, and 1,528 minifigures — so you can try the guardrail skill against real graph data without building your own database.

---

## Prerequisites

- Python 3.9 or higher
- The `neo4j` Python driver (`pip install neo4j`)
- A running Neo4j instance with the [APOC plugin](https://neo4j.com/labs/apoc/) installed
  - [Neo4j Aura](https://neo4j.com/cloud/platform/aura-graph-database/) (free tier works)
  - Or a local Neo4j Desktop instance

---

## Step 1 — Set your credentials

**Linux / macOS**
```bash
export NEO4J_URI="neo4j+s://<your-instance>.databases.neo4j.io"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"
```

**Windows PowerShell**
```powershell
$env:NEO4J_URI     = "neo4j+s://<your-instance>.databases.neo4j.io"
$env:NEO4J_USERNAME = "neo4j"
$env:NEO4J_PASSWORD = "your-password"
```

---

## Step 2 — Import the data

Run the scripts from the **repo root** in this order:

```bash
# 1. Load Star Wars themes and sets
python examples/star-wars-lego/import_starwars.py

# 2. Link minifigures to sets
python examples/star-wars-lego/import_minifigs.py

# 3. Generate the schema snapshot for the guardrail
python scripts/generate_schema.py
```

---

## Step 3 — Verify the import

Open Neo4j Browser and run:

```cypher
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count
```

You should see:

| label | count |
|-------|-------|
| Theme | 5 |
| Set | 1,122 |
| Minifig | 1,528 |

---

## Step 4 — Try the guardrail

With `assets/schema.json` generated, ask your AI agent (Claude Code, Cursor, Windsurf) a natural language question about the data. For example:

> "List the minifigures in the Cloud City set."

The guardrail will validate every node, relationship, and property against the schema before generating a Cypher query.

---

## Graph structure

```
(Theme)-[:HAS_SET]->(Set)-[:HAS_MINIFIG]->(Minifig)
```

| Node | Key properties |
|------|---------------|
| `Theme` | `name`, `theme_id` |
| `Set` | `name`, `id`, `year`, `pieces`, `parent_theme` |
| `Minifig` | `name`, `fig_num`, `num_parts` |

| Relationship | Properties |
|---|---|
| `HAS_SET` | none |
| `HAS_MINIFIG` | `quantity` |
