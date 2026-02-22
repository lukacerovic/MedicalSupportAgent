import time
from app.memory.conversation_state import SessionContext

memory_store: dict = {}
SESSION_TTL_SECONDS = 3600  # 1 hour idle expiry


class Memory:

    def init(self, session_id: str):
        memory_store[session_id] = {
            "messages": [],
            "context": SessionContext(),
            "last_active": time.time()
        }

    def _ensure(self, session_id: str):
        if session_id not in memory_store:
            self.init(session_id)

    def _touch(self, session_id: str):
        if session_id in memory_store:
            memory_store[session_id]["last_active"] = time.time()

    def add_message(self, session_id: str, message: dict):
        self._ensure(session_id)
        memory_store[session_id]["messages"].append(message)
        self._touch(session_id)

    def add_messages(self, session_id: str, messages: list[dict]):
        self._ensure(session_id)
        memory_store[session_id]["messages"].extend(messages)
        self._touch(session_id)

    def get(self, session_id: str) -> list[dict]:
        return memory_store.get(session_id, {}).get("messages", [])

    def get_context(self, session_id: str) -> SessionContext:
        self._ensure(session_id)
        return memory_store[session_id]["context"]

    def clear(self, session_id: str):
        if session_id in memory_store:
            memory_store[session_id]["messages"] = []
            memory_store[session_id]["context"] = SessionContext()
            memory_store[session_id]["last_active"] = time.time()

    def cleanup_expired(self):
        """Remove sessions that have been idle longer than SESSION_TTL_SECONDS."""
        now = time.time()
        expired = [
            sid for sid, data in memory_store.items()
            if now - data["last_active"] > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del memory_store[sid]


memory = Memory()
