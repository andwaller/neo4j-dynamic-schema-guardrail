import os
import csv
from neo4j import GraphDatabase

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MINIFIGS_CSV = os.getenv("MINIFIGS_CSV", os.path.join(_DATA_DIR, "minifigs.csv"))
INVENTORY_MINIFIGS_CSV = os.getenv("INVENTORY_MINIFIGS_CSV", os.path.join(_DATA_DIR, "inventory_minifigs.csv"))
INVENTORIES_CSV = os.getenv("INVENTORIES_CSV", os.path.join(_DATA_DIR, "inventories.csv"))


def get_existing_set_ids(driver):
    records, _, _ = driver.execute_query("MATCH (s:Set) RETURN s.id AS id")
    return {record["id"] for record in records}


def load_inventories():
    inventories = {}
    with open(INVENTORIES_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            inventories[row["id"]] = row["set_num"]
    return inventories


def load_minifigs():
    minifigs = {}
    with open(MINIFIGS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            minifigs[row["fig_num"]] = {
                "fig_num": row["fig_num"],
                "name": row["name"],
                "num_parts": int(row["num_parts"]) if row["num_parts"] else None,
            }
    return minifigs


def load_inventory_minifigs(inventories, minifigs, existing_set_ids):
    links = []
    with open(INVENTORY_MINIFIGS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            set_num = inventories.get(row["inventory_id"])
            if set_num not in existing_set_ids:
                continue
            fig = minifigs.get(row["fig_num"])
            if not fig:
                continue
            links.append({
                "set_id": set_num,
                "fig_num": fig["fig_num"],
                "name": fig["name"],
                "num_parts": fig["num_parts"],
                "quantity": int(row["quantity"]) if row["quantity"] else 1,
            })
    return links


def import_data(driver, links):
    batch_size = 500
    for i in range(0, len(links), batch_size):
        batch = links[i:i + batch_size]
        driver.execute_query("""
            UNWIND $batch AS row
            MATCH (s:Set {id: row.set_id})
            MERGE (m:Minifig {fig_num: row.fig_num})
            SET m.name = row.name, m.num_parts = row.num_parts
            MERGE (s)-[r:HAS_MINIFIG]->(m)
            SET r.quantity = row.quantity
        """, batch=batch)
        print(f"  Imported links {i + 1}–{min(i + batch_size, len(links))}")


def main():
    print(f"Connecting to {URI}...")
    with GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD)) as driver:
        print("Fetching existing Star Wars set IDs from Aura...")
        existing_set_ids = get_existing_set_ids(driver)
        print(f"Found {len(existing_set_ids)} sets in Aura")

        print("Loading CSVs...")
        inventories = load_inventories()
        minifigs = load_minifigs()
        links = load_inventory_minifigs(inventories, minifigs, existing_set_ids)
        print(f"Found {len(links)} minifig-to-set links matching your Aura sets")

        if not links:
            print("No matching minifigs found. Exiting.")
            return

        print("Importing...")
        import_data(driver, links)

    print("Done! Run MATCH (n) RETURN count(n) to verify.")


if __name__ == "__main__":
    main()
