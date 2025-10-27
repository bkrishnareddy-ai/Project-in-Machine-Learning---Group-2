# test_vectordb.py

from utils.config import Config
from utils.vector_db_manager import VectorDBManager

# Load configuration  
cfg = Config()
vectordb = VectorDBManager(cfg)

# Add sample data to different memory collections  
vectordb.add_to_memory("cognitive_memories", "User mentioned they feel happy when playing piano.")
vectordb.add_to_memory("personal_facts", "User's daughter studies ballet in grade 3.")
vectordb.add_to_memory("identity_links", "User prefers to be called Tessa.")

# Query from memory
result = vectordb.summarize_search_result("personal_facts", "What does Tessa’s daughter like?")
print("\n--- AI Summary Response ---")
print(result)