
import sqlite3
import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
from contextlib import contextmanager

from utils.logger import setup_logger

logger = setup_logger(__name__)

class DatabaseManager:
    """
    Manages SQLite database for Crawler V2.0.
    Handles persistence of tasks and resources.
    """
    
    def __init__(self, db_path: str = "crawler_data.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                logger.exception("Failed to close sqlite connection")

    def _init_db(self):
        """Initialize database schema and enable WAL."""
        create_tasks_table = """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            total_items INTEGER DEFAULT 0,
            downloaded_items INTEGER DEFAULT 0,
            save_path TEXT
        );
        """
        
        create_resources_table = """
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            url TEXT NOT NULL,
            resource_type TEXT,
            filename TEXT,
            local_path TEXT,
            file_size INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            error_msg TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        );
        """
        
        try:
            with self._get_connection() as conn:
                # Enable Write-Ahead Logging for concurrency
                conn.execute("PRAGMA journal_mode=WAL;")
                
                # Integrity Check on startup
                try:
                    integrity = conn.execute("PRAGMA integrity_check;").fetchone()[0]
                    if integrity != 'ok':
                        logger.critical(f"Database integrity check failed: {integrity}")
                    else:
                        logger.info("Database integrity check passed")
                except Exception as e:
                    logger.error(f"Failed to check DB integrity: {e}")

                conn.execute(create_tasks_table)
                conn.execute(create_resources_table)
                conn.commit()
            logger.info(f"Database initialized at {self.db_path} (WAL enabled)")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def create_task(self, source_url: str, save_path: str) -> int:
        """Create a new crawl task and return its ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO tasks (source_url, status, save_path, created_at) VALUES (?, ?, ?, ?)",
                    (source_url, 'running', save_path, datetime.datetime.now())
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return -1

    def update_task_status(self, task_id: int, status: str, finished: bool = False):
        """Update task status."""
        try:
            with self._get_connection() as conn:
                if finished:
                    conn.execute(
                        "UPDATE tasks SET status = ?, finished_at = ? WHERE id = ?",
                        (status, datetime.datetime.now(), task_id)
                    )
                else:
                    conn.execute(
                        "UPDATE tasks SET status = ? WHERE id = ?",
                        (status, task_id)
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")

    def update_task_progress(self, task_id: int, downloaded: int, total: int):
        """Update task progress counters."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE tasks SET downloaded_items = ?, total_items = ? WHERE id = ?",
                    (downloaded, total, task_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating progress for task {task_id}: {e}")

    def delete_task(self, task_id: int):
        """Delete a task and its resources."""
        try:
            with self._get_connection() as conn:
                # Cascade delete resources first (though foreign key might handle it, explicit is safer if not enabled)
                conn.execute("DELETE FROM resources WHERE task_id = ?", (task_id,))
                conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                conn.commit()
            logger.info(f"Deleted task {task_id}")
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")

    def clear_all_tasks(self):
        """Delete all tasks and resources."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM resources")
                conn.execute("DELETE FROM tasks")
                conn.execute("DELETE FROM sqlite_sequence WHERE name='tasks' OR name='resources'")
                conn.commit()
            logger.info("Cleared all history")
        except Exception as e:
            logger.error(f"Error clearing history: {e}")

    def add_resource(self, task_id: int, resource_obj: Any) -> int:
        """
        Add a resource record. 
        resource_obj should be a core.models.Resource instance or similar dict.
        """
        try:
            # Handle both Resource object and dict
            url = getattr(resource_obj, 'url', None) or resource_obj.get('url')
            r_type = getattr(resource_obj, 'resource_type', None) or resource_obj.get('resource_type')
            
            # Simple deduplication check within the same task
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT id FROM resources WHERE task_id = ? AND url = ?",
                    (task_id, url)
                )
                if cursor.fetchone():
                    return -1 # Already exists
                
                cursor = conn.execute(
                    """
                    INSERT INTO resources (task_id, url, resource_type, status)
                    VALUES (?, ?, ?, 'pending')
                    """,
                    (task_id, url, str(r_type))
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding resource: {e}")
            return -1

    def update_resource_status(self, task_id: int, url: str, status: str, local_path: str = None, file_size: int = 0, error: str = None):
        """Update resource status by Task ID and URL."""
        try:
            with self._get_connection() as conn:
                query = "UPDATE resources SET status = ?, updated_at = ?"
                params = [status, datetime.datetime.now()]
                
                if local_path:
                    query += ", local_path = ?"
                    params.append(local_path)
                
                if file_size > 0:
                    query += ", file_size = ?"
                    params.append(file_size)

                if error:
                    query += ", error_msg = ?"
                    params.append(error)
                
                query += " WHERE task_id = ? AND url = ?"
                params.append(task_id)
                params.append(url)
                
                conn.execute(query, tuple(params))
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating resource {url}: {e}")

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks for history view, ordered by latest first."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching tasks: {e}")
            return []

    def get_task_details(self, task_id: int) -> Dict[str, Any]:
        """Get task details along with resource stats."""
        try:
            with self._get_connection() as conn:
                task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
                if not task:
                    return {}
                return dict(task)
        except Exception as e:
            logger.error(f"Error fetching task details: {e}")
            return {}
