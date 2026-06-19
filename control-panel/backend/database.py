import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
DB_PATH = DATA_DIR / 'control_panel.db'

DEFAULT_SETTINGS = {
    'app_name': 'Red Team Control Panel',
    'default_target': 'https://lto.gov.ph',
    'tools_bin': '../decepticon-tools/bin',
    'wordpress_tool_dir': '../wordpress-tool',
    'bruter_threads': '30',
    'ato_spray_enabled': 'false',
    'ato_spray_limit': '100',
    'nuclei_severity': 'critical,high,medium',
    'scan_timeout_seconds': '600',
    'custom_openai_api_base': '',
    'custom_openai_api_key': '',
    'custom_openai_model': 'gpt-4o-mini',
    'decepticon_profile': 'eco',
    'allowed_engagement_domains': 'lto.gov.ph,sc.judiciary.gov.ph',
    'max_parallel_jobs': '2',
    'log_retention_days': '30',
    'notifications_webhook': '',
    'theme_accent': '#6366f1',
}

SENSITIVE_KEYS = {'custom_openai_api_key'}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TEXT NOT NULL,
                updated_by INTEGER
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                tool TEXT NOT NULL,
                target TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                pid INTEGER,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                exit_code INTEGER,
                output_path TEXT,
                log_tail TEXT,
                created_by INTEGER
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                resource TEXT,
                details TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS engagements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                target_url TEXT NOT NULL,
                notes TEXT,
                status TEXT DEFAULT 'active',
                created_by INTEGER,
                created_at TEXT NOT NULL
            );
            """
        )
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                'INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)',
                (key, value, _now()),
            )


def get_all_settings(mask_secrets: bool = True) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            'SELECT key, value, description, updated_at, updated_by FROM settings ORDER BY key'
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        if mask_secrets and item['key'] in SENSITIVE_KEYS and item['value']:
            item['value'] = '••••••••'
            item['masked'] = True
        result.append(item)
    return result


def get_all_settings_dict() -> dict[str, str]:
    with get_db() as conn:
        rows = conn.execute('SELECT key, value FROM settings').fetchall()
    return {r['key']: r['value'] for r in rows}


def get_setting(key: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            'SELECT key, value, description, updated_at, updated_by FROM settings WHERE key=?',
            (key,),
        ).fetchone()
    return dict(row) if row else None


def set_setting(
    key: str,
    value: str,
    description: str | None = None,
    updated_by: int | None = None,
) -> None:
    now = _now()
    with get_db() as conn:
        if description is not None:
            conn.execute(
                'INSERT INTO settings (key, value, description, updated_at, updated_by) VALUES (?, ?, ?, ?, ?) '
                'ON CONFLICT(key) DO UPDATE SET value=excluded.value, description=excluded.description, '
                'updated_at=excluded.updated_at, updated_by=excluded.updated_by',
                (key, value, description, now, updated_by),
            )
        else:
            conn.execute(
                'INSERT INTO settings (key, value, updated_at, updated_by) VALUES (?, ?, ?, ?) '
                'ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at, '
                'updated_by=excluded.updated_by',
                (key, value, now, updated_by),
            )


def log_audit(
    user_id: int | None,
    action: str,
    resource: str = '',
    details: str = '',
) -> None:
    with get_db() as conn:
        conn.execute(
            'INSERT INTO audit_log (user_id, action, resource, details, created_at) VALUES (?, ?, ?, ?, ?)',
            (user_id, action, resource, details, _now()),
        )


def get_user_by_username(username: str):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    return dict(row) if row else None


def create_user(username: str, password_hash: str, role: str = 'viewer') -> int:
    with get_db() as conn:
        cur = conn.execute(
            'INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)',
            (username, password_hash, role, _now()),
        )
        return cur.lastrowid


def update_user_password(user_id: int, password_hash: str) -> None:
    with get_db() as conn:
        conn.execute('UPDATE users SET password_hash=? WHERE id=?', (password_hash, user_id))


def list_users() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute('SELECT id, username, role, created_at FROM users').fetchall()
    return [dict(r) for r in rows]


def create_job_record(name: str, tool: str, target: str, created_by: int) -> int:
    with get_db() as conn:
        cur = conn.execute(
            'INSERT INTO jobs (name, tool, target, status, created_at, created_by) VALUES (?, ?, ?, ?, ?, ?)',
            (name, tool, target, 'queued', _now(), created_by),
        )
        return cur.lastrowid


def update_job(job_id: int, **fields) -> None:
    if not fields:
        return
    with get_db() as conn:
        sets = ', '.join(f'{k}=?' for k in fields)
        conn.execute(f'UPDATE jobs SET {sets} WHERE id=?', [*fields.values(), job_id])


def get_job(job_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
    return dict(row) if row else None


def list_jobs(limit: int = 50) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM jobs ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
    return [dict(r) for r in rows]


def list_running_jobs() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status IN ('queued', 'running') ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def append_job_log(job_id: int, text: str) -> None:
    with get_db() as conn:
        row = conn.execute('SELECT log_tail FROM jobs WHERE id=?', (job_id,)).fetchone()
        tail = (row['log_tail'] or '') + text
        if len(tail) > 50000:
            tail = tail[-50000:]
        conn.execute('UPDATE jobs SET log_tail=? WHERE id=?', (tail, job_id))


def get_audit_log(limit: int = 100) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT a.*, u.username
            FROM audit_log a
            LEFT JOIN users u ON u.id = a.user_id
            ORDER BY a.id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_dashboard_stats() -> dict:
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) c FROM jobs').fetchone()['c']
        running = conn.execute("SELECT COUNT(*) c FROM jobs WHERE status='running'").fetchone()['c']
        queued = conn.execute("SELECT COUNT(*) c FROM jobs WHERE status='queued'").fetchone()['c']
        success = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE status='completed' AND exit_code=0"
        ).fetchone()['c']
        failed = conn.execute(
            "SELECT COUNT(*) c FROM jobs WHERE status='failed' OR (status='completed' AND exit_code!=0)"
        ).fetchone()['c']
        engagements = conn.execute('SELECT COUNT(*) c FROM engagements').fetchone()['c']
        recent = conn.execute(
            'SELECT id, name, tool, status, created_at FROM jobs ORDER BY id DESC LIMIT 5'
        ).fetchall()
    return {
        'total_jobs': total,
        'running': running,
        'queued': queued,
        'success': success,
        'failed': failed,
        'engagements': engagements,
        'recent_jobs': [dict(r) for r in recent],
    }


def list_engagements() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM engagements ORDER BY id DESC').fetchall()
    return [dict(r) for r in rows]


def create_engagement(name: str, target_url: str, notes: str, created_by: int) -> int:
    with get_db() as conn:
        cur = conn.execute(
            'INSERT INTO engagements (name, target_url, notes, created_by, created_at) VALUES (?, ?, ?, ?, ?)',
            (name, target_url, notes, created_by, _now()),
        )
        return cur.lastrowid


def delete_engagement(engagement_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute('DELETE FROM engagements WHERE id=?', (engagement_id,))
        return cur.rowcount > 0
