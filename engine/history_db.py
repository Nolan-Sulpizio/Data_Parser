"""
history_db.py — Local SQLite processing history.

Stores past processing jobs so users can reference, reuse,
and build on previous configurations.
"""

import json
import os
import sqlite3
from datetime import datetime
from dataclasses import dataclass
from typing import Optional


DB_NAME = 'wesco_mro_history.db'


def _get_db_path():
    """Store DB in user's app data directory."""
    app_dir = os.path.join(os.path.expanduser('~'), '.wesco_mro_parser')
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, DB_NAME)


def _get_conn():
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            filename TEXT NOT NULL,
            instruction TEXT,
            pipeline TEXT,
            source_columns TEXT,
            target_mfg_col TEXT,
            target_pn_col TEXT,
            add_sim INTEGER DEFAULT 0,
            sim_pattern TEXT,
            total_rows INTEGER DEFAULT 0,
            mfg_filled INTEGER DEFAULT 0,
            pn_filled INTEGER DEFAULT 0,
            sim_filled INTEGER DEFAULT 0,
            issues_count INTEGER DEFAULT 0,
            output_path TEXT,
            status TEXT DEFAULT 'completed'
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS saved_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            instruction TEXT,
            pipeline TEXT,
            source_columns TEXT,
            target_mfg_col TEXT,
            target_pn_col TEXT,
            add_sim INTEGER DEFAULT 0,
            sim_pattern TEXT,
            created TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


@dataclass
class JobRecord:
    id: int = 0
    timestamp: str = ''
    filename: str = ''
    instruction: str = ''
    pipeline: str = ''
    source_columns: str = ''
    total_rows: int = 0
    mfg_filled: int = 0
    pn_filled: int = 0
    sim_filled: int = 0
    issues_count: int = 0
    output_path: str = ''
    status: str = 'completed'


def save_job(filename: str, instruction: str, pipeline: str,
             source_columns: list, target_mfg: str, target_pn: str,
             add_sim: bool, sim_pattern: str, total_rows: int,
             mfg_filled: int, pn_filled: int, sim_filled: int,
             issues_count: int, output_path: str) -> int:
    """Save a completed job to history. Returns the job ID."""
    conn = _get_conn()
    cursor = conn.execute('''
        INSERT INTO jobs (timestamp, filename, instruction, pipeline,
                         source_columns, target_mfg_col, target_pn_col,
                         add_sim, sim_pattern, total_rows, mfg_filled,
                         pn_filled, sim_filled, issues_count, output_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        filename, instruction, pipeline,
        json.dumps(source_columns), target_mfg, target_pn,
        int(add_sim), sim_pattern, total_rows,
        mfg_filled, pn_filled, sim_filled, issues_count, output_path,
    ))
    conn.commit()
    job_id = cursor.lastrowid
    conn.close()
    return job_id


def get_recent_jobs(limit: int = 20) -> list[dict]:
    """Retrieve recent processing jobs."""
    conn = _get_conn()
    rows = conn.execute(
        'SELECT * FROM jobs ORDER BY timestamp DESC LIMIT ?', (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_config(name: str, description: str, instruction: str,
                pipeline: str, source_columns: list,
                target_mfg: str, target_pn: str,
                add_sim: bool, sim_pattern: str):
    """Save a reusable configuration."""
    conn = _get_conn()
    conn.execute('''
        INSERT OR REPLACE INTO saved_configs
        (name, description, instruction, pipeline, source_columns,
         target_mfg_col, target_pn_col, add_sim, sim_pattern, created)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        name, description, instruction, pipeline,
        json.dumps(source_columns), target_mfg, target_pn,
        int(add_sim), sim_pattern, datetime.now().isoformat(),
    ))
    conn.commit()
    conn.close()


def get_saved_configs() -> list[dict]:
    """Retrieve all saved configurations."""
    conn = _get_conn()
    rows = conn.execute('SELECT * FROM saved_configs ORDER BY name').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_config(config_id: int):
    """Delete a saved configuration."""
    conn = _get_conn()
    conn.execute('DELETE FROM saved_configs WHERE id = ?', (config_id,))
    conn.commit()
    conn.close()


# Initialize on import
init_db()
