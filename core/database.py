# // Imports
import os
import sqlite3
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from core.config import load_config
from core.naming import normalize_app_name

# // Database Connection
def get_db_path() -> str:
    cfg = load_config()
    return cfg.get("db_path", os.path.expanduser("~/.local/share/focusshell/focus.db"))

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

# // Schema Initialization & Migrations
def init_db(db_path: Optional[str] = None) -> None:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                window_title TEXT NOT NULL,
                project_context TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL CHECK (duration_seconds >= 0),
                date TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT UNIQUE NOT NULL,
                category_name TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_name TEXT UNIQUE NOT NULL,
                target_type TEXT NOT NULL DEFAULT 'project',
                target_seconds INTEGER NOT NULL CHECK (target_seconds > 0),
                created_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "project_context" not in columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN project_context TEXT NOT NULL DEFAULT ''")
            
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions (date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_app ON sessions (app_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_category ON sessions (category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions (project_context);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions (started_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_goals_target ON goals (target_name);")
        
        conn.commit()
    finally:
        conn.close()

# // Session Lifecycle Management
def create_session(
    app_name: str,
    window_title: str,
    category: str,
    started_at: datetime,
    project_context: str = "",
    db_path: Optional[str] = None
) -> int:
    clean_app = normalize_app_name(app_name)
    clean_title = window_title.strip() if window_title and window_title.strip() else "Unknown"
    clean_cat = category.strip() if category and category.strip() else "Other"
    
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        date_str = started_at.strftime("%Y-%m-%d")
        start_str = started_at.strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO sessions (
                app_name, window_title, project_context, category, started_at, ended_at, duration_seconds, date
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """, (clean_app, clean_title, project_context, clean_cat, start_str, start_str, date_str))
        
        session_id = cursor.lastrowid
        conn.commit()
        return session_id
    finally:
        conn.close()

def update_session(
    session_id: int,
    ended_at: datetime,
    duration_seconds: int,
    db_path: Optional[str] = None
) -> None:
    safe_duration = max(0, duration_seconds)
    end_str = ended_at.strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions 
            SET ended_at = ?, duration_seconds = ?
            WHERE id = ?
        """, (end_str, safe_duration, session_id))
        conn.commit()
    finally:
        conn.close()

def close_session(
    session_id: int,
    ended_at: datetime,
    duration_seconds: int,
    min_duration: int = 1,
    db_path: Optional[str] = None
) -> None:
    safe_duration = max(0, duration_seconds)
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        if safe_duration < min_duration:
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        else:
            end_str = ended_at.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                UPDATE sessions 
                SET ended_at = ?, duration_seconds = ?
                WHERE id = ?
            """, (end_str, safe_duration, session_id))
        conn.commit()
    finally:
        conn.close()

# // Crash Recovery & Stale Session Sealer
def recover_stale_sessions(db_path: Optional[str] = None) -> int:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, started_at, ended_at, duration_seconds 
            FROM sessions 
            WHERE duration_seconds <= 0
        """)
        stale_empty = cursor.fetchall()
        for row in stale_empty:
            cursor.execute("DELETE FROM sessions WHERE id = ?", (row["id"],))
            
        cursor.execute("""
            SELECT id, started_at, ended_at, duration_seconds 
            FROM sessions 
            ORDER BY id DESC LIMIT 5
        """)
        recent = cursor.fetchall()
        recovered_count = len(stale_empty)
        
        for row in recent:
            try:
                s_dt = datetime.strptime(row["started_at"], "%Y-%m-%d %H:%M:%S")
                e_dt = datetime.strptime(row["ended_at"], "%Y-%m-%d %H:%M:%S")
                diff = int((e_dt - s_dt).total_seconds())
                if diff < 0:
                    cursor.execute("""
                        UPDATE sessions SET ended_at = started_at, duration_seconds = 0 WHERE id = ?
                    """, (row["id"],))
                    recovered_count += 1
            except Exception:
                pass
                
        conn.commit()
        return recovered_count
    finally:
        conn.close()

# // Query Functions
def get_sessions_for_date(target_date: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sessions 
            WHERE date = ? AND duration_seconds > 0
            ORDER BY started_at ASC
        """, (target_date,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_sessions_between_dates(start_date: str, end_date: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sessions 
            WHERE date >= ? AND date <= ? AND duration_seconds > 0
            ORDER BY started_at ASC
        """, (start_date, end_date))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_all_sessions(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sessions 
            WHERE duration_seconds > 0
            ORDER BY started_at ASC
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_last_session(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sessions 
            ORDER BY id DESC LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# // Custom Categories
def get_custom_categories(db_path: Optional[str] = None) -> Dict[str, str]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT pattern, category_name FROM categories")
        rows = cursor.fetchall()
        return {row["pattern"].lower(): row["category_name"] for row in rows}
    finally:
        conn.close()

def set_custom_category(pattern: str, category_name: str, db_path: Optional[str] = None) -> None:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO categories (pattern, category_name)
            VALUES (?, ?)
            ON CONFLICT(pattern) DO UPDATE SET category_name = excluded.category_name
        """, (pattern.lower(), category_name))
        conn.commit()
    finally:
        conn.close()

# // Goals Storage
def set_goal(target_name: str, target_seconds: int, target_type: str = "project", db_path: Optional[str] = None) -> None:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO goals (target_name, target_type, target_seconds, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(target_name) DO UPDATE SET target_type = excluded.target_type, target_seconds = excluded.target_seconds
        """, (target_name.strip(), target_type.strip().lower(), target_seconds, now_str))
        conn.commit()
    finally:
        conn.close()

def get_goals(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM goals ORDER BY id ASC")
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_goal_by_target(target_name: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM goals WHERE LOWER(target_name) = LOWER(?)", (target_name.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def delete_goal(target_name: str, db_path: Optional[str] = None) -> bool:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM goals WHERE LOWER(target_name) = LOWER(?)", (target_name.strip(),))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()

