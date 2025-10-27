from fastapi import APIRouter, HTTPException
from utils.sql_manager import SQLManager
from utils.user_manager import UserManager
from utils.config import Config

router = APIRouter(prefix="/profile", tags=["Profile"])
cfg = Config()
sql = SQLManager(cfg.db_path)
um = UserManager(sql)

@router.get("/")
def get_profile():
    return um.user_info

@router.post("/set")
def set_profile(data: dict):
    try:
        state, msg = um.add_user_info_to_database(data)
        if not state.startswith("Function call successful"):
            raise ValueError(msg)
        # Return the updated profile
        um.refresh_user_info()
        return {"status": "ok", "profile": um.user_info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
