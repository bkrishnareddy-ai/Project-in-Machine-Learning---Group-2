import os
import uuid
import json
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIStatusError, APIConnectionError, AuthenticationError
from traceback import format_exc

from utils.sql_manager import SQLManager
from utils.user_manager import UserManager
from utils.chat_history_manager import ChatHistoryManager
from utils.search_manager import SearchManager
from utils.prepare_system_prompt import prepare_system_prompt_for_agentic_chatbot_v3
from utils.utils import Utils
from utils.config import Config
from utils.vector_db_manager import VectorDBManager

load_dotenv()


class Chatbot:
    """
    Agentic v3 chatbot:
      - Function calling (search_vector_db, add_user_info_to_database)
      - Robust error handling + fallback model
      - Optional mock mode for offline demos (USE_MOCK_LLM=true)
    """

    def __init__(self):
        # --- Config & clients
        self.cfg = Config()
        self.chat_model = self.cfg.chat_model
        self.summary_model = self.cfg.summary_model
        self.temperature = self.cfg.temperature
        self.max_history_pairs = self.cfg.max_history_pairs

        # Fallback model if primary fails (safe defaults if not in YAML)
        self.fallback_model = getattr(self.cfg, "fallback_model", "gpt-4o-mini")

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # --- Infra
        self.session_id = str(uuid.uuid4())
        self.utils = Utils()
        self.sql_manager = SQLManager(self.cfg.db_path)
        self.user_manager = UserManager(self.sql_manager)
        self.chat_history_manager = ChatHistoryManager(
            self.sql_manager,
            self.user_manager.user_id,
            self.session_id,
            self.client,
            self.summary_model,
            self.cfg.max_tokens,
        )
        self.vector_db_manager = VectorDBManager(self.cfg)
        self.search_manager = SearchManager(
            self.sql_manager, self.utils, self.client, self.summary_model, self.cfg.max_characters
        )

        # Expose tools to the LLM
        self.agent_functions = [
            self.utils.jsonschema(self.user_manager.add_user_info_to_database),
            self.utils.jsonschema(self.vector_db_manager.search_vector_db),
        ]

        # Mock mode flag (lets you demo without API calls)
        self.use_mock = os.getenv("USE_MOCK_LLM", "").lower() == "true"

    # -------------------- internal helpers --------------------

    def _persist_to_vectordb(self, user_message: str, assistant_response: str):
        """Store the exchange in a collection, but don't crash on failure."""
        try:
            msg_pair = f"user: {user_message}, assistant: {assistant_response}"
            if hasattr(self.vector_db_manager, "update_vector_db"):
                self.vector_db_manager.update_vector_db(msg_pair, category="cognitive_memories")
            elif hasattr(self.vector_db_manager, "add_to_memory"):
                self.vector_db_manager.add_to_memory("cognitive_memories", msg_pair)
            if hasattr(self.vector_db_manager, "refresh_vector_db_client"):
                self.vector_db_manager.refresh_vector_db_client()
        except Exception:
            # best-effort; keep chat flowing
            pass

    def _safe_llm_call(self, messages, functions=None, function_call="auto"):
        """
        Call primary model; on error, try fallback; on repeated failure, return (None, error_text).
        Returns tuple: (openai_response, error_text)
        """
        try:
            resp = self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                functions=functions,
                function_call=function_call,
                temperature=self.temperature,
            )
            return resp, None

        except RateLimitError as e:
            # try fallback model once
            try:
                resp = self.client.chat.completions.create(
                    model=self.fallback_model,
                    messages=messages,
                    functions=functions,
                    function_call=function_call,
                    temperature=self.temperature,
                )
                return resp, None
            except Exception as e2:
                return None, f"Rate limit / quota issue. Fallback also failed: {e2}"

        except (APIConnectionError, APIStatusError, AuthenticationError) as e:
            return None, f"LLM call failed: {e}"

        except Exception as e:
            return None, f"Unexpected LLM error: {e}"
         
        # ---------------------two helper functions + calls at the beginning of chat()-----------------------
    def recall_user_fact(self, question: str):
        q = (question or "").lower()
        info = self.user_manager.user_info or {}

        # 1) Recall from SQL profile
        if ("where do i live" in q) or ("where am i from" in q):
            loc = info.get("location")
            if loc:
                return f"You live in {loc}."
        if ("what is my name" in q) or ("who am i" in q):
            name = info.get("name")
            if name:
                return f"Your name is {name}."
        if ("what do i do" in q) or ("my occupation" in q):
            occ = info.get("occupation")
            if occ:
                return f"You work as {occ}."

        # 2) Vector memory (as backup)
        try:
            if hasattr(self.vector_db_manager, "search_vector_db"):
                state, ans = self.vector_db_manager.search_vector_db(
                    query=question, category="identity_links"
                )
                if str(state).startswith("Function call successful") and ans:
                    return ans
        except Exception:
            pass

        return None

    # ------------------------ public API ------------------------

    def execute_function_call(self, function_name: str, function_args: dict) -> tuple[str, str]:
        """Dispatch function calls requested by the LLM."""
        if function_name == "search_vector_db":
            return self.vector_db_manager.search_vector_db(**function_args)
        elif function_name == "add_user_info_to_database":
            return self.user_manager.add_user_info_to_database(function_args)
        return "Function call failed.", f"Unknown function '{function_name}'"

    def chat(self, user_message: str) -> str:
        """
        Main conversational loop (single-turn for terminal UI).
        Returns the assistant's reply (never raises).
        """
        if self.use_mock:
            mock = f"(mock) I heard: {user_message}. I'll remember this context."
            try:
                self.chat_history_manager.add_to_history(user_message, mock, self.max_history_pairs)
            except Exception:
                pass
            self._persist_to_vectordb(user_message, mock)
            return mock
            # ALWAYS pull fresh profile (profile may have been updated via /profile/set)
        self.user_manager.refresh_user_info()
        print("DEBUG user_info:", self.user_manager.user_info)

            # --- capture and store personal facts ---
        self.catch_and_store_personal_facts(user_message)

        # --- check if we already have any user information, and return it ---
        recall = self.recall_user_fact(user_message)
        if recall:
            try:
                self.chat_history_manager.add_to_history(user_message, recall, self.max_history_pairs)
            except Exception:
                pass
            if hasattr(self.vector_db_manager, "add_to_memory"):
                self.vector_db_manager.add_to_memory(
                "cognitive_memories", f"user: {user_message} | assistant: {recall}"
                )
            return recall
        
        function_call_result_section = ""
        function_call_state = None
        chat_state = "thinking"
        function_call_count = 0
        
        # Pull summary and rolling history safely
        try:
            self.chat_history = self.chat_history_manager.chat_history
            self.previous_summary = self.chat_history_manager.get_latest_summary()
        except Exception:
            self.chat_history = []
            self.previous_summary = None

        while chat_state != "finished":
            try:
                # If we just executed a function, include the trace for the model
                if function_call_state == "Function call successful.":
                    chat_state = "finished"
                    if function_name == "add_user_info_to_database":
                        self.user_manager.refresh_user_info()
                    function_call_result_section = (
                        "## Function Call Executed\n\n"
                        f"- name: `{function_name}`\n"
                        f"- args:\n" + "".join([f"  - {k}: {v}\n" for k, v in function_args.items()]) +
                        f"- outcome: ✅ {function_call_state}\n\n"
                        f"{function_call_result}"
                    )
                elif function_call_state == "Function call failed.":
                    function_call_result_section = (
                        "## Function Call Attempted\n\n"
                        f"- name: `{function_name}`\n"
                        f"- args:\n" + "".join([f"  - {k}: {v}\n" for k, v in function_args.items()]) +
                        f"- outcome: ❌ {function_call_state} - {function_call_result}\n\n"
                        "Please continue helping the user with the available context."
                    )

                if function_call_count >= self.cfg.max_function_calls:
                    function_call_result_section = (
                        "# Function Call Limit Reached.\n"
                        "Please conclude the conversation with the available information."
                    )

                system_prompt = prepare_system_prompt_for_agentic_chatbot_v3(
                    self.user_manager.user_info,
                    self.previous_summary,
                    self.chat_history,
                    function_call_result_section,
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ]

                # Call LLM (with fallback & error text)
                response, llm_error = self._safe_llm_call(messages, functions=self.agent_functions, function_call="auto")
                if llm_error:
                    # Graceful fallback text
                    assistant_response = (
                        "I'm having trouble reaching the language model right now. "
                        "Based on what you said, here's a brief response for now:\n\n"
                        f"- You said: “{user_message}”. I'll keep this in mind for continuity."
                    )
                    try:
                        self.chat_history_manager.add_to_history(user_message, assistant_response, self.max_history_pairs)
                        self.chat_history_manager.update_chat_summary(self.max_history_pairs)
                    except Exception:
                        pass
                    self._persist_to_vectordb(user_message, assistant_response)
                    return assistant_response

                choice = response.choices[0].message

                # If the model returned a normal message
                if choice.content:
                    assistant_response = choice.content
                    try:
                        self.chat_history_manager.add_to_history(
                            user_message, assistant_response, self.max_history_pairs
                        )
                        self.chat_history_manager.update_chat_summary(self.max_history_pairs)
                    except Exception:
                        pass

                    chat_state = "finished"
                    self._persist_to_vectordb(user_message, assistant_response)
                    function_call_state = None
                    return assistant_response

                # If the model wants to call a function
                elif choice.function_call:
                    if function_call_count >= self.cfg.max_function_calls or chat_state == "finished":
                        # fallback to a plain completion
                        fallback_resp, _ = self._safe_llm_call(
                            messages=[{"role": "system", "content": system_prompt},
                                      {"role": "user", "content": user_message}],
                            functions=None,
                            function_call="none",
                        )
                        assistant_response = fallback_resp.choices[0].message.content
                        try:
                            self.chat_history_manager.add_to_history(
                                user_message, assistant_response, self.max_history_pairs
                            )
                        except Exception:
                            pass
                        self._persist_to_vectordb(user_message, assistant_response)
                        function_call_state = None
                        return assistant_response

                    function_call_count += 1
                    function_name = choice.function_call.name
                    function_args = json.loads(choice.function_call.arguments or "{}")
                    function_call_state, function_call_result = self.execute_function_call(function_name, function_args)

                else:
                    return "Warning: No valid assistant response from the chatbot. Please try again."

            except Exception as e:
                # Never explode to the terminal
                return f"Error: {str(e)}\n{format_exc()}"
            
    def catch_and_store_personal_facts(self, text: str):
        t = (text or "").lower()

        # Name
        if "my name is" in t:
            name = text.split("my name is")[-1].strip().split()[0]
            self.user_manager.add_user_info_to_database({"name": name})
            if hasattr(self.vector_db_manager, "add_to_memory"):
                self.vector_db_manager.add_to_memory("identity_links", f"User’s name is {name}.")

        # Location
        for k in ["i live in", "i am from"]:
            if k in t:
                loc = text.lower().split(k)[-1].split(".")[0].strip()
                if loc:
                    self.user_manager.add_user_info_to_database({"location": loc})
                    if hasattr(self.vector_db_manager, "add_to_memory"):
                        self.vector_db_manager.add_to_memory("identity_links", f"User lives in {loc}.")
                break

        # Profession
        if "i work as" in t:
            occ = text.lower().split("i work as")[-1].split(".")[0].strip()
            if occ:
                self.user_manager.add_user_info_to_database({"occupation": occ})
                if hasattr(self.vector_db_manager, "add_to_memory"):
                    self.vector_db_manager.add_to_memory("identity_links", f"User occupation: {occ}")        
