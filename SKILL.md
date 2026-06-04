---
name: neo4j-dynamic-schema-guardrail
description: A strict zero-hallucination guardrail that forces AI agents to dynamically validate user requests against a local Neo4j JSON schema before generating Cypher queries. Use this whenever writing, debugging, or analyzing database code.
---

## Instructions
1. **Dynamic Schema Ingestion:** Before writing any Cypher query, locate, open, and read the JSON schema file provided in `assets/schema.json`. Do not rely on pre-trained assumptions about the data structure.
2. **Strict Entity Verification:** Extract all node labels, relationship types, and properties requested by the user. Cross-reference them against the keys declared in `assets/schema.json`.
3. **The Hallucination Firewall:** If a requested label or property is *not* explicitly present in the schema file, do not invent or guess it. Halt immediately and output a "Schema Validation" matrix showing the missing elements.
4. **Property Type Enforcement:** For every property used in a filter or comparison, check its declared type in `assets/schema.json` (`STRING`, `INTEGER`, etc.). If the value supplied by the user does not match that type, halt and report a type mismatch — do not coerce or guess.
5. **Relationship Direction Enforcement:** For every relationship pattern, read the `direction` field from `assets/schema.json`. Always emit the arrow in the direction the schema declares (`out` = `(a)-[:REL]->(b)`, `in` = `(b)-[:REL]->(a)`). If the user's prompt implies the wrong direction, correct it silently and note the correction in your output.
6. **Cypher Generation:** If all validation passes, generate clean Cypher code using modern Cypher 25 parameter syntax (`$param`). Restrict returned fields strictly to the properties allowed by the schema.
