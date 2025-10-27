from pathlib import Path
from yaml import load, Loader

class Config:
    def __init__(self):
        # 📂 Automatically detect the project root (src folder)
        SRC_DIR = Path(__file__).resolve().parents[1]
        CONFIG_PATH = SRC_DIR / "config" / "config.yml"

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = load(f, Loader=Loader)

        # 🔹 Directories
        # Convert to absolute paths to avoid “unable to open database” errors
        self.db_path = str((SRC_DIR / config["directories"]["db_path"]).resolve())
        self.vectordb_dir = str((SRC_DIR / config["directories"]["vectordb_dir"]).resolve())

        # 🔹 LLM Configuration
        self.chat_model = config["llm_config"]["chat_model"]
        self.summary_model = config["llm_config"]["summary_model"]
        self.rag_model = config["llm_config"]["rag_model"]
        self.temperature = config["llm_config"]["temperature"]

        # 🔹 Chat History Configuration
        self.max_history_pairs = config["chat_history_config"]["max_history_pairs"]
        self.max_characters = config["chat_history_config"]["max_characters"]
        self.max_tokens = config["chat_history_config"]["max_tokens"]

        # 🔹 Agent Configuration
        self.max_function_calls = config["agent_config"]["max_function_calls"]

        # 🔹 VectorDB Configuration
        self.collections = config["vectordb_config"]["collections"]
        self.embedding_model = config["vectordb_config"]["embedding_model"]
        self.k = config["vectordb_config"]["k"]
