# // Imports
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from core.database import get_sessions_for_date
from core.context import is_file_name
from core.engine import (
    format_seconds,
    analyze_timeline_transitions
)

# // Date Resolution Helper
def resolve_target_date(date_input: Optional[str] = None) -> str:
    if not date_input or date_input.strip().lower() in ("today", "now"):
        return date.today().strftime("%Y-%m-%d")
    if date_input.strip().lower() == "yesterday":
        return (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        dt = datetime.strptime(date_input.strip(), "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return date.today().strftime("%Y-%m-%d")

# // Daily Review Builder Engine
def build_daily_review(target_date_str: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    target_date = resolve_target_date(target_date_str)
    
    # // Single Immutable Snapshot from SQLite
    sessions = get_sessions_for_date(target_date, db_path=db_path)
    total_sec = sum(s["duration_seconds"] for s in sessions)
    
    try:
        dt_obj = datetime.strptime(target_date, "%Y-%m-%d")
        display_date = dt_obj.strftime("%B %d, %Y")
        short_date = dt_obj.strftime("%b %d")
    except Exception:
        display_date = target_date
        short_date = target_date
        
    if total_sec == 0 or not sessions:
        return {
            "date": target_date,
            "display_date": display_date,
            "short_date": short_date,
            "is_empty": True,
            "overview": {
                "active_time": 0,
                "active_time_formatted": "0s",
                "project_time": 0,
                "project_time_formatted": "0s",
                "unattributed_time": 0,
                "unattributed_time_formatted": "0s",
                "longest_session": 0,
                "longest_session_formatted": "0s"
            },
            "project_attribution": {
                "tracked_projects_seconds": 0,
                "tracked_projects_formatted": "0s",
                "tracked_projects_pct": 0.0,
                "unattributed_seconds": 0,
                "unattributed_formatted": "0s",
                "unattributed_pct": 0.0
            },
            "main_project": None,
            "projects": [],
            "top_applications": [],
            "activity_mix": [],
            "patterns": {
                "most_active_window": "—",
                "longest_uninterrupted": "—",
                "application_switches": 0,
                "context_switches": 0
            },
            "activity_flow": [],
            "highlights": ["No recorded computer activity for this date."]
        }
        
    # // Process Snapshot in Single Pass
    app_map: Dict[str, int] = {}
    cat_map: Dict[str, int] = {}
    proj_map: Dict[str, int] = {}
    distractions_map: Dict[str, int] = {}
    distraction_categories = ("social", "entertainment", "gaming", "media")
    
    hourly_duration = [0] * 24
    app_switches = 0
    context_switches = 0
    max_uninterrupted = 0
    longest_uninterrupted_desc = "—"
    
    prev_app = None
    prev_title = None
    prev_proj = None
    
    for s in sessions:
        dur = s["duration_seconds"]
        app = s["app_name"]
        cat = s["category"].strip()
        cat_lower = cat.lower()
        raw_proj = s.get("project_context", "").strip()
        title = s["window_title"]
        start_time = s["started_at"]
        
        # Hourly distribution
        try:
            h = int(datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").strftime("%H"))
            hourly_duration[h] += dur
        except Exception:
            pass
            
        # Longest continuous session
        if dur > max_uninterrupted:
            max_uninterrupted = dur
            desc = f"{app}"
            if raw_proj and raw_proj != "Unattributed":
                desc += f" / {raw_proj}"
            longest_uninterrupted_desc = f"{format_seconds(dur)} ({desc})"
            
        # Aggregations
        app_map[app] = app_map.get(app, 0) + dur
        cat_map[cat] = cat_map.get(cat, 0) + dur
        
        if raw_proj and raw_proj != "Unattributed":
            proj_map[raw_proj] = proj_map.get(raw_proj, 0) + dur
            
        if cat_lower in distraction_categories or (cat_lower == "browsing" and not raw_proj):
            distractions_map[app] = distractions_map.get(app, 0) + dur
            
        # Switches
        if prev_app is not None:
            if app != prev_app:
                app_switches += 1
                context_switches += 1
            elif prev_title is not None and title != prev_title:
                if dur >= 5 or is_file_name(title) or (raw_proj and prev_proj != raw_proj):
                    context_switches += 1
                    
        prev_app = app
        prev_title = title
        prev_proj = raw_proj
        
    # // Project Attribution
    project_time_sec = sum(proj_map.values())
    unattr_time_sec = max(0, total_sec - project_time_sec)
    proj_pct = (project_time_sec / total_sec * 100) if total_sec > 0 else 0
    unattr_pct = (unattr_time_sec / total_sec * 100) if total_sec > 0 else 0
    
    # // Projects list & Main Project
    sorted_projs = sorted([{"name": k, "duration": v, "duration_formatted": format_seconds(v)} for k, v in proj_map.items()], key=lambda x: x["duration"], reverse=True)
    main_project = sorted_projs[0] if sorted_projs else None
    
    # // Top Applications (Top 4)
    sorted_apps = sorted([{"name": k, "duration": v, "duration_formatted": format_seconds(v), "percentage": (v / total_sec * 100) if total_sec > 0 else 0} for k, v in app_map.items()], key=lambda x: x["duration"], reverse=True)
    top_apps = sorted_apps[:4]
    
    # // Activity Mix / Categories
    sorted_cats = sorted([{"category": k, "duration": v, "duration_formatted": format_seconds(v), "percentage": (v / total_sec * 100) if total_sec > 0 else 0} for k, v in cat_map.items()], key=lambda x: x["duration"], reverse=True)
    
    # // Peak Hour Window
    peak_hour = 0
    peak_val = 0
    for h in range(24):
        if hourly_duration[h] > peak_val:
            peak_val = hourly_duration[h]
            peak_hour = h
    peak_win_str = f"{peak_hour:02d}:00–{(peak_hour + 1) % 24:02d}:00" if peak_val > 0 else "—"
    
    # // Activity Flow
    analyzed_sessions = analyze_timeline_transitions(sessions)
    flow_items = []
    prev_item = None
    for s in analyzed_sessions:
        p_str = s.get("project_context", "").strip()
        item = p_str if p_str and p_str != "Unattributed" else s["app_name"]
        if item != prev_item:
            flow_items.append(item)
            prev_item = item
    flow_nodes = flow_items[-8:] if len(flow_items) > 8 else flow_items
    
    # // Highlights (Strict Facts, No Judgments)
    highlights: List[str] = []
    
    if main_project and main_project["duration"] > 0:
        highlights.append(f"{main_project['name']} was your main tracked project — {main_project['duration_formatted']}.")
        
    if top_apps and top_apps[0]["duration"] > 0:
        highlights.append(f"{top_apps[0]['name']} was your most-used application — {top_apps[0]['duration_formatted']}.")
        
    if max_uninterrupted > 0:
        highlights.append(f"Longest uninterrupted work session — {format_seconds(max_uninterrupted)}.")
        
    if unattr_time_sec > 0:
        highlights.append(f"{format_seconds(unattr_time_sec)} of active time was unattributed to a tracked project.")
        
    sorted_dist = sorted([{"name": k, "duration": v, "duration_formatted": format_seconds(v)} for k, v in distractions_map.items()], key=lambda x: x["duration"], reverse=True)
    if sorted_dist and sorted_dist[0]["duration"] >= 180:
        highlights.append(f"{sorted_dist[0]['name']} accounted for {sorted_dist[0]['duration_formatted']} of active time.")
        
    return {
        "date": target_date,
        "display_date": display_date,
        "short_date": short_date,
        "is_empty": False,
        "overview": {
            "active_time": total_sec,
            "active_time_formatted": format_seconds(total_sec),
            "project_time": project_time_sec,
            "project_time_formatted": format_seconds(project_time_sec),
            "unattributed_time": unattr_time_sec,
            "unattributed_time_formatted": format_seconds(unattr_time_sec),
            "longest_session": max_uninterrupted,
            "longest_session_formatted": format_seconds(max_uninterrupted)
        },
        "project_attribution": {
            "tracked_projects_seconds": project_time_sec,
            "tracked_projects_formatted": format_seconds(project_time_sec),
            "tracked_projects_pct": proj_pct,
            "unattributed_seconds": unattr_time_sec,
            "unattributed_formatted": format_seconds(unattr_time_sec),
            "unattributed_pct": unattr_pct
        },
        "main_project": main_project,
        "projects": sorted_projs,
        "top_applications": top_apps,
        "activity_mix": sorted_cats,
        "patterns": {
            "most_active_window": peak_win_str,
            "longest_uninterrupted": longest_uninterrupted_desc,
            "application_switches": app_switches,
            "context_switches": context_switches
        },
        "activity_flow": flow_nodes,
        "highlights": highlights
    }
