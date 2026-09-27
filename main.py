# // Imports
import os
import sys
import argparse
from core.config import load_config, update_config_key
from core.database import init_db, set_custom_category, set_goal, delete_goal
from core.engine import parse_duration_string
from core.tracker import run_tracking_loop
from core.daemon import start_daemon, stop_daemon, restart_daemon
from core.doctor import run_diagnostics
from core.export import export_sessions_json, export_sessions_csv
from core.views import (
    render_today_view,
    render_report_view,
    render_review_view,
    render_projects_view,
    render_project_detail_view,
    render_week_view,
    render_trends_view,
    render_top_view,
    render_apps_tree_view,
    render_timeline_view,
    render_status_view,
    render_insights_view,
    render_goals_progress_view,
    render_goals_list_view,
    run_focus_session,
    console
)

# // Version Info
VERSION = "1.0.0"

# // Argument Parser Setup
def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="focusshell",
        description="FocusShell — Terminal Digital Activity & Focus Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Commands Overview:
  Tracking:    start, stop, restart, status, focus <duration> [project]
  Analytics:   review, today, week, trends, report, insights, progress
  Projects:    projects, project <name>, apps, top, timeline
  Management:  goal, doctor, export, config, categorize
"""
    )
    
    parser.add_argument("-v", "--version", action="version", version=f"FocusShell v{VERSION}")
    
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # // Tracking Subcommands
    subparsers.add_parser("start", help="Start the background tracking daemon")
    subparsers.add_parser("stop", help="Stop the background tracking daemon")
    subparsers.add_parser("restart", help="Restart the background tracking daemon")
    subparsers.add_parser("status", help="Show live daemon status, active window, and stats")
    
    focus_parser = subparsers.add_parser("focus", help="Start an active focus tracking session")
    focus_parser.add_argument("duration", nargs="?", default="45m", help="Target duration (e.g. 45m, 2h, 30m)")
    focus_parser.add_argument("project", nargs="?", default=None, help="Target project to focus on (optional)")

    # // Analytics Subcommands
    review_parser = subparsers.add_parser("review", help="Show structured daily review, highlights, and workflow patterns")
    review_parser.add_argument("date", nargs="?", default=None, help="Target date or alias (e.g. today, yesterday, YYYY-MM-DD)")
    review_parser.add_argument("--compact", action="store_true", help="Show compact one-liner summary")
    review_parser.add_argument("--json", action="store_true", help="Output review payload as JSON")

    report_parser = subparsers.add_parser("report", help="Show executive daily activity report")
    report_parser.add_argument("--date", help="Target date in YYYY-MM-DD format", default=None)

    today_parser = subparsers.add_parser("today", help="Show daily timeline, categories, and highlights")
    today_parser.add_argument("--date", help="Target date in YYYY-MM-DD format", default=None)
    
    insights_parser = subparsers.add_parser("insights", help="Show deep behavioral insights, patterns, and distractions breakdown")
    insights_parser.add_argument("--date", help="Target date in YYYY-MM-DD format", default=None)

    progress_parser = subparsers.add_parser("progress", help="Show visual progress toward daily goals")
    progress_parser.add_argument("--date", help="Target date in YYYY-MM-DD format", default=None)

    week_parser = subparsers.add_parser("week", help="Show 7-day activity report with daily averages")
    week_parser.add_argument("--date", help="End date in YYYY-MM-DD format", default=None)
    
    trends_parser = subparsers.add_parser("trends", help="Show multi-day usage evolution and day-over-day trends")
    trends_parser.add_argument("-d", "--days", type=int, default=14, help="Number of past days to analyze (default: 14)")


    # // Project Intelligence Subcommands
    projects_parser = subparsers.add_parser("projects", help="List all tracked projects and totals")
    projects_parser.add_argument("name", nargs="?", default=None, help="Optional project name for detailed breakdown")
    
    project_parser = subparsers.add_parser("project", help="Show detailed breakdown for a specific project")
    project_parser.add_argument("name", help="Project name to inspect")

    top_parser = subparsers.add_parser("top", help="Show top applications leaderboard")
    top_parser.add_argument("-n", "--limit", type=int, default=10, help="Number of top items to show")
    
    subparsers.add_parser("apps", help="Show hierarchical tree view of applications, projects, and window titles")
    
    timeline_parser = subparsers.add_parser("timeline", help="Show chronological timeline and workflow transitions")
    timeline_parser.add_argument("--date", help="Target date in YYYY-MM-DD format", default=None)
    
    # // Goals Subcommand
    goal_parser = subparsers.add_parser("goal", help="Set, view, or remove daily focus goals")
    goal_sub = goal_parser.add_subparsers(dest="goal_action", help="Goal action (set, list, remove)")
    
    set_goal_p = goal_sub.add_parser("set", help="Set a goal for a project, category, or total time")
    set_goal_p.add_argument("target", help="Target project or category name (e.g. FocusShell, Coding, 3h)")
    set_goal_p.add_argument("duration", nargs="?", default=None, help="Target duration (e.g. 2h, 45m)")
    set_goal_p.add_argument("--type", choices=["project", "category", "app", "total"], default="project", help="Target type")
    
    goal_sub.add_parser("list", help="List all configured goals")
    
    del_goal_p = goal_sub.add_parser("remove", help="Remove a configured goal")
    del_goal_p.add_argument("target", help="Target name to remove")

    # // Management Subcommands
    subparsers.add_parser("doctor", help="Run system diagnostics and verify all components")
    
    export_parser = subparsers.add_parser("export", help="Export session history to JSON or CSV")
    export_parser.add_argument("file", nargs="?", default=None, help="Optional output filename (e.g. today.json, report.csv)")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json", help="Export format (json or csv)")
    export_parser.add_argument("--date", help="Optional specific date in YYYY-MM-DD format", default=None)
    export_parser.add_argument("-o", "--out", help="Output file path (default: stdout)", default=None)


    cat_parser = subparsers.add_parser("categorize", help="Add or update a custom category rule")
    cat_parser.add_argument("pattern", help="Keyword or app name pattern (e.g. code, figma, blender)")
    cat_parser.add_argument("category", help="Category name (e.g. Coding, Design, Social, Gaming)")
    
    cfg_parser = subparsers.add_parser("config", help="View or update configuration settings")
    cfg_parser.add_argument("action", choices=["show", "set"], default="show", nargs="?")
    cfg_parser.add_argument("key", nargs="?", help="Configuration key")
    cfg_parser.add_argument("value", nargs="?", help="New value for configuration key")

    subparsers.add_parser("daemon-run", help=argparse.SUPPRESS)

    return parser

# // Main CLI Dispatcher
def main() -> None:
    init_db()
    parser = create_parser()
    args = parser.parse_args()

    current_script_path = os.path.abspath(__file__)

    if args.command == "start":
        success, message = start_daemon(current_script_path)
        if success:
            console.print(f"[bold green]✓[/bold green] {message}")
        else:
            console.print(f"[bold yellow]![/bold yellow] {message}")
            
    elif args.command == "stop":
        success, message = stop_daemon()
        if success:
            console.print(f"[bold green]✓[/bold green] {message}")
        else:
            console.print(f"[bold yellow]![/bold yellow] {message}")
            
    elif args.command == "restart":
        success, message = restart_daemon(current_script_path)
        if success:
            console.print(f"[bold green]✓[/bold green] {message}")
        else:
            console.print(f"[bold yellow]![/bold yellow] {message}")
            
    elif args.command == "status":
        render_status_view()
        
    elif args.command == "focus":
        run_focus_session(args.duration, args.project)
        
    elif args.command == "review":
        render_review_view(args.date, compact=args.compact, as_json=args.json)
        
    elif args.command == "report":
        render_report_view(args.date)
        
    elif args.command == "today":
        render_today_view(args.date)
        
    elif args.command == "insights":
        render_insights_view(args.date)

    elif args.command == "progress":
        render_goals_progress_view(args.date)

    elif args.command == "goal":
        if args.goal_action == "set":
            t_name = args.target
            d_str = args.duration
            if not d_str:
                d_str = t_name
                t_name = "Daily Focus"
                g_type = "total"
            else:
                g_type = args.type
            sec = parse_duration_string(d_str)
            if sec <= 0:
                console.print(f"[bold red]✗[/bold red] Invalid duration format: '{d_str}'. Use formats like 2h, 45m, 1h30m.")
            else:
                set_goal(t_name, sec, target_type=g_type)
                console.print(f"[bold green]✓[/bold green] Goal set: [bold yellow]{t_name}[/bold yellow] → [bold green]{d_str}[/bold green] ({g_type})")
        elif args.goal_action == "remove":
            deleted = delete_goal(args.target)
            if deleted:
                console.print(f"[bold green]✓[/bold green] Removed goal for '[bold yellow]{args.target}[/bold yellow]'")
            else:
                console.print(f"[bold yellow]![/bold yellow] Goal '[bold yellow]{args.target}[/bold yellow]' not found.")
        else:
            render_goals_list_view()
            
    elif args.command == "projects":
        if args.name:
            render_project_detail_view(args.name)
        else:
            render_projects_view()
            
    elif args.command == "project":
        render_project_detail_view(args.name)
        
    elif args.command == "week":
        render_week_view(args.date)
        
    elif args.command == "trends":
        render_trends_view(days_count=args.days)
        
    elif args.command == "top":
        render_top_view(limit=args.limit)
        
    elif args.command == "apps":
        render_apps_tree_view()
        
    elif args.command == "timeline":
        render_timeline_view(args.date)
        
    elif args.command == "doctor":
        run_diagnostics()
        
    elif args.command == "export":
        out_file = args.file or args.out
        if out_file and out_file.endswith(".csv"):
            fmt = "csv"
        elif out_file and out_file.endswith(".json"):
            fmt = "json"
        else:
            fmt = args.format
            
        if fmt == "csv":
            export_sessions_csv(target_date=args.date, out_file=out_file)
        else:
            export_sessions_json(target_date=args.date, out_file=out_file)
            
    elif args.command == "categorize":
        set_custom_category(args.pattern, args.category)
        console.print(f"[bold green]✓[/bold green] Rule saved: Pattern '[bold cyan]{args.pattern}[/bold cyan]' → Category '[bold magenta]{args.category}[/bold magenta]'")
        
    elif args.command == "config":
        if args.action == "set" and args.key and args.value:
            val = args.value
            if val.isdigit():
                val = int(val)
            elif val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            update_config_key(args.key, val)
            console.print(f"[bold green]✓[/bold green] Config key '[bold cyan]{args.key}[/bold cyan]' set to '[bold yellow]{val}[/bold yellow]'")
        else:
            cfg = load_config()
            console.print("\n[bold cyan]FocusShell Settings:[/bold cyan]")
            for k, v in cfg.items():
                console.print(f"  • [bold white]{k}[/bold white]: [dim cyan]{v}[/dim cyan]")
            console.print()
            
    elif args.command == "daemon-run":
        run_tracking_loop()
        
    else:
        render_today_view()

# // Main Execution
if __name__ == "__main__":
    main()

