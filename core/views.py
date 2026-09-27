# // Imports
import os
import time
import json
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.text import Text
from rich.live import Live
from rich import box

from core.config import DEFAULT_DATA_DIR
from core.engine import (
    get_daily_metrics,
    get_weekly_metrics,
    get_trends_metrics,
    get_projects_summary,
    get_project_detail,
    get_current_status_metrics,
    get_insights_metrics,
    get_goals_progress,
    analyze_timeline_transitions,
    parse_duration_string,
    is_focus_category,
    format_seconds,
    format_time_range
)
from core.database import get_goals, set_goal, delete_goal
from core.daemon import get_daemon_pid
from core.tracker import get_active_window
from core.categories import categorize_window
from core.context import extract_project_context, extract_project_and_context
from core.idle import get_idle_seconds

console = Console()

# // UI Helpers
def render_bar(percentage: float, width: int = 18) -> str:
    filled_len = int(round(width * percentage))
    filled_len = max(0, min(width, filled_len))
    return "█" * filled_len + "░" * (width - filled_len)


# // Status View
def render_status_view() -> None:
    pid = get_daemon_pid()
    status_metrics = get_current_status_metrics()
    idle_secs = get_idle_seconds()
    
    cached_app = None
    cached_title = None
    cached_project = None
    
    cache_path = os.path.join(DEFAULT_DATA_DIR, "active_state.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                c_data = json.load(f)
                cached_app = c_data.get("app_name")
                cached_title = c_data.get("window_title")
                cached_project = c_data.get("project_name")
        except Exception:
            pass
            
    if pid is not None and cached_app:
        app = cached_app
        raw_title = cached_title or ""
        project = cached_project or ""
        _, clean_title = extract_project_and_context(app, raw_title)
        title = clean_title if clean_title else raw_title
        if not project:
            project = extract_project_context(app, raw_title)
    else:
        app, raw_title = get_active_window()
        if app and raw_title:
            project, title = extract_project_and_context(app, raw_title)
        else:
            project, title = "", raw_title or ""
            
    category = categorize_window(app or "", title or "") if app else "None"
    live_session_str = status_metrics.get("live_session_formatted", "0s")
    if live_session_str == "0s" and pid is not None:
        last_sess = status_metrics.get("last_session")
        if last_sess:
            live_session_str = format_seconds(max(1, last_sess.get("duration_seconds", 0)))
            
    content = Text()
    
    # // Daemon Status Row
    content.append("Tracker:  ", style="bold white")
    if pid is not None:
        content.append("● Running", style="bold green")
        content.append(f" (PID: {pid})\n", style="dim")
    else:
        content.append("○ Stopped\n", style="bold red")
        
    # // Current Application Row
    content.append("Current:  ", style="bold white")
    if app:
        content.append(f"{app}", style="bold cyan")
        content.append(f" ({category})\n", style="dim magenta")
        if project and project != "Unattributed":
            content.append("Project:  ", style="bold white")
            content.append(f"{project}\n", style="bold yellow")
        if title and title != "Unknown":
            title_disp = title if len(title) <= 55 else title[:52] + "..."
            content.append("Window:   ", style="bold white")
            content.append(f"{title_disp}\n", style="white")
    else:
        content.append("No active window detected\n", style="dim")
        
    # // Session & Today Metrics
    content.append("Session:  ", style="bold white")
    content.append(f"{live_session_str}\n", style="bold yellow")
    
    content.append("Today:    ", style="bold white")
    content.append(f"{status_metrics['today_total_formatted']}\n", style="bold green")
    
    if idle_secs > 5:
        content.append("Idle:     ", style="bold white")
        content.append(f"{int(idle_secs)}s\n", style="dim cyan")
        
    border_col = "green" if pid is not None else "red"
    console.print()
    console.print(Panel(content, title="[bold cyan]FocusShell[/bold cyan]", box=box.ROUNDED, border_style=border_col))
    console.print()

# // Daily Report View
def render_report_view(target_date: Optional[str] = None) -> None:
    metrics = get_daily_metrics(target_date)
    d_str = metrics["date"]
    
    try:
        parsed_dt = datetime.strptime(d_str, "%Y-%m-%d")
        date_heading = parsed_dt.strftime("%B %d, %Y")
    except Exception:
        date_heading = d_str
        
    header_text = f"[bold cyan]FocusShell — Daily Report[/bold cyan]\n[dim white]{date_heading}[/dim white]"
    console.print()
    console.print(Panel(header_text, box=box.ROUNDED, border_style="cyan"))
    
    if metrics["total_duration"] == 0:
        console.print("[dim yellow]No activity recorded for this day.[/dim yellow]\n")
        return
        
    # // Primary Metrics Overview
    real_projs = [p for p in metrics["projects"] if p["project_name"] != "Unattributed"]
    unattr = next((p for p in metrics["projects"] if p["project_name"] == "Unattributed"), None)
    
    console.print(f"  • [bold white]Active Time     :[/bold white] [bold green]{metrics['total_duration_formatted']}[/bold green]")
    console.print(f"  • [bold white]App Sessions    :[/bold white] [bold cyan]{metrics['sessions_count']}[/bold cyan]")
    console.print(f"  • [bold white]Projects Tracked:[/bold white] [bold yellow]{len(real_projs)}[/bold yellow]")
    if unattr:
        console.print(f"  • [bold white]Unattributed    :[/bold white] [dim]{format_seconds(unattr['total_duration'])} ({unattr['sessions_count']} records)[/dim]")
    console.print()

    # // Top Applications
    if metrics["apps"]:
        console.print("[bold white]Top Applications[/bold white]")
        for a in metrics["apps"][:4]:
            console.print(f"  [bold cyan]{a['app_name']:<18}[/bold cyan] [green]{format_seconds(a['total_duration']):>8}[/green] [dim]({a['percentage']:.0f}%)[/dim]")
        console.print()

    # // Top Projects
    if real_projs:
        console.print("[bold white]Top Projects[/bold white]")
        for p in real_projs[:4]:
            p_name = p["project_name"]
            console.print(f"  [bold yellow]{p_name:<18}[/bold yellow] [green]{format_seconds(p['total_duration']):>8}[/green] [dim]({p['sessions_count']} records)[/dim]")
        console.print()

    # // Categories Distribution
    if metrics["categories"]:
        console.print("[bold white]Categories[/bold white]")
        c_table = Table(box=None, show_header=False, pad_edge=False)
        c_table.add_column("Category", style="bold magenta", width=14)
        c_table.add_column("Bar", width=20)
        c_table.add_column("Duration", justify="right", style="bold white", width=10)
        c_table.add_column("Share", justify="right", style="dim", width=8)
        
        for c in metrics["categories"]:
            pct = c["percentage"] / 100.0
            bar = render_bar(pct, width=16)
            c_table.add_row(
                c["category"],
                f"[cyan]{bar}[/cyan]",
                format_seconds(c["total_duration"]),
                f"{c['percentage']:.1f}%"
            )
        console.print(c_table)
        console.print()

    # // Key Highlights Card
    hl = metrics["highlights"]
    console.print("[bold white]Highlights[/bold white]")
    if metrics["longest_session"]:
        ls = metrics["longest_session"]
        ctx = f"{ls['app_name']} / {ls['project']}" if ls['project'] and ls['project'] != "Unattributed" else ls['app_name']
        console.print(f"  • [dim]Longest Session :[/dim] [bold cyan]{ctx}[/bold cyan] [bold green]({ls['duration_formatted']})[/bold green]")
    if hl["most_opened"]:
        mo = hl["most_opened"]
        console.print(f"  • [dim]Most Opened App :[/dim] [bold cyan]{mo['app_name']}[/bold cyan] [dim]— {mo['sessions_count']} opens[/dim]")
    console.print()

# // Projects List View
def render_projects_view() -> None:
    projects = get_projects_summary()
    
    console.print()
    console.print(Panel(
        "[bold cyan]FocusShell[/bold cyan] [dim]—[/dim] [bold white]Projects Overview[/bold white]",
        box=box.ROUNDED,
        border_style="cyan"
    ))
    
    real_projects = [p for p in projects if p["project_name"] != "Unattributed"]
    unattr = next((p for p in projects if p["project_name"] == "Unattributed"), None)
    
    if not real_projects and not unattr:
        console.print("[dim yellow]No projects tracked yet.[/dim yellow]\n")
        return
        
    table = Table(box=box.SIMPLE_HEAD, pad_edge=False)
    table.add_column("Project", style="bold yellow", width=22)
    table.add_column("Total Time", justify="right", style="bold green", width=12)
    table.add_column("Records", justify="right", style="white", width=10)
    table.add_column("Active Days", justify="right", style="dim", width=12)
    table.add_column("Last Active", style="dim", width=18)
    
    for p in real_projects:
        table.add_row(
            p["project_name"],
            p["total_duration_formatted"],
            str(p["sessions_count"]),
            str(p["active_days_count"]),
            p["last_active"]
        )
        
    console.print(table)
    if unattr:
        console.print(f"[dim]• Unattributed Activity: [bold white]{unattr['total_duration_formatted']}[/bold white] ({unattr['sessions_count']} records, last active {unattr['last_active']})[/dim]")
    console.print("\n[dim]To inspect a project, run: [bold cyan]focusshell project <ProjectName>[/bold cyan][/dim]\n")

# // Project Detail View
def render_project_detail_view(project_name: str) -> None:
    detail = get_project_detail(project_name)
    
    if not detail:
        all_projs = get_projects_summary()
        available_names = [p["project_name"] for p in all_projs if p["project_name"] != "Unattributed"]
        
        console.print(f"\n[bold yellow]![/bold yellow] Project '[bold cyan]{project_name}[/bold cyan]' was not found.\n")
        if available_names:
            console.print("[bold white]Tracked projects:[/bold white]")
            for name in available_names[:6]:
                console.print(f"  • [bold yellow]{name}[/bold yellow]")
            console.print("\n[dim]Tip: run [bold cyan]focusshell projects[/bold cyan] to list all tracked projects.[/dim]\n")
        return
        
    console.print()
    console.print(Panel(
        f"[bold cyan]FocusShell[/bold cyan] [dim]—[/dim] [bold yellow]Project: {detail['project_name']}[/bold yellow]",
        box=box.ROUNDED,
        border_style="yellow"
    ))
    
    console.print(f"  • [bold white]Today Time    :[/bold white] [bold green]{detail.get('today_duration_formatted', '0s')}[/bold green]")
    console.print(f"  • [bold white]Total Time    :[/bold white] [bold green]{detail['total_duration_formatted']}[/bold green]")
    console.print(f"  • [bold white]Tracked Records:[/bold white] [bold cyan]{detail['sessions_count']}[/bold cyan]")
    console.print(f"  • [bold white]Longest Sess. :[/bold white] [bold magenta]{detail.get('longest_session_formatted', '0s')}[/bold magenta]")
    console.print(f"  • [bold white]Active Days   :[/bold white] [bold white]{detail['active_days_count']}[/bold white]")
    console.print()

    # // Applications Used
    if detail["applications"]:
        console.print("[bold white]Applications[/bold white]")
        for a in detail["applications"]:
            console.print(f"  [bold cyan]{a['app_name']:<18}[/bold cyan] [green]{a['duration_formatted']:>10}[/green]")
        console.print()

    # // Files & Windows
    if detail["files"]:
        console.print("[bold white]Files[/bold white]")
        for f in detail["files"][:10]:
            f_title = f["window_title"]
            if len(f_title) > 55:
                f_title = f_title[:52] + "..."
            console.print(f"  [dim]{f_title:<56}[/dim] [cyan]{f['duration_formatted']:>8}[/cyan]")
        console.print()

    # // Recent Activity History
    if detail.get("recent_activity"):
        console.print("[bold white]Recent Activity[/bold white]")
        for r in detail["recent_activity"][:8]:
            r_title = r["window_title"]
            if len(r_title) > 48:
                r_title = r_title[:45] + "..."
            console.print(f"  [dim]{r['time_display']:<14}[/dim] [bold white]{r_title:<50}[/bold white] [bold green]{r['duration_formatted']:>8}[/bold green]")
        console.print()


# // Today View
def render_today_view(target_date: Optional[str] = None) -> None:
    metrics = get_daily_metrics(target_date)
    d_str = metrics["date"]
    total_str = metrics["total_duration_formatted"]
    sessions = metrics["sessions"]
    cats = metrics["categories"]
    hl = metrics["highlights"]
    
    header = Text()
    header.append("FocusShell", style="bold cyan")
    header.append(" — ", style="dim")
    header.append(f"Today ({d_str})", style="bold white")
    if metrics["total_duration"] > 0:
        header.append(f"  •  Total: {total_str}", style="bold green")
        
    console.print()
    console.print(Panel(header, box=box.ROUNDED, border_style="cyan"))
    
    if not sessions:
        console.print("[dim yellow]No recorded activities for this date yet.[/dim yellow]")
        console.print("[dim]Start tracking with: [bold cyan]focusshell start[/bold cyan][/dim]\n")
        return

    # // Timeline Summary Table
    t_table = Table(box=box.SIMPLE_HEAD, expand=False, show_edge=False, pad_edge=False)
    t_table.add_column("Time Range", style="dim", width=22)
    t_table.add_column("Application", style="bold cyan", width=18)
    t_table.add_column("Project / Window", style="white", width=40)
    t_table.add_column("Duration", justify="right", style="bold green", width=10)
    
    for s in sessions[-12:]:
        time_range = format_time_range(s["started_at"], s["ended_at"], s["duration_seconds"])
        proj = s.get("project_context", "").strip()
        win = s["window_title"]
        display_ctx = f"[{proj}] {win}" if proj and proj != win else win
        if len(display_ctx) > 38:
            display_ctx = display_ctx[:35] + "..."
            
        t_table.add_row(
            time_range,
            s["app_name"],
            display_ctx,
            format_seconds(s["duration_seconds"])
        )
        
    console.print("[bold white]Recent Timeline[/bold white]")
    console.print(t_table)
    console.print()

    # // Category Breakdown Bars
    if cats and metrics["total_duration"] > 0:
        console.print("[bold white]Category Distribution[/bold white]")
        c_table = Table(box=None, show_header=False, pad_edge=False)
        c_table.add_column("Category", style="bold magenta", width=14)
        c_table.add_column("Bar", width=20)
        c_table.add_column("Duration", justify="right", style="bold white", width=10)
        c_table.add_column("Share", justify="right", style="dim", width=8)
        
        for c in cats:
            pct = c["percentage"] / 100.0
            bar = render_bar(pct, width=16)
            c_table.add_row(
                c["category"],
                f"[cyan]{bar}[/cyan]",
                format_seconds(c["total_duration"]),
                f"{c['percentage']:.1f}%"
            )
        console.print(c_table)
        console.print()

    # // Highlights Card
    console.print("[bold white]Highlights[/bold white]")
    if hl["top_app"]:
        top_a = hl["top_app"]
        console.print(f"  • [dim]Most Used App   :[/dim] [bold cyan]{top_a['app_name']}[/bold cyan] [dim]({format_seconds(top_a['total_duration'])})[/dim]")
    if hl["most_opened"]:
        mo = hl["most_opened"]
        console.print(f"  • [dim]Most Opened App :[/dim] [bold cyan]{mo['app_name']}[/bold cyan] [dim]— {mo['sessions_count']} opens[/dim]")
    if hl["longest_session_app"]:
        ls = hl["longest_session_app"]
        console.print(f"  • [dim]Longest Session :[/dim] [bold cyan]{ls['app_name']}[/bold cyan] [dim]— {format_seconds(ls['max_session'])}[/dim]")
    console.print()

# // Trends & Evolution View
def render_trends_view(days_count: int = 14) -> None:
    trends = get_trends_metrics(days_count)
    daily = trends["daily_stats"]
    
    console.print()
    console.print(Panel(
        f"[bold cyan]FocusShell[/bold cyan] [dim]—[/dim] [bold white]{days_count}-Day Usage Evolution & Trends ({trends['start_date']} to {trends['end_date']})[/bold white]",
        box=box.ROUNDED,
        border_style="cyan"
    ))
    
    # // Daily Trend Table
    t_table = Table(box=box.SIMPLE_HEAD, pad_edge=False)
    t_table.add_column("Date", style="bold white", width=10)
    t_table.add_column("Activity Graph", width=22)
    t_table.add_column("Total Time", justify="right", style="bold green", width=12)
    t_table.add_column("Focus Time", justify="right", style="cyan", width=14)
    t_table.add_column("Focus Ratio", justify="right", style="magenta", width=12)
    
    for d in daily:
        bar = render_bar(d["relative_pct"], width=18)
        t_table.add_row(
            d["label"],
            f"[cyan]{bar}[/cyan]",
            d["total_formatted"],
            d["focus_formatted"],
            f"{d['focus_ratio']:.0f}%" if not d["is_empty"] else "—"
        )
        
    console.print(t_table)
    
    if trends["empty_days_count"] > 0:
        console.print(f"[dim]No activity recorded for {trends['empty_days_range']}.[/dim]")
    console.print()

    # // Today vs Yesterday Comparison
    console.print("[bold white]Today vs Yesterday Comparison[/bold white]")
    comp_table = Table(box=box.SIMPLE, pad_edge=False)
    comp_table.add_column("Metric / Category", style="bold white", width=18)
    comp_table.add_column("Yesterday", justify="right", style="dim", width=12)
    comp_table.add_column("Today", justify="right", style="bold green", width=12)
    comp_table.add_column("Progress / Delta", justify="right", width=16)
    
    diff_sign = "+" if trends["diff_seconds"] >= 0 else "-"
    diff_color = "bold green" if trends["diff_seconds"] >= 0 else "bold red"
    delta_str = f"[{diff_color}]{diff_sign}{format_seconds(abs(trends['diff_seconds']))} ({trends['diff_pct']:+.1f}%)[/{diff_color}]"
    
    comp_table.add_row(
        "[bold cyan]Total Screen Time[/bold cyan]",
        format_seconds(trends["yesterday_duration"]),
        format_seconds(trends["today_duration"]),
        delta_str
    )
    
    for c in trends["category_comparisons"]:
        c_color = "green" if c["diff_seconds"] >= 0 else "red"
        c_delta = f"[{c_color}]{c['diff_formatted']}[/{c_color}]"
        comp_table.add_row(
            f"[dim]{c['category']}[/dim]",
            c["yesterday_formatted"],
            c["today_formatted"],
            c_delta
        )
        
    console.print(comp_table)
    console.print("[dim]Focus Ratio: percentage of tracked active time spent in configured focus categories (Coding, Terminal, Notes, Design).[/dim]\n")

# // Week View
def render_week_view(end_date_str: Optional[str] = None) -> None:
    metrics = get_weekly_metrics(end_date_str)
    
    console.print()
    console.print(Panel(
        f"[bold cyan]FocusShell[/bold cyan] [dim]—[/dim] [bold white]7-Day Report ({metrics['start_date']} to {metrics['end_date']})[/bold white]",
        box=box.ROUNDED,
        border_style="cyan"
    ))
    
    if metrics["total_duration"] == 0:
        console.print("[dim yellow]No recorded activities in the last 7 days.[/dim yellow]\n")
        return
        
    w_table = Table(box=box.SIMPLE_HEAD, pad_edge=False)
    w_table.add_column("Day", style="bold white", width=15)
    w_table.add_column("Distribution", width=25)
    w_table.add_column("Screen Time", justify="right", style="bold green", width=12)
    
    for d in metrics["days"]:
        bar = render_bar(d["relative_percentage"], width=22)
        w_table.add_row(
            d["display_label"],
            f"[cyan]{bar}[/cyan]",
            d["duration_formatted"]
        )
        
    console.print(w_table)
    console.print(f"\n[bold]Total Screen Time:[/bold] [bold cyan]{metrics['total_duration_formatted']}[/bold cyan] [dim]• Daily Avg: {metrics['daily_average_formatted']}[/dim]\n")

# // Top Apps View
def render_top_view(limit: int = 10) -> None:
    today_str = date.today().strftime("%Y-%m-%d")
    metrics = get_daily_metrics(today_str)
    apps = metrics["apps"]
    
    console.print()
    console.print(Panel(
        f"[bold cyan]FocusShell[/bold cyan] [dim]—[/dim] [bold white]Top Applications Leaderboard[/bold white]",
        box=box.ROUNDED,
        border_style="cyan"
    ))
    
    if not apps:
        console.print("[dim yellow]No recorded activities today.[/dim yellow]\n")
        return
        
    top_table = Table(box=box.SIMPLE_HEAD, pad_edge=False)
    top_table.add_column("#", justify="right", style="dim", width=4)
    top_table.add_column("Application", style="bold cyan", width=22)
    top_table.add_column("Category", style="magenta", width=14)
    top_table.add_column("Time Spent", justify="right", style="bold green", width=12)
    top_table.add_column("Share", justify="right", style="dim", width=8)
    top_table.add_column("Sessions", justify="right", style="white", width=10)
    
    for idx, a in enumerate(apps[:limit], start=1):
        top_table.add_row(
            str(idx),
            a["app_name"],
            a["category"],
            format_seconds(a["total_duration"]),
            f"{a['percentage']:.1f}%",
            str(a["sessions_count"])
        )
        
    console.print(top_table)
    console.print()

# // Apps & Projects Tree View
def render_apps_tree_view() -> None:
    today_str = date.today().strftime("%Y-%m-%d")
    metrics = get_daily_metrics(today_str)
    apps = metrics["apps"]
    
    console.print()
    console.print(Panel(
        f"[bold cyan]FocusShell[/bold cyan] [dim]—[/dim] [bold white]Applications & Project Hierarchy Breakdown[/bold white]",
        box=box.ROUNDED,
        border_style="cyan"
    ))
    
    if not apps:
        console.print("[dim yellow]No recorded activities today.[/dim yellow]\n")
        return
        
    root_tree = Tree("[bold cyan]FocusShell Activity[/bold cyan]")
    
    for a in apps:
        app_branch = root_tree.add(
            f"[bold white]{a['app_name']}[/bold white] [dim]({a['category']})[/dim] [bold green]{format_seconds(a['total_duration'])}[/bold green]"
        )
        
        for proj in a["projects_list"]:
            p_name = proj["name"]
            p_dur = format_seconds(proj["duration"])
            
            if p_name and p_name != "Unattributed":
                proj_branch = app_branch.add(f"[bold yellow]{p_name}[/bold yellow] [bold green]{p_dur}[/bold green]")
                for f in proj["files"][:8]:
                    f_title = f["title"].strip()
                    if f_title == p_name or f_title == f"GitHub: {p_name}":
                        continue
                    if len(f_title) > 55:
                        f_title = f_title[:52] + "..."
                    proj_branch.add(f"[dim]{f_title}[/dim] [cyan]{format_seconds(f['duration'])}[/cyan]")
            else:
                for f in proj["files"][:8]:
                    f_title = f["title"].strip()
                    if len(f_title) > 55:
                        f_title = f_title[:52] + "..."
                    app_branch.add(f"[dim]{f_title}[/dim] [cyan]{format_seconds(f['duration'])}[/cyan]")
                    
    console.print(root_tree)
    console.print()

# // Timeline Full View
def render_timeline_view(target_date: Optional[str] = None) -> None:
    metrics = get_daily_metrics(target_date)
    raw_sessions = metrics["sessions"]
    
    console.print()
    console.print(Panel(
        f"[bold cyan]FocusShell[/bold cyan] [dim]—[/dim] [bold white]Chronological Timeline & Transitions ({metrics['date']})[/bold white]",
        box=box.ROUNDED,
        border_style="cyan"
    ))
    
    if not raw_sessions:
        console.print("[dim yellow]No recorded activities for this date.[/dim yellow]\n")
        return
        
    sessions = analyze_timeline_transitions(raw_sessions)
    
    table = Table(box=box.SIMPLE_HEAD, pad_edge=False)
    table.add_column("Time Range", style="dim", width=22)
    table.add_column("App / Project", style="bold cyan", width=24)
    table.add_column("Context / File", style="white", width=34)
    table.add_column("Duration", justify="right", style="bold green", width=10)
    table.add_column("End Reason / Switch", style="dim magenta", width=22)
    
    for s in sessions:
        time_range = format_time_range(s["started_at"], s["ended_at"], s["duration_seconds"])
        t_str = s["window_title"]
        if len(t_str) > 32:
            t_str = t_str[:29] + "..."
            
        p_str = s.get("project_context", "").strip()
        app_name = s["app_name"]
        if p_str and p_str != "Unattributed":
            app_proj = f"[bold yellow]{p_str}[/bold yellow] [dim]({app_name})[/dim]"
        else:
            app_proj = f"[bold cyan]{app_name}[/bold cyan]"
            
        table.add_row(
            time_range,
            app_proj,
            t_str,
            format_seconds(s["duration_seconds"]),
            s.get("transition_cause", "")
        )
        
    console.print(table)
    console.print()

    # // Transition Flow Strip
    flow_items = []
    prev_item = None
    for s in sessions:
        p_str = s.get("project_context", "").strip()
        item = p_str if p_str and p_str != "Unattributed" else s["app_name"]
        if item != prev_item:
            flow_items.append(item)
            prev_item = item
            
    if flow_items:
        console.print("[bold white]Workflow Transitions Flow:[/bold white]")
        formatted_nodes = []
        for x in flow_items[-8:]:
            if x in ("FocusShell", "LogMorph"):
                formatted_nodes.append(f"[bold yellow]{x}[/bold yellow]")
            else:
                formatted_nodes.append(f"[bold cyan]{x}[/bold cyan]")
        flow_str = " [dim]→[/dim] ".join(formatted_nodes)
        console.print(f"  {flow_str}\n")

# // Insights View
def render_insights_view(target_date: Optional[str] = None) -> None:
    insights = get_insights_metrics(target_date)
    d_str = insights["date"]
    
    console.print()
    console.print(Panel(
        f"[bold cyan]FocusShell[/bold cyan] [dim]—[/dim] [bold white]Today's Insights & Behavioral Patterns ({d_str})[/bold white]",
        box=box.ROUNDED,
        border_style="cyan"
    ))
    
    if insights["total_duration"] == 0:
        console.print("[dim yellow]No recorded activities for this date yet.[/dim yellow]\n")
        return
        
    # // Focus Projects Breakdown
    if insights["projects"]:
        console.print("[bold white]Focus Projects[/bold white]")
        for p in insights["projects"]:
            console.print(f"  [bold yellow]{p['project_name']}[/bold yellow]")
            console.print(f"    [dim]• Total Time       :[/dim] [bold green]{p['total_duration_formatted']}[/bold green]")
            console.print(f"    [dim]• Longest Session  :[/dim] [cyan]{p['longest_session_formatted']}[/cyan]")
            console.print(f"    [dim]• Context Switches :[/dim] [white]{p['context_switches']}[/white]")
        console.print()

    # // Distractions Breakdown
    if insights["distractions"]:
        console.print("[bold white]Distractions & Browsing[/bold white]")
        for d in insights["distractions"]:
            console.print(f"  [dim cyan]{d['name']:<20}[/dim cyan] [yellow]{d['duration_formatted']:>10}[/yellow]")
        console.print(f"  [dim]• Total Distraction Time: [bold yellow]{insights['total_distractions_formatted']}[/bold yellow][/dim]\n")

    # // Patterns Summary
    pats = insights["patterns"]
    console.print("[bold white]Patterns[/bold white]")
    console.print(f"  • [dim]Most Active Window       :[/dim] [bold cyan]{pats['most_active_hour']}[/bold cyan] [dim]({pats['most_active_hour_duration']} active)[/dim]")
    if pats["longest_uninterrupted"]:
        lu = pats["longest_uninterrupted"]
        lu_desc = f"{lu['app_name']}"
        if lu['project'] and lu['project'] != "Unattributed":
            lu_desc += f" / {lu['project']}"
        console.print(f"  • [dim]Longest Uninterrupted Work:[/dim] [bold green]{lu['duration_formatted']}[/bold green] [dim]({lu_desc})[/dim]")
    console.print(f"  • [dim]Context / Task Switches  :[/dim] [bold magenta]{pats['context_switches_count']}[/bold magenta]")
    console.print(f"  • [dim]Application Switches     :[/dim] [bold cyan]{pats.get('app_switches_count', 0)}[/bold cyan]")
    console.print()

# // Goals Progress View
def render_goals_progress_view(target_date: Optional[str] = None) -> None:
    goals_prog = get_goals_progress(target_date)
    
    console.print()
    console.print(Panel(
        "[bold cyan]FocusShell[/bold cyan] [dim]—[/dim] [bold white]Goals & Target Progress[/bold white]",
        box=box.ROUNDED,
        border_style="cyan"
    ))
    
    if not goals_prog:
        console.print("[dim yellow]No active goals defined yet.[/dim yellow]")
        console.print("[dim]Set a goal with: [bold cyan]focusshell goal set <TargetName> <Duration>[/bold cyan][/dim]")
        console.print("[dim]Example: [bold cyan]focusshell goal set FocusShell 2h[/bold cyan]\n[/dim]")
        return
        
    for g in goals_prog:
        bar = render_bar(g["percentage"] / 100.0, width=22)
        bar_color = "green" if g["is_completed"] else "cyan"
        
        console.print(f"[bold yellow]{g['target_name']}[/bold yellow] [dim]({g['target_type']})[/dim]")
        console.print(f"  [{bar_color}]{bar}[/{bar_color}]  [bold white]{g['achieved_formatted']} / {g['target_formatted']}[/bold white] [dim]({g['percentage']:.0f}%)[/dim]")
        
        if g["is_completed"]:
            console.print("  [bold green]✓ Target completed for today![/bold green]")
        else:
            console.print(f"  [dim]Today: [bold green]{g['achieved_formatted']}[/bold green]  •  Remaining: [bold cyan]{g['remaining_formatted']}[/bold cyan][/dim]")
        console.print()

def render_goals_list_view() -> None:
    goals = get_goals()
    console.print()
    console.print(Panel(
        "[bold cyan]FocusShell[/bold cyan] [dim]—[/dim] [bold white]Configured Goals[/bold white]",
        box=box.ROUNDED,
        border_style="cyan"
    ))
    if not goals:
        console.print("[dim yellow]No goals configured yet.[/dim yellow]")
        console.print("[dim]Set a goal using: [bold cyan]focusshell goal set <target> <duration>[/bold cyan]\n[/dim]")
        return
        
    table = Table(box=box.SIMPLE_HEAD, pad_edge=False)
    table.add_column("Target Name", style="bold yellow", width=20)
    table.add_column("Type", style="dim", width=12)
    table.add_column("Target Duration", justify="right", style="bold green", width=16)
    table.add_column("Created At", style="dim", width=20)
    
    for g in goals:
        table.add_row(
            g["target_name"],
            g["target_type"],
            format_seconds(g["target_seconds"]),
            g["created_at"]
        )
    console.print(table)
    console.print()

# // Focus Session Runner
def run_focus_session(duration_str: str, target_project: Optional[str] = None) -> None:
    target_seconds = parse_duration_string(duration_str)
    if target_seconds <= 0:
        target_seconds = 25 * 60
        
    target_formatted = format_seconds(target_seconds)
    proj_desc = f" on [bold yellow]{target_project}[/bold yellow]" if target_project else ""
    
    console.print()
    console.print(Panel(
        f"[bold cyan]FocusShell[/bold cyan] [dim]—[/dim] [bold white]Focus Session ({target_formatted}){proj_desc}[/bold white]\n"
        f"[dim]Tracking active apps, interruptions, and focus ratio in real time. Press Ctrl+C to conclude early.[/dim]",
        box=box.ROUNDED,
        border_style="cyan"
    ))
    
    elapsed = 0
    focused_seconds = 0
    distracted_seconds = 0
    idle_seconds_total = 0
    interruptions_count = 0
    apps_used: Dict[str, int] = {}
    
    prev_was_focus = True
    
    try:
        with Live(console=console, refresh_per_second=2, auto_refresh=True) as live:
            while elapsed < target_seconds:
                time.sleep(1)
                elapsed += 1
                
                app, raw_title = get_active_window()
                curr_app = app or "Desktop / Idle"
                proj, clean_title = extract_project_and_context(curr_app, raw_title or "")
                idle_sec = get_idle_seconds()
                cat = categorize_window(curr_app, clean_title)
                
                if idle_sec >= 120:
                    idle_seconds_total += 1
                    is_current_focus = False
                elif target_project:
                    clean_t_proj = target_project.strip().lower()
                    if proj and proj.lower() == clean_t_proj:
                        is_current_focus = True
                    elif is_focus_category(cat) and (not proj or proj == "Unattributed" or proj.lower() == clean_t_proj):
                        is_current_focus = True
                    else:
                        is_current_focus = False
                else:
                    is_current_focus = is_focus_category(cat)
                    
                if is_current_focus:
                    focused_seconds += 1
                    prev_was_focus = True
                else:
                    distracted_seconds += 1
                    if prev_was_focus:
                        interruptions_count += 1
                        prev_was_focus = False
                        
                apps_used[curr_app] = apps_used.get(curr_app, 0) + 1
                
                pct = (elapsed / target_seconds)
                bar = render_bar(pct, width=24)
                rem_sec = max(0, target_seconds - elapsed)
                
                status_text = Text()
                status_text.append("Progress:     ", style="bold white")
                status_text.append(f"{bar} ", style="bold green")
                status_text.append(f"{format_seconds(elapsed)} / {target_formatted} ({pct * 100:.0f}%)\n", style="bold white")
                
                status_text.append("Remaining:    ", style="bold white")
                status_text.append(f"{format_seconds(rem_sec)}\n", style="bold cyan")
                
                status_text.append("Active App:   ", style="bold white")
                app_style = "bold green" if is_current_focus else "bold yellow"
                status_text.append(f"{curr_app}", style=app_style)
                if proj and proj != "Unattributed":
                    status_text.append(f" [{proj}]", style="bold yellow")
                status_text.append("\n")
                
                status_text.append("Focused Time: ", style="bold white")
                focus_pct = (focused_seconds / elapsed * 100) if elapsed > 0 else 100
                status_text.append(f"{format_seconds(focused_seconds)} ({focus_pct:.0f}%)\n", style="bold green")
                
                status_text.append("Interruptions: ", style="bold white")
                status_text.append(f"{interruptions_count}\n", style="bold magenta" if interruptions_count > 0 else "dim")
                
                live.update(Panel(status_text, box=box.ROUNDED, border_style="green" if is_current_focus else "yellow", title="Live Focus Session Tracker"))
    except KeyboardInterrupt:
        console.print("\n[dim]Focus session ended early by user.[/dim]")
        
    # // Summary Card
    console.print()
    console.print(Panel(
        "[bold cyan]FocusShell[/bold cyan] [dim]—[/dim] [bold white]Focus Session Summary[/bold white]",
        box=box.ROUNDED,
        border_style="green"
    ))
    
    total_time_str = format_seconds(elapsed)
    focus_time_str = format_seconds(focused_seconds)
    focus_ratio = (focused_seconds / elapsed * 100) if elapsed > 0 else 0
    
    console.print(f"  • [bold white]Target Duration   :[/bold white] [bold cyan]{target_formatted}[/bold cyan]")
    console.print(f"  • [bold white]Actual Session Time:[/bold white] [bold white]{total_time_str}[/bold white]")
    console.print(f"  • [bold white]Focused Work Time :[/bold white] [bold green]{focus_time_str}[/bold green] [dim]({focus_ratio:.0f}% focus ratio)[/dim]")
    console.print(f"  • [bold white]Idle / Break Time :[/bold white] [bold yellow]{format_seconds(idle_seconds_total)}[/bold yellow]")
    console.print(f"  • [bold white]Interruptions     :[/bold white] [bold magenta]{interruptions_count}[/bold magenta]")
    console.print()
    
    if apps_used:
        console.print("[bold white]Applications Used During Session[/bold white]")
        sorted_apps = sorted(apps_used.items(), key=lambda x: x[1], reverse=True)
        for app_name, sec in sorted_apps:
            console.print(f"  [bold cyan]{app_name:<24}[/bold cyan] [green]{format_seconds(sec):>10}[/green]")
        console.print()

# // Daily Review View
def render_review_view(target_date: Optional[str] = None, compact: bool = False, as_json: bool = False) -> None:
    from core.review import build_daily_review
    review = build_daily_review(target_date)
    
    if as_json:
        import sys
        sys.stdout.write(json.dumps(review, indent=2, ensure_ascii=False) + "\n")
        return
        
    if compact:
        if review["is_empty"]:
            console.print(f"[dim]{review['short_date']} • No activity recorded.[/dim]")
            return
            
        ov = review["overview"]
        mp = review.get("main_project")
        mp_str = f"{mp['name']} {mp['duration_formatted']}" if mp else "No main project"
        longest_str = ov["longest_session_formatted"]
        
        top_apps = review.get("top_applications", [])
        top_str = " • ".join([f"{a['name']} {a['duration_formatted']}" for a in top_apps[:2]])
        
        pats = review["patterns"]
        
        console.print(f"[bold cyan]{review['short_date']}[/bold cyan] [dim]•[/dim] [bold green]{ov['active_time_formatted']} active[/bold green] [dim]•[/dim] [bold yellow]{mp_str}[/bold yellow] [dim]•[/dim] Longest {longest_str}")
        if top_str:
            console.print(f"[dim]Top:[/dim] {top_str}")
        console.print(f"[dim]Switches:[/dim] {pats['application_switches']} app / {pats['context_switches']} context\n")
        return
        
    console.print()
    header_text = Text()
    header_text.append("FocusShell", style="bold cyan")
    header_text.append(" — ", style="dim")
    header_text.append("Daily Review\n", style="bold white")
    header_text.append(f"{review['display_date']}", style="dim")
    
    console.print(Panel(header_text, box=box.ROUNDED, border_style="cyan"))
    
    if review["is_empty"]:
        console.print("[dim yellow]No computer activity recorded for this date.[/dim yellow]\n")
        return
        
    ov = review["overview"]
    attr = review.get("project_attribution", {})
    
    # // Overview Section
    console.print("[bold white]Overview[/bold white]")
    console.print(f"  [dim]Active Time            :[/dim] [bold green]{ov['active_time_formatted']:>10}[/bold green]")
    console.print(f"  [dim]Project Time           :[/dim] [bold yellow]{ov['project_time_formatted']:>10}[/bold yellow]")
    console.print(f"  [dim]Unattributed Time      :[/dim] [dim white]{ov['unattributed_time_formatted']:>10}[/dim white]")
    console.print(f"  [dim]Longest Session        :[/dim] [bold magenta]{ov['longest_session_formatted']:>10}[/bold magenta]")
    console.print()

    # // Project Attribution Section
    if attr:
        console.print("[bold white]Project Attribution[/bold white]")
        console.print(f"  [dim]Tracked Projects       :[/dim] [bold yellow]{attr['tracked_projects_formatted']:>10}[/bold yellow] [dim]({attr['tracked_projects_pct']:.0f}%)[/dim]")
        console.print(f"  [dim]Unattributed           :[/dim] [dim white]{attr['unattributed_formatted']:>10}[/dim white] [dim]({attr['unattributed_pct']:.0f}%)[/dim]")
        console.print()

    # // Main Project Section
    if review.get("main_project"):
        mp = review["main_project"]
        console.print("[bold white]Main Project[/bold white]")
        console.print(f"  [bold yellow]{mp['name']:<22}[/bold yellow] [green]{mp['duration_formatted']:>10}[/green]\n")

    # // Top Applications Section
    if review.get("top_applications"):
        console.print("[bold white]Top Applications[/bold white]")
        for a in review["top_applications"]:
            console.print(f"  [bold cyan]{a['name']:<22}[/bold cyan] [green]{a['duration_formatted']:>10}[/green]")
        console.print()

    # // Activity Mix Section
    if review.get("activity_mix"):
        console.print("[bold white]Activity Mix[/bold white]")
        for c in review["activity_mix"]:
            console.print(f"  [dim magenta]{c['category']:<22}[/dim magenta] [green]{c['duration_formatted']:>10}[/green]")
        console.print()

    # // Work Patterns Section
    pats = review["patterns"]
    console.print("[bold white]Work Patterns[/bold white]")
    console.print(f"  [dim]Most Active Window     :[/dim] [bold cyan]{pats['most_active_window']}[/bold cyan]")
    console.print(f"  [dim]Longest Uninterrupted  :[/dim] [bold green]{pats['longest_uninterrupted']}[/bold green]")
    console.print(f"  [dim]Application Switches   :[/dim] [white]{pats['application_switches']}[/white]")
    console.print(f"  [dim]Context Transitions    :[/dim] [white]{pats['context_switches']}[/white]")
    console.print()

    # // Activity Flow
    if review.get("activity_flow"):
        console.print("[bold white]Activity Flow[/bold white]")
        flow_str = " [dim]→[/dim] ".join([f"[bold yellow]{x}[/bold yellow]" if x in ("FocusShell", "LogMorph") else f"[bold cyan]{x}[/bold cyan]" for x in review["activity_flow"]])
        console.print(f"  {flow_str}\n")

    # // Factual Highlights
    if review.get("highlights"):
        console.print("[bold white]Highlights[/bold white]")
        for hl in review["highlights"]:
            console.print(f"  • [white]{hl}[/white]")
        console.print()



