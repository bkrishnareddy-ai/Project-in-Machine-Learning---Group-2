from utils.sql_manager import SQLManager
from utils.user_manager import UserManager
from utils.config import Config

class ProfileService:
    def __init__(self):
        cfg = Config()
        self.sql = SQLManager(cfg.db_path)
        self.um = UserManager(self.sql)

    def get_profile(self):
        return self.um.user_info

    def update_profile(self, data: dict):
        return self.um.add_user_info_to_database(data)
