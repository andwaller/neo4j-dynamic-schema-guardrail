import os
import csv
from neo4j import GraphDatabase

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
THEMES_CSV = os.getenv("THEMES_CSV", os.path.join(_DATA_DIR, "themes.csv"))
SETS_CSV = os.getenv("SETS_CSV", os.path.join(_DATA_DIR, "sets.csv"))

STARWARS_THEME_IDS = {"18", "158", "171", "209", "261"}


def load_starwars_themes():
    themes = {}
    with open(THEMES_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["id"] in STARWARS_THEME_IDS:
                themes[row["id"]] = row["name"]
    return themes


def load_starwars_sets():
    sets = []
    with open(SETS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["theme_id"] in STARWARS_THEME_IDS:
                sets.append({
                    "id": row["set_num"],
                    "name": row["name"],
                    "year": int(row["year"]) if row["year"] else None,
                    "pieces": int(row["num_parts"]) if row["num_parts"] else None,
                    "parent_theme": "Star Wars",
                    "theme_id": row["theme_id"],
                })
    return sets


def import_data(driver, themes, sets):
    with driver.session() as session:
        # Upsert Theme nodes
        session.run("""
            UNWIND $themes AS t
            MERGE (n:Theme {name: t.name})
            SET n.theme_id = t.theme_id
        """, themes=[{"name": name, "theme_id": int(tid)} for tid, name in themes.items()])
        print(f"  Merged {len(themes)} Theme nodes")

        # Upsert Set nodes and HAS_SET relationships in batches
        batch_size = 500
        for i in range(0, len(sets), batch_size):
            batch = sets[i:i + batch_size]
            session.run("""
                UNWIND $sets AS s
                MERGE (n:Set {id: s.id})
                SET n.name = s.name,
                    n.year = s.year,
                    n.pieces = s.pieces,
                    n.parent_theme = s.parent_theme
                WITH n, s
                MATCH (t:Theme {theme_id: toInteger(s.theme_id)})
                MERGE (t)-[:HAS_SET]->(n)
            """, sets=batch)
            print(f"  Imported sets {i + 1}–{min(i + batch_size, len(sets))}")


def main():
    print("Loading CSVs...")
    themes = load_starwars_themes()
    sets = load_starwars_sets()
    print(f"Found {len(themes)} Star Wars themes and {len(sets)} Star Wars sets")

    print(f"Connecting to {URI}...")
    with GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD)) as driver:
        import_data(driver, themes, sets)

    print("Done! Run MATCH (n) RETURN count(n) to verify.")


if __name__ == "__main__":
    main()
