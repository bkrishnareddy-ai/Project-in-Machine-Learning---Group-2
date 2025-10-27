# src/utils/user_manager.py
import math
from typing import Optional, Dict, Any, Tuple
from utils.sql_manager import SQLManager


class UserManager:
    """
    Manages user-related operations: reading/updating the single demo user's profile.
    """

    def __init__(self, sql_manager: SQLManager):
        self.sql_manager = sql_manager
        self.user_id = self.get_user_id()
        self.user_info = self.get_user_info()

    # ---------- reads ----------

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve user info with correct field order matching the DB schema:
        id, name, last_name, age, gender, location, occupation, interests
        """
        row = self.sql_manager.execute_query(
            """
            SELECT id, name, last_name, age, gender, location, occupation, interests
            FROM user_info
            WHERE id = (SELECT id FROM user_info LIMIT 1)
            """,
            fetch_one=True,
        )
        if not row:
            return None

        (uid, name, last_name, age, gender, location, occupation, interests) = row
        user_info = {
            "id": uid,
            "name": name,
            "last_name": last_name,
            "age": age,
            "gender": gender,
            "location": location,
            "occupation": occupation,
            "interests": interests,
        }
        # filter out empty/None/NaN
        return {
            k: v
            for k, v in user_info.items()
            if v not in (None, "")
            and not (isinstance(v, float) and math.isnan(v))
        }

    def refresh_user_info(self):
        self.user_info = self.get_user_info()

    def get_user_id(self) -> Optional[int]:
        row = self.sql_manager.execute_query(
            "SELECT id FROM user_info LIMIT 1;", fetch_one=True
        )
        return row[0] if row else None

    # ---------- writes ----------

    def add_user_info_to_database(self, user_info: dict) -> Tuple[str, str]:
        """
        Update user_info with provided keys. Merges 'interests' if present.
        Valid keys: name, last_name, age, gender, location, occupation, interests
        """
        try:
            valid_keys = {
                "name", "last_name", "age", "gender",
                "location", "occupation", "interests"
            }

            # validate keys
            for k in user_info.keys():
                if k not in valid_keys:
                    return (
                        "Function call failed.",
                        "Please provide a valid key from: name, last_name, age, gender, location, occupation, interests",
                    )

            processed = dict(user_info)

            # merge interests if provided
            if "interests" in processed:
                new_interests: list[str] = []
                src = processed["interests"]
                if isinstance(src, list):
                    new_interests = [s.strip() for s in src if isinstance(s, str)]
                elif isinstance(src, str):
                    new_interests = [s.strip() for s in src.split(",") if s.strip()]

                # get existing interests
                row = self.sql_manager.execute_query(
                    "SELECT interests FROM user_info LIMIT 1;",
                    fetch_one=True,
                )
                existing: list[str] = []
                if row and row[0]:
                    existing = [s.strip() for s in str(row[0]).split(",") if s.strip()]

                merged = sorted(set(existing + new_interests))
                processed["interests"] = ", ".join(merged)

            if not processed:
                return "Function call failed.", "No valid fields provided."

            # build SET clause
            sets = [f"{k} = ?" for k in processed.keys()]
            params = tuple(processed.values())

            self.sql_manager.execute_query(
                f"""
                UPDATE user_info
                SET {', '.join(sets)}
                WHERE id = (SELECT id FROM user_info LIMIT 1);
                """,
                params=params,
            )
            # refresh & return
            self.refresh_user_info()
            return "Function call successful.", f"Profile updated: {self.user_info}"
        except Exception as e:
            return "Function call failed.", f"Error: {e}"
