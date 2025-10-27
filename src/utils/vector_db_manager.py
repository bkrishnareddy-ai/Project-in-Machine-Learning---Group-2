import os
import uuid
import chromadb
from openai import OpenAI
from chromadb.utils import embedding_functions
from utils.config import Config
from utils.prepare_system_prompt import prepare_system_prompt_for_rag_chatbot


def _make_embedding_fn(cfg: Config | None = None):
    """
    EMBEDDINGS_PROVIDER:
      - 'local'  -> SentenceTransformer (offline, free)
          SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
      - 'openai' -> OpenAI embeddings (paid / online veya OpenAI-compatible)
          OPENAI_EMBEDDING_MODEL=text-embedding-3-small
          OPENAI_API_KEY=...
          OPENAI_BASE_URL=...   # can also be used for LM Studio / Ollama
    """
    provider = os.getenv("EMBEDDINGS_PROVIDER", "local").lower()
    if provider == "openai":
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=os.getenv("OPENAI_EMBEDDING_MODEL", (getattr(cfg, "embedding_model", None) or "text-embedding-3-small")),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )
    # Default: local embedding (offline, no usage limits)
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
    )


class VectorDBManager:
    def __init__(self, config: Config):
        """
        VectorDBManager for MemoriAI Cognitive Service.
        Manages multiple memory collections: cognitive, identity, personal facts.
        """
        self.cfg = config

        # ✅ Embedding provider depends on configuration
        self.embedding_function = _make_embedding_fn(self.cfg)

        # ✅ Vector database client (persistent)
        self.db_client = chromadb.PersistentClient(path=str(self.cfg.vectordb_dir))

        # ✅ Supports multiple collections
        self.collections = {
            "cognitive_memories": self.db_client.get_or_create_collection(
                name=self.cfg.collections["cognitive_memories"],
                embedding_function=self.embedding_function
            ),
            "identity_links": self.db_client.get_or_create_collection(
                name=self.cfg.collections["identity_links"],
                embedding_function=self.embedding_function
            ),
            "personal_facts": self.db_client.get_or_create_collection(
                name=self.cfg.collections["personal_facts"],
                embedding_function=self.embedding_function
            )
        }

        # ✅ LLM client (opsiyonel). OPENAI_DISABLED=true ise None.
        openai_disabled = os.getenv("OPENAI_DISABLED", "false").lower() in ("1", "true", "yes")
        if openai_disabled:
            self.client = None
        else:
            self.client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY") or None,
                base_url=os.getenv("OPENAI_BASE_URL") or None,
            )

        self.system_prompt = prepare_system_prompt_for_rag_chatbot()

    # ---------------------------
    # Core vector operations
    # ---------------------------
    def add_to_memory(self, category: str, content: str):
        """Adds content to one of the cognitive collections."""
        if category not in self.collections:
            raise ValueError(f"Invalid memory category: {category}")
        self.collections[category].add(
            ids=[str(uuid.uuid4())],
            documents=[content]
        )
        print(f"✅ Added to {category}: {content[:60]}")

    def search_memory(self, category: str, query: str):
        """Searches a specific memory category for relevant entries."""
        if category not in self.collections:
            raise ValueError(f"Invalid memory category: {category}")
        results = self.collections[category].query(
            query_texts=[query],
            n_results=self.cfg.k
        )
        return results["documents"][0] if results and results.get("documents") else []

    # ---------------------------
    # High-level helpers (FC/RAG)
    # ---------------------------
    def search_vector_db(self, query: str, category: str = "cognitive_memories") -> tuple[str, str]:
        """
        Function-calling için semantik arama + LLM ile özetleme (varsa).
        Returns: (status, text)
        """
        try:
            docs = self.search_memory(category, query)
            llm_result = self.prepare_search_result(docs, query)
            return "Function call successful.", llm_result
        except Exception as e:
            return "Function call failed.", f"Error: {e}"

    def summarize_search_result(self, category: str, query: str):
        """Uses the LLM to summarize the search result (LLM yoksa graceful fallback)."""
        docs = self.search_memory(category, query)
        input_text = (
            "## Memory Category: {cat}\n"
            "## Search Results:\n{docs}\n"
            "## Query:\n{q}\n"
        ).format(cat=category, docs="\n".join(docs) if isinstance(docs, list) else str(docs), q=query)

        # If the LLM is disabled, return a simple fallback
        if self.client is None:
            return f"[LLM disabled] Top-{self.cfg.k} results for '{query}' in '{category}':\n{input_text}"

        response = self.client.chat.completions.create(
            model=self.cfg.rag_model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": input_text}
            ]
        )
        return response.choices[0].message.content

    # ---------------------------
    # Internal: how to post-process docs
    # ---------------------------
    def prepare_search_result(self, docs, query: str) -> str:
        """
        Arama sonuçlarını LLM'e göndermeden önce minimal biçimde toparlar.
        LLM kapalıysa basit bir metin döndürür.
        """
        if not docs:
            return f"No relevant memories found for: {query}"

        preview = docs if isinstance(docs, list) else [str(docs)]
        preview_text = "\n- " + "\n- ".join(d[:280] for d in preview)  # Short preview output
        if self.client is None:
            return f"[LLM disabled] Query: {query}\nTop-{self.cfg.k} snippets:{preview_text}"

        # If LLM is available, use summarize_search_result for a smarter summary
        return self.summarize_search_result("cognitive_memories", query)
