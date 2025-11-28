import os
import json
from typing import List, Optional
from google.adk.sessions import BaseSessionService, Session
from google.genai.types import Content, Part

class FileSessionService(BaseSessionService):
    def __init__(self, storage_dir="sessions"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def _get_file_path(self, session_id: str) -> str:
        # Sanitize session_id to be a valid filename
        safe_id = "".join([c for c in session_id if c.isalnum() or c in ('-', '_')]).strip()
        return os.path.join(self.storage_dir, f"{safe_id}.json")

    async def create_session(self, app_name: str, user_id: str, session_id: str) -> Session:
        session = Session(app_name=app_name, user_id=user_id, session_id=session_id, history=[])
        self._save_session(session)
        return session

    async def get_session(self, app_name: str, user_id: str, session_id: str) -> Session:
        file_path = self._get_file_path(session_id)
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
                # Reconstruct Content objects from JSON data
                history = []
                for item in data.get("history", []):
                    parts = [Part(text=p.get("text", "")) for p in item.get("parts", [])]
                    history.append(Content(role=item.get("role"), parts=parts))
                
                return Session(app_name=app_name, user_id=user_id, session_id=session_id, history=history)
        raise Exception(f"Session {session_id} not found")

    async def delete_session(self, app_name: str, user_id: str, session_id: str) -> None:
        file_path = self._get_file_path(session_id)
        if os.path.exists(file_path):
            os.remove(file_path)

    async def update_session(self, session: Session) -> None:
        self._save_session(session)

    async def list_sessions(self, app_name: str, user_id: str) -> List[Session]:
        """List all sessions for a given app and user."""
        sessions = []
        if os.path.exists(self.storage_dir):
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.storage_dir, filename)
                    try:
                        with open(file_path, "r") as f:
                            data = json.load(f)
                            if data.get("app_name") == app_name and data.get("user_id") == user_id:
                                history = []
                                for item in data.get("history", []):
                                    parts = [Part(text=p.get("text", "")) for p in item.get("parts", [])]
                                    history.append(Content(role=item.get("role"), parts=parts))
                                
                                session = Session(app_name=app_name, user_id=user_id, 
                                                session_id=data.get("session_id"), history=history)
                                sessions.append(session)
                    except (json.JSONDecodeError, KeyError):
                        pass
        return sessions

    def _save_session(self, session: Session):
        file_path = self._get_file_path(session.session_id)
        # Serialize Content objects to JSON-serializable format
        history_data = []
        for content in session.history:
            parts_data = [{"text": p.text} for p in content.parts]
            history_data.append({"role": content.role, "parts": parts_data})
            
        data = {
            "app_name": session.app_name,
            "user_id": session.user_id,
            "session_id": session.session_id,
            "history": history_data
        }
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
