import asyncio
import time
import sqlite3
import os

DB_PATH = "test_memory_perf.db"

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_text TEXT NOT NULL,
            summary TEXT NOT NULL,
            created_at TEXT NOT NULL,
            consolidated INTEGER NOT NULL DEFAULT 0
        );
    """)
    return db

async def monitor_latency(stop_event, latencies):
    while not stop_event.is_set():
        start = time.perf_counter()
        await asyncio.sleep(0.001)
        latency = time.perf_counter() - start - 0.001
        latencies.append(latency)

def heavy_sync_query():
    # Entire DB lifecycle in one thread
    db = get_db()
    db.execute("BEGIN TRANSACTION")
    for i in range(50000):
        db.execute("INSERT INTO memories (raw_text, summary, created_at) VALUES (?, ?, ?)",
                   ("some long text " * 50, "summary", "now"))
    db.commit()

    start_db = time.perf_counter()
    count = db.execute("SELECT COUNT(*) FROM memories WHERE raw_text LIKE '%NOTFOUND%'").fetchone()[0]
    db_duration = time.perf_counter() - start_db
    db.close()
    return db_duration

async def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    latencies = []
    stop_event = asyncio.Event()
    monitor_task = asyncio.create_task(monitor_latency(stop_event, latencies))

    await asyncio.sleep(0.1)

    print("Running heavy DB query in background thread...")
    db_duration = await asyncio.to_thread(heavy_sync_query)
    print(f"DB query took: {db_duration:.6f}s")

    stop_event.set()
    await monitor_task

    if latencies:
        max_lat = max(latencies)
        print(f"Max event loop latency: {max_lat:.6f}s")
        if max_lat < 0.05:
            print("SUCCESS: Performance optimization verified (latency is low).")
        else:
            print("FAILURE: Performance optimization not as effective as expected.")
    else:
        print("No latencies recorded")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

if __name__ == "__main__":
    asyncio.run(main())
