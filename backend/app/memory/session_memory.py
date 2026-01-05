memory_store = {}

class Memory:
    def init(self, session_id: str):
        memory_store[session_id] = []

    def add_user(self, session_id: str, text: str):
        memory_store[session_id].append(text)

    def add_ai(self, session_id: str, text: str):
        memory_store[session_id].append(text)

    def get(self, session_id: str):
        return memory_store.get(session_id, [])

memory = Memory()
