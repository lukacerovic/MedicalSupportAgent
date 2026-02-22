memory_store = {}

class Memory:
    def init(self, session_id: str):
        memory_store[session_id] = []

    def add_message(self, session_id: str, message: dict):
        if session_id not in memory_store:
            self.init(session_id)
        memory_store[session_id].append(message)

    def add_messages(self, session_id: str, messages: list[dict]):
        if session_id not in memory_store:
            self.init(session_id)
        memory_store[session_id].extend(messages)

    def get(self, session_id: str) -> list[dict]:
        return memory_store.get(session_id, [])

    def clear(self, session_id: str):
        if session_id in memory_store:
            memory_store[session_id] = []

memory = Memory()
