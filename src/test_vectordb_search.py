# test_vectordb_search.py
from utils.config import Config
from utils.vector_db_manager import VectorDBManager

cfg = Config()
vdb = VectorDBManager(cfg)

# Örnek veri ekle
vdb.add_to_memory("personal_facts", "Tessa’s daughter likes ballet.")

# Arama + özet
state, summary = vdb.search_vector_db(query="What does Tessa's daughter like?", category="personal_facts")
print(state)
print(summary)
