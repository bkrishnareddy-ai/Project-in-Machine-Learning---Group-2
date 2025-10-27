# src/routers/dashboard_router.py
from fastapi import APIRouter
from utils.sql_manager import SQLManager
from utils.user_manager import UserManager
from services.reminder_service import ReminderService
from utils.config import Config

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

def _deps():
    cfg = Config()
    sql = SQLManager(cfg.db_path)
    user = UserManager(sql)
    return sql, user

@router.get("/summary")
def dashboard_summary():
    sql, user = _deps()

    # Reminder metrics
    reminder_svc = ReminderService(sql, user.user_id)
    reminder_stats = reminder_svc.count_by_status()

    # Chat mesaj counts  
    chat_count = 0
    if hasattr(sql, "conn"):
        try:
            row = sql.conn.execute(
                "SELECT COUNT(*) FROM chat_history WHERE user_id=?", (user.user_id,)
            ).fetchone()
            chat_count = row[0] if row else 0
        except Exception:
            chat_count = 0

    return {
        "user_id": user.user_id,
        "reminders": reminder_stats,  # {pending, done, canceled, total}
        "chat_messages_total": chat_count,
        "notes": "Extend with more KPIs (e.g., latency, uptime, hallucination rate)."
    }
