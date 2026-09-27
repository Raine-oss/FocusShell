# // Imports
import csv
import json
import sys
from datetime import date
from typing import Optional
from core.database import get_all_sessions, get_sessions_for_date
from core.engine import get_daily_metrics, format_seconds

# // JSON Exporter
def export_sessions_json(target_date: Optional[str] = None, out_file: Optional[str] = None) -> None:
    if target_date:
        metrics = get_daily_metrics(target_date)
        export_payload = {
            "date": target_date,
            "active_time": metrics["total_duration"],
            "active_time_formatted": metrics["total_duration_formatted"],
            "projects": [
                {
                    "project_name": p["project_name"],
                    "duration_seconds": p["total_duration"],
                    "duration_formatted": format_seconds(p["total_duration"]),
                    "sessions_count": p["sessions_count"]
                }
                for p in metrics["projects"]
            ],
            "apps": [
                {
                    "app_name": a["app_name"],
                    "category": a["category"],
                    "duration_seconds": a["total_duration"],
                    "duration_formatted": format_seconds(a["total_duration"]),
                    "sessions_count": a["sessions_count"]
                }
                for a in metrics["apps"]
            ],
            "sessions": [dict(s) for s in metrics["sessions"]]
        }
    else:
        all_s = get_all_sessions()
        total_time = sum(s["duration_seconds"] for s in all_s)
        export_payload = {
            "exported_at": date.today().strftime("%Y-%m-%d"),
            "total_active_time": total_time,
            "total_active_time_formatted": format_seconds(total_time),
            "sessions_count": len(all_s),
            "sessions": [dict(s) for s in all_s]
        }
        
    output_str = json.dumps(export_payload, indent=2, ensure_ascii=False)
    
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(output_str)
        print(f"✓ Exported data to {out_file}")
    else:
        sys.stdout.write(output_str + "\n")

# // CSV Exporter
def export_sessions_csv(target_date: Optional[str] = None, out_file: Optional[str] = None) -> None:
    if target_date:
        sessions = get_sessions_for_date(target_date)
    else:
        sessions = get_all_sessions()
        
    raw_data = [dict(s) for s in sessions]
    fieldnames = [
        "id", "app_name", "project_context", "category", 
        "window_title", "started_at", "ended_at", 
        "duration_seconds", "duration_formatted", "date"
    ]
    
    data = []
    for r in raw_data:
        entry = dict(r)
        entry["duration_formatted"] = format_seconds(entry.get("duration_seconds", 0))
        data.append(entry)
    
    if out_file:
        with open(out_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                clean_row = {k: row.get(k, "") for k in fieldnames}
                writer.writerow(clean_row)
        print(f"✓ Exported {len(data)} sessions to {out_file}")
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            clean_row = {k: row.get(k, "") for k in fieldnames}
            writer.writerow(clean_row)

