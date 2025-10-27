# src/services/reminder_service.py
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from utils.sql_manager import SQLManager

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

class ReminderService:
    def __init__(self, sql: SQLManager, user_id: int):
        self.sql = sql
        self.user_id = user_id
        if hasattr(self.sql, "ensure_reminders_table"):
            self.sql.ensure_reminders_table()

    def create(self, title: str, due_at: Optional[str]) -> int:
        created = now_iso()
        updated = created
        cur = self.sql.conn.execute(
            "INSERT INTO reminders(user_id, title, due_at, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (self.user_id, title, due_at, "pending", created, updated)
        )
        self.sql.conn.commit()
        return cur.lastrowid

    def list(self, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> Tuple[List[dict], int]:
        params = [self.user_id]
        where = "WHERE user_id = ?"
        if status:
            where += " AND status = ?"
            params.append(status)

        count_row = self.sql.conn.execute(f"SELECT COUNT(*) FROM reminders {where}", params).fetchone()
        total = count_row[0] if count_row else 0

        params += [limit, offset]
        rows = self.sql.conn.execute(
            f"""
            SELECT id, user_id, title, due_at, status, created_at, updated_at
            FROM reminders
            {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            params
        ).fetchall()

        items = [dict(zip(["id","user_id","title","due_at","status","created_at","updated_at"], r)) for r in rows]
        return items, total

    def update_status(self, reminder_id: int, status: str) -> bool:
        updated = now_iso()
        res = self.sql.conn.execute(
            "UPDATE reminders SET status=?, updated_at=? WHERE id=? AND user_id=?",
            (status, updated, reminder_id, self.user_id)
        )
        self.sql.conn.commit()
        return res.rowcount > 0

    def count_by_status(self) -> dict:
        stats = {}
        for s in ["pending", "done", "canceled"]:
            row = self.sql.conn.execute(
                "SELECT COUNT(*) FROM reminders WHERE user_id=? AND status=?",
                (self.user_id, s)
            ).fetchone()
            stats[s] = row[0] if row else 0
        total_row = self.sql.conn.execute(
            "SELECT COUNT(*) FROM reminders WHERE user_id=?",
            (self.user_id,)
        ).fetchone()
        stats["total"] = total_row[0] if total_row else 0
        return stats
