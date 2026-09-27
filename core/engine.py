# // Imports
import os
import re
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from core.database import (
    get_sessions_for_date,
    get_sessions_between_dates,
    get_all_sessions,
    get_last_session,
    get_goals
)
from core.context import is_file_name
from core.config import DEFAULT_DATA_DIR

# // Formatting Helpers
def format_seconds(seconds: int) -> str:
    if seconds <= 0:
        return "0s"
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    hours = minutes // 60
    rem_min = minutes % 60
    
    if hours > 0:
        if rem_min > 0:
            return f"{hours}h {rem_min:02d}m"
        return f"{hours}h"
    return f"{minutes}m"

def parse_duration_string(dur_str: str) -> int:
    clean = str(dur_str).strip().lower()
    if not clean:
        return 0
    if clean.isdigit():
        return int(clean) * 60
    
    matches = re.findall(r'(\d+(?:\.\d+)?)\s*([hms])', clean)
    if matches:
        total_sec = 0
        for val_str, unit in matches:
            val = float(val_str)
            if unit == 'h':
                total_sec += int(val * 3600)
            elif unit == 'm':
                total_sec += int(val * 60)
            elif unit == 's':
                total_sec += int(val)
        return total_sec
    
    try:
        val = float(clean)
        return int(val * 60)
    except ValueError:
        return 0

def format_time_range(start_str: str, end_str: str, duration_seconds: int) -> str:
    try:
        s_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        e_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
        if duration_seconds < 60:
            return f"{s_dt.strftime('%H:%M:%S')} → {e_dt.strftime('%H:%M:%S')}"
        return f"{s_dt.strftime('%H:%M')} → {e_dt.strftime('%H:%M')}"
    except Exception:
        return f"{start_str} → {end_str}"

# // Focus Category Helpers
FOCUS_CATEGORIES = ("coding", "terminal", "notes", "design")

def is_focus_category(category_name: str) -> bool:
    return category_name.lower().strip() in FOCUS_CATEGORIES


