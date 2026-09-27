# // Imports
import os
import sys
import time
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import init_db, create_session, close_session, get_sessions_for_date
from core.context import extract_project_and_context
from core.review import build_daily_review
from core.engine import get_insights_metrics

# // Benchmark Suite
def run_benchmarks() -> None:
    print("==========================================================")
    print("           FocusShell Performance Benchmarks              ")
    print("==========================================================")
    
    # // Benchmark 1: Context Resolution Throughput
    test_cases = [
        ("Antigravity", "FocusShell — core/context.py"),
        ("Zed", "WorkSpace — main.py"),
        ("Brave", "GitHub - Raine-oss/FocusShell: Terminal Focus Tracker"),
        ("GNOME Terminal", "Terminal — ~/WorkSpace/FocusShell"),
        ("Discord", "Direct Messages - General"),
        ("VS Code", "LogMorph — src/engine.rs — Visual Studio Code")
    ]
    
    iterations = 20000
    t0 = time.perf_counter()
    for _ in range(iterations):
        for app, title in test_cases:
            extract_project_and_context(app, title)
    t1 = time.perf_counter()
    
    total_resolutions = iterations * len(test_cases)
    elapsed = t1 - t0
    rate = total_resolutions / elapsed
    print(f"\n1. Context Resolution:")
    print(f"   - Resolved {total_resolutions:,} window titles in {elapsed:.4f}s")
    print(f"   - Throughput: {rate:,.0f} resolutions/sec ({(elapsed/total_resolutions)*1e6:.2f} µs/op)")

    # // Benchmark 2: SQLite WAL Session Inserts
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = os.path.join(tmp_dir.name, "bench_focus.db")
    init_db(db_path)
    
    insert_count = 1000
    base_dt = datetime(2026, 9, 27, 8, 0, 0)
    
    t0 = time.perf_counter()
    for i in range(insert_count):
        s_dt = base_dt + timedelta(seconds=i * 5)
        e_dt = s_dt + timedelta(seconds=4)
        s_id = create_session("Antigravity", "engine.py", "Coding", s_dt, "FocusShell", db_path=db_path)
        close_session(s_id, e_dt, 4, db_path=db_path)
    t1 = time.perf_counter()
    
    elapsed_db = t1 - t0
    rate_db = insert_count / elapsed_db
    print(f"\n2. SQLite WAL Lifecycle Throughput:")
    print(f"   - Created & Closed {insert_count:,} sessions in {elapsed_db:.4f}s")
    print(f"   - Write Throughput: {rate_db:,.0f} session lifecycles/sec ({(elapsed_db/insert_count)*1e6:.2f} µs/lifecycle)")

    # // Benchmark 3: Review & Analytics Query Latency
    t0 = time.perf_counter()
    query_runs = 100
    for _ in range(query_runs):
        build_daily_review("2026-09-27", db_path=db_path)
    t1 = time.perf_counter()
    
    elapsed_rev = t1 - t0
    latency_per_review = (elapsed_rev / query_runs) * 1000
    print(f"\n3. Daily Review Query Latency (over {insert_count:,} records):")
    print(f"   - Executed {query_runs} full reviews in {elapsed_rev:.4f}s")
    print(f"   - Average Latency: {latency_per_review:.2f} ms per full daily review")

    tmp_dir.cleanup()
    print("\n==========================================================")
    print("           All Benchmark Operations Completed             ")
    print("==========================================================")

# // Main Execution
if __name__ == "__main__":
    run_benchmarks()
