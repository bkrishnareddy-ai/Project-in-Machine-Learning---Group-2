# src/utils/sql_manager.py
import sqlite3
from pathlib import Path


class SQLManager:
    """
    Manages a single SQLite connection for the MemoriAI Cognitive Service
    and ensures required tables exist.
    """

    def __init__(self, db_path: str):
        """
        Initialize SQLManager and ensure the database/schema exist.

        Args:
            db_path (str): Absolute path to the SQLite database file.
        """
        self.db_path = db_path

        # Ensure the folder for the DB file exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # One persistent connection for the whole app
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.execute("PRAGMA journal_mode = WAL;")

        # ORDER MATTERS
        self.ensure_base_tables()        # 1) user_info + chat_history
        self.ensure_summary_table()      # 2) summary (rolling chat summaries)
        self.ensure_reminders_table()    # 3) reminders
        self.ensure_default_user()       # 4) seed a minimal user if table is empty

    # --- Schema creation ---

    def ensure_base_tables(self):
        """Create user_info and chat_history tables if they don't exist."""
        cur = self.conn.cursor()

        # Main user table (expected by UserManager)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                last_name TEXT,
                age INTEGER,
                gender TEXT,
                location TEXT,
                occupation TEXT,
                interests TEXT,                -- JSON string (or CSV) is fine
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Chat history linked to user_info
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_message TEXT,
                assistant_message TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_info(id)
            );
        """)

        self.conn.commit()

    def ensure_summary_table(self):
        """
        Create summary table for rolling conversation summaries.

        IMPORTANT: ChatHistoryManager expects columns:
          - summary_text (TEXT)
          - timestamp (TEXT, default CURRENT_TIMESTAMP)
        """
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT,
                summary_text TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_info(id)
            );
        """)
        # Helpful index for "latest summary"
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_summary_user_time
            ON summary (user_id, timestamp);
        """)
        self.conn.commit()

    def ensure_reminders_table(self):
        """Create reminders table if it doesn't exist."""
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                title TEXT NOT NULL,
                due_at TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_info(id)
            );
        """)
        self.conn.commit()

    def ensure_default_user(self):
        """
        Seed one default user if user_info is empty.
        Keeps the app working out-of-the-box for demos/tests.
        """
        cur = self.conn.cursor()
        row = cur.execute("SELECT id FROM user_info LIMIT 1").fetchone()
        if not row:
            cur.execute("""
                INSERT INTO user_info (name, last_name, age, gender, location, occupation, interests)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("Tessa", "", None, None, "Waterloo", "Student", '["AI","ML"]'))
            self.conn.commit()

    # --- Query helper ---

    def execute_query(self, query: str, params: tuple = (), *, fetch_one: bool = False, fetch_all: bool = False):
        """
        Execute a query and optionally return one/all rows.

        Args:
            query: SQL query string with placeholders.
            params: Parameters tuple for the SQL query.
            fetch_one: If True, return a single row (or None).
            fetch_all: If True, return a list of rows (possibly empty).

        Returns:
            A single row (tuple) if fetch_one, a list[tuple] if fetch_all, or None.
        """
        cur = self.conn.cursor()
        cur.execute(query, params)
        result = None
        if fetch_one:
            result = cur.fetchone()
        elif fetch_all:
            result = cur.fetchall()
        self.conn.commit()
        return result

    def __del__(self):
        try:
            self.conn.close()
        except Exception:
            pass