# // Daily Engine
def get_daily_metrics(target_date: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")
        
    sessions = get_sessions_for_date(target_date, db_path=db_path)
    total_duration = sum(s["duration_seconds"] for s in sessions)
    
    app_map: Dict[str, Dict[str, Any]] = {}
    project_map: Dict[str, Dict[str, Any]] = {}
    cat_map: Dict[str, Dict[str, Any]] = {}
    
    # // Contiguous Application Session Grouping
    app_switches_count: Dict[str, int] = {}
    prev_app = None
    for s in sessions:
        cur_app = s["app_name"]
        if cur_app != prev_app:
            app_switches_count[cur_app] = app_switches_count.get(cur_app, 0) + 1
            prev_app = cur_app
            
    longest_session = None
    max_single_session_dur = 0
    
    for s in sessions:
        app = s["app_name"]
        cat = s["category"]
        title = s["window_title"]
        raw_proj = s.get("project_context", "").strip()
        project = raw_proj if raw_proj else "Unattributed"
        dur = s["duration_seconds"]
        
        if dur > max_single_session_dur:
            max_single_session_dur = dur
            longest_session = {
                "app_name": app,
                "project": raw_proj,
                "window_title": title,
                "duration": dur,
                "duration_formatted": format_seconds(dur)
            }
        
        # // App Mapping
        if app not in app_map:
            app_map[app] = {
                "app_name": app,
                "category": cat,
                "total_duration": 0,
                "sessions_count": app_switches_count.get(app, 1),
                "max_session": 0,
                "projects": {},
                "windows": {}
            }
        app_map[app]["total_duration"] += dur
        if dur > app_map[app]["max_session"]:
            app_map[app]["max_session"] = dur
            
        # // Project Mapping
        if project not in project_map:
            project_map[project] = {
                "project_name": project,
                "total_duration": 0,
                "sessions_count": 0
            }
        project_map[project]["total_duration"] += dur
        project_map[project]["sessions_count"] += 1
            
        # // Nested App-Project Mapping
        if project not in app_map[app]["projects"]:
            app_map[app]["projects"][project] = {
                "project_name": project,
                "total_duration": 0,
                "files": {}
            }
        app_map[app]["projects"][project]["total_duration"] += dur
        if title not in app_map[app]["projects"][project]["files"]:
            app_map[app]["projects"][project]["files"][title] = 0
        app_map[app]["projects"][project]["files"][title] += dur
        
        # // Flat Windows Map
        if title not in app_map[app]["windows"]:
            app_map[app]["windows"][title] = 0
        app_map[app]["windows"][title] += dur
        
        # // Category Mapping
        if cat not in cat_map:
            cat_map[cat] = {
                "category": cat,
                "total_duration": 0,
                "sessions_count": 0
            }
        cat_map[cat]["total_duration"] += dur
        cat_map[cat]["sessions_count"] += 1
        
    apps_list = sorted(app_map.values(), key=lambda x: x["total_duration"], reverse=True)
    for a in apps_list:
        a["percentage"] = (a["total_duration"] / total_duration * 100) if total_duration > 0 else 0
        a["windows_list"] = sorted(
            [{"title": k, "duration": v} for k, v in a["windows"].items()],
            key=lambda x: x["duration"],
            reverse=True
        )
        
        proj_list = []
        for p_name, p_data in a["projects"].items():
            files_list = sorted(
                [{"title": k, "duration": v} for k, v in p_data["files"].items()],
                key=lambda x: x["duration"],
                reverse=True
            )
            proj_list.append({
                "name": p_name,
                "duration": p_data["total_duration"],
                "files": files_list
            })
        a["projects_list"] = sorted(proj_list, key=lambda x: x["duration"], reverse=True)
        
    projects_list = sorted(project_map.values(), key=lambda x: x["total_duration"], reverse=True)
    categories_list = sorted(cat_map.values(), key=lambda x: x["total_duration"], reverse=True)
    for c in categories_list:
        c["percentage"] = (c["total_duration"] / total_duration * 100) if total_duration > 0 else 0

    most_opened = max(apps_list, key=lambda x: x["sessions_count"]) if apps_list else None
    longest_session_app = max(apps_list, key=lambda x: x["max_session"]) if apps_list else None
    top_app = apps_list[0] if apps_list else None
    
    total_app_sessions = sum(app_switches_count.values())
    
    return {
        "date": target_date,
        "total_duration": total_duration,
        "total_duration_formatted": format_seconds(total_duration),
        "sessions": sessions,
        "sessions_count": total_app_sessions,
        "raw_records_count": len(sessions),
        "apps": apps_list,
        "projects": projects_list,
        "categories": categories_list,
        "longest_session": longest_session,
        "highlights": {
            "top_app": top_app,
            "most_opened": most_opened,
            "longest_session_app": longest_session_app
        }
    }

# // Projects Engine
def get_projects_summary(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    sessions = get_all_sessions(db_path=db_path)
    proj_map: Dict[str, Dict[str, Any]] = {}
    
    for s in sessions:
        raw_name = s.get("project_context", "").strip()
        p_name = raw_name if raw_name else "Unattributed"
        dur = s["duration_seconds"]
        d = s["date"]
        
        if p_name not in proj_map:
            proj_map[p_name] = {
                "project_name": p_name,
                "total_duration": 0,
                "sessions_count": 0,
                "active_days": set(),
                "last_active": s["started_at"]
            }
        proj_map[p_name]["total_duration"] += dur
        proj_map[p_name]["sessions_count"] += 1
        proj_map[p_name]["active_days"].add(d)
        if s["started_at"] > proj_map[p_name]["last_active"]:
            proj_map[p_name]["last_active"] = s["started_at"]
            
    res = []
    for p_name, data in proj_map.items():
        res.append({
            "project_name": p_name,
            "total_duration": data["total_duration"],
            "total_duration_formatted": format_seconds(data["total_duration"]),
            "sessions_count": data["sessions_count"],
            "active_days_count": len(data["active_days"]),
            "last_active": data["last_active"]
        })
        
    return sorted(res, key=lambda x: x["total_duration"], reverse=True)

def get_project_detail(project_name: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    clean_target = project_name.strip().lower()
    all_sess = get_all_sessions(db_path=db_path)
    today_str = date.today().strftime("%Y-%m-%d")
    
    matching_sessions = [
        s for s in all_sess 
        if (s.get("project_context", "").strip().lower() == clean_target) or 
           (clean_target in ("unattributed", "general", "unknown") and not s.get("project_context", "").strip())
    ]
    
    if not matching_sessions:
        return None
        
    actual_name = matching_sessions[0].get("project_context", "").strip() or "Unattributed"
    total_dur = sum(s["duration_seconds"] for s in matching_sessions)
    today_dur = sum(s["duration_seconds"] for s in matching_sessions if s["date"] == today_str)
    active_days = set(s["date"] for s in matching_sessions)
    
    max_dur = max(s["duration_seconds"] for s in matching_sessions) if matching_sessions else 0
    
    app_map: Dict[str, int] = {}
    file_map: Dict[str, int] = {}
    
    for s in matching_sessions:
        app = s["app_name"]
        win = s["window_title"]
        dur = s["duration_seconds"]
        
        app_map[app] = app_map.get(app, 0) + dur
        file_map[win] = file_map.get(win, 0) + dur
        
    apps_list = sorted([{"app_name": k, "duration": v, "duration_formatted": format_seconds(v)} for k, v in app_map.items()], key=lambda x: x["duration"], reverse=True)
    files_list = sorted([{"window_title": k, "duration": v, "duration_formatted": format_seconds(v)} for k, v in file_map.items()], key=lambda x: x["duration"], reverse=True)
    
    # // Recent Activity History
    sorted_recent = sorted(matching_sessions, key=lambda x: x["started_at"], reverse=True)
    recent_activity = []
    for r in sorted_recent[:10]:
        try:
            st_dt = datetime.strptime(r["started_at"], "%Y-%m-%d %H:%M:%S")
            time_disp = st_dt.strftime("%H:%M") if r["date"] == today_str else st_dt.strftime("%d %b %H:%M")
        except Exception:
            time_disp = r["started_at"]
            
        recent_activity.append({
            "started_at": r["started_at"],
            "time_display": time_disp,
            "app_name": r["app_name"],
            "window_title": r["window_title"],
            "duration": r["duration_seconds"],
            "duration_formatted": format_seconds(r["duration_seconds"])
        })
    
    return {
        "project_name": actual_name,
        "total_duration": total_dur,
        "total_duration_formatted": format_seconds(total_dur),
        "today_duration": today_dur,
        "today_duration_formatted": format_seconds(today_dur),
        "longest_session": max_dur,
        "longest_session_formatted": format_seconds(max_dur),
        "sessions_count": len(matching_sessions),
        "active_days_count": len(active_days),
        "applications": apps_list,
        "files": files_list,
        "recent_activity": recent_activity
    }

# // Insights Engine
def get_insights_metrics(target_date: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")
        
    sessions = get_sessions_for_date(target_date, db_path=db_path)
    total_duration = sum(s["duration_seconds"] for s in sessions)
    
    projects_breakdown: Dict[str, Dict[str, Any]] = {}
    distractions_map: Dict[str, int] = {}
    distraction_categories = ("social", "entertainment", "gaming", "media")
    
    hourly_duration = [0] * 24
    app_switches_count = 0
    meaningful_context_switches = 0
    longest_uninterrupted = None
    max_uninterrupted_sec = 0
    
    prev_app = None
    prev_title = None
    prev_proj = None
    
    for s in sessions:
        dur = s["duration_seconds"]
        app = s["app_name"]
        cat = s["category"].lower().strip()
        raw_proj = s.get("project_context", "").strip()
        title = s["window_title"]
        start_time = s["started_at"]
        
        try:
            h = int(datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").strftime("%H"))
            hourly_duration[h] += dur
        except Exception:
            pass
            
        if dur > max_uninterrupted_sec:
            max_uninterrupted_sec = dur
            longest_uninterrupted = {
                "app_name": app,
                "project": raw_proj or "Unattributed",
                "window_title": title,
                "duration": dur,
                "duration_formatted": format_seconds(dur)
            }
            
        # // App Switches & Meaningful Context Switches
        if prev_app is not None:
            if app != prev_app:
                app_switches_count += 1
                meaningful_context_switches += 1
            elif prev_title is not None and title != prev_title:
                if dur >= 5 or is_file_name(title) or (raw_proj and prev_proj != raw_proj):
                    meaningful_context_switches += 1
                    
        prev_app = app
        prev_title = title
        prev_proj = raw_proj
        
        if raw_proj and raw_proj != "Unattributed":
            if raw_proj not in projects_breakdown:
                projects_breakdown[raw_proj] = {
                    "project_name": raw_proj,
                    "total_duration": 0,
                    "longest_session": 0,
                    "context_switches": 0,
                    "_last_title": None
                }
            p_entry = projects_breakdown[raw_proj]
            p_entry["total_duration"] += dur
            if dur > p_entry["longest_session"]:
                p_entry["longest_session"] = dur
            if p_entry["_last_title"] is not None and p_entry["_last_title"] != title:
                if dur >= 5 or is_file_name(title):
                    p_entry["context_switches"] += 1
            p_entry["_last_title"] = title
            
        if cat in distraction_categories or (cat == "browsing" and not raw_proj):
            dist_label = app
            distractions_map[dist_label] = distractions_map.get(dist_label, 0) + dur

    peak_hour = 0
    peak_val = 0
    for h in range(24):
        if hourly_duration[h] > peak_val:
            peak_val = hourly_duration[h]
            peak_hour = h
            
    peak_hour_range = f"{peak_hour:02d}:00–{(peak_hour + 1) % 24:02d}:00" if peak_val > 0 else "—"
    
    projects_list = []
    for p_name, p_data in projects_breakdown.items():
        projects_list.append({
            "project_name": p_name,
            "total_duration": p_data["total_duration"],
            "total_duration_formatted": format_seconds(p_data["total_duration"]),
            "longest_session": p_data["longest_session"],
            "longest_session_formatted": format_seconds(p_data["longest_session"]),
            "context_switches": p_data["context_switches"]
        })
    projects_list = sorted(projects_list, key=lambda x: x["total_duration"], reverse=True)
    
    distractions_list = sorted(
        [{"name": k, "duration": v, "duration_formatted": format_seconds(v)} for k, v in distractions_map.items()],
        key=lambda x: x["duration"],
        reverse=True
    )
    total_distractions = sum(d["duration"] for d in distractions_list)
    
    return {
        "date": target_date,
        "total_duration": total_duration,
        "total_duration_formatted": format_seconds(total_duration),
        "projects": projects_list,
        "distractions": distractions_list,
        "total_distractions_duration": total_distractions,
        "total_distractions_formatted": format_seconds(total_distractions),
        "patterns": {
            "most_active_hour": peak_hour_range,
            "most_active_hour_duration": format_seconds(peak_val),
            "longest_uninterrupted": longest_uninterrupted,
            "context_switches_count": meaningful_context_switches,
            "app_switches_count": app_switches_count
        }
    }


# // Timeline Transition Engine
def analyze_timeline_transitions(sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    analyzed = []
    total = len(sessions)
    
    for idx, s in enumerate(sessions):
        s_dict = dict(s)
        app = s_dict["app_name"]
        raw_proj = s_dict.get("project_context", "").strip()
        title = s_dict["window_title"]
        end_str = s_dict["ended_at"]
        
        if idx < total - 1:
            nxt = sessions[idx + 1]
            nxt_app = nxt["app_name"]
            nxt_raw_proj = nxt.get("project_context", "").strip()
            nxt_title = nxt["window_title"]
            nxt_start = nxt["started_at"]
            
            try:
                cur_end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
                nxt_start_dt = datetime.strptime(nxt_start, "%Y-%m-%d %H:%M:%S")
                gap_seconds = int((nxt_start_dt - cur_end_dt).total_seconds())
            except Exception:
                gap_seconds = 0
                
            if gap_seconds >= 60:
                cause = f"Idle / Break ({format_seconds(gap_seconds)})"
            elif raw_proj and nxt_raw_proj and raw_proj != nxt_raw_proj:
                cause = "Project switch"
            elif app != nxt_app:
                cause = "App switch"
            elif title != nxt_title:
                cause = "Context switch"
            else:
                cause = "Session switch"
        else:
            cause = "Active session"
            
        s_dict["transition_cause"] = cause
        analyzed.append(s_dict)
        
    return analyzed

# // Goals Progress Engine
def get_goals_progress(target_date: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")
        
    goals = get_goals(db_path=db_path)
    if not goals:
        return []
        
    sessions = get_sessions_for_date(target_date, db_path=db_path)
    
    res = []
    for g in goals:
        t_name = g["target_name"].strip()
        t_type = g.get("target_type", "project").strip().lower()
        t_sec = g["target_seconds"]
        
        achieved_sec = 0
        if t_type == "project":
            achieved_sec = sum(s["duration_seconds"] for s in sessions if s.get("project_context", "").strip().lower() == t_name.lower())
        elif t_type == "category":
            achieved_sec = sum(s["duration_seconds"] for s in sessions if s.get("category", "").strip().lower() == t_name.lower())
        elif t_type == "app":
            achieved_sec = sum(s["duration_seconds"] for s in sessions if s.get("app_name", "").strip().lower() == t_name.lower())
        else:
            achieved_sec = sum(s["duration_seconds"] for s in sessions)
            
        pct = (achieved_sec / t_sec * 100) if t_sec > 0 else 0
        rem_sec = max(0, t_sec - achieved_sec)
        
        res.append({
            "target_name": t_name,
            "target_type": t_type,
            "target_seconds": t_sec,
            "target_formatted": format_seconds(t_sec),
            "achieved_seconds": achieved_sec,
            "achieved_formatted": format_seconds(achieved_sec),
            "percentage": min(100.0, pct),
            "raw_percentage": pct,
            "remaining_seconds": rem_sec,
            "remaining_formatted": format_seconds(rem_sec),
            "is_completed": achieved_sec >= t_sec,
            "date": target_date
        })
        
    return res


# // Trends Engine
def get_trends_metrics(days_count: int = 14, db_path: Optional[str] = None) -> Dict[str, Any]:
    end_dt = date.today()
    start_dt = end_dt - timedelta(days=days_count - 1)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")
    
    sessions = get_sessions_between_dates(start_str, end_str, db_path=db_path)
    
    daily_stats: List[Dict[str, Any]] = []
    category_totals: Dict[str, int] = {}
    
    today_str = end_dt.strftime("%Y-%m-%d")
    yesterday_str = (end_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    
    today_dur = 0
    yesterday_dur = 0
    today_cats: Dict[str, int] = {}
    yesterday_cats: Dict[str, int] = {}
    
    empty_days_labels = []
    
    for i in range(days_count):
        curr_dt = start_dt + timedelta(days=i)
        curr_str = curr_dt.strftime("%Y-%m-%d")
        d_sessions = [s for s in sessions if s["date"] == curr_str]
        
        d_total = sum(s["duration_seconds"] for s in d_sessions)
        d_focus = sum(s["duration_seconds"] for s in d_sessions if is_focus_category(s["category"]))
        
        d_cats: Dict[str, int] = {}
        for s in d_sessions:
            c = s["category"]
            d_cats[c] = d_cats.get(c, 0) + s["duration_seconds"]
            category_totals[c] = category_totals.get(c, 0) + s["duration_seconds"]
            
        if curr_str == today_str:
            today_dur = d_total
            today_cats = d_cats
        elif curr_str == yesterday_str:
            yesterday_dur = d_total
            yesterday_cats = d_cats
            
        focus_ratio = (d_focus / d_total * 100) if d_total > 0 else 0
        
        if d_total == 0:
            empty_days_labels.append(curr_dt.strftime("%d %b"))
        
        daily_stats.append({
            "date": curr_str,
            "label": curr_dt.strftime("%d %b"),
            "total_seconds": d_total,
            "total_formatted": format_seconds(d_total) if d_total > 0 else "—",
            "focus_seconds": d_focus,
            "focus_formatted": format_seconds(d_focus) if d_focus > 0 else "—",
            "focus_ratio": focus_ratio,
            "categories": d_cats,
            "is_empty": d_total == 0
        })
        
    diff_seconds = today_dur - yesterday_dur
    diff_pct = ((today_dur - yesterday_dur) / yesterday_dur * 100) if yesterday_dur > 0 else (100.0 if today_dur > 0 else 0.0)
    
    cat_comparisons = []
    all_cat_keys = set(today_cats.keys()).union(set(yesterday_cats.keys()))
    for c in sorted(all_cat_keys):
        t_c = today_cats.get(c, 0)
        y_c = yesterday_cats.get(c, 0)
        diff_c = t_c - y_c
        cat_comparisons.append({
            "category": c,
            "today_seconds": t_c,
            "today_formatted": format_seconds(t_c),
            "yesterday_seconds": y_c,
            "yesterday_formatted": format_seconds(y_c),
            "diff_seconds": diff_c,
            "diff_formatted": ("+" if diff_c >= 0 else "-") + format_seconds(abs(diff_c))
        })
        
    max_day = max([d["total_seconds"] for d in daily_stats]) if daily_stats else 1
    for d in daily_stats:
        d["relative_pct"] = (d["total_seconds"] / max_day) if max_day > 0 else 0
        
    return {
        "days_count": days_count,
        "start_date": start_str,
        "end_date": end_str,
        "daily_stats": daily_stats,
        "today_duration": today_dur,
        "yesterday_duration": yesterday_dur,
        "diff_seconds": diff_seconds,
        "diff_pct": diff_pct,
        "category_comparisons": cat_comparisons,
        "empty_days_count": len(empty_days_labels),
        "empty_days_range": f"{empty_days_labels[0]}–{empty_days_labels[-1]}" if len(empty_days_labels) > 1 else (empty_days_labels[0] if empty_days_labels else "")
    }

# // Weekly Engine
def get_weekly_metrics(end_date_str: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    if end_date_str is None:
        end_dt = date.today()
    else:
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
    start_dt = end_dt - timedelta(days=6)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")
    
    sessions = get_sessions_between_dates(start_str, end_str, db_path=db_path)
    
    days_data: List[Dict[str, Any]] = []
    total_week_seconds = 0
    
    for i in range(7):
        curr_dt = start_dt + timedelta(days=i)
        curr_str = curr_dt.strftime("%Y-%m-%d")
        day_sessions = [s for s in sessions if s["date"] == curr_str]
        day_dur = sum(s["duration_seconds"] for s in day_sessions)
        total_week_seconds += day_dur
        
        days_data.append({
            "date": curr_str,
            "day_name": curr_dt.strftime("%a"),
            "display_label": curr_dt.strftime("%a (%d %b)"),
            "duration": day_dur,
            "duration_formatted": format_seconds(day_dur)
        })
        
    max_day_duration = max([d["duration"] for d in days_data]) if days_data else 1
    for d in days_data:
        d["relative_percentage"] = (d["duration"] / max_day_duration) if max_day_duration > 0 else 0
        
    return {
        "start_date": start_str,
        "end_date": end_str,
        "total_duration": total_week_seconds,
        "total_duration_formatted": format_seconds(total_week_seconds),
        "daily_average": total_week_seconds // 7,
        "daily_average_formatted": format_seconds(total_week_seconds // 7),
        "days": days_data
    }

# // Status Engine
def get_current_status_metrics(db_path: Optional[str] = None) -> Dict[str, Any]:
    today_str = date.today().strftime("%Y-%m-%d")
    daily = get_daily_metrics(today_str, db_path=db_path)
    last_sess = get_last_session(db_path=db_path)
    
    live_active_sec = 0
    cache_path = os.path.join(DEFAULT_DATA_DIR, "active_state.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                c_data = json.load(f)
                s_start = c_data.get("session_start")
                ts_str = c_data.get("timestamp")
                dur_sec = int(c_data.get("duration_seconds", 0))
                now_dt = datetime.now()
                
                if s_start:
                    start_dt = datetime.strptime(s_start, "%Y-%m-%d %H:%M:%S")
                    diff = int((now_dt - start_dt).total_seconds())
                    if ts_str:
                        ts_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        if (now_dt - ts_dt).total_seconds() <= 30:
                            live_active_sec = max(1, dur_sec, diff)
                if live_active_sec == 0:
                    live_active_sec = max(1, dur_sec)
        except Exception:
            pass
            
    if live_active_sec == 0 and last_sess:
        live_active_sec = max(1, last_sess.get("duration_seconds", 0))
            
    return {
        "today_total_seconds": daily["total_duration"],
        "today_total_formatted": daily["total_duration_formatted"],
        "last_session": last_sess,
        "live_session_seconds": live_active_sec,
        "live_session_formatted": format_seconds(live_active_sec)
    }
